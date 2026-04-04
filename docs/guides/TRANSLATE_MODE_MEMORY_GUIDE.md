# 翻訳モード メモリ別ガイド

翻訳モードはLLMが不要なため、メモリ効率が非常に高いです。このガイドでは、メモリ別の最適な構成をご紹介します。

---

## 🎯 翻訳モード vs チャットモードのメモリ比較

### メモリ使用量の違い

| モード | LLM | メモリ使用量 | ASR | TTS |
|---|---|---|---|---|
| **翻訳モード** ❌ LLMなし | 不要 | **3-7GB** ✅ | Whisper | VOICEVOX等 |
| **チャットモード** ✅ LLMあり | 必要 | 8-20GB | Whisper | VOICEVOX等 |

**翻訳モードのメリット：**
- LLMが不要 → メモリ節約
- ASRのみで動作 → シンプル
- Google Translate対応 → 品質安定
- どのメモリ環境でも動作可能

---

## 💾 メモリ別セットアップ

### 📌 4GB メモリ（超軽量）

**仕様：**
```bash
python main.py --mode translate \
  --asr moonshine \
  --chunk 2.0 \
  --source-lang en --target-lang ja
```

**メモリ使用量：** 2-3GB
- Moonshine ASR：1.5GB（軽量）
- Edge TTS：0.5GB（ネット利用）

**特徴：**
- 🟢 低遅延（英語向け）
- 🟢 メモリ最小
- 🟡 日本語認識精度は低め

**推奨用途：**
- 英語 → 日本語翻訳
- YouTube 英語動画
- 低メモリマシン

---

### 💻 8GB メモリ（推奨軽量）

**仕様：**
```bash
python main.py --mode translate \
  --asr whisper --model tiny \
  --source-lang en --target-lang ja \
  --voicevox
```

**メモリ使用量：** 3-4GB
- Whisper tiny ASR：1GB
- VOICEVOX TTS：0.5GB
- その他：1.5GB

**特徴：**
- 🟢 日本語対応
- 🟢 メモリ効率的
- 🟡 精度は tiny モデル相当

**複数ドライブでの同時実行例：**
```bash
# ターミナル 1：翻訳モード
python main.py --mode translate --asr whisper --model tiny

# ターミナル 2：別タスク
# メモリに余裕があれば他の作業も可能
```

**推奨用途：**
- 一般的な翻訳（日本語・英語）
- 複数言語翻訳
- YouTube 動画翻訳

---

### 🖥️ 16GB メモリ（推奨バランス）

**仕様：**
```bash
python main.py --mode translate \
  --asr whisper --model small \
  --source-lang en --target-lang ja \
  --voicevox
```

**メモリ使用量：** 4-5GB
- Whisper small ASR：2GB
- VOICEVOX TTS：0.5GB
- その他：1.5GB

**特徴：**
- 🟢 高精度ASR
- 🟢 複数言語対応
- 🟢 メモリ余裕あり

**複数タスク併用例：**

```bash
# ターミナル 1：翻訳モード（高精度）
python main.py --mode translate --asr whisper --model small

# ターミナル 2：軽量チャット（別Ollama）
# メモリ：4-5GB（翻訳）+ 5GB（LLM 7B）= 9-10GB
ollama pull qwen2.5:7b-instruct
python main.py --mode chat --vad
```

**推奨用途：**
- 高精度翻訳
- 複雑な日本語対応
- YouTube 高品質翻訳
- 翻訳+軽量チャット兼用

---

### 🚀 32GB 以上（高精度構成）

**仕様：**
```bash
python main.py --mode translate \
  --asr whisper --model medium \
  --source-lang en --target-lang ja \
  --coeiroink
```

**メモリ使用量：** 6-7GB
- Whisper medium ASR：5GB
- CoeiroInk TTS：0.5GB
- その他：1GB

**特徴：**
- 🟢 最高精度ASR
- 🟢 複数言語高精度対応
- 🟢 メモリ大幅余裕

**複数タスク高性能併用例：**

```bash
# ターミナル 1：翻訳モード（最高精度）
python main.py --mode translate --asr whisper --model medium --coeiroink

# ターミナル 2：高性能チャット
# メモリ：6-7GB（翻訳）+ 10GB（LLM 14B）= 16-17GB
ollama pull qwen2.5:14b-instruct
python main.py --mode chat --vad
```

**推奨用途：**
- 最高精度翻訳
- 会議・重要な翻訳
- 複雑な専門用語対応
- 翻訳+高性能チャット同時運用

---

## 🎯 ASR モデル選択ガイド

翻訳精度は **ASR モデルサイズ** に直結します。

### 言語別推奨

**日本語：**
| メモリ | ASR | 推奨 | 特徴 |
|---|---|---|---|
| 4GB 以下 | tiny | ⭐ | 最軽量 |
| 8GB | **small** | ⭐ 推奨 | バランス最適 |
| 16GB+ | **medium** | ⭐ 最高精度 | 最高品質 |

