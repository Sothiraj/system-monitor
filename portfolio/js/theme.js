/* Applied synchronously in <head>, before first paint, so the theme never
   flashes. Kept in its own file (no inline script) so the site can ship a
   CSP of `script-src 'self'` with no unsafe-inline.  ~500 bytes, cached. */
(function () {
  var root = document.documentElement;
  var stored = null;
  try { stored = localStorage.getItem('theme'); } catch (e) {}
  var light = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  root.dataset.theme = stored || (light ? 'light' : 'dark');
  /* .js lets CSS hide reveal-targets only when animations are possible */
  root.classList.add('js');
})();
