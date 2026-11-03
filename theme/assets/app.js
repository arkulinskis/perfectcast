/* core.js: the shared front-end engine (window.UI). Same in every app made from APP_MAKER/template;
   app-specific things live in web/app.js (brand, nav, footer) and web/pages/*.html (the pages).

   Pages:   UI.page(name, {title, nav, icon, auth, order, chrome}, mount)
              auth: null (anyone) | 'guest' (signed-out only) | 'user' | 'admin'
              nav: label for the header / phone tab bar (omit to keep it out of the menus)
              mount(view, ctx) draws into `view`; ctx = {args, me, go, api}. Return a Promise (the page
              is "ready" when it resolves) or {ready, destroy}. URLs are #name/arg1/arg2.
   Server:  UI.api(fn, ...args) -> Promise of the server function's return value. A reply of
              {ok: false, error} rejects with that message (shown as a toast unless you .catch it).
            UI.apiQuiet(fn, ...args) is the same without Anvil's loading spinner.
   Auth:    UI.auth('login'|'signup'|'reset'|'logout', {...}) -> Promise of {ok, me, message}
   Helpers: UI.esc, UI.icon, UI.toast, UI.modal, UI.confirm, UI.busy, UI.formData, UI.fmtDate, UI.ago,
            UI.store, UI.setTheme, UI.feedback, UI.go, UI.refresh
   Tests:   window.UI_READY is true when the current page has finished loading. */
(function () {
  'use strict';
  if (window.UI && window.UI.__v) return;
  var UI = window.UI = { __v: 1, pages: {}, me: null, config: { name: 'App', key: 'app', home: 'home', landing: 'landing' } };
  window.UI_READY = false;

  // The saved theme lives under the app's key ('<key>.theme'), which is only known once the app configures UI:
  // apply it again then, or a saved Light/Dark choice is ignored after every reload.
  UI.configure = function (cfg) { Object.keys(cfg).forEach(function (k) { UI.config[k] = cfg[k]; }); if (cfg.key && UI.applyTheme) UI.applyTheme(UI.theme()); };

  /* ------------------------------------------------------------------ small helpers */
  UI.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  UI.plural = function (n, one, many) { return n + ' ' + (n === 1 ? one : (many || one + 's')); };
  UI.initials = function (name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  };
  UI.fmtDate = function (iso, opts) {
    if (!iso) return '';
    var d = iso.length <= 10 ? new Date(iso + 'T12:00:00') : new Date(iso);
    return d.toLocaleDateString(undefined, opts || { day: 'numeric', month: 'short', year: 'numeric' });
  };
  UI.fmtDateTime = function (iso) {
    return iso ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
  };
  UI.ago = function (iso) {
    if (!iso) return '';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    var steps = [[60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year']], n = s / 60;
    for (var i = 0; i < steps.length; i++) {
      if (n < steps[i][0]) { n = Math.floor(n); return UI.plural(n, steps[i][1]) + ' ago'; }
      n = n / steps[i][0];
    }
    return '';
  };
  UI.store = {
    get: function (k, dflt) { try { var v = localStorage.getItem(UI.config.key + '.' + k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem(UI.config.key + '.' + k, JSON.stringify(v)); } catch (e) {} }
  };
  UI.formData = function (form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled) return;
      if (el.type === 'checkbox') out[el.name] = el.checked;
      else if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; }
      else out[el.name] = el.value;
    });
    return out;
  };
  /* Disable a button while a Promise runs; returns the Promise. */
  UI.busy = function (btn, promise) {
    if (!btn) return promise;
    btn.disabled = true; btn.classList.add('is-busy');
    var done = function () { btn.disabled = false; btn.classList.remove('is-busy'); };
    promise.then(done, done);
    return promise;
  };

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.7c2.2.6 3.5 2.4 3.5 5.3"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    bug: '<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5M9 5.5 7.5 4M15 5.5 16.5 4M7 13H3M21 13h-4M7.5 18l-3 2M16.5 18l3 2M7.5 9.5l-3-2M16.5 9.5l3-2"/>',
    bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13"/><path d="M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20v-4h-4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    pin: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    camera: '<path d="M4 8h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13.5" r="3.5"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>'
  };
  UI.ICONS = ICONS;
  UI.icon = function (name, cls) {
    return '<svg class="ui-ic ' + (cls || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || ICONS.sparkle) + '</svg>';
  };

  /* ------------------------------------------------------------------ toasts, modals */
  UI.toast = function (msg, kind) {
    var box = document.querySelector('.ui-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'ui ui-toasts'; box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'ui-toast' + (kind ? ' ' + kind : '');
    t.innerHTML = (kind === 'error' ? UI.icon('info') : kind === 'ok' ? UI.icon('check') : '') + '<span>' + UI.esc(msg) + '</span>';
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 300); }, kind === 'error' ? 6500 : 3200);
  };
  UI.modal = function (html, opts) {
    opts = opts || {};
    var prev = document.activeElement;
    var wrap = document.createElement('div');
    wrap.className = 'ui ui-modal-wrap';
    wrap.innerHTML = '<div class="ui-modal' + (opts.wide ? ' wide' : '') + '" role="dialog" aria-modal="true">' +
      '<button class="ui-btn ghost icon ui-modal-x" data-close aria-label="Close">' + UI.icon('x') + '</button>' + html + '</div>';
    document.body.appendChild(wrap);
    document.documentElement.classList.add('ui-modal-open');
    function key(e) { if (e.key === 'Escape') close(); }
    function close() {
      if (!wrap.parentNode) return;
      wrap.remove(); document.removeEventListener('keydown', key);
      if (!document.querySelector('.ui-modal-wrap')) document.documentElement.classList.remove('ui-modal-open');
      if (opts.onclose) opts.onclose();
      if (prev && prev.focus) prev.focus();
    }
    document.addEventListener('keydown', key);
    wrap.addEventListener('mousedown', function (e) { if (e.target === wrap) close(); });
    wrap.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) close(); });
    var first = wrap.querySelector('input, textarea, select');
    setTimeout(function () { (first || wrap.querySelector('.ui-modal')).focus && (first || wrap.querySelector('.ui-modal')).focus(); }, 30);
    return { el: wrap.querySelector('.ui-modal'), close: close };
  };
  UI.confirm = function (o) {
    o = typeof o === 'string' ? { title: o } : (o || {});
    return new Promise(function (resolve) {
      var answered = false;
      var m = UI.modal('<h2>' + UI.esc(o.title || 'Are you sure?') + '</h2>' + (o.text ? '<p class="muted">' + UI.esc(o.text) + '</p>' : '') +
        '<div class="ui-row end" style="margin-top:20px"><button class="ui-btn ghost" data-close>' + UI.esc(o.cancel || 'Cancel') + '</button>' +
        '<button class="ui-btn ' + (o.danger ? 'danger solid' : 'primary') + '" data-ok>' + UI.esc(o.ok || 'OK') + '</button></div>',
      { onclose: function () { if (!answered) resolve(false); } });
      m.el.querySelector('[data-ok]').onclick = function () { answered = true; m.close(); resolve(true); };
    });
  };

  /* ------------------------------------------------------------------ theme */
  UI.theme = function () { return UI.store.get('theme', 'auto'); };
  UI.applyTheme = function (t) {
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
    var dark = t === 'dark' || (t !== 'light' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('ui-dark', !!dark);
  };
  UI.setTheme = function (t) { UI.store.set('theme', t); UI.applyTheme(t); };
  UI.applyTheme(UI.theme());
  if (window.matchMedia) {
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { UI.applyTheme(UI.theme()); }); } catch (e) {}
  }

  /* ------------------------------------------------------------------ server bridge */
  var bridge = null;
  function send(kind, payload) {
    if (!bridge) return Promise.reject(new Error('The app is still starting.'));
    var out;
    try { out = bridge(kind, JSON.stringify(payload || {})); } catch (e) { return Promise.reject(e); }
    return Promise.resolve(out).then(function (r) {
      r = typeof r === 'string' ? JSON.parse(r) : (r || {});
      if (r.error) {
        var err = new Error(r.error); err.uiApi = true; err.denied = !!r.denied;
        if (r.detail) console.error(kind, payload && payload.fn, r.detail);
        if (r.reload) setTimeout(function () { location.reload(); }, 2500);
        throw err;
      }
      return r.result;
    });
  }
  function apiCall(quiet, fn, args) {
    return send('call', { fn: fn, args: args, quiet: quiet }).then(function (res) {
      if (res && typeof res === 'object' && res.ok === false) {
        var err = new Error(res.error || 'That didn\'t work.'); err.uiApi = true; err.expected = true; err.result = res;
        throw err;
      }
      return res;
    });
  }
  UI.api = function (fn) { return apiCall(false, fn, Array.prototype.slice.call(arguments, 1)); };
  UI.apiQuiet = function (fn) { return apiCall(true, fn, Array.prototype.slice.call(arguments, 1)); };
  /* Errors nobody caught become a toast, so a failed action is never silent. */
  window.addEventListener('unhandledrejection', function (e) {
    if (e.reason && e.reason.uiApi) { e.preventDefault(); UI.toast(e.reason.message, 'error'); }
  });

  /* Sign in / up / out. On success it navigates: to where the visitor was heading (UI.after) or home
     after signing in, to the landing page after signing out. */
  UI.auth = function (kind, payload) {
    return send(kind, payload || {}).then(function (r) {
      if (r && r.ok === false) { var err = new Error(r.error); err.uiApi = true; err.expected = true; throw err; }
      if (r && 'me' in r && (r.me || kind === 'logout')) {
        UI.me = r.me || null;
        var target = r.me ? (UI.after || '#' + UI.config.home) : '#' + UI.config.landing;
        UI.after = null;
        if (location.hash === target) route(); else location.hash = target;
      }
      return r;
    });
  };
  /* Update the signed-in user's details (e.g. a new name) and redraw the header, without reloading the page. */
  UI.setMe = function (me) {
    UI.me = me || null;
    if (shellRoot) renderChrome(current.name);
  };

  /* ------------------------------------------------------------------ pages and routing */
  UI.page = function (name, opts, mount) {
    if (typeof opts === 'function') { mount = opts; opts = {}; }
    opts.name = name; opts.mount = mount;
    UI.pages[name] = opts;
  };
  UI.allowed = function (p) {
    if (!p) return false;
    if (p.auth === 'user') return !!UI.me;
    if (p.auth === 'admin') return !!(UI.me && UI.me.is_admin);
    if (p.auth === 'guest') return !UI.me;
    return true;
  };
  UI.navPages = function () {
    return Object.keys(UI.pages).map(function (k) { return UI.pages[k]; })
      .filter(function (p) { return p.nav && UI.allowed(p) && (!p.when || p.when()); })
      .sort(function (a, b) { return (a.order || 50) - (b.order || 50); });
  };
  UI.parseHash = function () {
    var h = (location.hash || '').replace(/^#!?\/?/, '');
    var parts = h.split('?')[0].split('/').filter(function (x) { return x !== ''; }).map(decodeURIComponent);
    return { name: parts[0] || '', args: parts.slice(1) };
  };
  UI.hashFor = function (name) {
    var args = Array.prototype.slice.call(arguments, 1).filter(function (a) { return a != null && a !== ''; });
    return '#' + [name].concat(args.map(encodeURIComponent)).join('/');
  };
  UI.go = function (name) {
    var h = UI.hashFor.apply(null, arguments);
    if (location.hash === h) route(); else location.hash = h;
  };
  UI.refresh = function () { route(); };
  UI.after = null;  // where to go after signing in

  var shellRoot = null, view = null, current = { name: null, destroy: null }, routeSeq = 0;

  function defaultPage() { return UI.me ? UI.config.home : UI.config.landing; }

  function route() {
    var r = UI.parseHash(), name = r.name || defaultPage(), p = UI.pages[name];
    if (!p) { name = defaultPage(); p = UI.pages[name]; r.args = []; }
    if (p.auth === 'guest' && UI.me) { p = UI.pages[UI.config.home]; name = UI.config.home; r.args = []; }
    if ((p.auth === 'user' || p.auth === 'admin') && !UI.me) {
      UI.after = location.hash && location.hash !== '#' ? location.hash : null;
      p = UI.pages.auth; name = 'auth'; r.args = [];
    }
    if (p.auth === 'admin' && !(UI.me && UI.me.is_admin)) {
      UI.toast('That page is for admins only.', 'error');
      p = UI.pages[UI.config.home]; name = UI.config.home; r.args = [];
    }
    var seq = ++routeSeq;
    window.UI_READY = false;
    if (current.destroy) { try { current.destroy(); } catch (e) { console.error(e); } }
    current = { name: name, args: r.args, destroy: null };
    if (shellRoot) {
      shellRoot.className = 'ui ui-shell page-' + name + (UI.me ? ' signed-in' : ' signed-out') + (p.chrome === false ? ' no-chrome' : '');
      renderChrome(name);
    }
    // A fresh element for every page, so listeners a page adds to `view` never pile up.
    var fresh = view.cloneNode(false);
    view.parentNode.replaceChild(fresh, view);
    view = fresh;
    window.scrollTo(0, 0);
    document.title = (p.title ? (typeof p.title === 'function' ? p.title(r.args) : p.title) + ' · ' : '') + UI.config.name;
    var ctx = { name: name, args: r.args, me: UI.me, go: UI.go, api: UI.api, page: p };
    var out;
    try { out = p.mount(view, ctx); } catch (e) { console.error(e); out = Promise.reject(e); }
    var ready = out && typeof out.then === 'function' ? out : (out && out.ready) || Promise.resolve();
    if (out && out.destroy) current.destroy = out.destroy;
    Promise.resolve(ready).then(function () { if (seq === routeSeq) window.UI_READY = true; },
      function (e) {
        if (seq !== routeSeq) return;
        console.error(e);
        if (!view.innerHTML) view.innerHTML = '<div class="ui-wrap"><div class="ui-empty">' + UI.icon('info') +
          '<h3>This page didn\'t load</h3><p class="muted">' + UI.esc(e && e.message || 'Something went wrong.') + '</p>' +
          '<button class="ui-btn" onclick="UI.refresh()">Try again</button></div></div>';
        window.UI_READY = true;
      });
  }
  UI.current = function () { return current; };

  /* The shell's parts come from web/app.js: UI.shell = {header(me, active), footer(me), tabbar(me, active)} */
  function renderChrome(active) {
    var S = UI.shell || {};
    var hd = shellRoot.querySelector('[data-ui-header]'), ft = shellRoot.querySelector('[data-ui-footer]'), tb = shellRoot.querySelector('[data-ui-tabbar]');
    if (hd) hd.innerHTML = S.header ? S.header(UI.me, active) : '';
    if (ft) ft.innerHTML = S.footer ? S.footer(UI.me, active) : '';
    if (tb) tb.innerHTML = S.tabbar ? S.tabbar(UI.me, active) : '';
  }
  UI.renderChrome = function () { if (shellRoot) renderChrome(current.name); };

  /* Called by client_code/Main.py (and by the local harness) once the page is up. */
  UI.start = function (node, bridgeFn, bootJson) {
    bridge = bridgeFn;
    var boot = typeof bootJson === 'string' ? JSON.parse(bootJson || '{}') : (bootJson || {});
    UI.me = boot.me || null;
    var host = node && node.matches && node.matches('[data-ui-app]') ? node : (node && node.querySelector('[data-ui-app]')) || node || document.body;
    host.innerHTML = '<div class="ui ui-shell">' +
      '<header class="ui-header" data-ui-header></header>' +
      '<main class="ui-main" data-ui-view></main>' +
      '<footer class="ui-footer" data-ui-footer></footer>' +
      '<nav class="ui-tabbar" data-ui-tabbar aria-label="Main"></nav></div>';
    shellRoot = host.firstChild;
    view = host.querySelector('[data-ui-view]');
    if (UI.shell && UI.shell.wire) UI.shell.wire(shellRoot);
    window.addEventListener('hashchange', route);
    route();
  };

  /* ------------------------------------------------------------------ feedback (footer + menu)
     All feedback goes to Prepsto. The widget tag in head.html (data-prepsto="CODE") slides its panel in;
     any [data-feedback] or [data-prepsto-open] element opens it. If the widget hasn't loaded, the panel opens in a new tab.
     There is no in-app feedback form any more: Admin -> Feedback only lists older messages (and app requests). */
  UI.feedback = function () {
    if (window.Prepsto && window.Prepsto.open) { window.Prepsto.open(); return; }
    var tag = document.querySelector('script[data-prepsto]');
    var code = tag && tag.getAttribute('data-prepsto');
    if (code && code.indexOf('__') !== 0) window.open('https://prepsto.com/#f/' + encodeURIComponent(code), '_blank', 'noopener');
    else UI.toast('Feedback is not set up yet.', 'error');
  };

  /* Shared clicks: [data-go="page/arg"], [data-feedback], [data-theme-set] anywhere in the app. */
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-go],[data-feedback],[data-theme-set]');
    if (!el) return;
    if (el.hasAttribute('data-go')) { e.preventDefault(); UI.go.apply(null, el.getAttribute('data-go').split('/')); }
    else if (el.hasAttribute('data-feedback')) { e.preventDefault(); UI.feedback(el.getAttribute('data-feedback') || null); }
    else if (el.hasAttribute('data-theme-set')) { e.preventDefault(); UI.setTheme(el.getAttribute('data-theme-set')); if (UI.shell && UI.shell.onTheme) UI.shell.onTheme(); }
  });
})();


/* app.js: this app's identity and frame: name, header, footer, phone tab bar.
   Pages live in web/pages/*.html. The engine (window.UI) is web/core.js. */
