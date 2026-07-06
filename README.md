<div align="center">

# 🎙️ Voice Bridge

**リアルタイム音声翻訳 & AI 音声チャット**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat-square)]()
[![Languages](https://img.shields.io/badge/Languages-7%2B-orange?style=flat-square)]()

[📖 ドキュメント](./docs/README.md) · [🚀 クイックスタート](#クイックスタート) · [🐛 Issues](https://github.com/zephel01/voice-bridge/issues)

</div>

---

## 概要

Voice Bridge は **2つのモード** を持つリアルタイム音声処理アプリです。

| モード | 説明 | ガイド |
|--------|------|--------|
| 🌍 **翻訳モード** | システム音声をキャプチャして ASR → 翻訳 → TTS をリアルタイムに実行。YouTube の英語動画を日本語音声で聴くなどの用途に。 | [翻訳モードガイド](./docs/guides/TRANSLATE_MODE_GUIDE.md) |
| 💬 **チャットモード** | マイクで話しかけるとローカル LLM が音声で返答。VOICEVOX・CoeiroInk と組み合わせてずんだもん・リリンちゃんと会話可能。 | [チャットモードガイド](./docs/guides/CHAT_MODE_GUIDE.md) |

> どちらを選ぶか迷ったら → [モード選択ガイド](./docs/guides/MODES_OVERVIEW.md)

---

## ✨ 主な機能

- **リアルタイム多言語翻訳** — 7言語対応（英 / 日 / 中 / 西 / 仏 / 独 / 韓）
- **AI 音声チャット** — Ollama / LM Studio などのローカル LLM に対応
- **複数の TTS エンジン** — CoeiroInk（リリンちゃん）、VOICEVOX（ずんだもん等）、Edge TTS
- **🎭 Live2D アバター連携** — Electron + pixi-live2d-display で Cubism 4/5 モデルを表示し、TTS に合わせて口パク・まばたき・感情表現
- **入力ゲイン / オートゲイン** — 音量の小さい動画でも自動増幅して検出（AGC）
- **Silero VAD** による自然な発話検出
- **低遅延応答** — LLM ストリーミング + TTS ダブルバッファリング
- **Qwen3-ASR 対応** — 52言語対応、本アプリでは7言語 + 自動言語検出
- **GUI でリアルタイム切り替え** — モード・ASR エンジン・LLM モデル・チャンク長・入力ゲイン
- **パイプラインレイテンシ** のリアルタイム計測・表示

---

## 🌐 対応言語

英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

> **Note:** Moonshine エンジン使用時は `en / ja / zh / es / ko` の5言語に対応（`fr`, `de` は未対応）。  
> Qwen3-ASR は52言語に対応しており（本アプリでは7言語を使用）、言語自動検出もサポートしています。

---

## 🖥️ 動作環境

| 項目 | 要件 |
|------|------|
| Python | 3.9 以上 |
| OS | macOS 10.12+ / Windows 10・11 / Linux（PulseAudio or PipeWire） |
| メモリ | 4 GB 以上（8 GB 推奨） |

---

## 🚀 クイックスタート

### 1. リポジトリをクローン

```bash
git clone https://github.com/zephel01/voice-bridge.git
cd voice-bridge
```

### 2. 仮想環境を作成・依存関係をインストール

```bash
# macOS / Linux
python3 -m venv venv && source venv/bin/activate

# Windows
python -m venv venv && venv\Scripts\activate

pip install -r requirements.txt
```

<details>
<summary>Linux の場合（追加パッケージが必要）</summary>

```bash
# Ubuntu / Debian
sudo apt install portaudio19-dev python3-tk

# Fedora
sudo dnf install portaudio-devel python3-tkinter
```

</details>

### 3. モード別セットアップ

<details>
<summary>💬 チャットモード</summary>

ローカル LLM（Ollama）が必要です。メモリ別推奨モデル：

| メモリ | 推奨モデル |
|--------|-----------|
| 8 GB 以下 | `qwen2.5:7b-instruct` |
| 16 GB | `qwen2.5:14b-instruct` |
| 32 GB 以上 | `qwen3:14b`（最新・推奨） |

詳細：[チャットモード完全ガイド](./docs/guides/CHAT_MODE_GUIDE.md) / [Ollama セットアップ](./docs/setup/OLLAMA_SETUP.md) / [メモリ別ガイド](./docs/setup/MEMORY_REQUIREMENTS.md)

</details>

<details>
<summary>🌍 翻訳モード</summary>

⚡ **LLM は不要** — ASR + Google Translate のみで動作します。

OS ごとのセットアップ：

| OS | 方法 |
|----|------|
| macOS | [BlackHole クイックスタート](./docs/setup/BLACKHOLE_QUICK_START.md) |
| Windows | WASAPI ループバック（自動対応） |
| Linux | [Linux トラブルシューティング](./docs/troubleshooting/LINUX_TROUBLESHOOTING.md) |

詳細：[翻訳モード完全ガイド](./docs/guides/TRANSLATE_MODE_GUIDE.md)

</details>

### 4. 起動

```bash
# 翻訳モード（GUI）
python main.py

# チャットモード（VAD + Whisper）
python main.py --mode chat --vad

# リリンちゃんでチャット（CoeiroInk）
python main.py --mode chat --vad --coeiroink

# 自動言語検出で翻訳
python main.py --source-lang auto

# Qwen3-ASR で起動
python main.py --asr qwen3

# 音量が小さい動画向け（オートゲインで自動増幅）
python main.py --auto-gain

# 手動で3倍に増幅
python main.py --gain 3.0

# Live2D アバター連携（別ターミナルで Electron UI を起動しておく）
python main.py --mode chat --vad --live2d
```

> すべてのオプション → [CLI リファレンス](./docs/reference/CLI_REFERENCE.md)

---

## 🎭 Live2D アバター連携

TTS 出力に合わせて Live2D キャラクターが口パク・まばたき・表情変化するフロントエンドを
同梱しています。Electron + React + pixi-live2d-display 構成で、Cubism 4/5 モデル
（`.moc3` + `.model3.json`）に対応。

```
voice-bridge (Python)
  └─ live2d_bridge.py  ── WebSocket ──▶  live2d-ui (Electron)
                                           └─ pixi-live2d-display で表示
                                              + AnalyserNode で口パク
                                              + 感情プリセットで表情補間
```

### Live2D クイックスタート

```bash
# 1) Cubism Core を配置（Live2D 公式 SDK から DL）
#    → live2d-ui/public/live2dcubismcore.min.js

# 2) モデルを配置（公式サンプル Haru 等）
#    → live2d-ui/public/live2d/<name>/runtime/*.model3.json

# 3) Electron UI を起動
cd live2d-ui
npm install
npm run start

# 4) 別ターミナルで voice-bridge を --live2d 付きで起動
cd ..
python main.py --mode chat --vad --live2d
```

Live2D フロントが接続されると右上に **Connected** バッジが出て、TTS 出力が
自動的にフロントへ転送されキャラクターが喋ります。未接続時は従来どおり
pygame で再生されます。

詳細:

- ファイル・フォルダ構成リファレンス: [`docs/guides/LIVE2D_FILES.md`](./docs/guides/LIVE2D_FILES.md)
- セットアップ手順: [`docs/guides/LIVE2D_SETUP.md`](./docs/guides/LIVE2D_SETUP.md)
- `main.py` への組み込み詳細: [`docs/guides/LIVE2D_INTEGRATION_PATCH.md`](./docs/guides/LIVE2D_INTEGRATION_PATCH.md)

---

## 🗂️ ドキュメント

```
docs/
├── guides/          # モード別ガイド
├── setup/           # 環境構築
├── reference/       # CLI・アーキテクチャ
├── troubleshooting/ # トラブルシューティング・FAQ
└── internal/        # 開発者向け
```

| カテゴリ | リンク |
|----------|--------|
| GUI の使い方 | [GUI ガイド](./docs/guides/GUI_GUIDE.md) |
| Live2D セットアップ | [Live2D セットアップ](./docs/guides/LIVE2D_SETUP.md) / [ファイル構成](./docs/guides/LIVE2D_FILES.md) |
| システム設計 | [アーキテクチャ](./docs/reference/ARCHITECTURE.md) |
| FAQ | [よくある質問](./docs/troubleshooting/FAQ.md) |
| 開発者向け | [内部ドキュメント](./docs/internal/) |

---

## 🔊 音声合成エンジン

本アプリは以下の TTS エンジンに対応しています。配信・動画で使用する際はクレジット表記をお願いします。

| エンジン | キャラクター例 | クレジット表記 |
|----------|--------------|--------------|
| [VOICEVOX](https://voicevox.hiroshiba.jp/) | ずんだもん、四国めたぼ 等 | `VOICEVOX:キャラクター名` |
| [CoeiroInk](https://coeiroink.com/) | リリンちゃん 等 | 公式サイトを参照 |
| Edge TTS | — | 不要 |

---

## 🎭 Live2D 関連クレジット

Live2D アバター機能を配信・動画・公開アプリで使用する際は、各コンポーネントの
利用条件・クレジット表記を必ず確認してください。

| コンポーネント | 提供元 | 利用条件 |
|----------------|--------|----------|
| [Live2D Cubism SDK for Web](https://www.live2d.com/sdk/download/web/) | Live2D Inc. | 無償版は年間売上上限あり。商用利用は [Live2D 商用ライセンス](https://www.live2d.com/download/cubism-sdk/release-license/) 要 |
| [Live2D 公式サンプルモデル](https://www.live2d.com/download/sample-data/)（Haru / Hiyori 等） | Live2D Inc. | 同梱の `ReadMe.txt` / [サンプルデータ利用規約](https://www.live2d.com/eula/live2d-free-material-license-agreement_jp.html) に従う。個人の動画投稿は無償、商用はライセンス契約要 |
| [pixi-live2d-display](https://github.com/guansss/pixi-live2d-display) | guansss | MIT License |
| [Pixi.js](https://pixijs.com/) | Pixi.js Team | MIT License |
| 自作・第三者モデル | 各モデル作者 | 作者指定の規約に従う（[nizima](https://nizima.com/) 等） |

**クレジット表記例（動画・配信）**:

```
Live2D Cubism SDK / Model © Live2D Inc.
Character: Haru (Live2D 公式サンプルモデル)
```

> モデルをリポジトリに含める場合、ライセンス文書（`ReadMe.txt` 等）を削除せず
> そのまま同梱してください。再配布条件に違反する可能性があります。
> 詳細: [`docs/guides/LIVE2D_FILES.md`](./docs/guides/LIVE2D_FILES.md) §7・§9

---

## 📄 ライセンス

本リポジトリのソースコードは [MIT License](./LICENSE) で提供されます。

ただし以下は本リポジトリのライセンス対象外です（それぞれの配布元の規約に従います）:

- `live2d-ui/public/live2dcubismcore.min.js` — Live2D Cubism SDK（各自 DL）
- `live2d-ui/public/live2d/**` — Live2D モデル本体（サンプル・有償・自作いずれも）
