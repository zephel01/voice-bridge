# メモリ別セットアップガイド

Voice Bridge のチャットモードで使用する LLM は、ご利用のメモリサイズに合わせて選択する必要があります。

---

## 🎯 クイック選択ガイド

**ご利用のメモリサイズを選択してください：**

- **8GB 以下** → [セットアップ](#-メモリ-8gb-以下)
- **16GB** → [セットアップ](#-メモリ-16gb)
- **32GB 以上** → [セットアップ](#-メモリ-32gb-以上)

---

## 💾 メモリ 8GB 以下

**推奨：最軽量・リーズナブル**

### 推奨モデル

**最もバランスの取れた推奨：**
```bash
ollama pull qwen2.5:7b-instruct
```

**超軽量版（4GB メモリでも可）：**
```bash
ollama pull phi:3              # Microsoft Phi-3 Mini（2.3GB）
ollama pull gemma:2b           # Google Gemma 2B（1.6GB）
```

### パフォーマンス

| モデル | メモリ使用量 | 日本語対応 | 速度 | 推奨環境 |
|---|---|---|---|---|
| `qwen2.5:7b-instruct` ⭐ | 4-5GB | ✅ 高 | 普通 | 8GB メモリ推奨 |
| `phi:3` | 2-3GB | 普通 | 高速 | 最軽量 |
| `gemma:2b` | 1-2GB | 普通 | 最速 | 超軽量 |

### セットアップ手順

```bash
# 1. Ollama をインストール
# https://ollama.com/ からダウンロード

# 2. モデルをダウンロード
ollama pull qwen2.5:7b-instruct

# 3. Ollama サーバーを起動
ollama serve

# 4. 別のターミナルで Voice Bridge を起動
python main.py --mode chat --vad
```

### .env 設定

```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen2.5:7b-instruct
AI_API_KEY=ollama
```

### パフォーマンス最適化

**低遅延化：**
```bash
python main.py --mode chat --vad --asr whisper --model tiny
```

**軽量化：**
```bash
python main.py --mode chat --vad --asr moonshine --chunk 2.0
```

---

## 💻 メモリ 16GB

**推奨：ベストバランス**

### 推奨モデル

**最高推奨（バランス最適）：**
```bash
ollama pull qwen2.5:14b-instruct
```

**高速版（Qwen3 最新）：**
```bash
ollama pull qwen3:8b
```

**新世代（Google 最新）：**
```bash
ollama pull gemma4:9b
```

### パフォーマンス

| モデル | メモリ使用量 | 日本語対応 | 速度 | 推奨用途 |
|---|---|---|---|---|
| `qwen2.5:14b-instruct` ⭐ | 8-10GB | ✅ 最高 | 普通 | **推奨** |
| `qwen3:8b` | 5-7GB | ✅ 高 | 高速 | 高速版 |
| `gemma4:9b` | 6-8GB | ✅ 高 | 高速 | 新世代 |

### セットアップ手順

```bash
# 1. Ollama をインストール
# https://ollama.com/ からダウンロード

# 2. モデルをダウンロード
ollama pull qwen2.5:14b-instruct

# 3. Ollama サーバーを起動
ollama serve

# 4. 別のターミナルで Voice Bridge を起動
python main.py --mode chat --vad
```

### .env 設定

```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen2.5:14b-instruct     # ⭐ 推奨
AI_API_KEY=ollama
```

**代替案：**
```env
# 高速版
AI_MODEL=qwen3:8b

# 新世代
AI_MODEL=gemma4:9b
```

### パフォーマンス最適化

**高速化（複数モデル切り替え）：**
```bash
# 高速版を追加
ollama pull qwen3:8b

# GUI で「LLM」ドロップダウンから選択
python main.py --mode chat --vad
```

**高精度化：**
```bash
python main.py --mode chat --vad --asr whisper --model small
```

---

## 🖥️ メモリ 32GB 以上

**推奨：最高性能**

### 推奨モデル

**最新最高性能（推奨）：**
```bash
ollama pull qwen3:14b
```

**超高精度：**
```bash
ollama pull qwen2.5:32b-instruct
```

**超高性能（最新リリース）：**
```bash
ollama pull qwen3:32b
```

**推論特化：**
```bash
ollama pull deepseek-r1:32b
```

### パフォーマンス

| モデル | メモリ使用量 | 日本語対応 | 速度 | 推奨用途 |
|---|---|---|---|---|
| `qwen3:14b` ⭐ | 10-12GB | ✅ 最高 | 普通 | **総合推奨** |
| `qwen2.5:32b-instruct` | 18-22GB | ✅ 最高 | 普通 | 超高精度 |
| `qwen3:32b` | 18-22GB | ✅ 最高 | 普通 | 超高性能 |
| `deepseek-r1:32b` | 18-22GB | ✅ 高 | 普通 | 推論特化 |

### セットアップ手順

```bash
# 1. Ollama をインストール
# https://ollama.com/ からダウンロード

# 2. モデルをダウンロード
ollama pull qwen3:14b

# 3. Ollama サーバーを起動
ollama serve

# 4. 別のターミナルで Voice Bridge を起動
python main.py --mode chat --vad
```

### .env 設定

```env
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:14b              # ⭐ 推奨
AI_API_KEY=ollama
```

**代替案（複数モデル構成）：**
```env
# 標準
AI_MODEL=qwen3:14b

# 高精度版に切り替える場合は下記を有効化
# AI_MODEL=qwen2.5:32b-instruct

# 超高性能版
# AI_MODEL=qwen3:32b
```

### パフォーマンス最適化

**複数モデルで使い分け：**
```bash
# 複数モデルをダウンロード
ollama pull qwen3:14b
ollama pull qwen2.5:32b-instruct
ollama pull qwen3:32b

# Voice Bridge 起動
python main.py --mode chat --vad

# GUI の「LLM」ドロップダウンで切り替え可能
```

**超高精度化：**
```bash
python main.py --mode chat --vad --asr whisper --model medium
```

---

## 📊 メモリ別選択表

| メモリ | 推奨モデル | メモリ使用量 | 日本語対応 | 理由 |
|---|---|---|---|---|
| **8GB 以下** | `qwen2.5:7b-instruct` | 4-5GB | ✅ 高 | バランス最適 |
| **16GB** | `qwen2.5:14b-instruct` ⭐ | 8-10GB | ✅ 最高 | ベストバランス |
| **32GB+** | `qwen3:14b` ⭐ | 10-12GB | ✅ 最高 | 最新・最高性能 |

---

## 🔄 モデル比較

### 日本語性能
1. **`qwen3:14b`** — 最新リリース・最高性能
2. **`qwen2.5:32b-instruct`** — 超高精度
3. **`qwen2.5:14b-instruct`** — 信頼性高い・安定

### 処理速度
1. **`phi:3`** — 最速（軽量モデル）
2. **`qwen3:8b`** — 高速
3. **`qwen2.5:7b-instruct`** — 標準速

### メモリ効率
1. **`gemma:2b`** — 最軽量（1-2GB）
2. **`phi:3`** — 軽量（2-3GB）
3. **`qwen2.5:7b-instruct`** — バランス（4-5GB）

---

## 💡 よくある質問

### Q: 自分のメモリがいくつあるか確認するには？

**Windows:**
```bash
# PowerShell で実行
Get-ComputerInfo | Select-Object CsPhyicallyInstalledMemory
# または
wmic OS get TotalVisibleMemorySize
```

**macOS/Linux:**
```bash
# ターミナルで実行
free -h          # Linux
sysctl hw.memsize  # macOS
```

### Q: モデルをダウンロード後、メモリ使用量を確認するには？

```bash
# Ollama の設定を確認
ollama show qwen2.5:14b-instruct

# または実行中にモニタリング
# タスクマネージャー（Windows）
# アクティビティモニタ（macOS）
# htop（Linux）
```

### Q: メモリが足りない場合は？

**対処方法（優先順）：**

1. **より軽量なモデルに変更**
   - `qwen2.5:7b-instruct` → `phi:3`
   - `qwen2.5:14b-instruct` → `qwen2.5:7b-instruct`

2. **バックグラウンドアプリを終了**
   - Chrome、IDE、その他メモリ消費アプリ

3. **ASR モデルを軽量化**
   ```bash
   python main.py --mode chat --model tiny --vad
   ```

4. **Moonshine + チャンク調整**
   ```bash
   python main.py --mode chat --asr moonshine --chunk 2.0
   ```

### Q: GPU がある場合のメモリ要件は？

GPU メモリと CPU メモリは別です。GPU がある場合は CUDA でも実行可能です。

詳しくは [Ollama セットアップガイド](./OLLAMA_SETUP.md) の「パフォーマンスチューニング」セクションを参照してください。

---

## 📖 関連ドキュメント

- [Ollama セットアップガイド](./OLLAMA_SETUP.md) — 詳細セットアップ
- [チャットモード完全ガイド](../guides/CHAT_MODE_GUIDE.md) — チャットモード解説
- [システムアーキテクチャ](../reference/ARCHITECTURE.md) — 技術詳細