(function () {
  'use strict';
  UI.configure({
    name: 'PerfectCast',
    key: 'perfectcast',          // prefix for this app's browser storage
    tagline: 'Fan-cast every new romantasy. Made with love for readers.',   // footer line
    home: 'books',               // first page after signing in
    landing: 'landing'           // first page for visitors who aren't signed in
  });

  var esc = UI.esc;

  function brand() {
    return '<a class="ui-brand" href="#" data-go="' + (UI.me ? UI.config.home : UI.config.landing) + '" aria-label="' + esc(UI.config.name) + ' home">' +
      '<img src="_/theme/icon.svg" alt="" width="32" height="32"><span>Perfect<em>Cast</em></span></a>';
  }

  function themeSwitch() {
    var t = UI.theme();
    return '<div class="ui-seg" role="group" aria-label="Appearance">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
      return '<button type="button" data-theme-set="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
    }).join('') + '</div>';
  }

  function userMenu(me) {
    return '<div class="ui-menu" data-menu hidden>' +
      '<div class="ui-menu-head"><strong>' + esc(me.name) + '</strong><span class="muted small">' + esc(me.email) + '</span></div>' +
      '<a href="#profile" data-go="profile">' + UI.icon('user') + 'Your profile</a>' +
      '<a href="#fan/' + esc(me.id) + '" data-go="fan/' + esc(me.id) + '">' + UI.icon('eye') + 'Your public fan page</a>' +
      '<a href="#suggest" data-go="suggest">' + UI.icon('book') + 'Suggest a book</a>' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<div class="ui-menu-block"><span class="small muted">Appearance</span>' + themeSwitch() + '</div>' +
      '<button type="button" data-feedback>' + UI.icon('chat') + 'Submit feedback</button>' +
      '<button type="button" data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms</button>' +
      '<button type="button" data-signout>' + UI.icon('logout') + 'Sign out</button></div>';
  }

  UI.shell = {
    header: function (me, active) {
      var nav = UI.navPages();
      return '<div class="ui-header-in">' + brand() +
        (nav.length ? '<nav class="ui-nav" aria-label="Main">' + nav.map(function (p) {
          return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
        }).join('') + '</nav>' : '') +
        '<div class="ui-header-right">' +
        (me ? '<button type="button" class="ui-avatar-btn" data-menu-toggle aria-label="Your account" aria-haspopup="true">' + esc(UI.initials(me.name)) + '</button>' + userMenu(me)
          : (active === 'auth' ? '' : '<a class="ui-btn ghost" href="#auth" data-go="auth">Sign in</a><a class="ui-btn primary" href="#auth/signup" data-go="auth/signup">Get started</a>')) +
        '</div></div>';
    },
    footer: function (me) {
      return '<div class="ui-footer-in"><div class="ui-footer-brand">' + brand() + '<p class="muted small">' + esc(UI.config.tagline) + '</p></div>' +
        '<div class="ui-footer-links">' +
        '<a href="#landing" data-go="landing">About</a>' +
        '<a href="#books" data-go="books">New releases</a>' +
        '<a href="#stars" data-go="stars">Stars</a>' +
        '<a href="https://prepsto.com/#f/73d9np2" target="_blank" rel="noopener" data-prepsto-open>Submit feedback</a>' +
        '<button type="button" data-lk-open="overview">Privacy &amp; Terms</button>' +
        '</div><p class="ui-footer-legal small muted">© ' + new Date().getFullYear() + ' ' + esc(UI.config.name) + '</p></div>';
    },
    tabbar: function (me, active) {
      var nav = UI.navPages();
      if (!me || nav.length < 2) return '';
      return nav.slice(0, 4).map(function (p) {
        return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
      }).join('') + '<a href="#profile" class="' + (active === 'profile' ? 'on' : '') + '">' + UI.icon('user') + '<span>You</span></a>';
    },
    wire: function (root) {
      root.addEventListener('click', function (e) {
        var t = e.target.closest('[data-menu-toggle]');
        var menu = root.querySelector('[data-menu]');
        if (t && menu) { menu.hidden = !menu.hidden; t.setAttribute('aria-expanded', String(!menu.hidden)); return; }
        if (e.target.closest('[data-signout]')) { UI.auth('logout').then(function () { UI.toast('Signed out. See you soon!'); }); }
        if (menu && !menu.hidden && !e.target.closest('[data-menu] .ui-seg')) menu.hidden = true;
      });
      document.addEventListener('keydown', function (e) {
        var menu = root.querySelector('[data-menu]');
        if (e.key === 'Escape' && menu) menu.hidden = true;
      });
    },
    onTheme: function () {  // redraw the menu's Auto/Light/Dark buttons and keep the menu open
      var menu = document.querySelector('[data-menu]'), open = menu && !menu.hidden;
      UI.renderChrome();
      if (open) document.querySelector('[data-menu]').hidden = false;
    }
  };
})();


/* ===== _pc.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var PC = window.PC = {};

  /* extra icons for this app */
  var I = UI.ICONS;
  I.book = '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/>';
  I.flame = '<path d="M12 3c.6 3.6 5.5 5.6 5.5 10.8A5.5 5.5 0 0 1 6.5 13.8c0-2.6 1.4-4.3 2.6-5.3 0 2 .9 3.1 1.9 3.3C11 9 10.6 6.2 12 3z"/>';
  I.crown = '<path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z"/><path d="M5 19h14"/>';
  I.film = '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>';
  I.upload = '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>';
  I.download = '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>';
  I.share = '<circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.6-4.4M8.2 13.2l7.6 4.4"/>';
  I.flag = '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>';
  I.up = '<path d="m6 15 6-6 6 6"/>';
  I.down = '<path d="m6 9 6 6 6-6"/>';
  I.wand = '<path d="M4 20 15 9M14 4v3M19 9h-3M17.5 5.5l-2 2M9 3v2M3 9h2"/>';
  I.layout = '<rect x="3" y="3" width="11" height="18" rx="2"/><rect x="16" y="3" width="5" height="8" rx="1.5"/><rect x="16" y="13" width="5" height="8" rx="1.5"/>';
  I.quote = '<path d="M7 7h4v4c0 3-2 5-4 6M15 7h4v4c0 3-2 5-4 6"/>';
  I.eye = '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>';

  /* ---------------------------------------------------------------- photos and covers */
  PC.apiBase = function () { return (window.APP_API || '_/api').replace(/\/$/, ''); };
  PC.photo = function (key, thumb) { return key ? PC.apiBase() + '/photo?k=' + encodeURIComponent(key) + (thumb ? '&s=t' : '') : ''; };
  PC.cover = function (b, opts) {
    opts = opts || {};
    return '<div class="pc-cover' + (opts.cls ? ' ' + opts.cls : '') + '">' + (opts.badge ? '<span class="pc-badge-new">' + esc(opts.badge) + '</span>' : '') +
      (b.cover ? '<img src="' + PC.photo(b.cover, !opts.full) + '" alt="Cover of ' + esc(b.title) + '" loading="lazy">' : '<div class="ph">' + esc(b.title) + '</div>') + '</div>';
  };
  PC.spice = function (n) {
    var out = '<span class="pc-spice" title="Spice ' + n + ' of 5" aria-label="Spice ' + n + ' of 5">';
    for (var i = 1; i <= 5; i++) out += '<span class="' + (i <= n ? '' : 'off') + '">' + UI.icon('flame') + '</span>';
    return out + '</span>';
  };
  PC.days = function (iso) {
    if (!iso) return null;
    var d = new Date(iso + 'T12:00:00'), t = new Date(); t.setHours(12, 0, 0, 0);
    return Math.round((d - t) / 86400000);
  };
  PC.when = function (iso) {
    var n = PC.days(iso);
    if (n === null) return '<span class="pc-when">Release date to come</span>';
    if (n > 1) return '<span class="pc-when soon">Out in ' + n + ' days</span>';
    if (n === 1) return '<span class="pc-when soon">Out tomorrow</span>';
    if (n === 0) return '<span class="pc-when new">Out today!</span>';
    if (n > -31) return '<span class="pc-when new">New · ' + UI.fmtDate(iso, { day: 'numeric', month: 'short' }) + '</span>';
    return '<span class="pc-when">' + UI.fmtDate(iso, { month: 'short', year: 'numeric' }) + '</span>';
  };
  PC.bookCard = function (b) {
    var n = PC.days(b.release), badge = n !== null && n > 0 ? 'Soon' : n !== null && n > -15 ? 'New' : '';
    return '<a class="pc-book" href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + PC.cover(b, { badge: badge }) +
      '<h3>' + esc(b.title) + '</h3><div class="by">' + esc(b.author) + '</div>' +
      '<div class="meta">' + PC.when(b.release) + (b.casts ? '<span class="small muted">' + UI.icon('heart') + ' ' + b.casts + '</span>' : '') + '</div></a>';
  };
  PC.seriesLine = function (b) { return b.series ? esc(b.series) + (b.series_no ? ' · Book ' + b.series_no : '') : 'Standalone'; };

  /* ---------------------------------------------------------------- collages */
  PC.LAYOUTS = { hero: 'Leading star', grid: 'Gallery grid', polaroid: 'Polaroid wall', strip: 'Film strip' };
  PC.TONES = { rose: 'Rose', violet: 'Violet', crimson: 'Crimson', midnight: 'Midnight' };
  PC.mono = function (name) { return '<div class="mono">' + esc(UI.initials(name)) + '</div>'; };
  PC.collage = function (c, opts) {
    opts = opts || {};
    var picks = (c.picks || []).slice(0, 6), n = Math.max(1, picks.length);
    return '<div class="pc-col lay-' + esc(c.layout || 'hero') + ' tone-' + esc(c.tone || 'rose') + ' n' + n + (opts.big ? ' big' : '') + '">' +
      picks.map(function (p, i) {
        var thumb = !opts.big && !(i === 0 && (c.layout || 'hero') === 'hero');
        return '<figure class="pc-pick">' + (i === 0 && picks.length > 1 && (c.layout === 'hero' || !c.layout) ? '<span class="lead">Lead</span>' : '') +
          (p.photo ? '<img src="' + PC.photo(p.photo, thumb) + '" alt="' + esc(p.name) + '" loading="lazy">' : PC.mono(p.name)) +
          '<figcaption>' + esc(p.name) + '</figcaption></figure>';
      }).join('') + (picks.length ? '' : '<figure class="pc-pick">' + PC.mono('?') + '<figcaption>Add a star</figcaption></figure>') + '</div>';
  };
  PC.heartBtn = function (c, lg) {
    return '<button type="button" class="pc-heart' + (c.hearted ? ' on' : '') + (lg ? ' lg' : '') + '" data-heart="' + esc(c.key) + '" aria-pressed="' + (c.hearted ? 'true' : 'false') + '"' +
      (c.mine ? ' title="Your collage"' : ' title="Swoon"') + '>' + UI.icon('heart') + '<span>' + (c.hearts || 0) + '</span></button>';
  };
  PC.castCard = function (c, opts) {
    opts = opts || {};
    return '<article class="pc-cast" data-cast="' + esc(c.key) + '"><a href="#cast/' + esc(c.key) + '" data-go="cast/' + esc(c.key) + '" aria-label="Open this collage">' + PC.collage(c) + '</a>' +
      '<div class="body"><div class="who"><span class="ui-avatar grad">' + esc(UI.initials(c.user.name)) + '</span>' +
      (c.user.id ? '<a href="#fan/' + esc(c.user.id) + '" data-go="fan/' + esc(c.user.id) + '">' + esc(c.user.name) + '</a>' : '<b>' + esc(c.user.name) + '</b>') +
      '<span class="t">· ' + esc(UI.ago(c.updated)) + '</span></div>' +
      (c.caption ? '<p class="cap">' + esc(c.caption) + '</p>' : '') +
      (opts.noFor || !c.character ? '' : '<div class="for">as <a href="#character/' + esc(c.character.key) + '" data-go="character/' + esc(c.character.key) + '">' + esc(c.character.name) + '</a>' +
        (c.book ? ' in <i>' + esc(c.book.title) + '</i>' : '') + '</div>') +
      '<div class="foot">' + PC.heartBtn(c) + '<span class="c">' + UI.icon('chat') + c.comments + '</span>' +
      (c.hidden ? '<span class="ui-badge bad">Hidden by a moderator</span>' : '') + '</div></div></article>';
  };
  PC.castGrid = function (list, opts) {
    return '<div class="pc-casts">' + list.map(function (c) { return PC.castCard(c, opts); }).join('') + '</div>';
  };

  /* ---------------------------------------------------------------- signing in, hearts, fx */
  PC.needSignIn = function (why) {
    UI.after = location.hash;
    var m = UI.modal('<div style="text-align:center"><img src="_/theme/icon.svg" width="56" height="56" alt="" style="border-radius:16px;margin-bottom:10px">' +
      '<h2 style="padding:0">Join the casting couch</h2><p class="muted">' + esc(why || 'Sign up to cast characters, swoon over collages and join the conversation.') + ' It\'s free.</p>' +
      '<div class="ui-row" style="justify-content:center;margin-top:16px"><a class="ui-btn" href="#auth" data-go="auth" data-close>Sign in</a>' +
      '<a class="ui-btn primary" href="#auth/signup" data-go="auth/signup" data-close>Create an account</a></div></div>');
    return m;
  };
  PC.hearts = function (n) {
    var box = document.createElement('div'), glyphs = ['♥', '✦', '♥', '❤'], colors = ['#e11d74', '#c026d3', '#7c3aed', '#f43f5e', '#f9a8d4'];
    box.className = 'pc-hearts-fx';
    for (var i = 0; i < (n || 26); i++) {
      var h = document.createElement('i');
      h.textContent = glyphs[i % glyphs.length];
      h.style.left = (Math.random() * 100) + 'vw';
      h.style.color = colors[i % colors.length];
      h.style.fontSize = (14 + Math.random() * 22) + 'px';
      h.style.setProperty('--dx', (Math.random() * 120 - 60) + 'px');
      h.style.setProperty('--r', (Math.random() * 120 - 60) + 'deg');
      h.style.setProperty('--d', (1.8 + Math.random() * 1.6) + 's');
      h.style.animationDelay = (Math.random() * 0.5) + 's';
      box.appendChild(h);
    }
    document.body.appendChild(box);
    setTimeout(function () { box.remove(); }, 4200);
  };
  /* One listener per page view: swoon buttons anywhere in `view`. */
  PC.wireHearts = function (view) {
    view.addEventListener('click', function (e) {
      var b = e.target.closest('[data-heart]');
      if (!b) return;
      e.preventDefault();
      if (!UI.me) { PC.needSignIn('Sign up to swoon over collages.'); return; }
      UI.apiQuiet('toggle_heart', b.getAttribute('data-heart')).then(function (r) {
        view.querySelectorAll('[data-heart="' + b.getAttribute('data-heart') + '"]').forEach(function (x) {
          x.classList.toggle('on', r.hearted); x.setAttribute('aria-pressed', r.hearted ? 'true' : 'false');
          x.querySelector('span').textContent = r.hearts;
          if (r.hearted) { x.classList.remove('pop'); void x.offsetWidth; x.classList.add('pop'); }
        });
      });
    });
  };

  /* ---------------------------------------------------------------- photos: crop, shrink, upload */
  PC.SHAPES = { portrait: { w: 600, h: 750, tw: 320, th: 400, limit: 210 * 1024 }, cover: { w: 600, h: 900, tw: 300, th: 450, limit: 300 * 1024 } };
  function loadImage(src) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.onload = function () { resolve(img); };
      img.onerror = function () { reject(new Error('That picture couldn\'t be read. Try a JPEG, PNG or WebP.')); };
      img.src = src;
    });
  }
  function bytesOf(dataUrl) { return Math.round((dataUrl.length - dataUrl.indexOf(',') - 1) * 3 / 4); }
  function encode(canvas, limit) {
    var q = [0.84, 0.76, 0.68, 0.6, 0.5], url = '';
    for (var i = 0; i < q.length; i++) { url = canvas.toDataURL('image/jpeg', q[i]); if (bytesOf(url) <= limit) break; }
    return url;
  }
  PC.kb = function (n) { if (!n) return '0 KB'; return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'; };
  /* Show the cropper for a picked file. Resolves {full, thumb, label, bytes} or null (cancelled). */
  PC.crop = function (file, opts) {
    opts = opts || {};
    var shape = PC.SHAPES[opts.kind || 'portrait'];
    if (!file || !/^image\//.test(file.type || '')) return Promise.reject(new Error('That file isn\'t a picture.'));
    if (file.size > 25 * 1048576) return Promise.reject(new Error('That picture is huge (over 25 MB). Try a smaller one.'));
    var url = URL.createObjectURL(file);
    return loadImage(url).then(function (img) {
      return new Promise(function (resolve) {
        var done = false;
        var m = UI.modal('<h2>' + (opts.kind === 'cover' ? 'Frame the cover' : 'Frame the photo') + '</h2>' +
          '<p class="muted small">Drag to move, zoom with the slider. We save a small ' + shape.w + '×' + shape.h + ' picture, so your drawer stays light.</p>' +
          '<div class="pc-crop' + (opts.kind === 'cover' ? ' cover' : '') + '" data-frame style="aspect-ratio:' + shape.w + ' / ' + shape.h + '"></div>' +
          '<label class="pc-zoom">' + UI.icon('image') + '<input type="range" min="1" max="4" step="0.01" value="1" data-zoom aria-label="Zoom">' + UI.icon('search') + '</label>' +
          (opts.kind === 'cover' ? '' : '<label class="ui-field" style="margin-top:14px"><span>Who is this?</span><input type="text" name="label" maxlength="60" value="' + esc(opts.label || '') + '" placeholder="The star\'s name"></label>') +
          '<div class="ui-row end" style="margin-top:18px"><button class="ui-btn ghost" type="button" data-close>Cancel</button><button class="ui-btn primary" type="button" data-use>' + UI.icon('check') + 'Use this photo</button></div>',
        { onclose: function () { URL.revokeObjectURL(url); if (!done) resolve(null); } });
        var frame = m.el.querySelector('[data-frame]'), zoom = m.el.querySelector('[data-zoom]');
        img.alt = '';
        frame.appendChild(img);
        var W, H, base, z = 1, x = 0, y = 0;
        function measure() { W = frame.clientWidth || 300; H = W * shape.h / shape.w; base = Math.max(W / img.naturalWidth, H / img.naturalHeight); }
        function clamp() {
          var s = base * z, iw = img.naturalWidth * s, ih = img.naturalHeight * s;
          x = Math.min(0, Math.max(W - iw, x)); y = Math.min(0, Math.max(H - ih, y));
        }
        function paint() { clamp(); img.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + (base * z) + ')'; }
        measure();
        x = (W - img.naturalWidth * base) / 2; y = (H - img.naturalHeight * base) / 2;
        paint();
        function setZoom(nz, cx, cy) {
          nz = Math.max(1, Math.min(4, nz));
          cx = cx == null ? W / 2 : cx; cy = cy == null ? H / 2 : cy;
          var k = nz / z; x = cx - (cx - x) * k; y = cy - (cy - y) * k; z = nz; zoom.value = z; paint();
        }
        zoom.addEventListener('input', function () { setZoom(parseFloat(zoom.value)); });
        var pts = {}, last = null, pinch = null;
        frame.addEventListener('pointerdown', function (e) { frame.setPointerCapture(e.pointerId); pts[e.pointerId] = [e.clientX, e.clientY]; last = [e.clientX, e.clientY]; });
        frame.addEventListener('pointermove', function (e) {
          if (!pts[e.pointerId]) return;
          pts[e.pointerId] = [e.clientX, e.clientY];
          var ids = Object.keys(pts);
          if (ids.length === 2) {
            var a = pts[ids[0]], b = pts[ids[1]], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
            if (pinch) { var r = frame.getBoundingClientRect(); setZoom(z * d / pinch, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top); }
            pinch = d; return;
          }
          if (last) { x += e.clientX - last[0]; y += e.clientY - last[1]; paint(); }
          last = [e.clientX, e.clientY];
        });
        function up(e) { delete pts[e.pointerId]; pinch = null; last = null; }
        frame.addEventListener('pointerup', up); frame.addEventListener('pointercancel', up);
        frame.addEventListener('wheel', function (e) { e.preventDefault(); var r = frame.getBoundingClientRect(); setZoom(z * (e.deltaY < 0 ? 1.08 : 0.93), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
        m.el.querySelector('[data-use]').addEventListener('click', function () {
          var c = document.createElement('canvas'); c.width = shape.w; c.height = shape.h;
          var g = c.getContext('2d'), k = shape.w / W, s = base * z;
          g.fillStyle = '#ffffff'; g.fillRect(0, 0, c.width, c.height);
          g.imageSmoothingQuality = 'high';
          g.drawImage(img, x * k, y * k, img.naturalWidth * s * k, img.naturalHeight * s * k);
          var t = document.createElement('canvas'); t.width = shape.tw; t.height = shape.th;
          var tg = t.getContext('2d'); tg.imageSmoothingQuality = 'high'; tg.drawImage(c, 0, 0, t.width, t.height);
          var full = encode(c, shape.limit), thumb = encode(t, 44 * 1024);
          var label = m.el.querySelector('[name=label]');
          done = true; m.close();
          resolve({ full: full, thumb: thumb, label: label ? label.value.trim() : '', bytes: bytesOf(full) + bytesOf(thumb) });
        });
      });
    }, function (err) { URL.revokeObjectURL(url); throw err; });
  };
  /* Crop + upload. Resolves the server's {photo, quota} or null. */
  PC.uploadFile = function (file, opts) {
    opts = opts || {};
    return PC.crop(file, opts).then(function (c) {
      if (!c) return null;
      return UI.api('upload_photo', c.full, c.thumb, c.label || opts.label || '', opts.kind || 'portrait').then(function (r) {
        UI.toast('Saved (' + PC.kb(c.bytes) + ')', 'ok');
        return r;
      });
    });
  };
  PC.fileInput = function (multiple) {
    return '<input type="file" accept="image/jpeg,image/png,image/webp,image/*"' + (multiple ? ' multiple' : '') + ' data-file>';
  };
  /* Choose a picture for a collage spot: upload a new one, or reuse one from the drawer.
     Resolves {key, label} or null. `photos` is the drawer list (updated in place on upload). */
  PC.choosePhoto = function (photos, opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var picked = false, q = (opts.label || '').toLowerCase();
      var sorted = photos.slice().sort(function (a, b) { return (b.label.toLowerCase() === q) - (a.label.toLowerCase() === q); });
      var m = UI.modal('<h2>Choose a photo' + (opts.label ? ' of ' + esc(opts.label) : '') + '</h2>' +
        '<label class="pc-upload-zone" data-zone>' + UI.icon('upload') + '<b>Upload a new photo</b><span class="small muted">JPEG, PNG or WebP. You\'ll frame it next; we keep a small copy.</span>' + PC.fileInput(false) + '</label>' +
        (photos.length ? '<h4 style="margin:18px 0 8px">Or reuse one from your drawer <span class="muted small">(' + photos.length + ')</span></h4><div class="pc-drawer-grid">' +
          sorted.map(function (p) { return '<button type="button" data-pick="' + esc(p.key) + '" title="' + esc(p.label) + '"><img src="' + PC.photo(p.key, true) + '" alt="' + esc(p.label) + '" loading="lazy">' + (p.label ? '<span>' + esc(p.label) + '</span>' : '') + '</button>'; }).join('') + '</div>' : ''),
      { wide: true, onclose: function () { if (!picked) resolve(null); } });
      m.el.addEventListener('click', function (e) {
        var b = e.target.closest('[data-pick]');
        if (!b) return;
        var p = photos.filter(function (x) { return x.key === b.getAttribute('data-pick'); })[0];
        picked = true; m.close(); resolve({ key: p.key, label: p.label });
      });
      m.el.querySelector('[data-file]').addEventListener('change', function (e) {
        var f = e.target.files && e.target.files[0];
        if (!f) return;
        picked = true; m.close();
        PC.uploadFile(f, { label: opts.label }).then(function (r) {
          if (!r) { resolve(null); return; }
          photos.unshift(r.photo);
          if (opts.onQuota) opts.onQuota(r.quota);
          resolve({ key: r.photo.key, label: r.photo.label });
        }, function (err) { UI.toast(err.message, 'error'); resolve(null); });
      });
    });
  };
  PC.quotaHtml = function (q) {
    if (!q) return '';
    if (q.max == null) return '<span class="small muted">' + q.used + ' photos · ' + PC.kb(q.bytes) + '</span>';
    var pct = Math.min(100, Math.round(100 * q.used / q.max));
    return '<div class="pc-quota"><div class="ui-row between small"><span><b>' + q.used + '</b> of ' + q.max + ' photos</span><span class="muted">' + PC.kb(q.bytes) + '</span></div>' +
      '<div class="pc-meter" style="margin-top:6px"><b style="width:' + pct + '%"></b></div></div>';
  };

  /* ---------------------------------------------------------------- save a collage as an image (1080x1350 PNG) */
  var TONE_STOPS = { rose: ['#ffd6e7', '#f9a8d4', '#fb7185'], violet: ['#ede4ff', '#c4b5fd', '#a78bfa'], crimson: ['#ffd1d8', '#f43f5e', '#9f1239'], midnight: ['#3b1069', '#1e1b4b', '#4c0519'] };
  function rr(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function drawCover(g, img, x, y, w, h) {
    var s = Math.max(w / img.naturalWidth, h / img.naturalHeight), iw = img.naturalWidth * s, ih = img.naturalHeight * s;
    g.drawImage(img, x + (w - iw) / 2, y + (h - ih) / 2, iw, ih);
  }
  function slots(n, layout, X, Y, W, H) {
    var out = [], gap = 18, i;
    if (layout === 'hero' && n > 1) {
      var bw = (W - gap) * 0.64, side = W - bw - gap, topH = n > 4 ? H * 0.66 : H;
      var right = Math.min(n - 1, n > 4 ? 2 : 3), sh = (topH - gap * (right - 1)) / right, rest = n - 1 - right;
      out.push([X, Y, bw, topH]);
      for (i = 0; i < right; i++) out.push([X + bw + gap, Y + i * (sh + gap), side, sh]);
      if (rest > 0) {
        var cw = (W - gap * (rest - 1)) / rest;
        for (i = 0; i < rest; i++) out.push([X + i * (cw + gap), Y + topH + gap, cw, H - topH - gap]);
      }
      return out;
    }
    var cols = n <= 1 ? 1 : n === 2 || n === 4 ? 2 : 3, rws = Math.ceil(n / cols);
    var cw2 = (W - gap * (cols - 1)) / cols, ch = Math.min((H - gap * (rws - 1)) / rws, cw2 * 1.25);
    var top = Y + (H - (ch * rws + gap * (rws - 1))) / 2;
    for (i = 0; i < n; i++) out.push([X + (i % cols) * (cw2 + gap), top + Math.floor(i / cols) * (ch + gap), cw2, ch]);
    return out;
  }
  PC.exportImage = function (c) {
    var picks = (c.picks || []).slice(0, 6);
    return (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () {
      return Promise.all(picks.map(function (p) { return p.photo ? loadImage(PC.photo(p.photo)).catch(function () { return null; }) : Promise.resolve(null); }));
    }).then(function (imgs) {
      var cv = document.createElement('canvas'); cv.width = 1080; cv.height = 1350;
      var g = cv.getContext('2d'), st = TONE_STOPS[c.tone] || TONE_STOPS.rose, dark = c.tone === 'midnight' || c.tone === 'crimson';
      var bg = g.createLinearGradient(0, 0, 1080, 1350); bg.addColorStop(0, st[0]); bg.addColorStop(0.55, st[1]); bg.addColorStop(1, st[2]);
      g.fillStyle = bg; g.fillRect(0, 0, 1080, 1350);
      var ink = dark ? '#fff4fa' : '#3b0d2e';
      g.fillStyle = ink; g.textAlign = 'center';
      g.font = '600 30px Manrope, sans-serif'; g.globalAlpha = 0.8;
      g.fillText(('My dream cast for ' + (c.book ? c.book.title : '')).toUpperCase().slice(0, 60), 540, 92);
      g.globalAlpha = 1; g.font = 'italic 700 92px "Cormorant Garamond", Georgia, serif';
      g.fillText(c.character ? c.character.name : '', 540, 190, 980);
      var area = slots(picks.length || 1, c.layout || 'hero', 70, 240, 940, 900);
      picks.forEach(function (p, i) {
        var s = area[i]; if (!s) return;
        g.save(); g.shadowColor = 'rgba(40,5,30,.35)'; g.shadowBlur = 24; g.shadowOffsetY = 10;
        rr(g, s[0], s[1], s[2], s[3], 22); g.fillStyle = '#fff'; g.fill(); g.restore();
        g.save(); rr(g, s[0], s[1], s[2], s[3], 22); g.clip();
        if (imgs[i]) drawCover(g, imgs[i], s[0], s[1], s[2], s[3]);
        else {
          var mg = g.createLinearGradient(s[0], s[1], s[0] + s[2], s[1] + s[3]); mg.addColorStop(0, '#6d28d9'); mg.addColorStop(0.6, '#db2777'); mg.addColorStop(1, '#e11d48');
          g.fillStyle = mg; g.fillRect(s[0], s[1], s[2], s[3]);
          g.fillStyle = '#fff'; g.font = 'italic 700 ' + Math.round(s[2] / 3.2) + 'px "Cormorant Garamond", Georgia, serif'; g.textBaseline = 'middle';
          g.fillText(UI.initials(p.name), s[0] + s[2] / 2, s[1] + s[3] / 2); g.textBaseline = 'alphabetic';
        }
        var fade = g.createLinearGradient(0, s[1] + s[3] - 120, 0, s[1] + s[3]); fade.addColorStop(0, 'rgba(30,5,25,0)'); fade.addColorStop(1, 'rgba(30,5,25,.8)');
        g.fillStyle = fade; g.fillRect(s[0], s[1] + s[3] - 120, s[2], 120);
        g.fillStyle = '#fff'; g.font = '700 ' + (i === 0 ? 40 : 28) + 'px Manrope, sans-serif';
        g.fillText(p.name, s[0] + s[2] / 2, s[1] + s[3] - (i === 0 ? 28 : 20), s[2] - 24);
        g.restore();
      });
      g.fillStyle = ink; g.font = 'italic 600 40px "Cormorant Garamond", Georgia, serif';
      g.fillText((c.caption || '').slice(0, 70), 540, 1215, 980);
      g.font = '700 28px Manrope, sans-serif'; g.globalAlpha = 0.85;
      g.fillText('♥ PerfectCast · cast by ' + (c.user ? c.user.name : 'a fan'), 540, 1290);
      g.globalAlpha = 1;
      return new Promise(function (resolve, reject) {
        try {
          cv.toBlob(function (blob) {
            if (!blob) { reject(new Error('The picture couldn\'t be made.')); return; }
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'perfectcast-' + String(c.character ? c.character.name : 'collage').toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.png';
            document.body.appendChild(a); a.click();
            setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
            resolve(blob);
          }, 'image/png');
        } catch (e) { reject(new Error('The picture couldn\'t be made in this browser.')); }
      });
    });
  };

  /* ---------------------------------------------------------------- share, report */
  PC.share = function (hash, title) {
    var url = location.href.split('#')[0] + hash;
    if (navigator.share) return navigator.share({ title: title, text: title + ' on PerfectCast', url: url }).catch(function () {});
    var show = function () { UI.modal('<h2>Share</h2><p class="muted small">Copy this link:</p><input type="text" readonly value="' + esc(url) + '" onfocus="this.select()">'); };
    if (navigator.clipboard) return navigator.clipboard.writeText(url).then(function () { UI.toast('Link copied. Paste it anywhere!', 'ok'); }, show);
    show();
  };
  PC.report = function (kind, id, reasons) {
    if (!UI.me) { PC.needSignIn('Sign in to report something to the admins.'); return; }
    reasons = reasons || { rude: 'Rude or hateful', spam: 'Spam or ads', explicit: 'Explicit picture', privacy: 'Private person or stolen photo', other: 'Something else' };
    var m = UI.modal('<h2>Report this ' + (kind === 'comment' ? 'comment' : 'collage') + '</h2><p class="muted">Only the admins see reports. Thank you for keeping PerfectCast kind.</p>' +
      '<form class="ui-stack" data-rep><div class="ui-choices">' + Object.keys(reasons).map(function (k, i) {
        return '<label class="ui-choice"><input type="radio" name="reason" value="' + k + '"' + (i === 0 ? ' checked' : '') + '><span>' + esc(reasons[k]) + '</span></label>';
      }).join('') + '</div><label class="ui-field"><span>Anything to add? <em>(optional)</em></span><textarea name="note" rows="3" maxlength="400"></textarea></label>' +
      '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + UI.icon('flag') + 'Send report</button></div></form>');
    m.el.querySelector('[data-rep]').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(e.target);
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('report', kind, id, v.reason, v.note)).then(function (r) { m.close(); UI.toast(r.message, 'ok'); });
    });
  };
})();

