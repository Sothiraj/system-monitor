/* =============================================================================
   YOUR NAME · portfolio behaviour
   Vanilla ES2020 — no dependencies, no build step, ~all progressively enhanced.
   The page is fully readable and navigable with JS disabled.

   00 PROFILE config      01 theme        02 nav + scrollspy   03 reveal
   04 counters            05 typer        06 terminal boot     07 matrix
   08 portrait tilt       09 project filter                   10 contact form
   11 command palette     12 housekeeping
   ========================================================================== */

/* ── 00 · SINGLE SOURCE OF TRUTH FOR YOUR DETAILS ────────────────────────
   Change these and the contact form, palette and mailto links all follow.   */
const PROFILE = {
  name:      'YOUR NAME',
  email:     'you@yourhandle.dev',
  phone:     '+91 90000 00000',
  location:  'Salem, Tamil Nadu, India',
  cvPath:    'assets/YOUR-NAME-CV.pdf',
  roles: [
    'Cybersecurity Analyst & Ethical Hacker',
    'Web & Network Penetration Tester',
    'SOC / Detection Engineer',
    'B.E. Computer Science Graduate',
    'Bug Bounty Hunter · VDP contributor'
  ]
};

/* ── helpers ─────────────────────────────────────────────────────────────── */
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const clamp = (n, min, max) => Math.min(Math.max(n, min), max);
const prefersLight = window.matchMedia('(prefers-color-scheme: light)');

