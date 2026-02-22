# Voice Bridge - Chrome 拡張機能

タブの英語音声をリアルタイムで日本語に翻訳して読み上げる Chrome 拡張機能です。

## 機能

- タブの音声をリアルタイムでキャプチャ（YouTube, Zoom, ポッドキャスト等）
- 英語音声を Web Speech API で認識
- Google Translate で日本語に翻訳
- Web Speech Synthesis で日本語読み上げ
- 追加ソフトウェア不要（Chrome のみで動作）

## インストール方法（開発者モード）

1. Chrome で `chrome://extensions` を開く
2. 右上の「**デベロッパーモード**」をオンにする
3. 「**パッケージ化されていない拡張機能を読み込む**」をクリック
4. `voice-bridge-chrome` フォルダを選択
5. 拡張機能が追加されたことを確認

## 使い方

1. 英語の動画・音声が再生されているタブを開く
2. ツールバーの Voice Bridge アイコンをクリック
3. 「▶ 開始」ボタンを押す
4. タブの音声が自動的に認識・翻訳・読み上げされる
5. 「■ 停止」で終了

## アーキテクチャ

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Popup UI   │────▶│  Service Worker   │────▶│    Offscreen      │
│ (popup.*)   │◀────│  (background.js)  │◀────│   Document        │
│             │     │                  │     │  (offscreen.*)    │
│ - 開始/停止  │     │ - オーケストレータ  │     │  - tabCapture     │
│ - テキスト表示│     │ - tabCapture ID   │     │  - 音声認識        │
│ - 設定      │     │ - メッセージ中継    │     │  - 翻訳           │
└─────────────┘     └──────────────────┘     │  - TTS 読み上げ    │
                                             └──────────────────┘
```

### なぜ Offscreen Document を使うのか

Manifest V3 の Service Worker では DOM や MediaStream を扱えません。
Offscreen Document は DOM にアクセスでき、Web Speech API や Audio API が使えるため、
音声処理のメインハブとして機能します。

## ファイル構成

```
voice-bridge-chrome/
├── manifest.json     # 拡張機能の設定
├── background.js     # Service Worker（オーケストレータ）
├── offscreen.html    # Offscreen Document のHTML
├── offscreen.js      # 音声キャプチャ・認識・翻訳・TTS
├── translator.js     # Google Translate API クライアント
├── popup.html        # ポップアップ UI
├── popup.js          # ポップアップのイベント処理
├── popup.css         # ポップアップのスタイル
├── icons/            # 拡張機能アイコン
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md         # このファイル
```

## 技術的な注意事項

### Web Speech API の制限

- ブラウザの音声認識サービス（Google のサーバー）に依存するため、インターネット接続が必要です
- 長時間の連続認識では自動的に切断されることがあります（自動再開を実装済み）
- 認識精度はブラウザと音声の品質に依存します

### 翻訳

- Google Translate の非公式エンドポイントを使用しています
- 大量のリクエストを送ると一時的にブロックされる可能性があります
- 商用利用の場合は Google Cloud Translation API への移行を推奨します

### TTS（読み上げ）

- OS にインストールされている日本語音声を使用します
- macOS: Kyoko, Otoya 等が利用可能
- Windows: Microsoft Haruka, Ayumi 等が利用可能
- 音声の品質は OS とインストールされた音声パックに依存します

### 既知の制限

- 一部のサイト（DRM 保護コンテンツ等）では音声キャプチャが機能しない場合があります
- 拡張機能のポップアップを閉じても翻訳は継続しますが、テキスト表示は更新されません
- VOICEVOX との連携は将来の拡張として検討中です

## デスクトップアプリ版との違い

| 機能 | Chrome 拡張 | デスクトップアプリ |
|------|-----------|----------------|
| セットアップ | Chrome のみ | Python + BlackHole/WASAPI |
| 音声認識 | Web Speech API | faster-whisper（ローカル） |
| 認識精度 | 中 | 高（モデル選択可能） |
| TTS | Web Speech Synthesis | VOICEVOX / Edge TTS |
| TTS 品質 | OS 依存 | 高（VOICEVOX） |
| オフライン | 不可 | 認識・TTS は可能 |
| 対応 OS | Chrome が動く全 OS | macOS / Windows |