/* ===== admin.html ===== */
(function () {
  var esc = UI.esc;
  var TABS = [['overview', 'Overview', 'grid'], ['books', 'Books', 'book'], ['queue', 'Review', 'check'], ['reports', 'Reports', 'flag'],
              ['feedback', 'Feedback', 'inbox'], ['users', 'Users', 'users'], ['demo', 'Demo data', 'database']];

  UI.page('admin', { title: 'Admin', auth: 'admin' }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'overview';
    var fbFilter = 'new';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Admin</h1><p class="muted">Only admins see this page.</p></div></div>' +
      '<nav class="ui-tabs">' + TABS.map(function (t) {
        return '<a href="#admin/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + '</a>';
      }).join('') + '</nav><div data-body><div class="ui-skel"></div></div></div>';
    var body = view.querySelector('[data-body]');

    function overview() {
      return UI.api('admin_overview').then(function (d) {
        var stat = function (n, label, go) { return '<a class="ui-card ui-stat" href="#admin/' + go + '" style="text-decoration:none;color:inherit"><b>' + n + '</b><span>' + label + '</span></a>'; };
        body.innerHTML = '<div class="ad-stats">' + stat(d.users, 'people signed up', 'users') + stat(d.books, 'live books', 'books') +
          stat(d.castings, 'collages', 'overview') + stat(d.photos, 'photos · ' + d.photo_mb + ' MB', 'overview') +
          stat(d.queue, 'waiting for review', 'queue') + stat(d.reports, 'open reports', 'reports') +
          stat(d.feedback_new, 'new feedback', 'feedback') + stat(d.admins, UI.plural(d.admins, 'admin').replace(/^\d+ /, ''), 'users') + '</div>' +
          '<p class="muted small" style="margin-top:18px">Demo data is <b>' + esc(d.demo.state) + '</b> (' + d.demo.counts.users + ' demo fans, ' + d.demo.counts.books + ' demo books). Manage it in the Demo data tab.</p>';
      });
    }

    var bookList = [];
    function books() {
      return UI.api('admin_books').then(function (d) {
        bookList = d.books;
        body.innerHTML = '<div class="ui-row between" style="margin-bottom:14px"><span class="muted small">' + UI.plural(d.books.length, 'book') + '</span>' +
          '<button class="ui-btn primary" data-book-new>' + UI.icon('plus') + 'Add a book</button></div><div class="ad-books">' + d.books.map(function (b) {
            return '<div class="ad-book" data-bkey="' + esc(b.key) + '">' + PC.cover(b) + '<div style="min-width:0"><h3>' + esc(b.title) + '</h3>' +
              '<div class="small muted">' + esc(b.author) + ' · ' + (b.release ? esc(UI.fmtDate(b.release)) : 'no date') + ' · ' + UI.plural(b.characters.length, 'character') + ' · ' + UI.plural(b.casts, 'collage') + '</div>' +
              '<div style="margin-top:4px"><span class="ui-badge ' + (b.status === 'live' ? 'good' : b.status === 'pending' ? 'warn' : 'bad') + '">' + esc(b.status) + '</span></div></div>' +
              '<div class="ui-row"><a class="ui-btn sm" href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">View</a><button class="ui-btn sm" data-book-edit>' + UI.icon('edit') + 'Edit</button>' +
              '<button class="ui-btn sm danger" data-book-del>' + UI.icon('trash') + '</button></div></div>';
          }).join('') + '</div>';
        body._tropes = d.tropes;
      });
    }
    function editBook(b) {
      var m = UI.modal('<h2>' + (b ? 'Edit ' + esc(b.title) : 'Add a book') + '</h2><form data-bookf><div data-bf></div><div class="ui-row end" style="margin-top:18px">' +
        '<button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">Save</button></div></form>', { wide: true });
      var form = PC.bookForm(m.el.querySelector('[data-bf]'), { book: b, tropes: body._tropes || [], admin: true });
      m.el.querySelector('[data-bookf]').addEventListener('submit', function (e) {
        e.preventDefault();
        var v = form.values();
        if (!v) return;
        var kept = {}; v.characters.forEach(function (c) { if (c.key) kept[c.key] = 1; });
        var lost = b ? b.characters.filter(function (c) { return !kept[c.key] && c.casts; }) : [];
        (lost.length ? UI.confirm({ title: 'Remove ' + lost.map(function (c) { return c.name; }).join(', ') + '?', text: 'Their collages (' + lost.reduce(function (n, c) { return n + c.casts; }, 0) + ') are deleted too.', ok: 'Save anyway', danger: true }) : Promise.resolve(true))
          .then(function (yes) {
            if (!yes) return;
            UI.busy(e.target.querySelector('[type=submit]'), UI.api('admin_save_book', b ? b.key : null, v)).then(function () { m.close(); UI.toast('Saved', 'ok'); books(); });
          });
      });
    }

    function queue() {
      return UI.api('admin_queue').then(function (d) {
        body.innerHTML = '<h3>Suggested books <span class="muted small">(' + d.books.length + ')</span></h3>' +
          (d.books.length ? '<div class="ad-q">' + d.books.map(function (b) {
            return '<div class="ui-item" data-qkind="book" data-qkey="' + esc(b.key) + '">' + PC.cover(b) + '<div style="min-width:0"><h3>' + esc(b.title) + ' <span class="muted small">by ' + esc(b.author) + '</span></h3>' +
              '<p class="small muted">Suggested by ' + esc(b.submitted_by ? b.submitted_by.name : 'someone') + ' · ' + esc(UI.ago(b.submitted_at)) + ' · ' + (b.release ? 'out ' + esc(UI.fmtDate(b.release)) : 'no date') + '</p>' +
              (b.blurb ? '<p>' + esc(b.blurb) + '</p>' : '') + '<p class="small"><b>Characters:</b> ' + b.characters.map(function (c) { return esc(c.name) + ' (' + esc(c.role_label) + ')'; }).join(', ') + '</p>' +
              '<div class="ui-row" style="margin-top:10px"><button class="ui-btn sm primary" data-review="approve">' + UI.icon('check') + 'Approve</button><button class="ui-btn sm" data-qedit>' + UI.icon('edit') + 'Edit first</button>' +
              '<button class="ui-btn sm danger" data-review="reject">Turn down</button></div></div></div>';
          }).join('') + '</div>' : '<p class="muted">Nothing waiting.</p>') +
          '<h3 style="margin-top:26px">Suggested characters <span class="muted small">(' + d.characters.length + ')</span></h3>' +
          (d.characters.length ? '<div class="ad-q">' + d.characters.map(function (c) {
            return '<div class="ui-item char" data-qkind="character" data-qkey="' + esc(c.key) + '"><div><h3 style="margin:0">' + esc(c.name) + ' <span class="ui-badge">' + esc(c.role_label) + '</span></h3>' +
              '<p class="small muted">in <a href="#book/' + esc(c.book.key) + '" data-go="book/' + esc(c.book.key) + '">' + esc(c.book.title) + '</a> · by ' + esc(c.by.name) + ' · ' + esc(UI.ago(c.submitted_at)) + '</p>' +
              (c.blurb ? '<p>' + esc(c.blurb) + '</p>' : '') + '<div class="ui-row" style="margin-top:8px"><button class="ui-btn sm primary" data-review="approve">' + UI.icon('check') + 'Approve</button>' +
              '<button class="ui-btn sm danger" data-review="reject">Turn down</button></div></div></div>';
          }).join('') + '</div>' : '<p class="muted">Nothing waiting.</p>');
        body._queue = d;
      });
    }

    var repFilter = 'open';
    function reports() {
      return UI.api('admin_reports', repFilter).then(function (d) {
        body.innerHTML = '<div class="ui-row" style="margin-bottom:16px"><div class="ui-seg">' + [['open', 'Open (' + d.open + ')'], ['all', 'All']].map(function (f) {
          return '<button data-repf="' + f[0] + '" class="' + (repFilter === f[0] ? 'on' : '') + '">' + f[1] + '</button>'; }).join('') + '</div></div>' +
          (d.reports.length ? '<div class="ad-fb ad-rep">' + d.reports.map(function (r) {
            var t = r.target, c = t.cast;
            return '<div class="ui-item" data-rid="' + esc(r.id) + '"><div class="meta"><span class="ui-badge bad">' + esc(r.reason) + '</span><b>' + esc(r.by.name) + '</b><span>' + esc(UI.fmtDateTime(r.created)) + '</span>' +
              (r.status !== 'open' ? '<span class="ui-badge good">done</span>' : '') + '</div>' + (r.note ? '<p class="msg">' + esc(r.note) + '</p>' : '') +
              (t.kind === 'comment' ? '<div class="quote"><b>' + esc(t.by.name) + '</b> commented' + (t.hidden ? ' (hidden)' : '') + ':\n' + esc(t.body) + '</div>' : '') +
              (c ? '<div class="prev"><a href="#cast/' + esc(c.key) + '" data-go="cast/' + esc(c.key) + '">' + PC.collage(c) + '</a><div class="small"><b>' + esc(c.user.name) + '</b>\'s ' + esc(c.character ? c.character.name : '') +
                (c.hidden ? ' <span class="ui-badge bad">hidden</span>' : '') + '<p class="muted">' + esc(c.caption) + '</p>' +
                (c.hidden ? '<button class="ui-btn sm" data-unhide="' + esc(c.key) + '">Unhide collage</button>' : '') + '</div></div>' : '<p class="muted small">The collage is gone.</p>') +
              (r.status === 'open' ? '<div class="ui-row"><button class="ui-btn sm" data-resolve="dismiss">Nothing wrong</button><button class="ui-btn sm" data-resolve="hide">' + UI.icon('lock') + 'Hide the ' + t.kind.replace('casting', 'collage') + '</button>' +
                '<button class="ui-btn sm danger" data-resolve="delete">' + UI.icon('trash') + 'Delete it</button></div>' : '') + '</div>';
          }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('flag') + '<h3>No reports</h3><p>Reports from members show up here.</p></div>');
      });
    }

    function feedback() {
      return UI.api('list_feedback', null).then(function (d) {
        var items = d.items.filter(function (i) { return fbFilter === 'all' || i.status === fbFilter; });
        body.innerHTML = '<div class="ui-row" style="margin-bottom:16px"><div class="ui-seg">' + [['new', 'New'], ['read', 'Read'], ['done', 'Done'], ['all', 'All']].map(function (f) {
          var n = f[0] === 'all' ? d.items.length : d.counts[f[0]];
          return '<button data-filter="' + f[0] + '" class="' + (fbFilter === f[0] ? 'on' : '') + '">' + f[1] + ' (' + n + ')</button>';
        }).join('') + '</div></div>' +
          (items.length ? '<div class="ad-fb">' + items.map(function (i) {
            var c = i.context || {};
            return '<div class="ui-item" data-id="' + esc(i.id) + '"><div class="meta"><span class="ui-badge ' + (i.kind === 'bug' ? 'bad' : i.kind === 'idea' ? 'brand' : '') + '">' + esc(i.kind_label) + '</span>' +
              '<b>' + esc(i.name) + '</b>' + (i.email ? '<a href="mailto:' + esc(i.email) + '">' + esc(i.email) + '</a>' : '') + '<span>' + esc(UI.fmtDateTime(i.created)) + '</span></div>' +
              '<p class="msg">' + esc(i.message) + '</p>' +
              '<div class="ctx">' + esc([c.page, c.screen, c.theme, c.browser].filter(Boolean).join(' · ')) + '</div>' +
              '<textarea data-note placeholder="Private note (only admins see it)">' + esc(i.note) + '</textarea>' +
              '<div class="ui-row" style="margin-top:10px">' + ['new', 'read', 'done'].map(function (s) {
                return '<button class="ui-btn sm' + (i.status === s ? ' primary' : '') + '" data-status="' + s + '">' + s[0].toUpperCase() + s.slice(1) + '</button>';
              }).join('') + '<span class="ui-spacer"></span><button class="ui-btn sm danger" data-del-fb>' + UI.icon('trash') + 'Delete</button></div></div>';
          }).join('') + '</div>'
            : '<div class="ui-empty">' + UI.icon('inbox') + '<h3>No ' + (fbFilter === 'all' ? '' : fbFilter + ' ') + 'messages</h3><p>New feedback goes to Prepsto (prepsto.com). Older messages and requests from the app show up here.</p></div>');
      });
    }

    function users(query) {
      return UI.api('list_users', query || null).then(function (d) {
        body.innerHTML = '<form class="ui-row" data-search style="margin-bottom:14px"><input type="search" name="q" placeholder="Search by name or email" value="' + esc(query || '') + '" style="max-width:360px">' +
          '<button class="ui-btn" type="submit">' + UI.icon('search') + 'Search</button><span class="muted small">' + UI.plural(d.total, 'person', 'people') + '</span></form>' +
          '<table class="ad-users"><thead><tr><th>Name</th><th>Email</th><th>Joined</th><th>Admin</th><th>Active</th></tr></thead><tbody>' +
          d.users.map(function (u) {
            return '<tr data-id="' + esc(u.id) + '"><td><b>' + esc(u.name) + '</b></td><td class="email">' + esc(u.email) + '</td><td class="joined muted">' + esc(UI.fmtDate(u.joined)) + '</td>' +
              '<td><label class="ui-check"><input type="checkbox" data-admin' + (u.is_admin ? ' checked' : '') + '> Admin</label></td>' +
              '<td><label class="ui-check"><input type="checkbox" data-enabled' + (u.enabled ? ' checked' : '') + '> Active</label></td></tr>';
          }).join('') + '</tbody></table>';
      });
    }

    function demo() {
      return UI.api('admin_overview').then(function (d) {
        var c = d.demo.counts;
        body.innerHTML = '<div class="ui-card ui-narrow" style="margin:0"><h3>Demo data</h3>' +
          '<p class="muted">Example people and content, so the app never looks empty for the first visitors. Demo rows are flagged, so removing them never touches real data. Once removed, it stays removed until you load it again.</p>' +
          '<p>Status: <b>' + esc(d.demo.state) + '</b> · ' + Object.keys(c).map(function (k) { return c[k] + ' ' + esc(k); }).join(', ') + '</p>' +
          '<div class="ui-row"><button class="ui-btn primary" data-demo="load">' + UI.icon('refresh') + (d.demo.state === 'loaded' ? 'Reload demo data' : 'Load demo data') + '</button>' +
          '<button class="ui-btn danger" data-demo="remove">' + UI.icon('trash') + 'Remove demo data</button></div></div>';
      });
    }

    var DRAW = { overview: overview, books: books, queue: queue, reports: reports, feedback: feedback, users: users, demo: demo };

    view.addEventListener('click', function (e) {
      if (e.target.closest('[data-book-new]')) { editBook(null); return; }
      var bk = e.target.closest('[data-bkey]');
      if (bk && e.target.closest('[data-book-edit]')) { editBook(bookList.filter(function (b) { return b.key === bk.getAttribute('data-bkey'); })[0]); return; }
      if (bk && e.target.closest('[data-book-del]')) {
        UI.confirm({ title: 'Delete this book?', text: 'Its characters and every collage of them are deleted. This can\'t be undone.', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('admin_delete_book', bk.getAttribute('data-bkey')).then(function () { UI.toast('Book deleted'); books(); });
        });
        return;
      }
      var qi = e.target.closest('[data-qkey]');
      if (qi && e.target.closest('[data-qedit]')) {
        UI.api('admin_books').then(function (d) { body._tropes = d.tropes; editBook(d.books.filter(function (b) { return b.key === qi.getAttribute('data-qkey'); })[0]); });
        return;
      }
      var rv = e.target.closest('[data-review]');
      if (qi && rv) { UI.busy(rv, UI.api('admin_review', qi.getAttribute('data-qkind'), qi.getAttribute('data-qkey'), rv.getAttribute('data-review'))).then(function () { UI.toast(rv.getAttribute('data-review') === 'approve' ? 'Approved' : 'Turned down', 'ok'); queue(); }); return; }
      var rf = e.target.closest('[data-repf]');
      if (rf) { repFilter = rf.getAttribute('data-repf'); reports(); return; }
      var rs = e.target.closest('[data-resolve]');
      if (rs) { UI.busy(rs, UI.api('admin_resolve', rs.closest('[data-rid]').getAttribute('data-rid'), rs.getAttribute('data-resolve'))).then(function () { UI.toast('Done', 'ok'); reports(); }); return; }
      var uh = e.target.closest('[data-unhide]');
      if (uh) { UI.api('admin_unhide', 'casting', uh.getAttribute('data-unhide')).then(function () { UI.toast('Visible again', 'ok'); reports(); }); return; }
      var f = e.target.closest('[data-filter]');
      if (f) { fbFilter = f.getAttribute('data-filter'); feedback(); return; }
      var st = e.target.closest('[data-status]');
      if (st) {
        var card = st.closest('[data-id]');
        UI.api('set_feedback_status', card.getAttribute('data-id'), st.getAttribute('data-status'), card.querySelector('[data-note]').value).then(function () { UI.toast('Saved', 'ok'); feedback(); });
        return;
      }
      var del = e.target.closest('[data-del-fb]');
      if (del) {
        UI.confirm({ title: 'Delete this message?', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_feedback', del.closest('[data-id]').getAttribute('data-id')).then(feedback);
        });
        return;
      }
      var dm = e.target.closest('[data-demo]');
      if (dm) {
        var load = dm.getAttribute('data-demo') === 'load';
        UI.confirm({ title: load ? 'Load the demo data?' : 'Remove the demo data?', text: load ? 'Demo people and content are added (any old demo rows are replaced).' : 'Every demo row is deleted. Real data stays.', ok: load ? 'Load' : 'Remove', danger: !load })
          .then(function (yes) { if (yes) UI.busy(dm, UI.api(load ? 'demo_load' : 'demo_remove')).then(function () { UI.toast('Done', 'ok'); demo(); }); });
      }
    });
    view.addEventListener('change', function (e) {
      var row = e.target.closest('tr[data-id]');
      if (!row) return;
      var id = row.getAttribute('data-id'), box = e.target;
      var fn = box.hasAttribute('data-admin') ? 'set_admin' : box.hasAttribute('data-enabled') ? 'set_enabled' : null;
      if (fn) UI.api(fn, id, box.checked).then(function () { UI.toast('Saved', 'ok'); }, function (err) { box.checked = !box.checked; UI.toast(err.message, 'error'); });
    });
    view.addEventListener('submit', function (e) {
      if (e.target.matches('[data-search]')) { e.preventDefault(); users(UI.formData(e.target).q); }
    });
    return DRAW[tab]();
  });
})();

