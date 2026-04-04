# チャットモード完全ガイド

AI ロボット（ずんだもん・リリンちゃん等）と音声で会話するチャットモードの完全ガイドです。

---

## 概要

チャットモードはローカル LLM を使用して、AI と自然な音声対話ができるモードです。

| 項目 | 説明 |
|---|---|
| **目的** | AI ロボットと音声で会話 |
| **入力** | マイク音声 |
| **出力** | AI の音声応答 |
| **必須環境** | Ollama（ローカル LLM サーバー） |
| **インターネット** | 不要（完全ローカル動作） |

### 利用シーン

```
あなた: 「おはよう」
  AI: 「おはよう！今日も頑張ろう！」（ずんだもんの声で返答）

あなた: 「今週の天気教えて」
  AI: 「月曜日は晴れ、火曜日は...」（リリンちゃんの声で返答）

あなた: 「プログラミングについて質問がある」
  AI: 「何について知りたいですか？」
```

---

## 必須準備

チャットモードを使うには、以下が必要です：

### 1. ローカル LLM サーバー（Ollama） — **必須**

Voice Bridge がローカル LLM サーバーと通信して、AI 応答を生成します。

**セットアップ手順：**

[Ollama セットアップガイド](../setup/OLLAMA_SETUP.md) の以下セクションを参照：
1. Ollama をインストール
2. LLM モデルをダウンロード
3. Ollama サーバーを起動

**推奨モデル（メモリ別・2026年4月版）：**

**8GB メモリ以下：**
```bash
ollama pull qwen2.5:7b-instruct   # 推奨
ollama pull phi:3                 # 超軽量版
```

**16GB メモリ：**
```bash
ollama pull qwen2.5:14b-instruct  # ⭐ 推奨：バランス最適
ollama pull qwen3:8b              # 高速版
ollama pull gemma4:9b             # 新世代
```

**32GB 以上：**
```bash
ollama pull qwen3:14b             # ⭐ 推奨：最新・最高性能
ollama pull qwen2.5:32b-instruct  # 超高精度
ollama pull qwen3:32b             # 超高性能
```

> **重要：** Voice Bridge を使う際は、常に Ollama サーバーが起動している状態にしてください。

### 2. オプション：キャラクターボイス

AI の声をキャラクターボイスに変更できます：

| TTS エンジン | キャラクター例 | 説明 |
|---|---|---|
| **VOICEVOX** | ずんだもん、四国めたぼ 等 | ローカル実行・複数キャラ |
| **CoeiroInk** | リリンちゃん 等 | ネット接続・キャラ豊富 |
| **Edge TTS** | 多言語ナレーター | ネット接続・多言語対応 |

指定なしの場合は Edge TTS でフォールバックします。

---

## クイックスタート（3ステップ）

### ステップ 1: Ollama を起動

ターミナルで：
```bash
ollama serve
```

このウィンドウは開いたままにしておいてください。

### ステップ 2: Voice Bridge を起動

別のターミナルで：
```bash
python main.py --mode chat --vad
```

### ステップ 3: マイクで話しかける

GUI が起動したら、マイクに向かって話しかけてください。AI が音声で返答します。

---

## 起動方法

### GUI で起動（推奨）

```bash
# 基本形
python main.py --mode chat --vad

# ずんだもんの声で起動
python main.py --mode chat --vad --voicevox

# リリンちゃんの声で起動
python main.py --mode chat --vad --coeiroink
```

### CLI で起動（GUI なし）

```bash
python main.py --mode chat --vad --cli
```

### 詳細なオプション指定

```bash
# 高精度・日本語最適化
python main.py --mode chat --vad --asr whisper --model medium --voicevox

# 低遅延・高速化
python main.py --mode chat --vad --asr moonshine --chunk 2.0 --model tiny

# カスタム言語・マイク
python main.py --mode chat --lang ja --device "USB Microphone" --voicevox
```

詳しくは [CLI リファレンス](../reference/CLI_REFERENCE.md) をご覧ください。

---

## GUI 設定（詳細）

### モード
- **選択値：** `chat`

### 入力デバイス
マイクデバイスを選択します。

**デバイス一覧を確認：**
```bash
python main.py --list-devices
```

