// Fantasia Library ― 蔵書の表示・案内タブ・ホーム画面追加ボタン
(function () {
  'use strict';

  // ---------- 蔵書(games.json から作る) ----------
  var gallery = document.getElementById('gallery');
  var count = document.getElementById('count');

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;   // textContent なので、文字がそのまま表示される(安全)
    return e;
  }

  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? m[1] + '.' + m[2] + '.' + m[3] : '';
  }

  function exhibit(g, i) {
    var a = el('a', 'exhibit');
    a.href = g.path;
    a.setAttribute('aria-label', g.title + ' を遊ぶ');

    var art = el('div', 'art');
    if (g.thumbnail) {
      var img = el('img');
      img.src = g.thumbnail;
      img.alt = '';
      img.loading = 'lazy';
      art.appendChild(img);
    }
    a.appendChild(art);

    var plate = el('div', 'plate');
    plate.appendChild(el('div', 'no', 'No.' + String(i + 1).padStart(3, '0')));
    plate.appendChild(el('h3', null, g.title));
    if (g.description) plate.appendChild(el('p', 'desc', g.description));
    if (g.tags && g.tags.length) {
      var meta = el('div', 'meta');
      g.tags.forEach(function (t) { meta.appendChild(el('span', 'tag', t)); });
      plate.appendChild(meta);
    }
    plate.appendChild(el('span', 'play', 'あそぶ ▶'));
    if (g.added) plate.appendChild(el('div', 'date', '収蔵日 ' + fmtDate(g.added)));
    a.appendChild(plate);
    return a;
  }

  function soon() {
    var d = el('div', 'exhibit soon');
    d.appendChild(el('div', 'big', '📖'));
    d.appendChild(el('p', null, 'つぎの一冊を準備中…'));
    return d;
  }

  fetch('games.json', { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      var games = (data && data.games) || [];
      gallery.textContent = '';
      games.forEach(function (g, i) { gallery.appendChild(exhibit(g, i)); });
      gallery.appendChild(soon());
      count.textContent = games.length + ' 冊を所蔵中';
    })
    .catch(function () {
      gallery.textContent = '';
      gallery.appendChild(el('p', 'loading', '蔵書を読み込めませんでした。通信を確認して、ページを開き直してください。'));
    });

  // ---------- 案内タブ ----------
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tabs [role="tab"]'));
  function select(tab) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
  }
  tabs.forEach(function (t) { t.addEventListener('click', function () { select(t); }); });

  // 見ている端末に合わせて、最初に開くタブを選ぶ
  var ua = navigator.userAgent || '';
  if (/Android/i.test(ua)) select(tabs[1]);
  else if (!/iPhone|iPad|iPod/i.test(ua) && !(/Macintosh/i.test(ua) && 'ontouchend' in document)) select(tabs[2]);

  // ---------- 図書館をアプリに追加(Android/PCのChromeなど) ----------
  var deferred = null;
  var box = document.getElementById('install-box');
  var btn = document.getElementById('install-btn');
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    box.hidden = false;
  });
  btn.addEventListener('click', function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.finally(function () { deferred = null; box.hidden = true; });
  });
  window.addEventListener('appinstalled', function () { box.hidden = true; });

  // ---------- オフライン対応 ----------
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    });
  }
})();