/* ===== auth.html ===== */
(function () {
  var esc = UI.esc;
  var GOOGLE_G = '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>' +
    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>' +
    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>' +
    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
  function pw(name, auto) {
    return '<div class="au-pw"><input type="password" name="' + name + '" autocomplete="' + auto + '" required minlength="8">' +
      '<button type="button" data-show>Show</button></div>';
  }
  UI.page('auth', { title: 'Sign in', auth: 'guest' }, function (view, ctx) {
    var mode = ['signup', 'reset'].indexOf(ctx.args[0]) >= 0 ? ctx.args[0] : 'login';
    function draw(msg, isErr) {
      var heading = { login: 'Welcome back', signup: 'Create your account', reset: 'Reset your password' }[mode];
      var sub = { login: 'Sign in to continue to ' + esc(UI.config.name) + '.', signup: 'It\'s free and takes a few seconds.',
        reset: 'We\'ll email you a link to choose a new password.' }[mode];
      view.innerHTML = '<div class="au-wrap"><div class="ui-card au-card">' +
        '<h1>' + heading + '</h1><p class="muted">' + sub + '</p>' +
        (mode !== 'reset' ? '<div class="ui-seg" role="tablist"><button type="button" data-mode="login" class="' + (mode === 'login' ? 'on' : '') + '">Sign in</button>' +
          '<button type="button" data-mode="signup" class="' + (mode === 'signup' ? 'on' : '') + '">Create account</button></div>' : '<div style="height:14px"></div>') +
        '<form class="ui-stack" data-form="' + mode + '" novalidate>' +
        (mode === 'signup' ? '<label class="ui-field"><span>Your name</span><input type="text" name="name" autocomplete="name" required maxlength="60"></label>' : '') +
        '<label class="ui-field"><span>Email</span><input type="email" name="email" autocomplete="email" required></label>' +
        (mode === 'login' ? '<label class="ui-field"><span>Password</span>' + pw('password', 'current-password') + '</label>' : '') +
        (mode === 'signup' ? '<label class="ui-field"><span>Password <em>(at least 8 characters)</em></span>' + pw('password', 'new-password') + '</label>' +
          (window.LegalKit ? '<div>' + LegalKit.consentField() + '</div>' : '') : '') +
        '<div data-msg role="alert"' + (msg ? ' class="' + (isErr ? 'ui-error' : 'ui-note') + '">' + esc(msg) : ' hidden>') + '</div>' +
        '<button class="ui-btn primary block" type="submit">' + { login: 'Sign in', signup: 'Create account', reset: 'Send the link' }[mode] + '</button></form>' +
        (mode !== 'reset' ? '<div class="au-or">or</div><button type="button" class="ui-btn block au-google" data-google>' + GOOGLE_G + 'Continue with Google</button>' : '') +
        '<div class="au-links">' + (mode === 'login' ? '<a data-mode="reset">Forgot your password?</a>' : '<a data-mode="login">' + UI.icon('back') + ' Back to sign in</a>') +
        '<a href="#landing" data-go="landing">About ' + esc(UI.config.name) + '</a></div></div></div>';
      var first = view.querySelector('input');
      if (first && !msg) first.focus();
    }
    view.addEventListener('click', function (e) {
      var m = e.target.closest('[data-mode]');
      if (m) { e.preventDefault(); mode = m.getAttribute('data-mode'); history.replaceState(null, '', '#auth' + (mode === 'login' ? '' : '/' + mode)); draw(); return; }
      var g = e.target.closest('[data-google]');
      if (g) { google(g); return; }
      var s = e.target.closest('[data-show]');
      if (s) { var i = s.parentNode.querySelector('input'); i.type = i.type === 'password' ? 'text' : 'password'; s.textContent = i.type === 'password' ? 'Show' : 'Hide'; }
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target, v = UI.formData(form);
      var problem = !/^\S+@\S+\.\S+$/.test(v.email || '') ? 'Please enter a valid email address.'
        : mode !== 'reset' && (v.password || '').length < (mode === 'signup' ? 8 : 1) ? (mode === 'signup' ? 'Please choose a password of at least 8 characters.' : 'Please enter your password.')
        : mode === 'signup' && (v.name || '').trim().length < 2 ? 'Please tell us your name.' : null;
      if (problem) { say(problem, true); return; }
      if (mode === 'signup' && window.LegalKit && !LegalKit.consentChecked(form)) return;  // the kit shows its own message
      UI.busy(form.querySelector('[type=submit]'), UI.auth(mode, v)).then(function (r) {
        if (mode === 'reset' || (r && !r.me)) { mode = 'login'; draw(r && r.message, false); restore({ email: v.email }); }
        else UI.toast(mode === 'signup' ? 'Welcome to ' + UI.config.name + '!' : 'Welcome back!', 'ok');
      }, function (err) { say(err.message, true); });
    });
    // Sign-up asks for the Privacy & Terms tick here too (ticking it is remembered for the new account).
    function google(btn) {
      var form = view.querySelector('form'), v = mode === 'signup' ? UI.formData(form) : {};
      if (mode === 'signup' && window.LegalKit && !LegalKit.consentChecked(form)) return;
      UI.busy(btn, UI.auth('google', { name: (v.name || '').trim() })).then(function () {
        UI.toast(mode === 'signup' ? 'Welcome to ' + UI.config.name + '!' : 'Welcome back!', 'ok');
      }, function (err) { say(err.message, true); });
    }
    function say(msg, isErr) {
      var box = view.querySelector('[data-msg]');
      box.className = isErr ? 'ui-error' : 'ui-note'; box.textContent = msg; box.hidden = false;
    }
    function restore(v) {
      ['name', 'email'].forEach(function (k) { var i = view.querySelector('[name=' + k + ']'); if (i && v[k]) i.value = v[k]; });
    }
    draw();
  });
})();

