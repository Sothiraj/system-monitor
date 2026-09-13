/* System Monitor Dashboard — real-data polling client.
 *
 * - Fetches relative /api/v1/stats (works on localhost, preview URLs, Render).
 * - Preloads /api/v1/history so charts are populated instantly.
 * - Exponential backoff on errors, pause/resume, interval control.
 * - No synthetic fluctuation: every point shown is a real server sample.
 */
(() => {
  'use strict';

  const cfg = window.DASHBOARD_CONFIG || {};
  const STATS_URL = cfg.statsUrl || '/api/v1/stats';
  const HISTORY_URL = cfg.historyUrl || '/api/v1/history?limit=60';
  const THRESHOLDS = cfg.thresholds || { cpu: 85, ram: 90, disk: 90 };
  const MAX_POINTS = cfg.maxPoints || 60;

  const $ = (id) => document.getElementById(id);
  const els = {
    hostname: $('hostname'), platform: $('platform'), uptime: $('uptime'),
    statusDot: $('statusDot'), lastUpdated: $('lastUpdated'),
    intervalSelect: $('intervalSelect'), pauseBtn: $('pauseBtn'), themeBtn: $('themeBtn'),
    alertBanner: $('alertBanner'),
    cpuValue: $('cpuValue'), cpuBar: $('cpuBar'), cpuSub: $('cpuSub'),
    ramValue: $('ramValue'), ramBar: $('ramBar'), ramSub: $('ramSub'),
    diskValue: $('diskValue'), diskBar: $('diskBar'), diskSub: $('diskSub'),
    netValue: $('netValue'), netDown: $('netDown'), netUp: $('netUp'), netSub: $('netSub'),
    bootTime: $('bootTime'), procCount: $('procCount'), cpuCores: $('cpuCores'),
    loadAvg: $('loadAvg'), cpuFreq: $('cpuFreq'), pyVersion: $('pyVersion'),
    errorToast: $('errorToast'), errorToastBody: $('errorToastBody'),
  };

  const state = {
    timer: null,
    intervalMs: parseInt(els.intervalSelect.value, 10) || 2000,
    paused: false,
    failures: 0,
    retryDelayMs: 2000,
  };

  // ---------------------------------------------------------------- charts --
  const gridColor = () => getComputedStyle(document.documentElement)
    .getPropertyValue('--card-border').trim() || '#263049';
  const tickColor = () => getComputedStyle(document.documentElement)
    .getPropertyValue('--muted').trim() || '#9aa5bd';

  function baseOptions({ min = 0, max = 100, unit = '%' } = {}) {
    return {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: tickColor(), boxWidth: 12 } } },
      scales: {
        x: { ticks: { display: false, maxTicksLimit: 8 }, grid: { color: gridColor() } },
        y: {
          min, max,
          ticks: { color: tickColor(), maxTicksLimit: 5 },
          grid: { color: gridColor() },
          title: { display: true, text: unit, color: tickColor() },
        },
      },
    };
  }

  function makeChart(id, datasets, opts) {
    const ctx = $(id).getContext('2d');
    return new Chart(ctx, { type: 'line', data: { labels: [], datasets }, options: opts });
  }

  const ds = (label, color) => ({
    label, data: [], borderColor: color, backgroundColor: color + '22',
    borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 0,
  });

  const cpuChart = makeChart('cpuChart', [ds('CPU %', '#ef4444')], baseOptions({}));
  const ramChart = makeChart('ramChart', [ds('RAM %', '#22c55e')], baseOptions({}));
  const diskChart = makeChart('diskChart', [ds('Disk %', '#f59e0b')], baseOptions({}));
  const netChart = makeChart('netChart',
    [ds('↓ down KB/s', '#38bdf8'), ds('↑ up KB/s', '#a78bfa')],
    baseOptions({ min: 0, max: undefined, unit: 'KB/s' }));
  delete netChart.options.scales.y.max; // autoscale throughput

  function pushPoint(chart, label, values) {
    chart.data.labels.push(label);
    values.forEach((v, i) => chart.data.datasets[i].data.push(v));
    while (chart.data.labels.length > MAX_POINTS) {
      chart.data.labels.shift();
      chart.data.datasets.forEach((d) => d.data.shift());
    }
    chart.update('none');
  }

  function setBar(barEl, pct) {
    const v = Math.max(0, Math.min(100, pct));
    barEl.style.width = v.toFixed(1) + '%';
    barEl.setAttribute('aria-valuenow', v.toFixed(1));
    barEl.classList.toggle('bar-warn', v >= 70 && v < 90);
    barEl.classList.toggle('bar-danger', v >= 90);
  }

  // ---------------------------------------------------------------- format --
  const fmtTime = (iso) => {
    try { return new Date(iso).toLocaleTimeString(); } catch { return ''; }
  };

  // ---------------------------------------------------------------- update --
  function setStatus(mode) {
    els.statusDot.className = 'status-dot ' + (
      mode === 'ok' ? 'status-ok' :
      mode === 'warn' ? 'status-warn' :
      mode === 'err' ? 'status-err' : 'status-paused');
  }

  function showError(msg) {
    els.errorToastBody.textContent = msg;
    if (window.bootstrap) {
      bootstrap.Toast.getOrCreateInstance(els.errorToast, { delay: 4000 }).show();
    }
  }

  function checkAlerts(d) {
    const hits = [];
    if (d.cpu >= THRESHOLDS.cpu) hits.push(`CPU ${d.cpu}% ≥ ${THRESHOLDS.cpu}%`);
    if (d.ram >= THRESHOLDS.ram) hits.push(`RAM ${d.ram}% ≥ ${THRESHOLDS.ram}%`);
    if (d.disk >= THRESHOLDS.disk) hits.push(`Disk ${d.disk}% ≥ ${THRESHOLDS.disk}%`);
    if (hits.length) {
      els.alertBanner.textContent = '⚠ High usage: ' + hits.join(' · ');
      els.alertBanner.classList.remove('d-none');
    } else {
      els.alertBanner.classList.add('d-none');
    }
  }

  function render(d) {
    const label = fmtTime(d.timestamp) || new Date().toLocaleTimeString();
    els.hostname.textContent = d.hostname ?? '—';
    els.platform.textContent = d.platform ?? '—';
    els.uptime.textContent = d.uptime_human ?? '—';
    els.lastUpdated.textContent = 'updated ' + label;

    els.cpuValue.textContent = (d.cpu ?? 0).toFixed(1) + '%';
    setBar(els.cpuBar, d.cpu ?? 0);
    const cd = d.cpu_detail || {};
    els.cpuSub.textContent =
      `${(cd.count_logical ?? '?')} cores` +
      (cd.freq?.current_mhz ? ` · ${cd.freq.current_mhz} MHz` : '');

    els.ramValue.textContent = (d.ram ?? 0).toFixed(1) + '%';
    setBar(els.ramBar, d.ram ?? 0);
    const mem = d.memory || {};
    els.ramSub.textContent = (mem.used_gb != null && mem.total_gb != null)
      ? `${mem.used_gb} / ${mem.total_gb} GB` : '—';

    els.diskValue.textContent = (d.disk ?? 0).toFixed(1) + '%';
    setBar(els.diskBar, d.disk ?? 0);
    const dk = d.disks || {};
    els.diskSub.textContent = (dk.used_gb != null && dk.total_gb != null)
      ? `${dk.used_gb} / ${dk.total_gb} GB (${dk.root_path || ''})` : '—';

    const net = d.network || {};
    els.netDown.textContent = (net.recv_per_sec_kb ?? 0).toFixed(1) + ' KB/s';
    els.netUp.textContent = (net.sent_per_sec_kb ?? 0).toFixed(1) + ' KB/s';
    els.netValue.textContent = ((net.recv_per_sec_kb ?? 0) + (net.sent_per_sec_kb ?? 0)).toFixed(1) + ' KB/s';
    els.netSub.textContent = `total ↓ ${net.recv_mb ?? 0} MB · ↑ ${net.sent_mb ?? 0} MB`;

    const sys = d.system || {};
    els.bootTime.textContent = sys.boot_time_iso ? new Date(sys.boot_time_iso).toLocaleString() : '—';
    els.procCount.textContent = sys.process_count ?? '—';
    els.cpuCores.textContent = `${cd.count_physical ?? '?'} physical / ${cd.count_logical ?? '?'} logical`;
    els.loadAvg.textContent = cd.load_avg_1_5_15
      ? cd.load_avg_1_5_15.map((x) => x.toFixed(2)).join(' / ') : 'n/a (Windows)';
    els.cpuFreq.textContent = cd.freq ? `${cd.freq.current_mhz} MHz` : 'n/a';
    els.pyVersion.textContent = sys.python_version ?? '—';

    pushPoint(cpuChart, label, [d.cpu ?? 0]);
    pushPoint(ramChart, label, [d.ram ?? 0]);
    pushPoint(diskChart, label, [d.disk ?? 0]);
    pushPoint(netChart, label, [net.recv_per_sec_kb ?? 0, net.sent_per_sec_kb ?? 0]);

    checkAlerts(d);
  }

  // ---------------------------------------------------------------- fetch --
  async function fetchStats() {
    if (state.paused || document.hidden) return;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 8000);
    try {
      const res = await fetch(STATS_URL, { signal: ctrl.signal, cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.failures = 0;
      state.retryDelayMs = 2000;
      setStatus('ok');
      render(data);
    } catch (err) {
      state.failures += 1;
      setStatus(state.failures >= 3 ? 'err' : 'warn');
      els.lastUpdated.textContent = `retrying… (attempt ${state.failures})`;
      if (state.failures === 3) showError('Lost connection to server. Retrying…');
      // Exponential backoff: temporarily slow the poll loop.
      restartLoop(Math.min(state.intervalMs * 2 ** Math.min(state.failures, 4), 30000));
    } finally {
      clearTimeout(timeout);
    }
  }

  async function preloadHistory() {
    try {
      const res = await fetch(HISTORY_URL, { cache: 'no-store' });
      if (!res.ok) return;
      const { points = [] } = await res.json();
      points.forEach((p) => {
        const label = fmtTime(p.t) || '';
        pushPoint(cpuChart, label, [p.cpu ?? 0]);
        pushPoint(ramChart, label, [p.ram ?? 0]);
        pushPoint(diskChart, label, [p.disk ?? 0]);
        pushPoint(netChart, label, [p.net_down_kbps ?? 0, p.net_up_kbps ?? 0]);
      });
    } catch { /* history is optional; live polling still works */ }
  }

  function restartLoop(ms) {
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(fetchStats, ms || state.intervalMs);
  }

  // ---------------------------------------------------------------- events --
  els.intervalSelect.addEventListener('change', () => {
    state.intervalMs = parseInt(els.intervalSelect.value, 10) || 2000;
    restartLoop();
    fetchStats();
  });

  els.pauseBtn.addEventListener('click', () => {
    state.paused = !state.paused;
    els.pauseBtn.textContent = state.paused ? '▶ Resume' : '⏸ Pause';
    els.pauseBtn.setAttribute('aria-pressed', String(state.paused));
    setStatus(state.paused ? 'paused' : 'ok');
    if (!state.paused) fetchStats();
  });

  els.themeBtn.addEventListener('click', () => {
    const html = document.documentElement;
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    els.themeBtn.textContent = next === 'dark' ? '🌙 Light' : '☀️ Dark';
    try { localStorage.setItem('theme', next); } catch {}
    [cpuChart, ramChart, diskChart, netChart].forEach((c) => c.update('none'));
  });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !state.paused) fetchStats(); // refresh on tab focus
  });

  // ----------------------------------------------------------------- init --
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
      els.themeBtn.textContent = '☀️ Dark';
    }
  } catch {}

  (async () => {
    await preloadHistory();
    await fetchStats();
    restartLoop();
  })();
})();
