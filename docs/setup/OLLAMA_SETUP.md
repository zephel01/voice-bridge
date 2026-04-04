# Ollama セットアップガイド

Voice Bridge のチャットモードで使用するローカル LLM サーバー「Ollama」のセットアップ方法を説明します。

## Ollama とは

**Ollama** はローカルコンピュータ上で大規模言語モデル（LLM）を実行するためのツールです。インターネット接続やクラウドサービスに依存せず、完全にプライベートな環境で AI チャットが実現できます。

## Voice Bridge での役割

Voice Bridge のチャットモードでは、Ollama がバックグラウンドで実行する LLM サーバーに HTTP リクエストを送信して、AI の応答を取得しています：

1. **マイク入力** → Whisper で音声認識 → テキスト化
2. **テキスト送信** → **Ollama サーバー（localhost:11434）** に OpenAI 互換 API でリクエスト
3. **LLM 応答** → Streaming で逐次受信 → 文単位で TTS エンジンに送信
4. **音声出力** → CoeiroInk / VOICEVOX / Edge TTS で読み上げ

つまり、Ollama は Voice Bridge の「裏で動く AI エンジン」として機能しており、ユーザーがマイクで話しかけると、自動的に Ollama と通信して応答を生成しています。

## インストール手順

### 1. Ollama をインストール

