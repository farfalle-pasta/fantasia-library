# Fantasia Library(小さな世界と創造の記録)

ChatGPT・Gemini・ClaudeなどのAIと作ったブラウザゲームを保管する、GitHub Pages 用の静的サイトです。
ビルド作業は不要で、このフォルダの中身をそのまま公開できます。

```
index.html / style.css / app.js   図書館のトップページ
games.json                        蔵書リスト(ここに書いた作品がカードになる)
manifest.webmanifest / sw.js      図書館そのものをアプリにする設定
icons/                            図書館のアイコン
games/dream-witch/                蔵書 No.001 ドリームウィッチ(ゲーム本体+アプリ設定)
tools/add_game.py                 新しいゲームを蔵書に追加する道具
.nojekyll                         GitHub Pages に「そのまま公開して」と伝える空ファイル
```

## 1. GitHub Pages で公開する(最初の1回)

1. GitHub で **New repository**。名前は何でもOK(例: `game-museum`)。**Public** にして作成。
2. 作ったリポジトリで **Add file → Upload files**。このフォルダの**中身すべて**(`.nojekyll` と各フォルダを含む)をドラッグして **Commit changes**。
   - ゲームのHTMLは約10MBですが、ブラウザからのアップロード上限(25MB)以内です。
   - 隠しファイル `.nojekyll` が見えないときは、リポジトリ上で **Add file → Create new file** にファイル名 `.nojekyll` を入れて空のまま保存してもOKです。
3. **Settings → Pages** を開き、**Source: Deploy from a branch** / **Branch: main**・**/ (root)** を選んで **Save**。
4. 1〜2分待つと `https://あなたのユーザー名.github.io/リポジトリ名/` で公開されます。

ゲームの直接URLは `https://あなたのユーザー名.github.io/リポジトリ名/games/dream-witch/` です。

## 2. ゲームをホーム画面に置く

**置きたいゲームのページを開いてから**追加します(図書館トップで追加すると図書館がアプリになります)。

- **iPhone / iPad**: Safari で開く → 共有ボタン → 「ホーム画面に追加」
- **Android**: Chrome で開く → 右上︙ → 「アプリをインストール」(または「ホーム画面に追加」)
- **パソコン**: Chrome / Edge のアドレスバー右端のインストールアイコン

⚠️ **iPhone の注意**: Safari で遊んだセーブデータと、ホーム画面アプリのセーブデータは別物です。
すでに Safari で進めている場合は、ゲーム内の「💾 セーブコード」で引っ越してください。
また、同じサイトの中のゲームは同じ保存領域を共有するため、新しいゲームのセーブ名(キー)は
ゲームごとに別の名前(例: `dreamwitch_save_v1` のように頭にゲーム名)をつけると安全です。

## 3. 新しいゲームを蔵書に追加する

Python 3 が使えるパソコンで、このフォルダの一番上から実行します。

```
python3 tools/add_game.py \
  --html  ~/Downloads/new-game.html \
  --slug  new-game \
  --title "新しいゲーム" \
  --description "ひとことで言うとどんなゲームか" \
  --icon  ~/Downloads/icon.png \
  --thumb ~/Downloads/thumb.jpg \
  --tags  "パズル,スマホ縦向き"
```

- `--slug` はURLになる半角英数字(小文字とハイフン)。
- `--icon` は正方形のPNG(キャラ絵など)。パステル背景に自動でのせて、ホーム画面アイコン4種類を作ります(Pillow があれば)。
- `--thumb` は蔵書カードの画像。省略するとアイコンを使います。
- 横向きのゲームは `--orientation landscape` を付けます。
- 「ホーム画面アプリにすると、ヘッダーや下のタブごと画面がずるずる動く」ゲームには `--lock-scroll` を付けます(ドリームウィッチは設定済み。一度付ければ次回以降も覚えています)。
- 実行したら、変更されたファイルを GitHub にアップロード(または `git add . && git commit && git push`)すれば完成です。
- **ゲームを更新したとき**も同じコマンドをもう一度実行します。中身が変わると自動で新しい版が配信されます。

Python が使えない場合は、Claude に「この新作を図書館に追加して」と HTML を渡せば、同じ作業をしてくれます。

## 4. 見た目を変える・蔵書を直す

- 色・雰囲気: `style.css` の一番上 `:root`
- 図書館の名前・文言: `index.html`(「Fantasia Library」で検索)
- 蔵書の説明文・順番・タグ: `games.json`(上から順に No.001, 002… と番号がつきます)
- 手元で確認: このフォルダで `python3 -m http.server 8000` → ブラウザで `http://localhost:8000/`
  (ファイルを直接ダブルクリックで開くと、蔵書リストの読み込みが動きません)
