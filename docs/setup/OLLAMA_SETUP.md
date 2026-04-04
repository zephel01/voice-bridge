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

### 2. LLM モデルをダウンロード

Ollama をインストール後、ターミナルでモデルをダウンロードします：

```bash
# 推奨：日本語対応、バランスの取れた 9B モデル
ollama pull gemma-2-9b-it

# または軽量な 7B モデル（低スペック環境向け）
ollama pull qwen2.5-7b-instruct

# または高精度な 14B モデル（メモリ8GB+推奨）
ollama pull qwen2.5-14b-instruct
```

**モデル選択の目安：**

| モデル | 日本語精度 | 処理速度 | メモリ | 推奨環境 |
|---|---|---|---|---|
| `gemma-2-9b-it` | 高 | 普通 | ~7GB | メモリ 8GB 推奨 |
| `qwen2.5-7b-instruct` | 普通 | 最速 | ~5GB | メモリ 4GB でもOK |
| `qwen2.5-14b-instruct` | 最高 | 遅い | ~10GB | メモリ 16GB 推奨 |

**日本語チャットでの推奨：** `gemma-2-9b-it`

### 3. Ollama サーバーを起動

```bash
ollama serve
```

このコマンドで Ollama サーバーがバックグラウンドで起動し、`localhost:11434` でリッスンを開始します。

> **重要：** Voice Bridge を実行する際は、**常に Ollama サーバーが起動している状態**にしておいてください。起動していないと、チャットモードで「LLM モデル一覧が空」になったり、応答が返ってきません。

### 4. Voice Bridge で使用するモデルを設定

`.env` ファイルで、使用するモデルと接続先を指定します：

```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=gemma-2-9b-it
AI_API_KEY=ollama
```

または、GUI のドロップダウンで実行時に選択：

```bash
python main.py --mode chat --vad
# GUI 起動後、「LLM」ドロップダウンから使用するモデルを選択
```

## 複数モデルの管理

複数のモデルをダウンロードしておくと、GUI で実行時に切り替え可能です：

```bash
ollama pull gemma-2-9b-it
ollama pull qwen2.5-7b-instruct
ollama pull qwen2.5-14b-instruct
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
