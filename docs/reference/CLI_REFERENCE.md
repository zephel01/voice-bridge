# CLI リファレンス

Voice Bridge のコマンドラインオプション完全リファレンスです。

## 基本的な起動方法

```bash
python main.py [OPTIONS]
```

## オプション一覧

### モード選択

#### `--mode {translate,chat}`

実行モードを指定します。

```bash
# 翻訳モード（デフォルト）
python main.py --mode translate

# チャットモード
python main.py --mode chat
```

| 値 | 説明 |
|---|---|
| `translate` | リアルタイム音声翻訳モード（デフォルト） |
| `chat` | ローカル LLM との音声会話モード |

### 音声認識（ASR）エンジン

#### `--asr {whisper,moonshine,qwen3}`

音声認識エンジンを指定します。デフォルトは `whisper` です。

```bash
# Whisper を使用（日本語推奨）
python main.py --asr whisper

# Moonshine を使用（英語向け、高速）
python main.py --asr moonshine --chunk 2.0

# Qwen3-ASR を使用（全7言語対応・自動検出対応）
python main.py --asr qwen3
```

| 値 | 日本語精度 | 英語精度 | 速度 | 推奨用途 |
|---|---|---|---|---|
| `whisper` | 高 | 高 | 普通 | 日本語チャット・翻訳全般 |
| `moonshine` | 低 | 高 | 最速 | 英語チャット・英語翻訳 |
| `qwen3` | 高 | 高 | 普通 | 多言語翻訳・自動言語検出 |

#### `--model {tiny,small,medium}`

Whisper のモデルサイズを指定します。デフォルトは `small` です。

```bash
# 小さいモデル（高速）
python main.py --model tiny

# 標準モデル（バランス型）
python main.py --model small

# 大きいモデル（高精度）
python main.py --model medium
```

| 値 | メモリ | 精度 | 速度 |
|---|---|---|---|
| `tiny` | 1GB | 普通 | 最速 |
| `small` | 2GB | 高 | 高速 |
| `medium` | 5GB | 最高 | 普通 |

#### `--asr-device {cpu,cuda}`

Qwen3-ASR の実行デバイスを指定します。デフォルトは `cpu` です。

```bash
# GPU で Qwen3-ASR を実行
python main.py --asr qwen3 --asr-device cuda
```

#### `--chunk FLOAT`

音声チャンク長（秒数）を指定します。デフォルトは `4.0` です。GUI のスライダーでもリアルタイムに変更可能です。

```bash
# チャンクサイズ 2.0s（低遅延）
python main.py --chunk 2.0

# チャンクサイズ 5.0s（高精度）
python main.py --chunk 5.0
```

短いチャンクは低遅延ですが ASR 精度が低下する可能性があります。話者のペースに合わせて調整してください。

### 言語設定

#### `--source-lang LANGUAGE`

翻訳モードのソース言語を指定します。デフォルトは `auto`（自動検出）です。

```bash
python main.py --mode translate --source-lang ja --target-lang en
```

`auto` を指定すると、Whisper または Qwen3-ASR の言語検出機能を使い、ソース言語を自動判定します。Moonshine は自動検出に対応していません。

#### `--target-lang LANGUAGE`

翻訳モードのターゲット言語を指定します。デフォルトは `ja` です。

```bash
python main.py --mode translate --source-lang en --target-lang ja
```

**対応言語：** `auto`, `ja`, `en`, `zh`, `es`, `fr`, `de`, `ko`

#### `--lang LANGUAGE`

チャットモードの言語を指定します。デフォルトは `ja` です。

```bash
python main.py --mode chat --lang ja
```

### デバイス設定

#### `--device "DEVICE_NAME"`

入力デバイスを指定します。デバイス名は `--list-devices` で確認できます。

```bash
# BlackHole（macOS）
python main.py --device "BlackHole 2ch"

# Loopback（Windows）
python main.py --device "Loopback"

# マイク
python main.py --device "MacBook Pro マイク"

# Linux モニターデバイス
python main.py --device "Monitor of Built-in Audio"
```