**例：**
- MacBook Pro マイク
- USB マイク
- AirPods Pro
- Bluetooth ヘッドセット

### 会話言語
チャットの言語を選択します。

**対応言語：** 日本語 / 英語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

> **Moonshine エンジン時：** en / ja / zh / es / ko のみ対応

### ASR（音声認識エンジン）

| エンジン | 日本語精度 | 英語精度 | 速度 | 推奨 |
|---|---|---|---|---|
| **Whisper** | 高 | 高 | 普通 | ✅ 日本語チャット |
| **Moonshine** | 低 | 高 | 最速 | 英語・低遅延 |

日本語チャットは **Whisper** 推奨。

### Whisper モデルサイズ

Whisper 選択時に表示：

| サイズ | メモリ | 精度 | 速度 | 推奨環境 |
|---|---|---|---|---|
| `tiny` | 1GB | 普通 | 最速 | メモリ 4GB |
| `small` | 2GB | 高 | 高速 | **推奨** |
| `medium` | 5GB | 最高 | 普通 | メモリ 8GB+ |

### VAD（音声アクティビティ検出）

**チェック推奨** ✅

Silero VAD により発話終了を 0.8s で自動検出します。

| 設定 | 説明 |
|---|---|
| ✅ チェック | 自然な会話体験（推奨） |
| ☐ チェック未 | RMS ベース（遅い） |

### LLM（ローカル LLM モデル）

ダウンロード済みモデルの一覧から選択します。

**モデル選択の目安（メモリ別・2026年4月版）：**

**8GB メモリ以下：**
| モデル | 日本語精度 | 速度 | メモリ |
|---|---|---|---|
| `qwen2.5:7b-instruct` | 普通 | 最速 | ~5GB |
| `phi:3` | 普通 | 高速 | 2.3GB |

**16GB メモリ：**
| モデル | 日本語精度 | 速度 | メモリ | 推奨 |
|---|---|---|---|---|
| `qwen2.5:14b-instruct` ⭐ | 最高 | 普通 | ~10GB | **推奨** |
| `qwen3:8b` | 高 | 高速 | ~6GB | 高速版 |
| `gemma4:9b` | 高 | 高速 | ~7GB | 新世代 |

**32GB 以上：**
| モデル | 日本語精度 | 速度 | メモリ | 推奨 |
|---|---|---|---|---|
| `qwen3:14b` ⭐ | 最高 | 普通 | ~10GB | **総合推奨** |
| `qwen2.5:32b-instruct` | 最高 | 普通 | ~20GB | 超高精度 |
| `qwen3:32b` | 最高 | 普通 | ~20GB | 超高性能 |

> **モデル一覧が空の場合：**
> Ollama が起動していないか、モデルがダウンロードされていません。
> [Ollama セットアップガイド](../setup/OLLAMA_SETUP.md) を参照。

### 声（TTS エンジン）

AI の読み上げ音声を選択します。

| エンジン | 説明 | 起動要否 |
|---|---|---|
| **VOICEVOX** | ずんだもん等のキャラ | VOICEVOX アプリ起動必須 |
| **CoeiroInk** | リリンちゃん等のキャラ | CoeiroInk アプリ起動必須 |
| **Edge TTS** | 汎用ナレーター | ネット接続のみで動作 |

---

## パフォーマンス最適化

### 目的別の推奨設定

#### 低遅延（応答速度重視）

```bash
python main.py --mode chat \
  --vad \
  --asr moonshine \
  --chunk 2.0 \
  --model tiny
```

**期待値：** 初回 0.3-0.5s で最初の音声が出る

#### 高精度（精度重視）

```bash
python main.py --mode chat \
  --vad \
  --asr whisper \
  --model medium
```

**.env で高精度 LLM を指定：**
```env
AI_MODEL=qwen2.5-14b-instruct
```

**期待値：** より正確な日本語応答

#### バランス型（推奨）

```bash
python main.py --mode chat \
  --vad \
  --asr whisper \
  --model small \
  --voicevox
```

**.env：**
```env
AI_MODEL=gemma-2-9b-it
```

**期待値：** 精度と速度のバランス

### GPU 活用

NVIDIA GPU を搭載している場合、自動的に CUDA で高速化されます。

---

## 実際の会話例