/* ── 01 · THEME (persisted, follows OS on first visit) ──────────────────── */
(function theme() {
  const btn = $('#themeToggle');
  if (!btn) return;
  const root = document.documentElement;
  const sync = () => btn.setAttribute('aria-label',
    root.dataset.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  sync();

  const apply = (next, persist = true) => {
    root.dataset.theme = next;
    if (persist) { try { localStorage.setItem('theme', next); } catch (e) {} }
    sync();
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
  };

  btn.addEventListener('click', () => apply(root.dataset.theme === 'dark' ? 'light' : 'dark'));
  btn.addEventListener('dblclick', () => { try { localStorage.removeItem('theme'); } catch (e) {} apply(prefersLight.matches ? 'light' : 'dark', false); });

  // follow the OS only while the user has not chosen manually
  prefersLight.addEventListener('change', (e) => {
    let saved = null; try { saved = localStorage.getItem('theme'); } catch (err) {}
    if (!saved) apply(e.matches ? 'light' : 'dark', false);
  });

  window.__setTheme = apply;
})();

/* ── 02 · HEADER STATE, MOBILE NAV, SCROLLSPY ───────────────────────────── */
(function nav() {
  const header = $('.site-header');
  const menu   = $('#primaryNav');
  const toggle = $('#navToggle');
  const links  = $$('a[href^="#"]', menu);

  // sticky shadow
  if (header) {
    const onScroll = () => header.classList.toggle('is-stuck', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // mobile drawer
  const setOpen = (open) => {
    if (!menu || !toggle) return;
    menu.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.body.style.overflow = open && window.innerWidth <= 900 ? 'hidden' : '';
    let scrim = $('.mobile-scrim');
    if (open) {
      scrim = scrim || Object.assign(document.createElement('div'), { className: 'mobile-scrim' });
      if (!scrim.isConnected) document.body.appendChild(scrim);
      scrim.addEventListener('click', () => setOpen(false), { once: true });
    } else if (scrim) scrim.remove();
  };
  toggle?.addEventListener('click', () => setOpen(!menu.classList.contains('is-open')));
  links.forEach(a => a.addEventListener('click', () => setOpen(false)));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') setOpen(false); });
  window.addEventListener('resize', () => { if (window.innerWidth > 900) setOpen(false); });

  // scrollspy
  const targets = links
    .map(a => document.getElementById(a.getAttribute('href').slice(1)))
    .filter(Boolean);
  if (!targets.length || !('IntersectionObserver' in window)) return;

  const setActive = (id) => links.forEach(a =>
    a.classList.toggle('is-active', a.getAttribute('href') === '#' + id));

  const spy = new IntersectionObserver((entries) => {
    entries
      .filter(e => e.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      .slice(0, 1)
      .forEach(e => setActive(e.target.id));
  }, { rootMargin: '-45% 0px -50% 0px', threshold: [0, 0.2, 0.6, 1] });

  targets.forEach(t => spy.observe(t));
})();

/* ── 03 · REVEAL ON SCROLL (with per-grid stagger index) ────────────────── */
(function reveal() {
  const items = $$('.reveal');
  if (!items.length) return;
  if (reducedMotion.matches || !('IntersectionObserver' in window)) {
    items.forEach(el => el.classList.add('is-visible'));
    return;
  }
  $$('.projects-grid, .services-grid, .skills-grid, .posts, .quotes-grid, .cert-list, .timeline').forEach(grid => {
    Array.from(grid.children).forEach((child, i) => child.style.setProperty('--i', i));
  });
  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-visible');
      obs.unobserve(e.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
  items.forEach(el => io.observe(el));
})();

/* ── 04 · COUNT-UP STATISTICS ───────────────────────────────────────────── */
(function counters() {
  const nums = $$('[data-count]');
  if (!nums.length || !('IntersectionObserver' in window)) {
    nums.forEach(n => { n.textContent = (parseInt(n.dataset.count, 10) || 0).toLocaleString('en-IN'); });
    return;
  }
  const fmt = (v) => v >= 1000 ? v.toLocaleString('en-IN') : String(v);

  const run = (el) => {
    const target = parseInt(el.dataset.count, 10) || 0;
    if (reducedMotion.matches) { el.textContent = fmt(target) + (el.dataset.suffix || ''); return; }
    const dur = 1150 + Math.min(target, 400);
    const t0 = performance.now();
    const tick = (now) => {
      const p = clamp((now - t0) / dur, 0, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(Math.round(target * eased)) + (p === 1 ? (el.dataset.suffix || '') : '');
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach(e => { if (e.isIntersecting) { run(e.target); obs.unobserve(e.target); } });
  }, { threshold: 0.6 });
  nums.forEach(n => io.observe(n));
})();

/* ── 05 · ROLE TYPER ────────────────────────────────────────────────────── */
(function typer() {
  const el = $('#roleTyper');
  if (!el) return;
  const roles = PROFILE.roles.filter(Boolean);
  if (roles.length < 2 || reducedMotion.matches) { el.textContent = roles[0] || el.textContent; return; }

  let idx = 0, text = roles[0], deleting = true, pause = 40;
  const tick = () => {
    if (pause > 0) { pause--; return; }
    if (deleting) {
      text = roles[idx].slice(0, Math.max(0, text.length - 2));
      if (!text.length) { deleting = false; idx = (idx + 1) % roles.length; pause = 2; }
    } else {
      text = roles[idx].slice(0, Math.min(roles[idx].length, text.length + 2));
      if (text === roles[idx]) { deleting = true; pause = 56; }
    }
    el.textContent = text;
  };
  setInterval(tick, 45);
})();

/* ── 06 · TERMINAL BOOT SEQUENCE ────────────────────────────────────────── */
(function boot() {
  const term = $('#bootTerminal');
  if (!term || reducedMotion.matches || !('IntersectionObserver' in window)) return;
  const lines = $$('.term-body .l', term);
  if (!lines.length) return;

  term.classList.add('is-booting');
  const play = () => {
    lines.forEach((l, i) => setTimeout(() => l.style.cssText = 'opacity:1;transform:none;transition:opacity .28s ease,transform .28s ease', i * 135));
    setTimeout(() => term.classList.remove('is-booting'), lines.length * 135 + 320);
  };
  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach(e => { if (e.isIntersecting) { play(); obs.disconnect(); } });
  }, { threshold: 0.25 });
  io.observe(term);
})();

/* ── 07 · MATRIX RAIN (dark theme only, pauses off-screen / blurred) ────── */
(function matrix() {
  const canvas = $('#matrix');
  if (!canvas) return;
  const ctx = canvas.getContext && canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  const glyphs = 'アカサタナハマヤラワ0123456789ABCDEF$#@%&*<>/\\|_=+{}[]();:'.split('');
  const dpr = clamp(window.devicePixelRatio || 1, 1, 2);
  let cols = [], w = 0, h = 0, size = 14, raf = 0, last = 0, running = false;

  const dark = () => document.documentElement.dataset.theme === 'dark';
  const visible = () => {
    const r = canvas.getBoundingClientRect();
    return r.bottom > -40 && r.top < window.innerHeight + 40 && running;
  };

  const resize = () => {
    const rect = canvas.parentElement.getBoundingClientRect();
    w = Math.max(1, Math.floor(rect.width));
    h = Math.max(1, Math.floor(rect.height));
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    size = w < 640 ? 11 : 14;
    const n = Math.ceil(w / size);
    cols = Array.from({ length: n }, (_, i) => ({ x: i * size + size / 2, y: Math.random() * -h, sp: 32 + Math.random() * 70 }));
    ctx.clearRect(0, 0, w, h);
  };

  const frame = (t) => {
    raf = requestAnimationFrame(frame);
    if (!dark() || reducedMotion.matches || !visible()) return;
    if (t - last < 55) return;                 // ~18 fps keeps it subtle + cheap
    const dt = Math.min((t - last) / 1000, 0.3);
    last = t;

    ctx.globalCompositeOperation = 'destination-out';
    ctx.fillStyle = 'rgba(0,0,0,0.09)';
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = 'source-over';
    ctx.font = `500 ${size}px "JetBrains Mono", ui-monospace, monospace`;

    const col = getComputedStyle(document.documentElement).getPropertyValue('--matrix').trim() || 'rgba(0,229,160,.42)';
    cols.forEach(c => {
      c.y += c.sp * dt;
      if (c.y > h + size) { c.y = -size; c.x = Math.random() * w; }
      const g = glyphs[(Math.random() * glyphs.length) | 0];
      ctx.fillStyle = col;
      ctx.globalAlpha = 0.55;
      ctx.fillText(g, c.x, c.y);
      ctx.globalAlpha = 1;
    });
  };

  running = true;
  resize();
  raf = requestAnimationFrame(frame);
  let rid; addEventListener('resize', () => { clearTimeout(rid); rid = setTimeout(resize, 160); });
  document.addEventListener('visibilitychange', () => {
    running = !document.hidden;
    if (running) last = performance.now();
    else ctx.clearRect(0, 0, w, h);
  });
  document.addEventListener('themechange', (e) => {
    if (e.detail.theme !== 'dark') ctx.clearRect(0, 0, w, h);
  });
})();

/* ── 08 · PORTRAIT PARALLAX / TILT ──────────────────────────────────────── */
(function tilt() {
  const card = $('#portrait');
  const frame = $('.portrait-frame', card || document);
  if (!frame || reducedMotion.matches || !window.matchMedia('(hover: hover)').matches) return;
  let raf = 0;
  const onMove = (e) => {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      frame.style.transform = `perspective(900px) rotateY(${(px * 7).toFixed(2)}deg) rotateX(${(-py * 7).toFixed(2)}deg) translateZ(0)`;
    });
  };
  card.addEventListener('pointermove', onMove);
  card.addEventListener('pointerleave', () => { frame.style.transform = ''; });
})();

/* ── 09 · PROJECT FILTERS ──────────────────────────────────────────────── */
(function filterProjects() {
  const buttons = $$('.filter');
  const grid = $('#projectGrid');
  if (!buttons.length || !grid) return;
  const cards = $$('.project', grid);

  buttons.forEach(btn => btn.addEventListener('click', () => {
    const want = btn.dataset.filter;
    buttons.forEach(b => { b.classList.toggle('is-active', b === btn); b.setAttribute('aria-selected', String(b === btn)); });
    let shown = 0;
    cards.forEach(card => {
      const tags = (card.dataset.tags || '').split(/\s+/);
      const ok = want === 'all' || tags.includes(want);
      card.classList.toggle('is-hidden', !ok);
      if (ok) { shown++; card.style.setProperty('--i', shown); }
    });
    const count = $('span', buttons[0]);
    if (count) count.textContent = String(shown).padStart(2, '0');
  }));
})();

/* ── 10 · CONTACT FORM: validate locally, then hand off to the mail client ─ */
(function contactForm() {
  const form = $('#contactForm');
  if (!form) return;
  const msg = $('#cf-msg');
  const counter = $('#cf-count');
  const ok = $('#formOk');

  const slotFor = (input) => {
    const id = (input.getAttribute('aria-describedby') || '').split(/\s+/)[0];
    return id ? document.getElementById(id) : null;
  };
  const setError = (input, message) => {
    const field = input.closest('.field') || input.closest('.check');
    const slot = slotFor(input);
    field?.classList.toggle('is-bad', Boolean(message));
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    if (slot) slot.textContent = message || '';
    return !message;
  };

  if (msg && counter) {
    const update = () => { counter.textContent = `${msg.value.length} / 2000`; };
    msg.addEventListener('input', update); update();
  }

  const validators = {
    name:    v => v.trim().length >= 2 || 'Please tell me your name.',
    email:   v => /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(v.trim()) || 'That email doesn’t look valid.',
    message: v => v.trim().length >= 20 || 'A little more context, please (20 characters minimum).'
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    let valid = true, firstBad = null;

    Object.keys(validators).forEach(key => {
      const input = form.elements[key];
      const res = validators[key](input.value || '');
      if (res !== true) { valid = false; firstBad = firstBad || input; }
      setError(input, res === true ? '' : res);
    });

    const ack = $('#cf-ack');
    if (ack && !ack.checked) {
      valid = false; firstBad = firstBad || ack;
      $('#err-ack').textContent = 'Please confirm before sending.';
    } else if (ack) $('#err-ack').textContent = '';

    if (!valid) {
      ok.textContent = '// fix the highlighted fields';
      ok.style.color = 'var(--danger)';
      firstBad?.focus();
      return;
    }

    const subject = `[Portfolio] ${data.topic || 'Enquiry'} — ${data.name.trim()}`;
    const body =
      `From:    ${data.name.trim()} <${data.email.trim()}>${data.org ? `\nCompany: ${data.org.trim()}` : ''}\n` +
      `Topic:   ${data.topic}\nTimeline: ${data.timeline}\n\n` +
      `${data.message.trim()}\n\n—\nsent via ${location.host || 'portfolio'} · ${new Date().toISOString().slice(0, 10)}`;

    const href = `mailto:${PROFILE.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    ok.style.color = 'var(--accent)';
    ok.textContent = '// opening your mail client… nothing was sent to a server.';
    const a = document.createElement('a');
    a.href = href;
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.append(a);
    a.click();
    a.remove();
    form.reset();
    if (counter) counter.textContent = '0 / 2000';
    setTimeout(() => { ok.textContent = ''; }, 9000);
  });

  // live-clear errors as the user types
  ['cf-name', 'cf-email', 'cf-msg'].forEach(id => {
    const el = document.getElementById(id);
    el?.addEventListener('input', () => {
      const res = validators[el.name]?.(el.value);
      if (res === true) setError(el, '');
    });
  });
})();

/* ── 11 · COMMAND PALETTE (⌘/Ctrl-K) ─────────────────────────────────────── */
(function palette() {
  const root = $('#palette');
  const input = $('#paletteInput');
  const list = $('#paletteList');
  const opener = $('#paletteBtn');
  if (!root || !input || !list) return;

  const sections = $$('main section[id]');
  const clean = (t) => (t || '').replace(/\s+/g, ' ').replace(/^\/\/\s*/, '').trim();
  const navLabel = (id) => clean($(`.primary-nav a[href="#${id}"]`)?.textContent);
  const label = (el) => {
    const h = $('h2, h3', el);
    return clean(h ? h.textContent : el.id);
  };
  // index the nav label, the section eyebrow and its sub-headings, so “arsenal”,
  // “credentials” or “references” all resolve even though they aren't the H2 text
  const haystack = (el) => clean([
    navLabel(el.id), el.id,
    $('.eyebrow', el)?.textContent,
    ...$$('h3', el).slice(0, 6).map(h => h.textContent)
  ].filter(Boolean).join(' ')).toLowerCase();
  const COMMANDS = [
    { title: 'Toggle light / dark theme', key: 'T', run: () => window.__setTheme?.(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true) },
    { title: 'Copy email address', key: 'C', run: async () => {
        try { await navigator.clipboard.writeText(PROFILE.email); flash(`// ${PROFILE.email} copied`); }
        catch { flash('// clipboard blocked — ' + PROFILE.email); }
      } },
    { title: 'Print / save as PDF résumé', key: 'P', run: () => window.print() },
    { title: 'Open GitHub', key: '↗', run: () => window.open('https://github.com/yourusername', '_blank', 'noopener') },
    { title: 'Open Hack The Box profile', key: '↗', run: () => window.open('https://app.hackthebox.com/profile/yourusername', '_blank', 'noopener') }
  ];

  let items = [], active = 0, lastFocus = null;

  const flash = (t) => {
    let bar = $('#paletteFlash');
    if (!bar) {
      bar = Object.assign(document.createElement('div'), { id: 'paletteFlash', className: 'form-ok mono' });
      bar.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:310;padding:.5rem .9rem;border-radius:99px;background:var(--bg-3);border:1px solid var(--line-2)';
      document.body.appendChild(bar);
    }
    bar.textContent = t;
    clearTimeout(bar._t);
    bar._t = setTimeout(() => bar.remove(), 2600);
  };

  const build = () => {
    items = [
      ...sections.map(s => ({ title: label(s), key: navLabel(s.id) || '#' + s.id, extra: haystack(s), kind: 'section', go: () => document.getElementById(s.id)?.scrollIntoView({ behavior: reducedMotion.matches ? 'auto' : 'smooth', block: 'start' }) })),
      ...COMMANDS.map(c => ({ ...c, kind: 'command', go: c.run }))
    ];
  };

  const render = (q = '') => {
    const needle = q.trim().toLowerCase();
    const hits = items
      .map(it => ({ it, hay: (it.extra || (it.title + ' ' + it.key)).toLowerCase() }))
      .filter(({ it, hay }) => !needle || hay.includes(needle) || it.title.toLowerCase().includes(needle))
      .slice(0, 12)
      .map(x => x.it);
    active = 0;
    list.innerHTML = '';
    list._hits = hits;
    if (!hits.length) {
      const li = document.createElement('li');
      li.className = 'palette-empty mono';
      li.textContent = `no matches for “${q.trim()}”`;
      list.append(li);
      return;
    }
    hits.forEach((it, i) => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'palette-item' + (i === 0 ? ' is-active' : '');
      btn.innerHTML = `<span>${it.kind === 'command' ? '⌁ ' : ''}${it.title.replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]))}</span><span class="pi-key">${it.key}</span>`;
      btn.addEventListener('click', () => { close(); it.go(); });
      li.append(btn);
      list.append(li);
    });
  };

  const move = (d) => {
    const btns = $$('.palette-item', list);
    if (!btns.length) return;
    active = (active + d + btns.length) % btns.length;
    btns.forEach((b, i) => b.classList.toggle('is-active', i === active));
    btns[active].scrollIntoView({ block: 'nearest' });
  };

  const open = () => {
    build();
    lastFocus = document.activeElement;
    root.hidden = false;
    input.value = '';
    render();
    requestAnimationFrame(() => input.focus());
    document.body.style.overflow = 'hidden';
  };
  const close = () => {
    root.hidden = true;
    document.body.style.overflow = '';
    lastFocus?.focus?.();
  };

  opener?.addEventListener('click', open);
  root.addEventListener('click', (e) => { if (e.target === root) close(); });
  input.addEventListener('input', () => render(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      const hit = (list._hits || [])[active];
      if (hit) { close(); hit.go(); }
    } else if (e.key === 'Escape') { e.preventDefault(); close(); }
  });
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); root.hidden ? open() : close(); }
    if (e.key === 'Escape' && !root.hidden) close();
    if (!root.hidden && e.key === 'Tab') { e.preventDefault(); }
  });
})();