[Ollama 公式サイト](https://ollama.com/) から、ご使用のOS（macOS / Windows / Linux）に対応したインストーラをダウンロードしてください。

### 2. LLM モデルをダウンロード（メモリ別推奨）

ご利用のメモリサイズに合わせてモデルを選択してください。

#### 📌 メモリ 8GB 以下

限られたメモリでも会話可能です。以下から選択：

```bash
# 推奨：日本語対応・軽量（4GB メモリ推奨）
ollama pull qwen2.5:7b-instruct

# または超軽量（3GB メモリでも可）
ollama pull phi:3              # Phi-3 Mini（2.3GB）
ollama pull gemma:2b           # Gemma 2B（1.6GB）
ollama pull neural-chat:7b     # Neural Chat（軽量）
```

| モデル | メモリ | 日本語対応 | 推奨用途 |
|---|---|---|---|
| `qwen2.5:7b-instruct` | ~5GB | ✅ 高 | **推奨** |
| `phi:3` | 2.3GB | 普通 | 超軽量 |
| `gemma:2b` | 1.6GB | 普通 | 最軽量 |

#### 💻 メモリ 16GB

**最もバランスの取れた推奨構成**

```bash
# 🎯 推奨：最新・高性能・日本語最適（7-9GB メモリ推奨）
ollama pull qwen2.5:14b-instruct

# または高速版（7GB メモリ）
ollama pull qwen3:8b           # Qwen3 8B（最新・高速）

# または新世代（7GB メモリ）
ollama pull gemma4:9b          # Gemma4 9B（最新世代）
ollama pull gemma3:9b          # Gemma3 9B（安定性高い）
```

| モデル | メモリ | 日本語対応 | 推奨用途 |
|---|---|---|---|
| `qwen2.5:14b-instruct` ⭐ | ~10GB | ✅ 最高 | **総合推奨** |
| `qwen3:8b` | ~6GB | ✅ 高 | 高速・軽量 |
| `gemma4:9b` | ~7GB | ✅ 高 | 新世代・高性能 |

#### 🖥️ メモリ 32GB 以上

最高性能・最新モデルを利用可能：

```bash
# 🎯 推奨：最新最高性能（12-15GB メモリ推奨）
ollama pull qwen3:14b          # Qwen3 14B（最新リリース）

# または超高精度（13-15GB メモリ推奨）
ollama pull qwen2.5:32b-instruct

# または超高性能・マルチモーダル（20-25GB メモリ推奨）
ollama pull qwen3:32b          # Qwen3 32B
ollama pull deepseek-r1:32b    # DeepSeek R1 32B
```

| モデル | メモリ | 日本語対応 | 推奨用途 |
|---|---|---|---|
| `qwen3:14b` ⭐ | ~10GB | ✅ 最高 | **総合推奨** |
| `qwen2.5:32b-instruct` | ~20GB | ✅ 最高 | 超高精度 |
| `qwen3:32b` | ~20GB | ✅ 最高 | 最高性能 |

### 3. Ollama サーバーを起動

```bash
ollama serve
```

このコマンドで Ollama サーバーがバックグラウンドで起動し、`localhost:11434` でリッスンを開始します。

> **重要：** Voice Bridge を実行する際は、**常に Ollama サーバーが起動している状態**にしておいてください。起動していないと、チャットモードで「LLM モデル一覧が空」になったり、応答が返ってきません。

### 4. Voice Bridge で使用するモデルを設定（メモリ別）

`.env` ファイルで、ご利用のメモリに合わせてモデルを指定します：

**8GB メモリの場合：**
```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen2.5:7b-instruct     # 推奨
AI_API_KEY=ollama
```

**16GB メモリの場合：**
```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen2.5:14b-instruct    # ⭐ 推奨（バランス型）
AI_API_KEY=ollama
```

**32GB 以上の場合：**
```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:14b               # ⭐ 推奨（最新・最高性能）
AI_API_KEY=ollama
```

**代替案：**
```env
# 高速重視
AI_MODEL=qwen3:8b

# 新世代試験
AI_MODEL=gemma4:9b

# 超高精度（32GB 以上推奨）
AI_MODEL=qwen2.5:32b-instruct
```

または、GUI のドロップダウンで実行時に選択：

```bash
python main.py --mode chat --vad
# GUI 起動後、「LLM」ドロップダウンから使用するモデルを選択
```

## 複数モデルの管理（メモリ別推奨）

複数のモデルをダウンロードしておくと、GUI で実行時に切り替え可能です。

### 8GB メモリ環境での複数モデル

```bash
# メイン（推奨）
ollama pull qwen2.5:7b-instruct

# 軽量バックアップ
ollama pull phi:3
```

### 16GB メモリ環境での複数モデル

```bash
# メイン（推奨）
ollama pull qwen2.5:14b-instruct

# 高速版
ollama pull qwen3:8b

# 新世代試験
ollama pull gemma4:9b
```

### 32GB 以上メモリ環境での複数モデル

```bash
# メイン（推奨）
ollama pull qwen3:14b

# 高精度バージョン
ollama pull qwen2.5:32b-instruct

# 超高性能
ollama pull qwen3:32b

# 推論特化
ollama pull deepseek-r1:32b
```

その後、GUI の「LLM」ドロップダウンで任意のモデルを選択できます。

## バックグラウンド実行（推奨）

Ollama を起動したまま Voice Bridge を複数回使用する場合、バックグラウンドで Ollama を実行しておくと便利です：

### macOS / Linux

ターミナル 1 で Ollama サーバーを起動：
```bash
ollama serve
```

ターミナル 2 で Voice Bridge を起動：
```bash
python main.py --mode chat --vad
```

### Windows

PowerShell でバックグラウンド実行：
```powershell
Start-Process -NoNewWindow ollama serve
python main.py --mode chat --vad
```

## 別の LLM サーバーを使用する場合

Ollama の代わりに以下のツールも使用可能です（OpenAI 互換 API が必要）：

### LM Studio（GUI ベース）

LM Studio はデスクトップ GUI でモデルを管理できます。

```env
AI_BASE_URL=http://localhost:1234/v1
AI_MODEL=モデル名
AI_API_KEY=lm-studio
```

### OpenAI API（クラウド）

OpenAI API を使用する場合：

```env
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
AI_API_KEY=sk-...（OpenAI APIキー）
```

> **注意：** OpenAI API を使用する場合、インターネット接続が必須で、API 利用料金が発生します。

## トラブルシューティング

### LLM モデル一覧が空

**原因：** Ollama サーバーが起動していない

**対処：**
```bash
ollama serve
```

でサーバーを起動してください。

### 接続タイムアウト

**原因：** Ollama が起動していない、またはポートが異なる

**対処：** `AI_BASE_URL` を確認してください。デフォルトは `http://localhost:11434/v1` です。

### メモリ不足エラー

**原因：** LLM モデルが大きすぎる

**対処：** より小さいモデルに変更してください。

```bash
ollama pull qwen2.5-7b-instruct  # より軽量
```

### 日本語応答の精度が低い

**原因：** モデルが英語特化

**対処：** 以下のモデルに変更してください。

```bash
ollama pull gemma-2-9b-it        # 推奨：日本語対応
ollama pull qwen2.5-7b-instruct  # 軽量な日本語対応
```

## パフォーマンスチューニング

### GPU の活用

NVIDIA GPU を搭載している場合、CUDA で高速化できます。

Ollama は NVIDIA GPU を自動検出し、利用可能な場合は自動的に使用します。CUDA のインストール手順については、[Ollama 公式ドキュメント](https://ollama.com/) をご参照ください。

### CPU での最適化

CPU のみで実行する場合：

```bash
# スレッド数を調整
export ORT_NUM_THREADS=4
ollama serve
```

### メモリ最適化

メモリが限られている場合：

1. より小さいモデルを使用
   ```bash
   ollama pull qwen2.5-7b-instruct
   ```

2. コンテキストサイズを削減
   ```bash
   # .env で指定（オプション）
   AI_CONTEXT_SIZE=2048
   ```

## よくある質問

**Q: Ollama と OpenAI API の違いは？**

A: Ollama はローカルで実行するため、インターネット接続が不要で、プライバシーが保証されます。一方、OpenAI API はクラウドベースで精度が高いですが、インターネット接続と利用料金が必要です。

**Q: 複数のモデルを同時に実行できますか？**

A: Ollama では一度に1つのモデルのみ実行できます。別のモデルに切り替える場合は、前のモデルを終了する必要があります。

**Q: モデルはどこに保存されますか？**

A: デフォルトでは以下の位置に保存されます：
- macOS: `~/.ollama/models`
- Windows: `%USERPROFILE%\.ollama\models`
- Linux: `~/.ollama/models`

**Q: 日本語モデルのおすすめは？**

A: 総合的には `gemma-2-9b-it` が最もバランスが良いです。速度を優先する場合は `qwen2.5-7b-instruct`、精度を優先する場合は `qwen2.5-14b-instruct` をおすすめします。

## 参考リンク

- [Ollama 公式サイト](https://ollama.com/)
- [提供モデル一覧](https://ollama.com/library)
- [GUI ガイド](../guides/GUI_GUIDE.md)
- [CLI リファレンス](../reference/CLI_REFERENCE.md)
