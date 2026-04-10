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
- **Silero VAD** による自然な発話検出
- **低遅延応答** — LLM ストリーミング + TTS ダブルバッファリング
- **Qwen3-ASR 対応** — 52言語対応、本アプリでは7言語 + 自動言語検出
- **GUI でリアルタイム切り替え** — モード・ASR エンジン・LLM モデル・チャンク長
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
```

> すべてのオプション → [CLI リファレンス](./docs/reference/CLI_REFERENCE.md)

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

## 📄 ライセンス

[MIT License](./LICENSE)
