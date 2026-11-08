/* pc.js: PerfectCast's drawing engines (window.PC), wrapped by client_code/pc.py and Components/Collage.
   - PC.collage(cast, opts): the collage HTML (4 layouts x 4 tones; CSS .pc-col in app.css)
   - PC.mountCrop(frame, zoom, file, kind): the photo cropper (drag, pinch, wheel, zoom slider) inside a Python dialog;
     resolves a controller whose result() crops + shrinks to a fixed size and returns {full, thumb, bytes} (JPEG data URLs)
   - PC.exportImage(cast): "save as image", a 1080x1350 PNG drawn on a canvas and downloaded
   - PC.hearts(n): floating hearts after publishing
   Pages, lists and dialogs are Python Forms; this file only draws. */
(function () {
  'use strict';
  var PC = window.PC = window.PC || {};
  function esc(s) { return window.UI && UI.esc ? UI.esc(s) : String(s == null ? '' : s); }
  PC.initials = function (name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  };

  /* ---------------------------------------------------------------- photo URLs (the /photo endpoint, same origin) */
  PC.apiBase = function () { return (window.APP_API || '_/api').replace(/\/$/, ''); };
  PC.photo = function (key, thumb) { return key ? PC.apiBase() + '/photo?k=' + encodeURIComponent(key) + (thumb ? '&s=t' : '') : ''; };

  /* ---------------------------------------------------------------- collages */
  PC.mono = function (name) { return '<div class="mono">' + esc(PC.initials(name)) + '</div>'; };
  PC.collage = function (c, opts) {
    opts = opts || {};
    var picks = (c.picks || []).slice(0, 6), n = Math.max(1, picks.length), layout = c.layout || 'hero';
    return '<div class="pc-col lay-' + esc(layout) + ' tone-' + esc(c.tone || 'rose') + ' n' + n + (opts.big ? ' big' : '') + '">' +
      picks.map(function (p, i) {
        var thumb = !opts.big && !(i === 0 && layout === 'hero');
        return '<figure class="pc-pick">' + (i === 0 && picks.length > 1 && layout === 'hero' ? '<span class="lead">Lead</span>' : '') +
          (p.photo ? '<img src="' + PC.photo(p.photo, thumb) + '" alt="' + esc(p.name) + '" loading="lazy">' : PC.mono(p.name)) +
          '<figcaption>' + esc(p.name) + '</figcaption></figure>';
      }).join('') + (picks.length ? '' : '<figure class="pc-pick">' + PC.mono('?') + '<figcaption>Add a star</figcaption></figure>') + '</div>';
  };

  /* ---------------------------------------------------------------- floating hearts */
  PC.hearts = function (n) {
    if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var box = document.createElement('div'), glyphs = ['♥', '✦', '♥', '❤'], colors = ['#e11d74', '#c026d3', '#7c3aed', '#f43f5e', '#f9a8d4'];
    box.className = 'pc-hearts-fx';
    box.setAttribute('aria-hidden', 'true');
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

  /* ---------------------------------------------------------------- photos: crop + shrink */
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
  /* A problem with the picked file, or '' when it can be cropped. */
  PC.fileProblem = function (file) {
    if (!file || !/^image\//.test(file.type || '')) return 'That file isn\'t a picture.';
    if (file.size > 25 * 1048576) return 'That picture is huge (over 25 MB). Try a smaller one.';
    return '';
  };
  /* Mount the cropper in `frame` (an element already on screen) with `zoom` (an <input type=range>).
     Resolves {result() -> {full, thumb, bytes}, destroy()}; rejects with an Error the dialog shows. */
  PC.mountCrop = function (frame, zoom, file, kind) {
    var shape = PC.SHAPES[kind || 'portrait'];
    var problem = PC.fileProblem(file);
    if (problem) return Promise.reject(new Error(problem));
    var url = URL.createObjectURL(file);
    frame.style.aspectRatio = shape.w + ' / ' + shape.h;
    return loadImage(url).then(function (img) {
      img.alt = '';
      frame.innerHTML = '';
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
      function onZoom() { setZoom(parseFloat(zoom.value)); }
      zoom.value = 1;
      zoom.addEventListener('input', onZoom);
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
      frame.addEventListener('keydown', function (e) {  /* keyboard: arrows move, +/- zoom */
        var step = 12, k = e.key;
        if (k === 'ArrowLeft') x += step; else if (k === 'ArrowRight') x -= step; else if (k === 'ArrowUp') y += step; else if (k === 'ArrowDown') y -= step;
        else if (k === '+' || k === '=') { setZoom(z * 1.1); e.preventDefault(); return; } else if (k === '-') { setZoom(z / 1.1); e.preventDefault(); return; } else return;
        e.preventDefault(); paint();
      });
      return {
        result: function () {
          var c = document.createElement('canvas'); c.width = shape.w; c.height = shape.h;
          var g = c.getContext('2d'), k = shape.w / W, s = base * z;
          g.fillStyle = '#ffffff'; g.fillRect(0, 0, c.width, c.height);
          g.imageSmoothingQuality = 'high';
          g.drawImage(img, x * k, y * k, img.naturalWidth * s * k, img.naturalHeight * s * k);
          var t = document.createElement('canvas'); t.width = shape.tw; t.height = shape.th;
          var tg = t.getContext('2d'); tg.imageSmoothingQuality = 'high'; tg.drawImage(c, 0, 0, t.width, t.height);
          var full = encode(c, shape.limit), thumb = encode(t, 44 * 1024);
          return { full: full, thumb: thumb, bytes: bytesOf(full) + bytesOf(thumb) };
        },
        destroy: function () { zoom.removeEventListener('input', onZoom); URL.revokeObjectURL(url); }
      };
    }, function (err) { URL.revokeObjectURL(url); throw err; });
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
          g.fillText(PC.initials(p.name), s[0] + s[2] / 2, s[1] + s[3] / 2); g.textBaseline = 'alphabetic';
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
            resolve(true);
          }, 'image/png');
        } catch (e) { reject(new Error('The picture couldn\'t be made in this browser.')); }
      });
    });
  };
})();