### 音声処理

#### `--vad`

Silero VAD による発話検出を有効にします。チャットモードで推奨です。

```bash
# VAD を有効化
python main.py --mode chat --vad

# VAD なし（RMS ベース）
python main.py --mode chat
```

効果：
- 発話終了を 0.8s で自動検出
- 従来の RMS 方式より 7倍以上高速
- チャットモードでの応答遅延を最小化

### 音声合成（TTS）エンジン

#### `--voicevox`

VOICEVOX（ずんだもん等）で読み上げます。

```bash
# 翻訳モード
python main.py --mode translate --voicevox

# チャットモード
python main.py --mode chat --vad --voicevox
```

VOICEVOX が起動していない場合は Edge TTS にフォールバックします。

#### `--coeiroink`

CoeiroInk（リリンちゃん）で読み上げます。

```bash
# チャットモード（リリンちゃん）
python main.py --mode chat --vad --coeiroink

# 翻訳モード（リリンちゃんが翻訳結果を読み上げ）
python main.py --mode translate --coeiroink --source-lang ja --target-lang en
```

CoeiroInk が起動していない場合は Edge TTS にフォールバックします。

### 入出力方式

#### `--cli`

CLI（コマンドラインインターフェース）モードで起動します。GUI を使用しません。

```bash
# CLI チャット
python main.py --mode chat --vad --cli

# CLI 翻訳
python main.py --mode translate --cli
```

#### `--file FILE_PATH`

ファイルから音声を読み込みます。

```bash
python main.py --file input.wav
```

### ユーティリティ

#### `--list-devices`

利用可能な入力デバイス一覧を表示します。

```bash
python main.py --list-devices
```

出力例：
```
利用可能な入力デバイス:
  [0] MacBook Pro マイク (ch=1)
  [1] BlackHole 2ch (ch=2) [LOOPBACK]
  [2] AirPods Pro (ch=1)
  [3] 複合デバイス (ch=2)
```

## 使用例

### 翻訳モード

```bash
# GUI（日本語→英語）
python main.py --mode translate --source-lang ja --target-lang en

# リリンちゃんが翻訳結果を読み上げ
python main.py --mode translate --source-lang en --target-lang ja --coeiroink

# Moonshine で低遅延翻訳（英語向け）
python main.py --mode translate --asr moonshine --chunk 2.0 --source-lang en --target-lang ja
```

### チャットモード

```bash
# GUI チャット（Whisper + VAD）
python main.py --mode chat --vad

# ずんだもんとチャット
python main.py --mode chat --vad --voicevox

# リリンちゃんとチャット
python main.py --mode chat --vad --coeiroink

# CLI チャット
python main.py --mode chat --vad --cli

# 高精度チャット（medium モデル）
python main.py --mode chat --vad --model medium

# 軽量環境用チャット（tiny モデル）
python main.py --mode chat --vad --model tiny --asr moonshine --chunk 2.0
```

### デバイス指定

```bash
# 特定のマイクを指定
python main.py --device "USB Microphone"

# 特定のループバックデバイスを指定
python main.py --device "Monitor of Built-in Audio"
```

### 自動言語検出

```bash
# 言語自動検出で翻訳（Whisper）
python main.py --mode translate --source-lang auto --target-lang ja

# Qwen3-ASR + 自動言語検出
python main.py --mode translate --asr qwen3 --source-lang auto --target-lang ja
```

## 環境変数

`.env` ファイルでデフォルト設定を指定できます。

```env
# LLM 設定
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=gemma-2-9b-it
AI_API_KEY=ollama

# CoeiroInk ポート
COEIROINK_HOST=http://localhost:50031

# VOICEVOX ポート
VOICEVOX_HOST=http://localhost:50021
```

詳しくは [Ollama セットアップガイド](../setup/OLLAMA_SETUP.md) をご覧ください。