### 例 1：雑談

```
あなた: 「ずんだもん、今日の天気は？」
  AI: 「今日は晴れのようですね。気持ちいい日になりそう！」
```

### 例 2：質問・学習

```
あなた: 「Python でループを作るには？」
  AI: 「Python では for ループと while ループがあります。
        例えば、for i in range(10): でループできます。」
```

### 例 3：指示・タスク

```
あなた: 「今日の TODO リストを作ってよ」
  AI: 「了解しました。今日のやることは...」
```

---

## トラブルシューティング

### AI が応答しない

**確認事項：**

1. **Ollama サーバーが起動しているか**
   ```bash
   ollama serve
   ```

2. **LLM モデルがダウンロードされているか**
   ```bash
   ollama list
   ```

3. **ローカルホスト接続を確認**
   ```bash
   curl http://localhost:11434/api/version
   ```

詳しくは [FAQ — AI が応答しない](../troubleshooting/FAQ.md#q-ai-が応答しない)

### 日本語応答の精度が低い

**対処：**

1. **LLM モデルを変更**
   ```bash
   ollama pull gemma-2-9b-it
   ```

2. **GUI で `LLM` に `gemma-2-9b-it` を選択**

詳しくは [FAQ — 日本語精度が低い](../troubleshooting/FAQ.md#q-日本語の応答精度が低い)

### 応答が遅い

**対処（優先順）：**

1. VAD を有効化（既にしていたら次へ）
2. ASR モデルを `tiny` に変更
3. LLM モデルを `qwen2.5-7b-instruct` に変更
4. Moonshine + 低レイテンシ設定に変更

詳しくは [FAQ — 応答が遅い](../troubleshooting/FAQ.md#q-応答が遅い)

### マイクが入力を拾わない

**対処：**
```bash
python main.py --list-devices
```

で入力デバイスを確認し、正しいマイクを選択してください。

詳しくは [FAQ — マイクが入力レベルを拾わない](../troubleshooting/FAQ.md#q-マイクが入力レベルを拾わない)

### CoeiroInk / VOICEVOX が検出されない

**対処：**

1. アプリが起動しているか確認
2. ポート番号が正しいか確認
3. `.env` でポート番号を指定

詳しくは [FAQ — CoeiroInk/VOICEVOX](../troubleshooting/FAQ.md#q-coeiroink-が検出されない)

---

## よくある質問

### Q: インターネット接続が必要ですか？

**A:** いいえ。チャットモードはすべてローカルで動作します。
- Ollama：ローカル LLM サーバー
- VOICEVOX：ローカル音声合成
- CoeiroInk：ネット接続が必要

Edge TTS 使用時のみインターネット接続が必要です。

### Q: 複数モデルを切り替えられますか？

**A:** はい。複数モデルをダウンロードしておくと、GUI で実行時に切り替え可能です。

```bash
ollama pull gemma-2-9b-it
ollama pull qwen2.5-7b-instruct
ollama pull qwen2.5-14b-instruct
```

### Q: 何が AI の学習に使われますか？

**A:** Ollama と VOICEVOX を使用している場合、すべてローカルで処理されます。データが外部に送信されることはありません。

Edge TTS 使用時のみ、Microsoft に音声合成リクエストが送信されます。

### Q: 複数言語で会話できますか？

**A:** はい。GUI の「会話言語」で変更できます。

**対応言語：** 日本語 / 英語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

### Q: キャラクターボイスを変更できますか？

**A:** はい。VOICEVOX または CoeiroInk を起動して、GUI で選択してください。

---

## 関連ドキュメント

- [モード別ガイド](./MODES_OVERVIEW.md) — チャット vs 翻訳
- [翻訳モードガイド](./TRANSLATE_MODE_GUIDE.md) — 翻訳モード
- [GUI ガイド](./GUI_GUIDE.md) — GUI 詳細設定
- [CLI リファレンス](../reference/CLI_REFERENCE.md) — コマンドライン完全リファレンス
- [Ollama セットアップ](../setup/OLLAMA_SETUP.md) — LLM サーバーセットアップ
- [FAQ](../troubleshooting/FAQ.md) — トラブルシューティング
- [システムアーキテクチャ](../reference/ARCHITECTURE.md) — 技術詳細
