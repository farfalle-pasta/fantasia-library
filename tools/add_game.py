#!/usr/bin/env python3
"""
add_game.py ― 新しいブラウザゲームを「図書館」にしまうための道具
====================================================================
ゲームのHTMLを1つ渡すと、次のことを自動でやります。

  1. games/<slug>/ フォルダを作って、ゲームを index.html として置く
  2. ホーム画面に置くための設定(manifest・service worker・アイコン)を追加する
  3. games.json に蔵書カードを1件追加(同じ slug があれば更新)する

使い方(リポジトリのいちばん上のフォルダで実行):

  python3 tools/add_game.py \\
      --html  ~/Downloads/new-game.html \\
      --slug  new-game \\
      --title "新しいゲーム" \\
      --description "ひとことで言うとどんなゲームか" \\
      --icon  ~/Downloads/icon.png        # 省略可(正方形のPNG推奨)
      --thumb ~/Downloads/thumb.jpg       # 省略可(蔵書カードの画像)

ゲームを作り直したとき(更新)は、同じ --slug でもう一度実行すればOKです。
ゲームの中身が変わると service worker の版が自動で変わるので、
遊んでいる人にも次回起動時に新しい版が届きます。

必要なもの: Python 3。アイコン生成には Pillow があるとより便利(無くても動きます)。
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK_BEGIN = "<!-- PWA:BEGIN (add_game.py が自動で入れた部分。消さないでね) -->"
MARK_END = "<!-- PWA:END -->"


def make_icons(src, dest):
    """src(正方形PNG)から、ホーム画面用アイコン4種類を作る。Pillow が無ければ False。"""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return False

    def build(size, ratio, out):
        # パステルのグラデーション背景に、キャラ画像を中央に置く
        bg = Image.new("RGBA", (size, size))
        px = bg.load()
        c1, c2 = (255, 236, 246), (214, 200, 250)
        for y in range(size):
            for x in range(size):
                t = (x * 0.35 + y * 0.65) / size
                px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
        ch = Image.open(src).convert("RGBA")
        s = int(size * ratio)
        ch = ch.resize((s, s), Image.LANCZOS)
        off = ((size - s) // 2, (size - s) // 2)
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        alpha = ch.split()[3].point(lambda v: int(v * 0.25))
        shadow.paste((120, 90, 190, 255), (off[0], off[1] + size // 60), alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(size / 60))
        bg.alpha_composite(shadow)
        bg.alpha_composite(ch, off)
        bg.convert("RGB").save(out, optimize=True)

    build(512, 0.88, dest / "icon-512.png")
    build(192, 0.88, dest / "icon-192.png")
    build(512, 0.70, dest / "icon-maskable-512.png")  # Androidの丸/角丸マスク用に余白多め
    build(180, 0.80, dest / "apple-touch-icon.png")   # iPhone用
    return True


LOCK_BLOCK = """<style>
/* 画面固定(ホーム画面アプリで、ヘッダー・下のタブごと画面がずるずる動くのを防ぐ) */
html, body { position: fixed; top: 0; left: 0; right: 0; bottom: 0; width: 100%; height: 100%; overflow: hidden; overscroll-behavior: none; }
</style>
<script>
/* スクロールできる場所(中身が画面より長い部分)以外では、指でなぞっても画面全体が動かないようにする */
document.addEventListener('touchmove', function (e) {
  if (e.touches && e.touches.length > 1) return;
  for (var n = e.target; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
    var oy = getComputedStyle(n).overflowY;
    if ((oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight + 1) return;
  }
  if (e.cancelable) e.preventDefault();
}, { passive: false });
</script>
"""


def inject_head(html, title, theme, lock_scroll=False):
    block = f"""{MARK_BEGIN}
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{title}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<script>
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', function () {{
    navigator.serviceWorker.register('sw.js').catch(function () {{}});
  }});
}}
</script>
{LOCK_BLOCK if lock_scroll else ''}{MARK_END}
"""
    # 前に入れた分があれば取り除いてから入れ直す(何度実行しても同じ結果になる)
    html = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\s*", "", html, flags=re.S)
    # 文字コード指定(<meta charset>)は先頭1024バイト以内に必要なので、その直後に入れる
    m = re.search(r"<meta[^>]+charset[^>]*>", html, flags=re.I) or re.search(r"<head[^>]*>", html, flags=re.I)
    if not m:
        sys.exit("エラー: <head> が見つかりません。HTMLを確認してください。")
    return html[: m.end()] + "\n" + block + html[m.end():]


def detect_theme(html, default="#f6efff"):
    m = re.search(r'<meta[^>]+name=["\']theme-color["\'][^>]+content=["\']([^"\']+)', html, flags=re.I)
    return m.group(1) if m else default


def main():
    ap = argparse.ArgumentParser(description="ゲームを図書館にしまう")
    ap.add_argument("--html", required=True, help="ゲームのHTMLファイル")
    ap.add_argument("--slug", required=True, help="フォルダ名・URLになる英数字(例: dream-witch)")
    ap.add_argument("--title", required=True, help="ゲーム名")
    ap.add_argument("--description", default="", help="蔵書カードの説明文")
    ap.add_argument("--icon", help="ホーム画面アイコン元画像(正方形PNG)")
    ap.add_argument("--thumb", help="蔵書カードの画像(jpg/png)")
    ap.add_argument("--tags", default="", help="タグ(カンマ区切り)")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "any"],
                    help="ホーム画面から開いたときの向き(既定: portrait)")
    ap.add_argument("--lock-scroll", dest="lock_scroll", action="store_true", default=None,
                    help="ヘッダー/下タブが指でずれるゲーム用:ホーム画面アプリで画面全体を固定する")
    ap.add_argument("--no-lock-scroll", dest="lock_scroll", action="store_false",
                    help="画面固定をやめる")
    ap.add_argument("--background", default=None, help="起動時の背景色(既定: ゲームのtheme-color)")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.slug):
        sys.exit("エラー: --slug は半角の小文字英数字とハイフンだけにしてください。")
    src = Path(a.html).expanduser()
    if not src.is_file():
        sys.exit(f"エラー: {src} が見つかりません。")

    dest = ROOT / "games" / a.slug
    dest.mkdir(parents=True, exist_ok=True)

    html = src.read_text(encoding="utf-8")
    theme = detect_theme(html)
    # 画面固定の設定は games.json に覚えておき、指定が無ければ前回と同じにする
    cat_path = ROOT / "games.json"
    catalog = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {"games": []}
    old = next((g for g in catalog.get("games", []) if g.get("slug") == a.slug), None)
    lock = a.lock_scroll if a.lock_scroll is not None else bool((old or {}).get("lockScroll", False))
    html = inject_head(html, a.title, theme, lock)
    (dest / "index.html").write_text(html, encoding="utf-8")
    version = hashlib.sha1(html.encode("utf-8")).hexdigest()[:10]

    # --- アイコン ---
    if a.icon:
        icon = Path(a.icon).expanduser()
        if not make_icons(icon, dest):
            print("注意: Pillow が無いので、アイコン画像をそのまま使います(512x512の正方形PNG推奨)。")
            for n in ["icon-512.png", "icon-192.png", "icon-maskable-512.png", "apple-touch-icon.png"]:
                shutil.copyfile(icon, dest / n)
    elif not (dest / "icon-512.png").exists():
        for n in ["icon-512.png", "icon-192.png", "icon-maskable-512.png", "apple-touch-icon.png"]:
            shutil.copyfile(ROOT / "icons" / n, dest / n)  # 図書館のアイコンで代用
        print("注意: --icon が無いので図書館のアイコンを仮に使いました。")

    # --- 蔵書カードの画像 ---
    thumb_rel = None
    if a.thumb:
        t = Path(a.thumb).expanduser()
        ext = t.suffix.lower()
        target = dest / f"thumb{ext}"
        if t.resolve() != target.resolve():
            shutil.copyfile(t, target)
        thumb_rel = f"games/{a.slug}/thumb{ext}"
    else:
        for ext in (".jpg", ".png", ".webp"):
            if (dest / f"thumb{ext}").exists():
                thumb_rel = f"games/{a.slug}/thumb{ext}"
                break
        if not thumb_rel:
            thumb_rel = f"games/{a.slug}/icon-512.png"

    # --- manifest ---
    manifest = {
        "id": "./",
        "name": a.title,
        "short_name": a.title[:12],
        "description": a.description,
        "lang": "ja",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "orientation": a.orientation if a.orientation != "any" else "any",
        "background_color": a.background or theme,
        "theme_color": theme,
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (dest / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- service worker(オフラインでも遊べるようにする) ---
    sw = f"""// 自動生成: add_game.py ― {a.title}