/* ===== book.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('book', { title: 'Book' }, function (view, ctx) {
    var key = ctx.args[0], d = null;
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:360px"></div></div>';

    function charCard(c) {
      var top = c.top[0], mine = d.my[c.key];
      return '<article class="bp-char"><a class="pic" href="#character/' + esc(c.key) + '" data-go="character/' + esc(c.key) + '">' +
        (top && top.photo ? '<img src="' + PC.photo(top.photo) + '" alt="' + esc(top.name) + ' as ' + esc(c.name) + '" loading="lazy">' : '<div class="mono">' + esc(UI.initials(c.name)) + '</div>') +
        '<span class="role ' + esc(c.role) + '">' + esc(c.role_label) + '</span>' +
        '<div class="shade"><h3>' + esc(c.name) + '</h3><div class="pickline">' + (top ? 'Fans\' pick: <b>' + esc(top.name) + '</b> · ' + top.pct + '%' : 'Nobody has cast them yet') + '</div></div></a>' +
        '<div class="info">' + (c.blurb ? '<p>' + esc(c.blurb) + '</p>' : '') +
        (c.top.length > 1 ? '<div class="runners">' + c.top.slice(1).map(function (s) { return '<a href="#stars/' + esc(s.star) + '" data-go="stars/' + esc(s.star) + '">' + esc(s.name) + ' · ' + s.pct + '%</a>'; }).join('') + '</div>' : '') +
        '<div class="act">' + (d.book.status === 'live' ? '<a class="ui-btn ' + (mine ? 'soft' : 'primary') + ' sm" href="#castedit/' + esc(c.key) + '" data-cast-btn="' + esc(c.key) + '">' + UI.icon(mine ? 'edit' : 'sparkle') + (mine ? 'Edit yours' : 'Cast') + '</a>' : '') +
        '<a class="ui-btn sm" href="#character/' + esc(c.key) + '" data-go="character/' + esc(c.key) + '">' + UI.plural(c.casts, 'collage') + '</a></div></div></article>';
    }

    function draw(r) {
      d = r;
      var b = d.book;
      view.innerHTML = '<section class="bp-hero">' + (b.cover ? '<div class="bg" style="background-image:url(\'' + PC.photo(b.cover, true) + '\')"></div>' : '') +
        '<div class="ui-wrap">' + PC.cover(b, { full: true }) + '<div>' +
        '<p class="eyebrow">' + PC.seriesLine(b) + '</p><h1>' + esc(b.title) + '</h1><div class="by">by ' + esc(b.author) + '</div>' +
        '<div class="stats">' + PC.when(b.release) + PC.spice(b.spice) + '<span>' + UI.icon('heart') + ' ' + UI.plural(b.casts, 'collage') + '</span><span>' + UI.icon('users') + ' ' + UI.plural(d.fans, 'fan') + '</span></div>' +
        (b.blurb ? '<p class="blurb">' + esc(b.blurb) + '</p>' : '<div style="height:16px"></div>') +
        '<div class="pc-chips" style="margin-bottom:20px">' + b.tropes.map(function (t) { return '<span class="pc-chip static">' + esc(t) + '</span>'; }).join('') + '</div>' +
        '<div class="ui-row"><a class="ui-btn primary lg" href="#cast" data-jump>' + UI.icon('sparkle') + 'Cast a character</a>' +
        '<button class="ui-btn lg" data-share>' + UI.icon('share') + 'Share</button>' +
        (d.can_edit ? '<a class="ui-btn lg" href="#admin/books" data-go="admin/books">' + UI.icon('edit') + 'Edit</a>' : '') + '</div></div></div></section>' +
        '<div class="ui-wrap">' + (b.status !== 'live' ? '<div class="bp-pending">' + UI.icon('clock') + ' This book is waiting for an admin\'s review. Only you (and the admins) can see it for now.</div>' : '') +
        '<section id="cast"><div class="pc-section-head"><div><h2>The fans\' dream cast</h2><p class="muted" style="margin:4px 0 0">Every character, with the star most fans picked. Tap one to see every collage, or cast them yourself.</p></div>' +
        (b.status === 'live' ? '<button class="ui-btn sm" data-suggest-char>' + UI.icon('plus') + 'A character is missing</button>' : '') + '</div>' +
        '<div class="bp-chars">' + d.characters.map(charCard).join('') + '</div></section>' +
        (d.recent.length ? '<section class="pc-section"><div class="pc-section-head"><h2>Latest collages</h2></div>' + PC.castGrid(d.recent) + '</section>' : '') + '</div>';
      document.title = b.title + ' · ' + UI.config.name;
    }

    function suggestChar() {
      if (!UI.me) { PC.needSignIn('Sign up to add missing characters.'); return; }
      var m = UI.modal('<h2>Add a missing character</h2><p class="muted">An admin checks it, then everyone can cast them.</p><form class="ui-stack" data-sc>' +
        '<label class="ui-field"><span>Name</span><input type="text" name="name" maxlength="60" required></label>' +
        '<label class="ui-field"><span>Role</span><select name="role">' + Object.keys(d.roles).map(function (k) { return '<option value="' + k + '"' + (k === 'side' ? ' selected' : '') + '>' + esc(d.roles[k]) + '</option>'; }).join('') + '</select></label>' +
        '<label class="ui-field"><span>Who are they? <em>(optional, no spoilers please)</em></span><textarea name="blurb" rows="3" maxlength="400"></textarea></label>' +
        '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">Send</button></div></form>');
      m.el.querySelector('[data-sc]').addEventListener('submit', function (e) {
        e.preventDefault();
        var v = UI.formData(e.target);
        UI.busy(e.target.querySelector('[type=submit]'), UI.api('suggest_character', key, v.name, v.role, v.blurb)).then(function (r) { m.close(); UI.toast(r.message, 'ok'); });
      });
    }

    view.addEventListener('click', function (e) {
      if (e.target.closest('[data-jump]')) { e.preventDefault(); view.querySelector('#cast').scrollIntoView({ behavior: 'smooth' }); return; }
      if (e.target.closest('[data-share]')) { PC.share('#book/' + key, d.book.title); return; }
      if (e.target.closest('[data-suggest-char]')) { suggestChar(); return; }
      var c = e.target.closest('[data-cast-btn]');
      if (c) { e.preventDefault(); if (UI.me) UI.go('castedit', c.getAttribute('data-cast-btn')); else PC.needSignIn('Sign up to cast this character with your dream stars.'); }
    });
    PC.wireHearts(view);
    return UI.api('get_book', key).then(draw);
  });
})();

/* ===== books.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('books', { title: 'New romantasy releases', nav: 'Books', icon: 'book', order: 10 }, function (view, ctx) {
    var data = null, f = { q: '', trope: '', spice: '', sort: 'new' };
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:320px;border-radius:28px"></div><div class="ui-skel" style="height:200px;margin-top:22px"></div></div>';

    function feature(b) {
      return '<section class="bk-feature">' + (b.cover ? '<div class="bg" style="background-image:url(\'' + PC.photo(b.cover, true) + '\')"></div>' : '') +
        '<a href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + PC.cover(b, { full: true }) + '</a>' +
        '<div><div class="eyebrow">' + (PC.days(b.release) > 0 ? 'Coming soon' : 'Fresh from the forge') + '</div><h1>' + esc(b.title) + '</h1>' +
        '<div class="by">by ' + esc(b.author) + ' · ' + PC.seriesLine(b) + '</div>' +
        '<div class="bk-meta">' + PC.when(b.release) + PC.spice(b.spice) + '<span class="small">' + UI.icon('heart') + ' ' + UI.plural(b.casts, 'collage') + '</span></div>' +
        (b.blurb ? '<p class="blurb">' + esc(b.blurb) + '</p>' : '<div style="height:14px"></div>') +
        '<div class="pc-chips" style="margin-bottom:18px">' + b.tropes.map(function (t) { return '<span class="pc-chip static">' + esc(t) + '</span>'; }).join('') + '</div>' +
        '<div class="ui-row"><a class="ui-btn primary lg" href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + UI.icon('sparkle') + 'Cast the characters</a>' +
        '<button class="ui-btn lg" data-share="' + esc(b.key) + '">' + UI.icon('share') + 'Share</button></div></div></section>';
    }

    function filtered() {
      var q = f.q.trim().toLowerCase();
      var list = data.books.filter(function (b) {
        if (q && (b.title + ' ' + b.author + ' ' + b.series).toLowerCase().indexOf(q) < 0) return false;
        if (f.trope && b.tropes.indexOf(f.trope) < 0) return false;
        if (f.spice === 'mild' && b.spice > 1) return false;
        if (f.spice === 'warm' && (b.spice < 2 || b.spice > 3)) return false;
        if (f.spice === 'hot' && b.spice < 4) return false;
        return true;
      });
      if (f.sort === 'cast') list.sort(function (a, b) { return b.casts - a.casts; });
      else if (f.sort === 'soon') list = list.filter(function (b) { return PC.days(b.release) > 0; }).sort(function (a, b) { return a.release < b.release ? -1 : 1; });
      return list;
    }
    function drawShelf() {
      var list = filtered(), box = view.querySelector('[data-shelf]');
      box.innerHTML = list.length ? '<div class="pc-books">' + list.map(PC.bookCard).join('') + '</div>'
        : '<div class="ui-empty">' + UI.icon('book') + '<h3>No book matches</h3><p>Try another trope, or suggest the book you\'re looking for.</p>' +
          '<button class="ui-btn primary" data-suggest>' + UI.icon('plus') + 'Suggest a book</button></div>';
      view.querySelector('[data-count]').textContent = UI.plural(list.length, 'book');
      view.querySelectorAll('[data-trope]').forEach(function (c) { c.classList.toggle('on', c.getAttribute('data-trope') === f.trope); });
    }

    function draw(d) {
      data = d;
      var released = d.books.filter(function (b) { return PC.days(b.release) !== null && PC.days(b.release) <= 0; });
      var soon = d.books.filter(function (b) { return PC.days(b.release) > 0; }).sort(function (a, b) { return a.release < b.release ? -1 : 1; });
      var top = released[0] || d.books[0];
      var me = ctx.me;
      view.innerHTML = '<div class="ui-wrap">' + (top ? feature(top) : '') +
        (me ? '<div class="bk-hello"><p><b>Welcome back, ' + esc(me.name.split(' ')[0]) + '.</b> ' +
          (d.me && d.me.casts ? 'You\'ve made ' + UI.plural(d.me.casts, 'collage') + ' and earned ' + UI.plural(d.me.hearts, 'swoon') + '.' : 'Pick a book and cast your first character!') + '</p>' +
          '<div class="ui-row"><a class="ui-btn sm" href="#mine" data-go="mine">' + UI.icon('heart') + 'My casts</a><a class="ui-btn sm soft" href="#suggest" data-go="suggest">' + UI.icon('plus') + 'Suggest a book</a></div></div>' : '') +
        (soon.length ? '<section class="pc-section"><div class="pc-section-head"><h2>Coming soon</h2><span class="muted small">Cast them before anyone else</span></div><div class="bk-soon">' +
          soon.map(function (b) {
            var n = PC.days(b.release);
            return '<a href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + PC.cover(b) + '<div style="min-width:0"><h3>' + esc(b.title) + '</h3><div class="small muted">' + esc(b.author) + '</div>' +
              '<div style="margin-top:6px">' + PC.spice(b.spice) + '</div></div><div class="count"><b>' + n + '</b><span>' + (n === 1 ? 'day' : 'days') + '</span></div></a>';
          }).join('') + '</div></section>' : '') +
        (d.trending.length ? '<section class="pc-section bk-trend"><div class="pc-section-head"><h2>Swooned over this week</h2><a href="#stars" data-go="stars">The most-cast stars ' + UI.icon('arrow') + '</a></div>' +
          PC.castGrid(d.trending.slice(0, 4)) + '</section>' : '') +
        '<section class="pc-section"><div class="pc-section-head"><h2>Every book</h2><span class="muted small" data-count></span></div>' +
        '<div class="bk-filters"><div class="row"><input type="search" placeholder="Search a title, author or series" data-q aria-label="Search books">' +
        '<select data-spice aria-label="Spice"><option value="">Any spice</option><option value="mild">Sweet (0-1)</option><option value="warm">Warm (2-3)</option><option value="hot">Scorching (4-5)</option></select>' +
        '<div class="ui-seg" role="group" aria-label="Sort">' + [['new', 'Newest'], ['soon', 'Coming soon'], ['cast', 'Most cast']].map(function (s) {
          return '<button type="button" data-sort="' + s[0] + '" class="' + (f.sort === s[0] ? 'on' : '') + '">' + s[1] + '</button>'; }).join('') + '</div></div>' +
        '<div class="pc-scroll"><button type="button" class="pc-chip on" data-trope="">All tropes</button>' + d.tropes.map(function (t) {
          return '<button type="button" class="pc-chip" data-trope="' + esc(t) + '">' + esc(t) + '</button>'; }).join('') + '</div></div>' +
        '<div data-shelf></div></section>' +
        '<section class="pc-section"><div class="bk-hello"><p><b>Missing a book?</b> Suggest it with its characters, and an admin will add it to the shelf.</p>' +
        '<button class="ui-btn primary" data-suggest>' + UI.icon('plus') + 'Suggest a book</button></div></section></div>';
      drawShelf();
    }

    view.addEventListener('input', function (e) {
      if (e.target.matches('[data-q]')) { f.q = e.target.value; drawShelf(); }
    });
    view.addEventListener('change', function (e) {
      if (e.target.matches('[data-spice]')) { f.spice = e.target.value; drawShelf(); }
    });
    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-trope]');
      if (t) { f.trope = t.getAttribute('data-trope'); drawShelf(); return; }
      var s = e.target.closest('[data-sort]');
      if (s) { f.sort = s.getAttribute('data-sort'); view.querySelectorAll('[data-sort]').forEach(function (x) { x.classList.toggle('on', x === s); }); drawShelf(); return; }
      var sh = e.target.closest('[data-share]');
      if (sh) { PC.share('#book/' + sh.getAttribute('data-share'), 'A new romantasy to fan-cast'); return; }
      if (e.target.closest('[data-suggest]')) { if (UI.me) UI.go('suggest'); else PC.needSignIn('Sign up to suggest books for the shelf.'); }
    });
    PC.wireHearts(view);
    return UI.api('get_shelf').then(draw);
  });
})();

/* ===== cast.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('cast', { title: 'Collage' }, function (view, ctx) {
    var key = ctx.args[0], d = null;
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:520px"></div></div>';

    function commentHtml(x) {
      return '<div class="cs-c" data-cid="' + esc(x.id) + '"><span class="ui-avatar grad">' + esc(UI.initials(x.user.name)) + '</span>' +
        '<div class="bubble">' + (x.user.id ? '<a class="n" href="#fan/' + esc(x.user.id) + '" data-go="fan/' + esc(x.user.id) + '">' + esc(x.user.name) + '</a>' : '<b class="n">' + esc(x.user.name) + '</b>') +
        ' <span class="t">' + esc(UI.ago(x.created)) + '</span><p>' + esc(x.body) + '</p></div><div class="x">' +
        (x.can_delete ? '<button class="ui-btn ghost icon sm" data-del-c aria-label="Delete comment">' + UI.icon('trash') + '</button>' : '') +
        (!x.mine && UI.me ? '<button class="ui-btn ghost icon sm" data-rep-c aria-label="Report comment">' + UI.icon('flag') + '</button>' : '') + '</div></div>';
    }
    function drawComments() {
      var box = view.querySelector('[data-comments]');
      box.innerHTML = d.comments.length ? d.comments.map(commentHtml).join('') : '<p class="muted">No comments yet. Say something nice!</p>';
      view.querySelector('[data-ccount]').textContent = d.comments.length ? '(' + d.comments.length + ')' : '';
    }

    function draw(r) {
      d = r;
      var c = d.cast, ch = c.character;
      view.innerHTML = '<div class="ui-wrap"><div class="cs-grid"><div class="cs-art">' + PC.collage(c, { big: true }) + '</div><div>' +
        (c.hidden ? '<div class="cs-hidden">' + UI.icon('info') + ' A moderator hid this collage. Only you and the admins can see it.</div>' : '') +
        '<div class="cs-title"><a class="for" href="#character/' + esc(ch.key) + '" data-go="character/' + esc(ch.key) + '">' + esc(ch.role_label) + ' · ' + esc(c.book.title) + '</a>' +
        '<h1>' + esc(ch.name) + '</h1></div>' +
        '<div class="cs-who"><span class="ui-avatar grad">' + esc(UI.initials(c.user.name)) + '</span><div>Cast by ' +
        (c.user.id ? '<a href="#fan/' + esc(c.user.id) + '" data-go="fan/' + esc(c.user.id) + '">' + esc(c.user.name) + '</a>' : esc(c.user.name)) +
        '<div class="small muted">' + esc(UI.ago(c.updated)) + '</div></div></div>' +
        (c.caption ? '<p class="cs-cap">' + esc(c.caption) + '</p>' : '') +
        '<div class="cs-actions">' + PC.heartBtn(c, true) +
        '<button class="ui-btn" data-save-img>' + UI.icon('download') + 'Save image</button>' +
        '<button class="ui-btn" data-share>' + UI.icon('share') + 'Share</button>' +
        (c.mine ? '<a class="ui-btn" href="#castedit/' + esc(ch.key) + '" data-go="castedit/' + esc(ch.key) + '">' + UI.icon('edit') + 'Edit</a>' : '') +
        (c.can_delete ? '<button class="ui-btn danger" data-del>' + UI.icon('trash') + 'Delete</button>' : '') +
        (!c.mine ? '<button class="ui-btn ghost" data-rep>' + UI.icon('flag') + 'Report</button>' : '') + '</div>' +
        '<h3>The stars</h3><div class="cs-stars">' + c.picks.map(function (p, i) {
          return '<div class="cs-star"><div class="ph">' + (p.photo ? '<img src="' + PC.photo(p.photo, true) + '" alt="">' : esc(UI.initials(p.name))) + '</div>' +
            '<div><a href="#stars/' + esc(p.star) + '" data-go="stars/' + esc(p.star) + '">' + esc(p.name) + '</a>' + (i === 0 && c.picks.length > 1 ? ' <span class="ui-badge brand">Lead</span>' : '') +
            (p.note ? '<p>“' + esc(p.note) + '”</p>' : '') + '</div></div>';
        }).join('') + '</div>' +
        '<h3>Comments <span class="muted small" data-ccount></span></h3><div class="cs-comments" data-comments></div>' +
        (UI.me ? '<form class="cs-add" data-add-c><textarea name="body" maxlength="500" placeholder="Say something about this collage" required></textarea><button class="ui-btn primary" type="submit">' + UI.icon('arrow') + 'Post</button></form>'
          : '<p style="margin-top:12px"><a href="#auth/signup" data-go="auth/signup">Sign up</a> to join the conversation.</p>') +
        '</div></div>' +
        (d.more.length ? '<section class="pc-section"><div class="pc-section-head"><h2>More ' + esc(ch.name) + ' collages</h2><a href="#character/' + esc(ch.key) + '" data-go="character/' + esc(ch.key) + '">See all ' + UI.icon('arrow') + '</a></div>' + PC.castGrid(d.more, { noFor: true }) + '</section>' : '') +
        '</div>';
      drawComments();
      document.title = c.user.name + '\'s ' + ch.name + ' · ' + UI.config.name;
    }

    view.addEventListener('click', function (e) {
      var c = d && d.cast;
      if (!c) return;
      if (e.target.closest('[data-save-img]')) {
        var b = e.target.closest('[data-save-img]');
        UI.busy(b, PC.exportImage(c)).then(function () { UI.toast('Saved! Share it anywhere.', 'ok'); }, function (err) { UI.toast(err.message, 'error'); });
        return;
      }
      if (e.target.closest('[data-share]')) { PC.share('#cast/' + key, c.user.name + '\'s dream cast for ' + c.character.name); return; }
      if (e.target.closest('[data-rep]')) { PC.report('casting', key, d.reasons); return; }
      if (e.target.closest('[data-del]')) {
        UI.confirm({ title: 'Delete this collage?', text: 'Its swoons and comments go too. Your photos stay in your drawer.', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_casting', key).then(function () { UI.toast('Collage deleted'); UI.go('character', c.character.key); });
        });
        return;
      }
      var row = e.target.closest('[data-cid]');
      if (row && e.target.closest('[data-del-c]')) {
        UI.confirm({ title: 'Delete this comment?', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_comment', row.getAttribute('data-cid')).then(function () {
            d.comments = d.comments.filter(function (x) { return x.id !== row.getAttribute('data-cid'); }); drawComments();
          });
        });
        return;
      }
      if (row && e.target.closest('[data-rep-c]')) PC.report('comment', row.getAttribute('data-cid'), d.reasons);
    });
    view.addEventListener('submit', function (e) {
      if (!e.target.matches('[data-add-c]')) return;
      e.preventDefault();
      var f = e.target, v = UI.formData(f);
      UI.busy(f.querySelector('[type=submit]'), UI.api('add_comment', key, v.body)).then(function (r) {
        d.comments.push(r.comment); f.reset(); drawComments();
      });
    });
    PC.wireHearts(view);
    return UI.api('get_cast', key).then(draw);
  });
})();

/* ===== castedit.html ===== */
(function () {
  var esc = UI.esc;
  var LAYOUT_ART = {
    hero: '<svg viewBox="0 0 48 48" fill="currentColor"><rect x="4" y="6" width="25" height="36" rx="3"/><rect x="32" y="6" width="12" height="17" rx="2" opacity=".55"/><rect x="32" y="25" width="12" height="17" rx="2" opacity=".55"/></svg>',
    grid: '<svg viewBox="0 0 48 48" fill="currentColor"><rect x="4" y="8" width="12" height="15" rx="2"/><rect x="18" y="8" width="12" height="15" rx="2" opacity=".7"/><rect x="32" y="8" width="12" height="15" rx="2" opacity=".5"/><rect x="4" y="26" width="12" height="15" rx="2" opacity=".5"/><rect x="18" y="26" width="12" height="15" rx="2"/><rect x="32" y="26" width="12" height="15" rx="2" opacity=".7"/></svg>',
    polaroid: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.4"><rect x="5" y="9" width="17" height="21" rx="1" transform="rotate(-8 13 19)"/><rect x="25" y="14" width="17" height="21" rx="1" transform="rotate(7 33 24)"/><path d="M8 25h12M28 30h12" opacity=".5"/></svg>',
    strip: '<svg viewBox="0 0 48 48" fill="currentColor"><rect x="2" y="12" width="44" height="24" rx="3" opacity=".25"/><rect x="5" y="16" width="11" height="16" rx="1.5"/><rect x="18.5" y="16" width="11" height="16" rx="1.5"/><rect x="32" y="16" width="11" height="16" rx="1.5"/><path d="M4 13.5h3M10 13.5h3M16 13.5h3M22 13.5h3M28 13.5h3M34 13.5h3M40 13.5h3M4 34.5h3M10 34.5h3M16 34.5h3M22 34.5h3M28 34.5h3M34 34.5h3M40 34.5h3" stroke="#fff" stroke-width="1.6"/></svg>'
  };
  var TONE_SWATCH = { rose: 'linear-gradient(140deg,#ffd6e7,#fb7185)', violet: 'linear-gradient(140deg,#ede4ff,#a78bfa)', crimson: 'linear-gradient(140deg,#ffd1d8,#9f1239)', midnight: 'linear-gradient(140deg,#3b1069,#4c0519)' };

  UI.page('castedit', { title: 'Cast a character', auth: 'user' }, function (view, ctx) {
    var key = ctx.args[0], d = null, st = null;
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:460px"></div></div>';

    function previewCast() {
      return { picks: st.picks.filter(function (p) { return p.name.trim() || p.photo; }).map(function (p) { return { name: p.name.trim() || 'Who?', photo: p.photo }; }),
               layout: st.layout, tone: st.tone };
    }
    function drawPreview() {
      view.querySelector('[data-preview]').innerHTML = PC.collage(previewCast(), { big: true });
      view.querySelector('[data-cap-preview]').textContent = st.caption;
    }
    function slotHtml(p, i) {
      return '<div class="ce-slot' + (i === 0 && st.picks.length > 1 ? ' lead' : '') + '" data-i="' + i + '">' +
        '<button type="button" class="ph' + (p.photo ? ' has' : '') + '" data-photo aria-label="' + (p.photo ? 'Change photo' : 'Add a photo') + '">' +
        (p.photo ? '<img src="' + PC.photo(p.photo, true) + '" alt="">' : UI.icon('camera') + 'Add photo') + '</button>' +
        '<div class="fields"><input type="text" name="name" value="' + esc(p.name) + '" placeholder="Star\'s name" maxlength="60" list="ce-names" aria-label="Star\'s name">' +
        '<input type="text" name="note" value="' + esc(p.note) + '" placeholder="Why them? (optional)" maxlength="140" aria-label="Why them"></div>' +
        '<div class="tools"><button type="button" class="ui-btn ghost' + (i === 0 ? ' on' : '') + '" data-lead title="Make lead" aria-label="Make lead">' + UI.icon('crown') + '</button>' +
        '<button type="button" class="ui-btn ghost" data-remove title="Remove" aria-label="Remove">' + UI.icon('x') + '</button>' +
        '<button type="button" class="ui-btn ghost" data-move="-1" title="Move up" aria-label="Move up"' + (i === 0 ? ' disabled' : '') + '>' + UI.icon('up') + '</button>' +
        '<button type="button" class="ui-btn ghost" data-move="1" title="Move down" aria-label="Move down"' + (i === st.picks.length - 1 ? ' disabled' : '') + '>' + UI.icon('down') + '</button></div></div>';
    }
    function drawSlots() {
      view.querySelector('[data-slots]').innerHTML = st.picks.map(slotHtml).join('');
      view.querySelector('[data-n]').textContent = st.picks.length + ' of ' + d.max_picks;
      view.querySelector('[data-add]').disabled = st.picks.length >= d.max_picks;
      drawFavs();
      drawPreview();
    }
    function drawFavs() {
      var names = {};
      st.picks.forEach(function (p) { names[p.name.trim().toLowerCase()] = 1; });
      view.querySelectorAll('[data-fav]').forEach(function (b) { b.classList.toggle('on', !!names[b.getAttribute('data-fav').toLowerCase()]); });
    }
    function drawQuota() { view.querySelector('[data-quota]').innerHTML = PC.quotaHtml(d.quota); }

    function draw(r) {
      d = r;
      var c = d.character, b = d.book, dr = d.draft;
      st = dr ? { picks: dr.picks.map(function (p) { return { name: p.name, photo: p.photo, note: p.note }; }), layout: dr.layout, tone: dr.tone, caption: dr.caption }
        : { picks: [{ name: '', photo: null, note: '' }], layout: 'hero', tone: 'rose', caption: '' };
      var names = {};
      d.favourites.forEach(function (s) { names[s.name] = 1; });
      d.photos.forEach(function (p) { if (p.label) names[p.label] = 1; });
      view.innerHTML = '<div class="ui-wrap"><div class="ce-head">' + PC.cover(b) + '<div><span class="ui-badge brand">' + esc(c.role_label) + '</span>' +
        '<h1>' + (dr ? 'Your ' : 'Cast ') + esc(c.name) + '</h1><div class="muted">in <a href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + esc(b.title) + '</a>' +
        (c.blurb ? ' · ' + esc(c.blurb) : '') + '</div></div></div>' +
        '<datalist id="ce-names">' + Object.keys(names).map(function (n) { return '<option value="' + esc(n) + '">'; }).join('') + '</datalist>' +
        '<div class="ce-grid"><div>' +
        '<div class="ui-card ce-card"><h3>Your stars <span class="small muted" data-n></span></h3><p class="muted small" style="margin-top:-4px">The first one is your lead. Add a photo of each from your own camera roll (we keep a small copy).</p>' +
        '<div class="ce-slots" data-slots></div>' +
        '<button type="button" class="ui-btn block" style="margin-top:12px" data-add>' + UI.icon('plus') + 'Add a star</button>' +
        (d.favourites.length ? '<div class="ce-favs"><span class="small muted"><b>Fans\' favourites</b>: tap to add (with your own photo)</span><div class="pc-chips">' +
          d.favourites.map(function (s) { return '<button type="button" class="pc-chip" data-fav="' + esc(s.name) + '">' + esc(s.name) + ' · ' + s.pct + '%</button>'; }).join('') + '</div></div>' : '') + '</div>' +
        '<div class="ui-card ce-card"><h3>Style</h3><div class="ce-layouts" role="radiogroup" aria-label="Layout">' + d.layouts.map(function (l) {
          return '<label><input type="radio" name="layout" value="' + l + '"' + (st.layout === l ? ' checked' : '') + '><span>' + LAYOUT_ART[l] + esc(PC.LAYOUTS[l]) + '</span></label>';
        }).join('') + '</div><div class="ce-tones" role="radiogroup" aria-label="Colour" style="margin-top:14px">' + d.tones.map(function (t) {
          return '<label><input type="radio" name="tone" value="' + t + '"' + (st.tone === t ? ' checked' : '') + '><span><i style="background:' + TONE_SWATCH[t] + '"></i>' + esc(PC.TONES[t]) + '</span></label>';
        }).join('') + '</div></div>' +
        '<div class="ui-card ce-card"><h3>Caption</h3><textarea name="caption" maxlength="280" rows="3" placeholder="Make your case. Why is this THE cast?">' + esc(st.caption) + '</textarea></div>' +
        '<div class="ui-card ce-card tight"><div data-quota></div><p class="small muted" style="margin:8px 0 0">Photos are shrunk to 600×750 before upload. <a href="#photos" data-go="photos">Manage your photo drawer</a></p></div>' +
        '</div><div class="ce-preview"><div class="eyebrow">Preview</div><div data-preview></div><p class="cap" data-cap-preview></p>' +
        '<div class="ce-save"><button type="button" class="ui-btn primary lg block" data-save>' + UI.icon('heart') + (dr ? 'Save changes' : 'Publish my collage') + '</button>' +
        (dr ? '<a class="ui-btn block" href="#cast/' + esc(dr.key) + '" data-go="cast/' + esc(dr.key) + '">See it live</a>' : '<a class="ui-btn ghost block" href="#character/' + esc(c.key) + '" data-go="character/' + esc(c.key) + '">Cancel</a>') +
        '</div></div></div></div>';
      drawSlots(); drawQuota();
      document.title = 'Cast ' + c.name + ' · ' + UI.config.name;
    }

    function slotIndex(el) { var s = el.closest('[data-i]'); return s ? parseInt(s.getAttribute('data-i'), 10) : -1; }
    function addPick(name) {
      if (st.picks.length >= d.max_picks) { UI.toast('Up to ' + d.max_picks + ' stars per collage.', 'error'); return; }
      var empty = st.picks.filter(function (p) { return !p.name.trim() && !p.photo; })[0];
      if (empty) empty.name = name || ''; else st.picks.push({ name: name || '', photo: null, note: '' });
      drawSlots();
      if (!name) { var inputs = view.querySelectorAll('[data-slots] [name=name]'); inputs[inputs.length - 1].focus(); }
    }

    view.addEventListener('input', function (e) {
      var i = slotIndex(e.target);
      if (i >= 0 && (e.target.name === 'name' || e.target.name === 'note')) {
        st.picks[i][e.target.name] = e.target.value;
        if (e.target.name === 'name') drawPreview();
        return;
      }
      if (e.target.name === 'caption') { st.caption = e.target.value; drawPreview(); }
    });
    view.addEventListener('change', function (e) {
      if (e.target.name === 'layout') { st.layout = e.target.value; drawPreview(); }
      if (e.target.name === 'tone') { st.tone = e.target.value; drawPreview(); }
      if (e.target.name === 'name') drawFavs();
    });
    view.addEventListener('click', function (e) {
      if (e.target.closest('[data-add]')) { addPick(''); return; }
      var fav = e.target.closest('[data-fav]');
      if (fav) {
        var n = fav.getAttribute('data-fav');
        if (st.picks.some(function (p) { return p.name.trim().toLowerCase() === n.toLowerCase(); })) { UI.toast(n + ' is already in your collage.'); return; }
        addPick(n); return;
      }
      var i = slotIndex(e.target);
      if (i >= 0) {
        if (e.target.closest('[data-photo]')) {
          PC.choosePhoto(d.photos, { label: st.picks[i].name.trim(), onQuota: function (q) { d.quota = q; drawQuota(); } }).then(function (p) {
            if (!p) return;
            st.picks[i].photo = p.key;
            if (!st.picks[i].name.trim() && p.label) st.picks[i].name = p.label;
            drawSlots();
          });
          return;
        }
        if (e.target.closest('[data-remove]')) { st.picks.splice(i, 1); if (!st.picks.length) st.picks.push({ name: '', photo: null, note: '' }); drawSlots(); return; }
        if (e.target.closest('[data-lead]')) { st.picks.unshift(st.picks.splice(i, 1)[0]); drawSlots(); return; }
        var mv = e.target.closest('[data-move]');
        if (mv) {
          var j = i + parseInt(mv.getAttribute('data-move'), 10);
          if (j < 0 || j >= st.picks.length) return;
          var t = st.picks[i]; st.picks[i] = st.picks[j]; st.picks[j] = t; drawSlots(); return;
        }
      }
      var save = e.target.closest('[data-save]');
      if (save) {
        var picks = st.picks.filter(function (p) { return p.name.trim() || p.photo; });
        var nameless = picks.filter(function (p) { return !p.name.trim(); })[0];
        if (!picks.length) { UI.toast('Add at least one star first.', 'error'); return; }
        if (nameless) { UI.toast('Every star needs a name.', 'error'); return; }
        UI.busy(save, UI.api('save_casting', key, st.caption, st.layout, st.tone, picks.map(function (p) { return { name: p.name.trim(), photo: p.photo, note: p.note.trim() }; })))
          .then(function (r) {
            PC.hearts();
            UI.toast(r.created ? 'Your collage is live!' : 'Saved', 'ok');
            UI.go('cast', r.key);
          });
      }
    });
    return UI.api('get_editor', key).then(draw);
  });
})();

