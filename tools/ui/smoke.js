/* Smoke test: every page address opens without an error and isn't empty, signed out, as a new member and as the
   admin; the join, report and choose-photo dialogs open and close. ui_test.py fails the run on any Python/JS
   exception it sees.  python -I tools/ui_test.py --only smoke.js. Resolves to {ok, log}. */
(async function () {
  const log = [], bad = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 30000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const shown = (el) => el && el.getClientRects().length > 0;
  function type(input, value) {
    input.focus(); input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function visit(hash, minChars) {
    if (location.hash !== hash) window.UI_READY = false;
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash, hash, 40000);
    await sleep(500);
    const n = (($('.ui-main') || document.body).innerText || '').trim().length;
    if (n < (minChars || 40)) bad.push(hash + ' is empty');
    log.push((n < (minChars || 40) ? 'EMPTY ' : 'ok   ') + hash + ' (' + n + ' chars)');
  }
  const href = (sel, what) => until(() => { const a = $$(sel).find(shown); return a && a.getAttribute('href'); }, what);
  const button = (sel, re) => $$(sel + ' button').find((b) => re.test(b.textContent.trim()) && shown(b));
  const inputs = () => $$('.au-card input[type=text], .au-card input[type=email], .au-card input[type=password]').filter(shown);
  async function signOut() {
    $('.anvil-role-avatar button').click();
    await sleep(300);
    $$('.ui-menu button').find((b) => /Sign out/.test(b.textContent)).click();
    await until(() => location.hash === '#landing' && window.UI_READY, 'signed out');
    await sleep(600);
  }
  async function dialog(open, what, close) {
    open();
    await until(() => $('.anvil-modal-content .dlg-host'), what + ' dialog');
    await sleep(800);
    $$('.anvil-modal-content button').find((b) => (close || /^(Cancel|Not now|Close)$/).test(b.textContent.trim())).click();
    await until(() => !$('.anvil-modal-content .dlg-host'), what + ' closed');
    await sleep(300);
    log.push('ok   ' + what + ' dialog opens and closes');
  }
  async function signUp(name, email, pw) {
    await visit('#auth/signup');
    const i = inputs();
    type(i[0], name); type(i[1], email); type(i[2], pw);
    const tick = $('.au-card input[type=checkbox]'); if (tick && !tick.checked) tick.click();
    button('.au-card .anvil-role-btn-block', /Create account/).click();
  }
  try {
    // ---- visitors
    for (const h of ['#landing', '#books', '#stars', '#auth', '#auth/signup', '#auth/reset']) await visit(h);
    await visit('#books');
    const book = await href('.pc-books a.pc-book[href^="#book/"]', 'a book on the shelf');
    await visit(book);
    const character = await href('.bp-char a.pic[href^="#character/"]', 'a character card');
    await visit(character);
    const cast = await href('.pc-cast a[href^="#cast/"]', 'a collage card');
    await visit(cast);
    const fan = await href('.cs-who a[href^="#fan/"]', 'the collage maker');
    const star = await href('.cs-star a[href^="#stars/"]', 'a star in the collage');
    await dialog(() => $('.cs-actions .pc-heart').click(), 'join (swoon as a visitor)');
    for (const h of [fan, star, '#book/no-such-book', '#cast/no-such-collage', '#stars/nobody-at-all', '#fan/[1,2]']) await visit(h);
    window.UI_READY = false; location.hash = '#mine';  // members only: the sign-in page (the address follows)
    await until(() => window.UI_READY && location.hash === '#auth' && $('.au-card'), '#mine -> sign in', 30000);
    log.push('ok   #mine asks a visitor to sign in');

    // ---- a new member
    await signUp('Smoke Tester', 'smoke' + Date.now() + '@example.com', 'Pc-' + Math.random().toString(36).slice(2) + '-Kq7');
    await until(() => location.hash === '#mine' && window.UI_READY, 'signed up (back to #mine)', 60000);
    await sleep(500);
    for (const h of ['#books', '#mine', '#photos', '#profile', '#suggest', '#landing', book, character, star, fan]) await visit(h);
    const edit = '#castedit/' + character.split('/')[1];
    await visit(edit);
    await dialog(() => $('.ce-slot .ph').click(), 'choose a photo');
    await visit(cast);
    await dialog(() => button('.cs-actions', /^Report$/).click(), 'report');
    await signOut();

    // ---- the admin (ADMIN_EMAILS address; made on the first run in this local database)
    const pw = 'Pc-local-admin-Kq7-2026';
    await visit('#auth');
    let i = inputs(); type(i[0], 'arkulinskis@gmail.com'); type(i[1], pw);
    button('.au-card .anvil-role-btn-block', /^Sign in$/).click();
    await sleep(3500);
    if (location.hash !== '#books') await signUp('Local Admin', 'arkulinskis@gmail.com', pw);
    await until(() => location.hash === '#books' && window.UI_READY, 'signed in as admin', 60000);
    for (const h of ['#admin', '#admin/books', '#admin/queue', '#admin/reports', '#admin/feedback', '#admin/users', '#admin/demo', book]) await visit(h);
    await visit('#admin/books');
    await dialog(() => button('.ad-books', /^Edit$/).click(), 'edit a book');
    await signOut();
    log.push(bad.length ? 'PROBLEMS: ' + bad.join(' | ') : 'PASSED');
    return { ok: !bad.length, log };
  } catch (e) {
    log.push(String(e && e.message || e));
    log.push('at ' + location.hash + ': ' + ((($('.anvil-modal-content') || $('.ui-main') || document.body).innerText) || '').replace(/\s+/g, ' ').slice(0, 400));
    return { ok: false, log };
  }
})();
