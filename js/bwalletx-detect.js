/*!
 * bwalletx-detect.js: tiny standalone detector for the bWalletX wallet (Chrome extension, or the
 * bWalletX app's in-app browser). Reusable on any bX site; no dependencies, never prompts.
 *
 * How it detects (same rules as @bwalletx/connect discoverBwalletX):
 *   1. dispatches `brc100:requestWallet`, listens for `brc100:announceWallet`; the extension
 *      announces rdns `com.bwalletx.extension`, the mobile app `space.bwallet.mobile`;
 *   2. otherwise falls back to a bare `window.CWI` (in-app browser / older builds).
 * It waits up to DECIDE_MS before choosing (and flips to "yes" if an announcement arrives later).
 * Detection only listens to events; the wallet is never called until the visitor clicks.
 *
 * Markup contract (all optional, add what you use):
 *   <a data-bwx-cta href="https://bwalletx.com/get"><span class="bwx-t">Get bWalletX</span></a>
 *       -> when detected the label becomes "Open bWalletX" (override: data-bwx-yes="Connect") and a
 *          click asks the wallet to connect (getPublicKey identityKey); if that fails it opens the href.
 *   <span data-bwx-strip>Part of <b>bWalletX</b></span>
 *       -> becomes "You're on bWalletX ✓" (override: data-bwx-strip-yes="...").
 * State: <html data-bwx="pending|yes|no">. While pending, CTA labels are hidden (no flash of the
 * wrong label); a timeout guarantees they come back. Events: `bwalletx:detected` on window.
 * API: window.bwalletxDetect = { ready: Promise<{found,method,rdns,wallet}>, state() }.
 */
(function () {
  'use strict';
  var DECIDE_MS = 600, HARD_MS = 900;
  var RDNS = { 'com.bwalletx.extension': 'extension', 'space.bwallet.mobile': 'in-app' };
  var de = document.documentElement, result = null, done = false, resolveFn;
  var ready = new Promise(function (r) { resolveFn = r; });
  de.setAttribute('data-bwx', 'pending');
  var st = document.createElement('style');
  st.textContent = 'html[data-bwx="pending"] [data-bwx-cta] .bwx-t{visibility:hidden}';
  (document.head || de).appendChild(st);

  function apply(r) {
    var yes = !!r.found;
    de.setAttribute('data-bwx', yes ? 'yes' : 'no');
    Array.prototype.forEach.call(document.querySelectorAll('[data-bwx-cta]'), function (el) {
      var t = el.querySelector('.bwx-t') || el;
      if (!el.hasAttribute('data-bwx-no')) el.setAttribute('data-bwx-no', t.textContent);
      t.textContent = yes ? (el.getAttribute('data-bwx-yes') || 'Open bWalletX') : el.getAttribute('data-bwx-no');
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-bwx-strip]'), function (el) {
      if (!el.hasAttribute('data-bwx-strip-no')) el.setAttribute('data-bwx-strip-no', el.innerHTML);
      if (yes) el.textContent = el.getAttribute('data-bwx-strip-yes') || 'You’re on bWalletX ✓';
      else el.innerHTML = el.getAttribute('data-bwx-strip-no');
    });
  }
  function finish(r) {
    if (done && !(r.found && !result.found)) return; // allow a late "yes" to upgrade a "no"
    var first = !done; done = true; result = r; apply(r);
    if (first) resolveFn(r);
    try { window.dispatchEvent(new CustomEvent('bwalletx:detected', { detail: { found: r.found, method: r.method, rdns: r.rdns } })); } catch (e) {}
  }
  function onAnnounce(e) {
    try {
      var d = e.detail || {}, rdns = d.info && d.info.rdns;
      if (d.wallet && rdns && RDNS[rdns]) finish({ found: true, method: RDNS[rdns], rdns: rdns, wallet: d.wallet });
    } catch (err) {}
  }
  try {
    window.addEventListener('brc100:announceWallet', onAnnounce);
    window.dispatchEvent(new Event('brc100:requestWallet'));
  } catch (e) {}
  function decide() {
    if (done) return;
    var cwi = window.CWI;
    finish(cwi ? { found: true, method: 'in-app', rdns: null, wallet: cwi } : { found: false, method: null, rdns: null, wallet: null });
  }
  // announcements can arrive before the DOM exists: re-apply once it does
  function reapply() { if (done) apply(result); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', reapply); else reapply();
  window.addEventListener('load', reapply);
  setTimeout(decide, DECIDE_MS);
  setTimeout(function () { // hard fallback so labels can never stay hidden
    if (!done) finish({ found: false, method: null, rdns: null, wallet: null });
    try { window.dispatchEvent(new Event('brc100:requestWallet')); } catch (e) {} // late announcers
  }, HARD_MS);
  setTimeout(function () { try { window.dispatchEvent(new Event('brc100:requestWallet')); } catch (e) {} }, 2500);

  // Click: when the wallet is present, ask it to connect (user gesture); otherwise follow the link.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-bwx-cta]');
    if (!a || !result || !result.found || !result.wallet) return;
    e.preventDefault();
    var w = result.wallet, go = function () { if (a.href) window.open(a.href, '_blank', 'noopener'); };
    try {
      Promise.resolve(w.getPublicKey({ identityKey: true })).then(function () {
        a.setAttribute('data-bwx-connected', '1');
      }, go);
    } catch (err) { go(); }
  });

  window.bwalletxDetect = { ready: ready, state: function () { return de.getAttribute('data-bwx'); } };
})();