**英語：**
| メモリ | ASR | 推奨 | 特徴 |
|---|---|---|---|
| 4GB 以下 | **Moonshine** | ⭐ 推奨 | 高速・軽量 |
| 8GB | **Whisper small** | ⭐ | 高精度 |
| 16GB+ | **Whisper medium** | ⭐ | 最高精度 |

---

## 📊 メモリ別推奨構成表

### クイック選択

| メモリ | ASR | モデルサイズ | TTS | 推奨用途 |
|---|---|---|---|---|
| **4GB** | Moonshine | — | Edge TTS | 英語翻訳・低遅延 |
| **8GB** | Whisper | tiny | VOICEVOX | 一般翻訳・バランス |
| **16GB** | Whisper | small | VOICEVOX | 高精度翻訳・推奨 |
| **32GB+** | Whisper | medium | CoeiroInk | 最高精度翻訳 |

---

## ⚡ 翻訳モード最適化のコツ

### 1. ASR の選択が最重要

```bash
# 日本語高精度（推奨）
python main.py --mode translate --asr whisper --model small

# 英語向け高速（低遅延）
python main.py --mode translate --asr moonshine --chunk 2.0
```

### 2. LLM は不要（チャット兼用時のみ追加）

```bash
# 翻訳のみ → LLM不要
python main.py --mode translate

# 翻訳+チャット兼用 → LLM追加
ollama pull qwen2.5:7b-instruct
# GUI で 2 つのモードを切り替え
```

### 3. TTS エンジンの選択

| TTS | 説明 | メモリ | 推奨環境 |
|---|---|---|---|
| **Edge TTS** | ネット利用 | 0.1GB | 4GB メモリ |
| **VOICEVOX** | ローカル | 0.5GB | 8GB+ |
| **CoeiroInk** | ネット利用 | 0.2GB | 高品質重視 |

### 4. メモリ節約のコツ

```bash
# 最軽量構成
python main.py --mode translate \
  --asr whisper --model tiny \
  # TTS なし（テキストのみ出力）

# または Edge TTS で最軽量
python main.py --mode translate \
  --asr moonshine \
  # Edge TTS が自動選択（ネット必要）
```

---

## 🔄 翻訳+チャット兼用のメモリ計画

### シナリオ別メモリ配分

**16GB メモリの場合：**
```
OS: 2-3GB
翻訳モード (Whisper small): 2GB
チャット用 LLM (Qwen 7B): 5GB
TTS: 0.5GB
バッファ: 2-3GB
────────
合計: 11-12GB ✅ OK（16GB内で動作）
```

**32GB メモリの場合：**
```
OS: 2-3GB
翻訳モード (Whisper medium): 5GB
チャット用 LLM (Qwen 14B): 10GB
TTS: 1GB
バッファ: 3-4GB
────────
合計: 21-23GB ✅ OK（32GB内で動作）
```

---

## 💡 よくある質問

### Q: 翻訳モードでもLLMが必要ですか？

**A:** いいえ。翻訳はGoogle Translateが処理するため、LLMは不要です。

- 翻訳精度 = ASR（音声認識）の精度
- LLM は翻訳に関与していない
- LLM は チャットモードのみで使用

### Q: メモリが限られている場合、どうすればいい？

**A:** 以下の優先順で軽量化してください：

1. **ASR モデルを軽量化**
   ```bash
   python main.py --mode translate --asr whisper --model tiny
   ```

2. **TTS を Edge TTS に変更**
   ```bash
   python main.py --mode translate
   # Edge TTS が自動選択される
   ```

3. **英語翻訳なら Moonshine 使用**
   ```bash
   python main.py --mode translate --asr moonshine
   ```

### Q: 翻訳+チャットを両方やりたい場合は？

**A:** メモリを分割して運用してください：

```bash
# ターミナル 1：翻訳モード（メモリ効率重視）
python main.py --mode translate --asr whisper --model small

# ターミナル 2：チャットモード（LLM追加）
python main.py --mode chat --vad
# Ollama で LLM を選択
```

**メモリ配分例（16GB）：**
- 翻訳モード：4-5GB
- チャットモード LLM（7B）：5GB
- 合計：9-10GB（余裕あり）

### Q: 翻訳精度を上げるには何をすればいい？

**A:** **ASR モデルを大きくする** が最重要です：

```bash
# 推奨：Whisper small（メモリ 8GB+）
python main.py --mode translate --asr whisper --model small

# さらに高精度：Whisper medium（メモリ 16GB+）
python main.py --mode translate --asr whisper --model medium
```

LLM選択は翻訳精度に **影響しません。**

---

## 📚 関連ドキュメント

- [翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md)
- [チャットモード完全ガイド](./CHAT_MODE_GUIDE.md)
- [メモリ別セットアップガイド](../setup/MEMORY_REQUIREMENTS.md)
- [Ollama セットアップガイド](../setup/OLLAMA_SETUP.md)