// ゲームの中身が変わると VERSION も変わり、次回起動時に新しい版へ入れ替わります。
const PREFIX = 'game-{a.slug}-';
const CACHE = PREFIX + '{version}';
const FILES = ['./', './index.html', './manifest.webmanifest',
               './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', (e) => {{
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
}});

self.addEventListener('activate', (e) => {{
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
}});

// キャッシュ優先(通信しないので速い・オフラインOK)。無ければ通信して保存。
self.addEventListener('fetch', (e) => {{
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request, {{ ignoreSearch: true }}).then((hit) => {{
      if (hit) return hit;
      return fetch(e.request).then((res) => {{
        if (res && res.ok && new URL(e.request.url).origin === location.origin) {{
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }}
        return res;
      }}).catch(() => caches.match('./index.html'));
    }})
  );
}});
"""
    (dest / "sw.js").write_text(sw, encoding="utf-8")

    # --- games.json ---
    games = catalog.setdefault("games", [])
    today = datetime.date.today().isoformat()
    entry = {
        "slug": a.slug,
        "title": a.title,
        "description": a.description or (old or {}).get("description", ""),
        "path": f"games/{a.slug}/",
        "thumbnail": thumb_rel,
        "tags": [t.strip() for t in a.tags.split(",") if t.strip()] or (old or {}).get("tags", []),
        "added": (old or {}).get("added", today),
        "updated": today,
    }
    if lock:
        entry["lockScroll"] = True
    if old:
        games[games.index(old)] = entry
    else:
        games.append(entry)
    cat_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"できました: games/{a.slug}/  (版 {version})")
    print("次は git add / commit / push で公開してください。")


if __name__ == "__main__":
    main()