/* ===== character.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('character', { title: 'Character' }, function (view, ctx) {
    var key = ctx.args[0], sort = 'loved';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';

    function podium(list) {
      if (!list.length) return '<div class="cp-empty-pick"><h3>No fans\' pick yet</h3><p class="muted">Be the first to cast this character, and your stars lead the vote.</p></div>';
      var order = list.length >= 3 ? [1, 0, 2] : list.length === 2 ? [1, 0] : [0];
      return '<div class="cp-podium"' + (list.length < 3 ? ' style="grid-template-columns:repeat(' + list.length + ',minmax(0,1fr))"' : '') + '>' + order.map(function (i) {
        var s = list[i];
        return '<a class="' + (i === 0 ? 'first' : '') + '" href="#stars/' + esc(s.star) + '" data-go="stars/' + esc(s.star) + '"><div class="ph"><span class="medal">' + (i + 1) + '</span>' +
          (s.photo ? '<img src="' + PC.photo(s.photo, i > 0) + '" alt="' + esc(s.name) + '">' : '<div class="mono">' + esc(UI.initials(s.name)) + '</div>') + '</div>' +
          '<b>' + esc(s.name) + '</b><span>' + s.pct + '% · ' + UI.plural(s.votes, 'vote') + '</span></a>';
      }).join('') + '</div>';
    }

    function draw(d) {
      var c = d.character, b = d.book;
      var castBtn = b.status === 'live' ? '<a class="ui-btn primary lg" href="#castedit/' + esc(c.key) + '" data-cast>' + UI.icon(d.mine ? 'edit' : 'sparkle') + (d.mine ? 'Edit your collage' : 'Cast ' + esc(c.name.split(' ')[0])) + '</a>' : '';
      view.innerHTML = '<div class="ui-wrap"><div class="cp-head"><a href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + PC.cover(b) + '</a>' +
        '<div><span class="ui-badge brand">' + esc(c.role_label) + '</span><h1>' + esc(c.name) + '</h1>' +
        '<a class="book" href="#book/' + esc(b.key) + '" data-go="book/' + esc(b.key) + '">' + esc(b.title) + '</a> <span class="muted">by ' + esc(b.author) + '</span>' +
        (c.blurb ? '<p>' + esc(c.blurb) + '</p>' : '') + '</div>' + castBtn + '</div>' +
        '<div class="pc-scroll cp-sibs">' + d.siblings.map(function (s) {
          return '<a href="#character/' + esc(s.key) + '" data-go="character/' + esc(s.key) + '" class="' + (s.current ? 'on' : '') + '"><span class="face">' +
            (s.photo ? '<img src="' + PC.photo(s.photo, true) + '" alt="">' : esc(UI.initials(s.name))) + '</span>' + esc(s.name) + '</a>';
        }).join('') + '</div>' +
        '<section class="cp-pick"><div><div class="eyebrow">The fans\' pick</div>' + podium(d.consensus.slice(0, 3)) + '</div>' +
        '<div><h3 style="margin-bottom:12px">Every vote</h3>' + (d.consensus.length ? '<div class="cp-bars">' + d.consensus.map(function (s) {
          return '<div class="cp-bar"><a href="#stars/' + esc(s.star) + '" data-go="stars/' + esc(s.star) + '">' + esc(s.name) + '</a><span class="muted small">' + s.pct + '%</span>' +
            '<div class="pc-meter"><b style="width:' + Math.max(4, s.pct) + '%"></b></div></div>';
        }).join('') + '</div>' : '<p class="muted">No votes yet.</p>') +
        '<p class="small muted" style="margin:14px 0 0">One vote per collage for every star in it.</p></div></section>' +
        '<section class="pc-section"><div class="pc-section-head"><h2>' + UI.plural(d.total, 'collage') + '</h2>' +
        '<div class="ui-seg" role="group" aria-label="Sort">' + [['loved', 'Most swooned'], ['new', 'Newest']].map(function (s) {
          return '<button type="button" data-sort="' + s[0] + '" class="' + (sort === s[0] ? 'on' : '') + '">' + s[1] + '</button>'; }).join('') + '</div></div>' +
        (d.castings.length ? PC.castGrid(d.castings, { noFor: true }) : '<div class="ui-empty">' + UI.icon('sparkle') + '<h3>No collages yet</h3><p>Who do you see when you read ' + esc(c.name) + '?</p>' + castBtn + '</div>') +
        '</section></div>';
      document.title = c.name + ' · ' + UI.config.name;
    }
    function load() { return UI.api('get_character', key, sort).then(draw); }
    view.addEventListener('click', function (e) {
      var s = e.target.closest('[data-sort]');
      if (s) { sort = s.getAttribute('data-sort'); load(); return; }
      if (e.target.closest('[data-cast]')) { e.preventDefault(); if (UI.me) UI.go('castedit', key); else PC.needSignIn('Sign up to cast this character with your dream stars.'); }
    });
    PC.wireHearts(view);
    return load();
  });
})();

/* ===== fan.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('fan', { title: 'Fan' }, function (view, ctx) {
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:360px"></div></div>';
    PC.wireHearts(view);
    return UI.api('get_fan', ctx.args[0]).then(function (d) {
      var f = d.fan;
      view.innerHTML = '<div class="ui-wrap"><div class="fn-head"><span class="ui-avatar grad">' + esc(UI.initials(f.name)) + '</span><div>' +
        '<div class="eyebrow">Fan-caster</div><h1>' + esc(f.name) + '</h1>' + (f.bio ? '<p class="bio">' + esc(f.bio) + '</p>' : (f.me ? '<p class="muted">Add a bio on <a href="#mine" data-go="mine">My casts</a>.</p>' : '')) +
        '<div class="nums"><span><b>' + d.castings.length + '</b> ' + (d.castings.length === 1 ? 'collage' : 'collages') + '</span><span><b>' + d.hearts + '</b> swoons</span>' +
        '<span><b>' + d.books + '</b> ' + (d.books === 1 ? 'book' : 'books') + '</span>' + (f.joined ? '<span>Since ' + esc(UI.fmtDate(f.joined, { month: 'long', year: 'numeric' })) + '</span>' : '') + '</div>' +
        (d.stars.length ? '<div class="pc-chips" style="margin-top:12px">' + d.stars.map(function (s) { return '<a class="pc-chip" href="#stars/' + esc(s.star) + '" data-go="stars/' + esc(s.star) + '">' + UI.icon('star') + esc(s.name) + '</a>'; }).join('') + '</div>' : '') +
        '</div></div>' +
        (d.castings.length ? PC.castGrid(d.castings) : '<div class="ui-empty">' + UI.icon('sparkle') + '<h3>No collages yet</h3><p>' + (f.me ? 'Cast your first character!' : 'Nothing to see here yet.') + '</p></div>') + '</div>';
      document.title = f.name + ' · ' + UI.config.name;
    });
  });
})();

/* ===== landing.html ===== */
// Watch section: swap the video's cover for YouTube's player (privacy-enhanced) only when it's pressed.
  if (!window.__ytFilm) {
    window.__ytFilm = true;
    document.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('[data-yt-film]') : null;
      if (!b) return;
      var f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + b.getAttribute('data-yt-film') + '?autoplay=1&rel=0&playsinline=1';
      f.title = b.getAttribute('data-yt-title') || 'Video';
      f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      f.allowFullscreen = true;
      f.referrerPolicy = 'strict-origin-when-cross-origin';
      b.parentNode.replaceChild(f, b);
    });
  }