/* ── 12 · HOUSEKEEPING ──────────────────────────────────────────────────── */
(function housekeeping() {
  const year = $('#year');
  if (year) year.textContent = String(new Date().getFullYear());

  const stamp = $('#buildStamp');
  if (stamp) {
    const d = new Date(document.lastModified);
    if (!isNaN(d)) stamp.textContent = `Last updated ${d.toISOString().slice(0, 10)}.`;
  }

  // smooth anchor focus management for keyboard users
  $$('a[href^="#"]').forEach(a => a.addEventListener('click', () => {
    const t = document.getElementById(a.getAttribute('href').slice(1));
    if (t) { t.setAttribute('tabindex', '-1'); requestAnimationFrame(() => t.focus({ preventScroll: true })); }
  }));

  // skill bars animate even outside .reveal containers
  $$('.skill i > span').forEach(s => { if (reducedMotion.matches) s.classList.add('no-anim'); });

  // fill the mailto fallback in the contact list if JS is on
  const mail = $('.contact-list a[href^="mailto:"]');
  if (mail && PROFILE.email) {
    mail.textContent = PROFILE.email;
    mail.href = `mailto:${PROFILE.email}?subject=${encodeURIComponent('Security engagement enquiry')}`;
  }
  const cvLinks = $$('a[href$="CV.pdf"]');
  cvLinks.forEach(a => { a.href = PROFILE.cvPath; });
})();
