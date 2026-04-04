# Voice Bridge

リアルタイム音声翻訳 & AI チャットアプリ。2つのモードで使えます。

- **翻訳モード** — システム音声をキャプチャして、音声認識 → 翻訳 → 音声合成をリアルタイムに行います。YouTube の英語動画を日本語音声で聞く、といった使い方ができます。
- **チャットモード** — マイクで話しかけると、ローカル LLM が音声で返答します。VOICEVOX・CoeiroInk と組み合わせれば、ずんだもん・リリンちゃんと音声で会話できます。

## 主な機能

- リアルタイム多言語翻訳（7言語対応）
- ローカル LLM による AI 音声チャット（Ollama / LM Studio 等）
- 複数の TTS エンジン対応 — CoeiroInk（リリンちゃん）、VOICEVOX（ずんだもん等）、Edge TTS
- Silero VAD による自然な発話検出
- LLM ストリーミング + TTS ダブルバッファリングで低遅延応答
- GUI でモード・ASR エンジン・LLM モデルを切り替え可能

## 対応言語

英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

> **Note:** Moonshine エンジン使用時は en / ja / zh / es / ko の5言語に対応（fr, de は未対応）。

## 対応環境

- Python 3.9+
- macOS 10.12+ / Windows 10・11 / Linux（PulseAudio or PipeWire）
- メモリ 4GB以上（8GB推奨）

## 📌 モードを選ぶ

Voice Bridge には2つのモードがあります。使用目的に応じて選択してください：

| 目的 | ガイド | 難易度 |
|---|---|---|
| **💬 AI と会話したい** | [チャットモード完全ガイド](./docs/guides/CHAT_MODE_GUIDE.md) | 🟡 中 |
| **🌍 動画・会議を翻訳したい** | [翻訳モード完全ガイド](./docs/guides/TRANSLATE_MODE_GUIDE.md) | 🟢 簡単 |
| **🤔 どちらか迷っている** | [モード選択ガイド](./docs/guides/MODES_OVERVIEW.md) | — |

---

## クイックスタート

### 1. インストール

```bash
git clone https://github.com/zephel01/voice-bridge.git
cd voice-bridge
python3 -m venv venv && source venv/bin/activate   # macOS / Linux
# python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

**Linux の場合:**
```bash
# Ubuntu / Debian
sudo apt install portaudio19-dev python3-tk
# Fedora
sudo dnf install portaudio-devel python3-tkinter
```

### 2. セットアップ（OS別）

OS ごとに異なる設定があります。以下の該当ドキュメントをご参照ください：

- **macOS** → [BlackHole クイックスタート](./docs/setup/BLACKHOLE_QUICK_START.md)
- **Windows** → [インストールガイド](./docs/setup/INSTALL.md)
- **Linux** → [インストールガイド](./docs/setup/LINUX_INSTALL.md)

### 3. ローカル LLM の準備（チャットモード用）

チャットモードには Ollama などのローカル LLM サーバーが必要です。詳しくは [Ollama セットアップガイド](./docs/setup/OLLAMA_SETUP.md) をご覧ください。

### 4. 起動

```bash
# 翻訳モード（GUI）
python main.py

# チャットモード（VAD + Whisper）
python main.py --mode chat --vad

# リリンちゃんでチャット（CoeiroInk）
python main.py --mode chat --vad --coeiroink
```

詳しいオプションは [CLI リファレンス](./docs/reference/CLI_REFERENCE.md) をご覧ください。

## GUI の使い方

すべての設定はドロップダウンで変更できます。詳しくは [GUI ガイド](./docs/guides/GUI_GUIDE.md) をご覧ください。

## システムアーキテクチャ

全体設計や技術詳細については [システムアーキテクチャ](./docs/reference/ARCHITECTURE.md) をご覧ください。

## トラブルシューティング

問題が発生した場合は、以下のガイドをご覧ください：

- [macOS 用 BlackHole トラブルシューティング](./docs/troubleshooting/BLACKHOLE_TROUBLESHOOTING.md)
- [Linux トラブルシューティング](./docs/troubleshooting/LINUX_TROUBLESHOOTING.md)
- [よくある質問](./docs/troubleshooting/FAQ.md)

## ドキュメント一覧

すべてのドキュメントは [docs/](./docs/) フォルダに整理されています。詳しくは [ドキュメント索引](./docs/README.md) をご覧ください。

## 開発者向け

本プロジェクトの内部設計や拡張方法については [開発者ガイド](./docs/internal/) をご覧ください。

## 音声合成エンジンについて

本アプリケーションでは以下の音声合成エンジンを使用しています：

### VOICEVOX

[VOICEVOX](https://voicevox.hiroshiba.jp/) — ずんだもん・四国めたぼ等のキャラクターボイス

配信・動画で使用する場合はクレジット表記（`VOICEVOX:キャラクター名`）をお願いします。

### CoeiroInk

[CoeiroInk](https://coeiroink.com/) — リリンちゃん等のキャラクターボイス

配信・動画で使用する場合はクレジット表記をお願いします。詳しくは公式サイトをご確認ください。

## ライセンス

MIT License