(function () {
  var COPY = {
    eyebrow: 'Fan-casting for romantasy readers',
    title: 'Who do you see <em>when you read?</em>',
    lead: 'Every new romantasy release, every character, and your dream cast as a gorgeous photo collage. Swoon over other fans\' picks and watch the fandom crown its favourites.',
    cta: 'Start casting, it\'s free',
    proof: ['Every new release', 'Your own photo collages', 'No endless threads'],
    stepsTitle: 'How it works',
    stepsLead: 'From the last page to your dream cast in a couple of minutes.',
    steps: [['Pick a new release', 'Browse the newest romantasy books, with covers, tropes and spice levels. Every character is listed.'],
            ['Cast with your own photos', 'Add up to six stars per character. Frame each photo in a tap; we keep a small copy in your drawer to reuse anytime.'],
            ['See who the fans crown', 'Swoon over other collages, comment, and watch the fans\' pick rise to the top of every character.']],
    featuresTitle: 'A home for fan-casts, not another thread',
    features: [['book', 'Every new romantasy', 'New releases and upcoming books with countdowns. Missing one? Suggest it with its characters.'],
               ['grid', 'Four collage styles', 'Leading star, gallery grid, polaroid wall or film strip, in rose, violet, crimson or midnight.'],
               ['image', 'A tidy photo drawer', 'Photos are cropped and shrunk on your phone before upload. Reuse them across collages, rename, clean up.'],
               ['crown', 'The fans\' pick', 'Every character shows the stars fans chose most, with a podium and the share of the vote.'],
               ['heart', 'Swoons and comments', 'Heart the collages you love, talk about them, and build your own public fan page.'],
               ['download', 'Save and share', 'Turn any collage into a ready-to-post image for your socials, or share its link.']],
    faq: [['Is it free?', 'Yes. PerfectCast is free, with no ads.'],
          ['Which books are on PerfectCast?', 'New and upcoming romantasy releases. Members can suggest books and characters; an admin checks them before they go live.'],
          ['Which photos can I use?', 'Photos of public figures that you\'re allowed to share. No private people, nothing explicit. Members can report a collage and admins remove what breaks the rules.'],
          ['Why are photos so small?', 'To keep things fast and light, every photo is cropped on your device and saved at 600×750 pixels (a book cover at 600×900). Each member can keep up to 60 photos.'],
          ['Who can see my collages?', 'Everyone: collages, captions and comments are public, with your display name. Your email is never shown. The Privacy & Terms page has the details.'],
          ['Does it work on my phone?', 'Yes. It works in any modern browser, and you can add it to your home screen.']],
    bandTitle: 'Your dream cast is waiting.',
    bandLead: 'Join the fans casting the newest romantasy, one collage at a time.'
  };

  function heroArt() {
    return '<div class="lp-art" aria-hidden="true">' +
      '<div class="lp-book"><small>THE EMBER COURTS</small>' + UI.icon('crown') + '<b>A Crown of<br>Ash &amp; Honey</b><small>MIRELLE THORNE</small></div>' +
      '<div class="lp-pol p1"><i class="lp-face"></i><span>The lead</span></div>' +
      '<div class="lp-pol p2"><i class="lp-face"></i><span>The prince</span></div>' +
      '<div class="lp-pol p3"><i class="lp-face"></i><span>The villain</span></div>' +
      '<div class="lp-vote"><span>' + UI.icon('crown') + ' Fans\' pick for Isolde</span><b>Saoirse Vale</b><div class="pc-meter"><b style="width:62%"></b></div><span>62% of collages</span></div>' +
      '<div class="lp-heart">' + UI.icon('heart') + '</div>' +
      '<span class="lp-spark" style="left:48%;top:0">\u2726</span><span class="lp-spark" style="right:2%;top:6%;font-size:1rem">\u2726</span><span class="lp-spark" style="left:0;top:58%;font-size:.9rem">\u2726</span></div>';
  }

  UI.page('landing', { title: 'Welcome' }, function (view, ctx) {
    var me = ctx.me, C = COPY, esc = UI.esc;
    var primary = me ? '<a class="ui-btn primary lg" href="#books" data-go="books">Open the shelf ' + UI.icon('arrow') + '</a>'
      : '<a class="ui-btn primary lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + ' ' + UI.icon('arrow') + '</a>' +
        '<a class="ui-btn lg" href="#books" data-go="books">Browse new releases</a>';
    view.innerHTML =
      '<section class="lp-hero"><div class="ui-wrap"><div>' +
        '<div class="eyebrow">' + esc(C.eyebrow) + '</div><h1>' + C.title + '</h1><p class="lp-lead">' + esc(C.lead) + '</p>' +
        '<div class="lp-cta">' + primary + '</div>' +
        '<div class="lp-proof">' + C.proof.map(function (p) { return '<span>' + UI.icon('check') + esc(p) + '</span>'; }).join('') + '</div>' +
      '</div>' + heroArt() + '</div></section>' +
      '<section class="lp-section ytf" id="watch"><div class="ui-wrap"><div class="ytf-in"><div class="ytf-copy"><div class="eyebrow"><svg viewBox="0 0 28 20" width="20" height="14" aria-hidden="true"><rect width="28" height="20" rx="5" fill="#FF0033"/><path d="M11.2 5.8v8.4l7.3-4.2z" fill="#fff"/></svg>Watch</div><h2>See PerfectCast in about a minute</h2><p>A short video tour of what PerfectCast does and how it works.</p><a class="ytf-link" href="https://www.youtube.com/watch?v=_pmaxTfTg38" target="_blank" rel="noopener">Watch on YouTube &#8599;</a></div><div><div class="ytf-frame"><button type="button" class="ytf-cover" data-yt-film="_pmaxTfTg38" data-yt-title="PerfectCast video" aria-label="Play the PerfectCast video (1:08)"><img src="_/theme/yt-cover.jpg" alt="" loading="lazy" decoding="async" width="960" height="540"><span class="ytf-play" aria-hidden="true"><svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.3.3 34 .3 34 .3s-21.3 0-26.5 1.4a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6c5.2 1.4 26.5 1.4 26.5 1.4s21.3 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#FF0033"/><path d="M45 24 27 14v20z" fill="#fff"/></svg></span><span class="ytf-len">1:08</span></button></div><p class="ytf-note">The video loads from YouTube when you press play.</p></div></div></div></section>' +
      '<section class="lp-section" data-shelf hidden><div class="ui-wrap"><div class="pc-section-head"><h2>Fresh on the shelf</h2><a href="#books" data-go="books">See every book ' + UI.icon('arrow') + '</a></div>' +
        '<div class="lp-shelf" data-shelf-list></div></div></section>' +
      '<section class="lp-section" id="how"><div class="ui-wrap"><div class="lp-head"><h2>' + esc(C.stepsTitle) + '</h2><p>' + esc(C.stepsLead) + '</p></div>' +
        '<div class="lp-steps">' + C.steps.map(function (s) { return '<div class="ui-card lp-step"><h3>' + esc(s[0]) + '</h3><p class="muted">' + esc(s[1]) + '</p></div>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><h2>' + esc(C.featuresTitle) + '</h2></div>' +
        '<div class="ui-grid">' + C.features.map(function (f) { return '<div class="ui-card lp-feature">' + UI.icon(f[0]) + '<h3>' + esc(f[1]) + '</h3><p>' + esc(f[2]) + '</p></div>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><h2>Questions</h2></div><div class="lp-faq">' +
        C.faq.map(function (q) { return '<details><summary>' + esc(q[0]) + '</summary><p>' + esc(q[1]) + '</p></details>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-band"><div><h2>' + esc(C.bandTitle) + '</h2><p>' + esc(C.bandLead) + '</p></div>' +
        (me ? '<a class="ui-btn lg" href="#books" data-go="books">Open the shelf</a>' : '<a class="ui-btn lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + '</a>') +
      '</div></div></section>';
    return UI.apiQuiet('get_shelf').then(function (d) {
      if (!d.books.length) return;
      view.querySelector('[data-shelf-list]').innerHTML = d.books.slice(0, 10).map(PC.bookCard).join('');
      view.querySelector('[data-shelf]').hidden = false;
    }, function () {});
  });
})();

/* ===== mine.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('mine', { title: 'My casts', nav: 'My casts', icon: 'heart', auth: 'user', order: 30 }, function (view, ctx) {
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:380px"></div></div>';
    function stat(n, label) { return '<div class="ui-card"><div class="ui-stat"><b>' + n + '</b><span>' + label + '</span></div></div>'; }
    function draw(d) {
      var s = d.stats;
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>My casts</h1><p class="muted">Your collages, your swoons, your corner of the fandom.</p></div>' +
        '<a class="ui-btn primary" href="#books" data-go="books">' + UI.icon('sparkle') + 'Cast someone new</a></div>' +
        '<div class="mn-stats">' + stat(s.casts, s.casts === 1 ? 'collage' : 'collages') + stat(s.hearts, 'swoons received') + stat(s.comments, 'comments received') + stat(s.books, s.books === 1 ? 'book' : 'books') + '</div>' +
        '<div class="mn-me"><form data-bio><input type="text" name="bio" maxlength="160" value="' + esc(d.me.bio) + '" placeholder="A line about you for your fan page (your favourite tropes?)" aria-label="Your bio">' +
        '<button class="ui-btn sm" type="submit">Save</button></form><a class="ui-btn sm soft" href="#fan/' + esc(d.me.id) + '" data-go="fan/' + esc(d.me.id) + '">' + UI.icon('eye') + 'My public page</a></div>' +
        (d.waiting.length ? '<section><div class="pc-section-head"><h2>Finish the cast</h2><span class="muted small">Characters from books you\'ve started</span></div><div class="pc-scroll mn-wait">' +
          d.waiting.map(function (w) {
            return '<a href="#castedit/' + esc(w.key) + '" data-go="castedit/' + esc(w.key) + '">' + PC.cover(w.book) + '<div><b>' + esc(w.name) + '</b><span>' + esc(w.book.title) + '</span></div></a>';
          }).join('') + '</div></section>' : '') +
        '<section class="pc-section"><div class="pc-section-head"><h2>Your collages</h2></div>' +
        (d.castings.length ? PC.castGrid(d.castings) : '<div class="ui-empty">' + UI.icon('sparkle') + '<h3>No collages yet</h3><p>Open a book, pick a character, and cast your dream stars.</p>' +
          '<a class="ui-btn primary" href="#books" data-go="books">Browse new releases</a></div>') + '</section>' +
        (d.swooned.length ? '<section class="pc-section"><div class="pc-section-head"><h2>You swooned over</h2></div>' + PC.castGrid(d.swooned) + '</section>' : '') + '</div>';
    }
    view.addEventListener('submit', function (e) {
      if (!e.target.matches('[data-bio]')) return;
      e.preventDefault();
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('update_bio', UI.formData(e.target).bio)).then(function (r) { UI.setMe(r.me); UI.toast('Saved', 'ok'); });
    });
    PC.wireHearts(view);
    return UI.api('my_castings').then(draw);
  });
})();

/* ===== photos.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('photos', { title: 'Your photo drawer', nav: 'Photos', icon: 'image', auth: 'user', order: 40 }, function (view, ctx) {
    var d = null, filter = 'all', q = '', selecting = false, picked = {};
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:360px"></div></div>';

    function visible() {
      var s = q.trim().toLowerCase();
      return d.photos.filter(function (p) {
        if (filter === 'used' && !p.uses.length) return false;
        if (filter === 'unused' && p.uses.length) return false;
        if (filter === 'cover' && p.kind !== 'cover') return false;
        return !s || p.label.toLowerCase().indexOf(s) >= 0;
      });
    }
    function tile(p) {
      return '<button type="button" class="ph-tile' + (p.kind === 'cover' ? ' cover' : '') + (picked[p.key] ? ' on' : '') + '" data-key="' + esc(p.key) + '">' +
        '<div class="img"><img src="' + PC.photo(p.key, true) + '" alt="' + esc(p.label) + '" loading="lazy"></div>' +
        '<span class="chk">' + UI.icon('check') + '</span>' +
        '<span class="use ui-badge ' + (p.uses.length ? 'brand' : '') + '">' + (p.uses.length ? 'In ' + p.uses.length : 'Unused') + '</span>' +
        '<div class="t"><b>' + (p.label ? esc(p.label) : '<span class="muted">No name</span>') + '</b><span class="s">' + PC.kb(p.size) + ' · ' + esc(UI.fmtDate(p.created, { day: 'numeric', month: 'short' })) + '</span></div></button>';
    }
    function drawGrid() {
      var list = visible(), n = Object.keys(picked).length;
      view.querySelector('[data-grid]').innerHTML = list.length ? '<div class="ph-grid' + (selecting ? ' ph-select' : '') + '">' + list.map(tile).join('') + '</div>'
        : '<div class="ui-empty">' + UI.icon('image') + '<h3>' + (d.photos.length ? 'Nothing here' : 'Your drawer is empty') + '</h3><p>' +
          (d.photos.length ? 'Try another filter.' : 'Upload photos of the stars you\'d cast. You can reuse each one in as many collages as you like.') + '</p></div>';
      view.querySelector('[data-quota]').innerHTML = PC.quotaHtml(d.quota);
      view.querySelectorAll('[data-filter]').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-filter') === filter); });
      var bulk = view.querySelector('[data-bulk]');
      bulk.hidden = !selecting;
      bulk.querySelector('[data-bulk-n]').textContent = UI.plural(n, 'photo') + ' selected';
      bulk.querySelector('[data-bulk-del]').disabled = !n;
      view.querySelector('[data-select]').textContent = selecting ? 'Done' : 'Select';
    }
    function draw(r) {
      d = r;
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Your photo drawer</h1><p class="muted">Every star you\'ve uploaded, ready to reuse in any collage.</p></div></div>' +
        '<div class="ph-top"><div data-quota></div><label class="ui-btn primary">' + UI.icon('upload') + 'Upload photos' + PC.fileInput(true) + '</label></div>' +
        '<div class="ph-bar"><div class="ui-seg" role="group" aria-label="Filter">' + [['all', 'All'], ['used', 'In use'], ['unused', 'Unused'], ['cover', 'Covers']].map(function (f) {
          return '<button type="button" data-filter="' + f[0] + '">' + f[1] + '</button>'; }).join('') + '</div>' +
        '<input type="search" placeholder="Find a star" data-q aria-label="Find a photo by name"><span class="ui-spacer"></span><button type="button" class="ui-btn sm" data-select>Select</button></div>' +
        '<div data-grid></div>' +
        '<div class="ph-bulk" data-bulk hidden><span data-bulk-n></span><div class="ui-row"><button type="button" class="ui-btn sm" data-unused>Select all unused</button>' +
        '<button type="button" class="ui-btn sm danger solid" data-bulk-del>' + UI.icon('trash') + 'Delete</button></div></div>' +
        '<div class="ui-card ph-tips"><h3>Good to know</h3><ul>' +
        '<li>Every photo is cropped and shrunk on your device to 600×750 (about 50–120 KB) before upload, so your drawer stays light. Location and camera details are removed.</li>' +
        '<li>You can keep up to ' + (d.quota.max || 'unlimited') + ' photos. Deleting one that\'s in a collage leaves the star\'s name with a monogram.</li>' +
        '<li>Only upload pictures you\'re allowed to share, of public figures. No private people.</li></ul></div></div>';
      drawGrid();
    }
    function load() { return UI.api('list_photos').then(draw); }

    function detail(p) {
      var m = UI.modal('<h2>' + (p.label ? esc(p.label) : 'Photo') + '</h2><div class="ph-detail"><img src="' + PC.photo(p.key) + '" alt="">' +
        '<div class="ui-stack"><form class="ui-stack" data-rename><label class="ui-field"><span>Name</span><input type="text" name="label" value="' + esc(p.label) + '" maxlength="60" placeholder="Who is this?"></label>' +
        '<button class="ui-btn sm" type="submit">Save name</button></form>' +
        '<p class="small muted" style="margin:0">' + PC.kb(p.size) + ' · uploaded ' + esc(UI.fmtDate(p.created)) + '</p>' +
        (p.uses.length ? '<div><b class="small">Used in</b><ul>' + p.uses.map(function (u) {
          return '<li>' + (u.casting ? '<a href="#cast/' + esc(u.casting) + '" data-go="cast/' + esc(u.casting) + '" data-close>' + esc(u.character) + '</a>' : '<a href="#book/' + esc(u.book) + '" data-go="book/' + esc(u.book) + '" data-close>' + esc(u.character) + '</a>') + '</li>';
        }).join('') + '</ul></div>' : '<p class="small muted" style="margin:0">Not in any collage yet.</p>') +
        '<div><button class="ui-btn danger sm" data-del>' + UI.icon('trash') + 'Delete photo</button></div></div></div>', { wide: true });
      m.el.querySelector('[data-rename]').addEventListener('submit', function (e) {
        e.preventDefault();
        UI.busy(e.target.querySelector('[type=submit]'), UI.api('rename_photo', p.key, UI.formData(e.target).label)).then(function (r) {
          p.label = r.photo.label; m.close(); UI.toast('Saved', 'ok'); drawGrid();
        });
      });
      m.el.querySelector('[data-del]').addEventListener('click', function () {
        UI.confirm({ title: 'Delete this photo?', text: p.uses.length ? 'It\'s in ' + UI.plural(p.uses.length, 'collage') + '. Those spots keep the name and show a monogram instead.' : 'This can\'t be undone.', ok: 'Delete', danger: true })
          .then(function (yes) {
            if (!yes) return;
            UI.api('delete_photo', p.key).then(function (r) { m.close(); d.photos = d.photos.filter(function (x) { return x.key !== p.key; }); d.quota = r.quota; drawGrid(); UI.toast('Photo deleted'); });
          });
      });
    }

    function uploadAll(files) {
      files = Array.prototype.slice.call(files || []);
      var chain = Promise.resolve();
      files.forEach(function (f) {
        chain = chain.then(function () {
          return PC.uploadFile(f).then(function (r) { if (r) { d.photos.unshift(r.photo); d.quota = r.quota; drawGrid(); } }, function (err) { UI.toast(err.message, 'error'); });
        });
      });
      return chain;
    }

    view.addEventListener('change', function (e) {
      if (e.target.matches('[data-file]')) { uploadAll(e.target.files); e.target.value = ''; }
    });
    view.addEventListener('input', function (e) { if (e.target.matches('[data-q]')) { q = e.target.value; drawGrid(); } });
    view.addEventListener('click', function (e) {
      var f = e.target.closest('[data-filter]');
      if (f) { filter = f.getAttribute('data-filter'); drawGrid(); return; }
      if (e.target.closest('[data-select]')) { selecting = !selecting; picked = {}; drawGrid(); return; }
      if (e.target.closest('[data-unused]')) { visible().forEach(function (p) { if (!p.uses.length && p.kind !== 'cover') picked[p.key] = 1; }); drawGrid(); return; }
      var del = e.target.closest('[data-bulk-del]');
      if (del) {
        var keys = Object.keys(picked);
        UI.confirm({ title: 'Delete ' + UI.plural(keys.length, 'photo') + '?', text: 'Collage spots using them keep the star\'s name with a monogram.', ok: 'Delete', danger: true }).then(function (yes) {
          if (!yes) return;
          var chain = Promise.resolve(), gone = 0;
          keys.forEach(function (k) { chain = chain.then(function () { return UI.apiQuiet('delete_photo', k).then(function (r) { gone++; d.quota = r.quota; d.photos = d.photos.filter(function (x) { return x.key !== k; }); }, function (err) { UI.toast(err.message, 'error'); }); }); });
          UI.busy(del, chain).then(function () { picked = {}; selecting = false; drawGrid(); UI.toast(UI.plural(gone, 'photo') + ' deleted', 'ok'); });
        });
        return;
      }
      var t = e.target.closest('[data-key]');
      if (t) {
        var p = d.photos.filter(function (x) { return x.key === t.getAttribute('data-key'); })[0];
        if (selecting) { if (picked[p.key]) delete picked[p.key]; else picked[p.key] = 1; drawGrid(); }
        else detail(p);
      }
    });
    return load();
  });
})();

/* ===== profile.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('profile', { title: 'Your profile', auth: 'user' }, function (view, ctx) {
    var me = ctx.me;
    view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="pf-head"><span class="ui-avatar">' + esc(UI.initials(me.name)) + '</span>' +
      '<div><h1>' + esc(me.name) + '</h1><div class="muted">' + esc(me.email) + (me.joined ? ' · member since ' + esc(UI.fmtDate(me.joined, { month: 'long', year: 'numeric' })) : '') + '</div></div></div>' +
      '<div class="pf-grid"><form class="ui-card ui-stack" data-name><h3>Your name</h3><label class="ui-field"><span>Shown to other people</span>' +
      '<input type="text" name="name" value="' + esc(me.name) + '" maxlength="60" required></label>' +
      '<label class="ui-field"><span>Bio <em>(on your public fan page)</em></span><input type="text" name="bio" value="' + esc(me.bio || '') + '" maxlength="160" placeholder="Your favourite tropes, your hottest take..."></label>' +
      '<button class="ui-btn primary" type="submit">Save</button></form>' +
      '<div class="ui-card ui-stack"><h3>Appearance</h3><p class="muted small">Follow your device, or pick one.</p><div data-theme-box></div>' +
      '<h3 style="margin-top:22px">Password</h3><p class="muted small">We\'ll email you a link to choose a new one.</p>' +
      '<button class="ui-btn" data-reset>' + UI.icon('mail') + 'Email me a reset link</button></div></div>' +
      '<div class="ui-card" style="margin-top:16px"><div class="pf-links">' +
      '<a href="#fan/' + esc(me.id) + '" data-go="fan/' + esc(me.id) + '">' + UI.icon('eye') + 'Your public fan page</a>' +
      '<a href="#mine" data-go="mine">' + UI.icon('heart') + 'My casts</a>' +
      '<a href="#photos" data-go="photos">' + UI.icon('image') + 'Your photo drawer</a>' +
      '<a href="#suggest" data-go="suggest">' + UI.icon('book') + 'Suggest a book</a>' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<button data-feedback>' + UI.icon('chat') + 'Submit feedback</button>' +
      '<button data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms, and your data</button>' +
      '<button data-signout-here>' + UI.icon('logout') + 'Sign out</button></div></div></div>';
    function themeBox() {
      var t = UI.theme();
      view.querySelector('[data-theme-box]').innerHTML = '<div class="ui-seg">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
        return '<button type="button" data-theme-pick="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
      }).join('') + '</div>';
    }
    themeBox();
    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-theme-pick]');
      if (t) { UI.setTheme(t.getAttribute('data-theme-pick')); themeBox(); UI.renderChrome(); return; }
      if (e.target.closest('[data-reset]')) {
        UI.busy(e.target.closest('[data-reset]'), UI.auth('reset', { email: me.email })).then(function (r) { UI.toast(r.message, 'ok'); });
      }
      if (e.target.closest('[data-signout-here]')) UI.auth('logout');
    });
    view.querySelector('[data-name]').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(e.target);
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('update_profile', v.name).then(function () { return UI.api('update_bio', v.bio); })).then(function (r) {
        UI.setMe(r.me); ctx.me = r.me; UI.toast('Saved', 'ok');
        view.querySelector('.pf-head h1').textContent = r.me.name;
      });
    });
  });
})();

/* ===== stars.html ===== */
(function () {
  var esc = UI.esc;
  function face(s, thumb) { return s.photo ? '<img src="' + PC.photo(s.photo, thumb) + '" alt="' + esc(s.name) + '" loading="lazy">' : '<div class="mono">' + esc(UI.initials(s.name)) + '</div>'; }

  function board(view) {
    var data = null, q = '';
    function sub(s) { return s.top_role ? 'Top as ' + esc(s.top_role.name) + ' · ' + esc(s.top_role.book) : ''; }
    function drawList() {
      var s = q.trim().toLowerCase(), rest = data.stars.map(function (x, i) { x.rank = i + 1; return x; });
      if (s) rest = rest.filter(function (x) { return x.name.toLowerCase().indexOf(s) >= 0; }); else rest = rest.slice(3);
      view.querySelector('[data-list]').innerHTML = rest.length ? '<div class="st-list">' + rest.map(function (x) {
        return '<a class="st-row" href="#stars/' + esc(x.star) + '" data-go="stars/' + esc(x.star) + '"><span class="n">' + x.rank + '</span><span class="ph">' +
          (x.photo ? '<img src="' + PC.photo(x.photo, true) + '" alt="" loading="lazy">' : esc(UI.initials(x.name))) + '</span>' +
          '<div style="min-width:0"><b>' + esc(x.name) + '</b><div class="sub">' + sub(x) + '</div></div><div class="c">' + x.casts + '<small>' + (x.casts === 1 ? 'collage' : 'collages') + '</small></div></a>';
      }).join('') + '</div>' : (s ? '<div class="ui-empty">' + UI.icon('search') + '<h3>Nobody by that name yet</h3><p>Cast them in a collage and they\'ll appear here.</p></div>' : '');
      view.querySelector('[data-podium]').hidden = !!s;
    }
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';
    view.addEventListener('input', function (e) { if (e.target.matches('[data-q]')) { q = e.target.value; drawList(); } });
    return UI.api('list_stars').then(function (d) {
      data = d;
      var top = d.stars.slice(0, 3), order = top.length === 3 ? [1, 0, 2] : top.map(function (x, i) { return i; });
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>The <span class="grad-text">most-cast</span> stars</h1>' +
        '<p class="muted">Who fans see when they read. ' + UI.plural(d.total, 'star') + ' cast so far.</p></div>' +
        '<input type="search" placeholder="Find a star" data-q aria-label="Find a star" style="max-width:260px"></div>' +
        (top.length ? '<div class="st-podium" data-podium' + (top.length < 3 ? ' style="grid-template-columns:repeat(' + top.length + ',minmax(0,1fr))"' : '') + '>' + order.map(function (i) {
          var s = top[i];
          return '<a class="' + (i === 0 ? 'first' : '') + '" href="#stars/' + esc(s.star) + '" data-go="stars/' + esc(s.star) + '"><div class="ph"><span class="rank">#' + (i + 1) + '</span>' + face(s, i > 0) + '</div>' +
            '<h3>' + esc(s.name) + '</h3><span>' + UI.plural(s.casts, 'collage') + ' · ' + UI.plural(s.roles, 'role') + '</span></a>';
        }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('star') + '<h3>No stars yet</h3><p>Cast a character, and your stars start the leaderboard.</p></div>') +
        '<div data-list></div></div>';
      drawList();
    });
  }

  function star(view, slug) {
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';
    return UI.api('get_star', slug).then(function (d) {
      var s = d.star;
      view.innerHTML = '<div class="ui-wrap"><a href="#stars" data-go="stars" class="small" style="text-decoration:none;font-weight:700">' + UI.icon('back') + ' All stars</a>' +
        '<div class="st-hero" style="margin-top:14px"><div class="ph">' + face(s) + '</div><div><div class="eyebrow">Fan-cast star</div><h1>' + esc(s.name) + '</h1>' +
        '<div class="st-stats"><div class="ui-stat"><b>' + s.casts + '</b><span>' + (s.casts === 1 ? 'collage' : 'collages') + '</span></div>' +
        '<div class="ui-stat"><b>' + d.roles.length + '</b><span>' + (d.roles.length === 1 ? 'role' : 'roles') + '</span></div>' +
        '<div class="ui-stat"><b>' + s.fans + '</b><span>' + (s.fans === 1 ? 'fan' : 'fans') + '</span></div>' +
        '<div class="ui-stat"><b>' + d.roles.filter(function (r) { return r.rank === 1; }).length + '</b><span>fans\' #1 picks</span></div></div></div></div>' +
        '<section><div class="pc-section-head"><h2>Cast as</h2></div><div class="st-roles">' + d.roles.map(function (r) {
          return '<a class="st-role" href="#character/' + esc(r.key) + '" data-go="character/' + esc(r.key) + '">' + PC.cover(r.book) +
            '<div style="min-width:0"><div class="ui-row" style="gap:6px">' + (r.rank === 1 ? '<span class="ui-badge brand">' + UI.icon('crown') + 'Fans\' pick</span>' : '<span class="ui-badge">#' + r.rank + '</span>') +
            '<span class="small muted">' + esc(r.role_label) + '</span></div><h3>' + esc(r.name) + '</h3><div class="small muted">' + esc(r.book.title) + '</div>' +
            '<div class="pc-meter"><b style="width:' + Math.max(4, r.pct) + '%"></b></div><div class="small muted" style="margin-top:4px">' + r.pct + '% of collages · ' + UI.plural(r.votes, 'vote') + '</div></div></a>';
        }).join('') + '</div></section>' +
        (d.gallery.length ? '<section class="pc-section"><div class="pc-section-head"><h2>Fans\' photos</h2><span class="muted small">Tap one to see the collage</span></div><div class="st-gallery">' +
          d.gallery.map(function (g) { return '<a href="#cast/' + esc(g.casting) + '" data-go="cast/' + esc(g.casting) + '"><img src="' + PC.photo(g.photo, true) + '" alt="" loading="lazy"><span>by ' + esc(g.by) + '</span></a>'; }).join('') +
          '</div></section>' : '') + '</div>';
      document.title = s.name + ' · ' + UI.config.name;
    });
  }

  UI.page('stars', { title: 'Stars', nav: 'Stars', icon: 'star', order: 20 }, function (view, ctx) {
    return ctx.args[0] ? star(view, ctx.args[0]) : board(view);
  });
})();

/* ===== suggest.html ===== */
(function () {
  var esc = UI.esc;
  PC.ROLES = { heroine: 'Heroine', hero: 'Hero', love: 'Love interest', villain: 'Villain', royal: 'Royalty', ally: 'Ally', side: 'Supporting' };

  /* The book form. opts: {book, tropes, admin}. Returns {values() -> data or null (with a toast)}. */
  PC.bookForm = function (box, opts) {
    var b = opts.book || { title: '', author: '', series: '', series_no: null, release: '', blurb: '', tropes: [], spice: 2, cover: null, status: 'live', characters: [] };
    var chosen = (b.tropes || []).slice(), cover = b.cover, chars = (b.characters || []).map(function (c) { return { key: c.key, name: c.name, role: c.role, blurb: c.blurb || '', status: c.status }; });
    if (!chars.length) chars = [{ name: '', role: 'heroine', blurb: '' }, { name: '', role: 'love', blurb: '' }];
    function charRow(c, i) {
      return '<div class="bf-char" data-ci="' + i + '"><input type="text" data-cf="name" value="' + esc(c.name) + '" placeholder="Character name" maxlength="60" aria-label="Character name">' +
        '<select data-cf="role" aria-label="Role">' + Object.keys(PC.ROLES).map(function (k) { return '<option value="' + k + '"' + (c.role === k ? ' selected' : '') + '>' + PC.ROLES[k] + '</option>'; }).join('') + '</select>' +
        '<button type="button" class="ui-btn ghost icon" data-cdel aria-label="Remove character">' + UI.icon('x') + '</button>' +
        '<textarea data-cf="blurb" maxlength="400" placeholder="Who are they? One line, no spoilers (optional)" aria-label="About the character">' + esc(c.blurb) + '</textarea>' +
        (c.status === 'pending' ? '<span class="pend ui-badge warn">Suggested by a member: saving publishes it</span>' : '') + '</div>';
    }
    function spiceHtml(n) {
      var out = '<div class="bf-spice" role="radiogroup" aria-label="Spice">';
      for (var i = 0; i <= 5; i++) out += '<label><input type="radio" name="spice" value="' + i + '"' + (i === n ? ' checked' : '') + '><span class="' + (i === 0 ? 'zero' : '') + (i && i <= n ? ' on' : '') + '" title="' + i + ' of 5">' + (i === 0 ? 'Sweet' : UI.icon('flame')) + '</span></label>';
      return out + '</div>';
    }
    box.innerHTML = '<div class="bf">' +
      '<div class="bf-cover"><div data-cover-prev>' + PC.cover({ title: b.title || 'Cover', cover: cover }) + '</div><div><b>Cover</b><p class="small muted" style="margin:2px 0 8px">Optional. Framed to 2:3 and shrunk to 600×900.</p>' +
      '<div class="ui-row"><label class="ui-btn sm">' + UI.icon('upload') + 'Upload a cover' + PC.fileInput(false) + '</label><button type="button" class="ui-btn ghost sm" data-cover-x' + (cover ? '' : ' hidden') + '>Remove</button></div></div></div>' +
      '<div class="bf-two"><label class="ui-field"><span>Title</span><input type="text" name="title" value="' + esc(b.title) + '" maxlength="120" required></label>' +
      '<label class="ui-field"><span>Author</span><input type="text" name="author" value="' + esc(b.author) + '" maxlength="80" required></label></div>' +
      '<div class="bf-three"><label class="ui-field"><span>Series <em>(optional)</em></span><input type="text" name="series" value="' + esc(b.series) + '" maxlength="80"></label>' +
      '<label class="ui-field"><span>Book #</span><input type="number" name="series_no" min="1" max="99" value="' + esc(b.series_no == null ? '' : b.series_no) + '"></label>' +
      '<label class="ui-field"><span>Release date</span><input type="date" name="release" value="' + esc(b.release || '') + '"></label></div>' +
      '<div class="ui-field"><span>Spice</span>' + spiceHtml(b.spice || 0) + '</div>' +
      '<div class="ui-field"><span>Tropes <em>(up to 6)</em></span><div class="pc-chips" data-tropes>' + opts.tropes.map(function (t) {
        return '<button type="button" class="pc-chip' + (chosen.indexOf(t) >= 0 ? ' on' : '') + '" data-trope="' + esc(t) + '">' + esc(t) + '</button>'; }).join('') + '</div></div>' +
      '<label class="ui-field"><span>Blurb <em>(no spoilers)</em></span><textarea name="blurb" rows="4" maxlength="1500">' + esc(b.blurb) + '</textarea></label>' +
      (opts.admin ? '<label class="ui-field"><span>Status</span><select name="status">' + [['live', 'Live: everyone sees it'], ['pending', 'Pending review'], ['rejected', 'Turned down (hidden)']].map(function (s) {
        return '<option value="' + s[0] + '"' + (b.status === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') + '</select></label>' : '') +
      '<div class="ui-field"><span>Characters</span><div class="bf-chars" data-chars></div><button type="button" class="ui-btn sm" style="margin-top:10px" data-cadd>' + UI.icon('plus') + 'Add a character</button></div></div>';
    function drawChars() { box.querySelector('[data-chars]').innerHTML = chars.map(charRow).join(''); }
    drawChars();
    box.addEventListener('click', function (e) {
      var t = e.target.closest('[data-trope]');
      if (t) {
        var name = t.getAttribute('data-trope'), at = chosen.indexOf(name);
        if (at >= 0) chosen.splice(at, 1); else if (chosen.length < 6) chosen.push(name); else UI.toast('Up to 6 tropes.');
        t.classList.toggle('on', chosen.indexOf(name) >= 0); return;
      }
      if (e.target.closest('[data-cadd]')) { chars.push({ name: '', role: 'side', blurb: '' }); drawChars(); box.querySelectorAll('[data-cf=name]')[chars.length - 1].focus(); return; }
      var del = e.target.closest('[data-cdel]');
      if (del) { chars.splice(parseInt(del.closest('[data-ci]').getAttribute('data-ci'), 10), 1); drawChars(); return; }
      if (e.target.closest('[data-cover-x]')) { cover = null; box.querySelector('[data-cover-prev]').innerHTML = PC.cover({ title: 'Cover', cover: null }); e.target.closest('[data-cover-x]').hidden = true; }
    });
    box.addEventListener('input', function (e) {
      var row = e.target.closest('[data-ci]');
      if (row && e.target.hasAttribute('data-cf')) chars[parseInt(row.getAttribute('data-ci'), 10)][e.target.getAttribute('data-cf')] = e.target.value;
    });
    box.addEventListener('change', function (e) {
      var row = e.target.closest('[data-ci]');
      if (row && e.target.hasAttribute('data-cf')) chars[parseInt(row.getAttribute('data-ci'), 10)][e.target.getAttribute('data-cf')] = e.target.value;
      if (e.target.name === 'spice') box.querySelectorAll('.bf-spice span').forEach(function (s, i) { s.classList.toggle('on', i > 0 && i <= parseInt(e.target.value, 10)); });
      if (e.target.matches('[data-file]')) {
        var f = e.target.files && e.target.files[0]; e.target.value = '';
        if (f) PC.uploadFile(f, { kind: 'cover' }).then(function (r) {
          if (!r) return;
          cover = r.photo.key;
          box.querySelector('[data-cover-prev]').innerHTML = PC.cover({ title: 'Cover', cover: cover });
          box.querySelector('[data-cover-x]').hidden = false;
        }, function (err) { UI.toast(err.message, 'error'); });
      }
    });
    return {
      values: function () {
        var v = {};
        box.querySelectorAll('input[name], textarea[name], select[name]').forEach(function (el) { if (el.type === 'radio') { if (el.checked) v[el.name] = el.value; } else v[el.name] = el.value; });
        var list = chars.filter(function (c) { return c.name.trim(); });
        if ((v.title || '').trim().length < 2) { UI.toast('The book needs a title.', 'error'); return null; }
        if ((v.author || '').trim().length < 2) { UI.toast('Who wrote it? Add the author.', 'error'); return null; }
        if (!list.length) { UI.toast('Add at least one character.', 'error'); return null; }
        v.spice = parseInt(v.spice || '0', 10); v.tropes = chosen; v.cover = cover; v.characters = list;
        return v;
      }
    };
  };

  UI.page('suggest', { title: 'Suggest a book', auth: 'user' }, function (view, ctx) {
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';
    return UI.api('get_shelf').then(function (d) {
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Suggest a book</h1><p class="muted">A new romantasy everyone should be casting? Add it with its characters.</p></div></div>' +
        '<div class="sg-intro"><form class="ui-card" data-suggest><div data-form></div><div class="ui-row end" style="margin-top:20px"><a class="ui-btn ghost" href="#books" data-go="books">Cancel</a>' +
        '<button class="ui-btn primary" type="submit">' + UI.icon('sparkle') + 'Send for review</button></div></form>' +
        '<aside class="sg-side"><h3>How it works</h3><ul><li>An admin checks the book (usually within a day), then it joins the shelf for everyone.</li>' +
        '<li>Only you see it until then: you\'ll find it under its own link.</li><li>Use the publisher\'s cover if you can share it, or skip it: we\'ll add one.</li>' +
        '<li>Already ' + UI.plural(d.books.length, 'book') + ' on PerfectCast. Search the shelf first!</li></ul></aside></div></div>';
      var form = PC.bookForm(view.querySelector('[data-form]'), { tropes: d.tropes });
      view.querySelector('[data-suggest]').addEventListener('submit', function (e) {
        e.preventDefault();
        var v = form.values();
        if (!v) return;
        UI.busy(e.target.querySelector('[type=submit]'), UI.api('suggest_book', v)).then(function (r) { UI.toast(r.message, 'ok'); PC.hearts(14); UI.go('book', r.key); });
      });
    });
  });
})();
