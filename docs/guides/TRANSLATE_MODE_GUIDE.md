# 翻訳モード完全ガイド

リアルタイム音声翻訳モードの完全ガイドです。YouTube 動画、会議、対話をリアルタイムで別言語に翻訳できます。

---

## 概要

翻訳モードはシステム音声またはマイク入力をリアルタイムで翻訳し、音声で出力します。

| 項目 | 説明 |
|---|---|
| **目的** | リアルタイム音声翻訳 |
| **入力** | マイク or システム音声（OS ごと） |
| **出力** | 翻訳結果の音声 |
| **必須環境** | Windows / macOS（BlackHole）/ Linux（PulseAudio/PipeWire） |
| **インターネット** | 翻訳に必要（Google Translate） |

### 利用シーン

```
📺 YouTube の英語動画を日本語で聞く
   入力：英語の音声
   出力：日本語の音声

🎤 国際会議の同時翻訳
   入力：スペイン語スピーチ
   出力：日本語音声

🎬 映画・ドラマの音声翻訳
   入力：フランス語の台詞
   出力：日本語音声

📞 国際電話の翻訳
   入力：中国語
   出力：日本語（リアルタイム）
```

---

## 対応言語

**7言語対応：**

英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

> **Moonshine エンジン使用時：** en / ja / zh / es / ko のみ対応（fr, de は未対応）

---

## 必須準備

翻訳モードに必須の準備は OS ごとに異なります。

### Windows

✅ **設定不要** — WASAPI ループバックで自動対応

システム音声を自動的にキャプチャできます。

### macOS

📋 **BlackHole（仮想オーディオデバイス）が必要**

[BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md) で以下を実施：
1. BlackHole をインストール
2. Audio MIDI 設定で複合デバイスを作成
3. Voice Bridge で複合デバイスを入力に設定

### Linux

⚙️ **PulseAudio / PipeWire のモニターデバイス設定**

[Linux トラブルシューティング](../troubleshooting/LINUX_TROUBLESHOOTING.md) で詳細を確認。

**簡易確認：**
```bash
python main.py --list-devices
# 「Monitor of ...」があればシステム音声キャプチャ可能
```

---

## クイックスタート（3ステップ）

### ステップ 1: 音声キャプチャの確認

**Windows：** 不要（自動対応）

**macOS：** [BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md) を実施

**Linux：** デバイス一覧を確認
```bash
python main.py --list-devices
```

### ステップ 2: Voice Bridge を起動

```bash
# 基本形（英語 → 日本語）
python main.py --mode translate --source-lang en --target-lang ja

# リリンちゃんの声で翻訳結果を読み上げ
python main.py --mode translate --source-lang en --target-lang ja --coeiroink
```

### ステップ 3：YouTube などで翻訳開始

1. ブラウザで YouTube 動画を再生
2. Voice Bridge の GUI で「開始」をクリック
3. 英語音声がリアルタイムで日本語に翻訳される

---

## 起動方法

### GUI で起動（推奨）

```bash
# 基本形
python main.py --mode translate

# 言語指定：英語 → 日本語
python main.py --mode translate --source-lang en --target-lang ja

# 言語指定：日本語 → 英語
python main.py --mode translate --source-lang ja --target-lang en

# リリンちゃんの声で翻訳
python main.py --mode translate --source-lang en --target-lang ja --coeiroink

# ずんだもんの声で翻訳
python main.py --mode translate --source-lang en --target-lang ja --voicevox
```

### CLI で起動（GUI なし）

```bash
python main.py --mode translate --cli --source-lang en --target-lang ja
```

### 詳細なオプション指定

```bash
# 高精度翻訳（日本語推奨）
python main.py --mode translate --source-lang en --target-lang ja \
  --asr whisper --model medium --coeiroink

# 低遅延翻訳（英語向け）
python main.py --mode translate --source-lang en --target-lang ja \
  --asr moonshine --chunk 2.0 --voicevox

# 特定デバイスから入力
python main.py --mode translate --source-lang en --target-lang ja \
  --device "Monitor of Built-in Audio"
```

詳しくは [CLI リファレンス](../reference/CLI_REFERENCE.md) をご覧ください。

---

## GUI 設定（詳細）

### モード
- **選択値：** `translate`

### 入力デバイス

シスム音声またはマイクを選択します。

**デバイス一覧を確認：**
```bash
python main.py --list-devices
```

**選択例：**

**Windows：**
- WASAPI ループバックデバイス（「Stereo Mix」など）
- マイク（声を翻訳する場合）

**macOS：**
- BlackHole（またはそれを含む複合デバイス）
- マイク（声を翻訳する場合）

**Linux：**
- `Monitor of ...` （システム音声キャプチャ）
- マイク

> 翻訳モードではループバックデバイスまたはマイクを選択してください。

### ソース言語（翻訳元）

翻訳前の言語を選択します。

**対応言語：** 英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

**例：**
- YouTube が英語 → `en` を選択
- ニュース動画が日本語 → `ja` を選択
- TED が日本語 → `ja` を選択

### ターゲット言語（翻訳先）

翻訳後の言語を選択します。

**例：**
- 日本語に翻訳したい → `ja` を選択
- 英語に翻訳したい → `en` を選択

### ASR（音声認識エンジン）

| エンジン | 精度 | 速度 | 推奨 |
|---|---|---|---|
| **Whisper** | 高 | 普通 | ✅ 標準 |
| **Moonshine** | 普通 | 最速 | 英語・低遅延 |

**推奨：** Whisper（日本語も含む多言語対応）

### Whisper モデルサイズ

Whisper 選択時に表示：

| サイズ | メモリ | 精度 | 速度 |
|---|---|---|---|
| `tiny` | 1GB | 普通 | 最速 |
| `small` | 2GB | 高 | 高速 |
| `medium` | 5GB | 最高 | 普通 |

**推奨：** `small`（バランス型）

### 声（TTS エンジン）

翻訳結果を読み上げるエンジン：

| エンジン | 説明 | 特徴 |
|---|---|---|
| **VOICEVOX** | ずんだもん等 | ローカル実行・複数キャラ |
| **CoeiroInk** | リリンちゃん等 | ネット接続・キャラ豊富 |
| **Edge TTS** | 汎用ナレーター | ネット接続・多言語対応 |

**推奨：** VOICEVOX または CoeiroInk（ローカル実行で低遅延）

---

## パフォーマンス最適化

### 目的別の推奨設定

#### 低遅延（YouTube など）

```bash
python main.py --mode translate \
  --source-lang en --target-lang ja \
  --asr moonshine --chunk 2.0 \
  --voicevox
```

**期待値：** 音声遅延 1-2s

#### 高精度（重要な会議など）

```bash
python main.py --mode translate \
  --source-lang en --target-lang ja \
  --asr whisper --model medium \
  --coeiroink
```

**期待値：** 精度重視（少し遅延増加）

#### バランス型（推奨）

```bash
python main.py --mode translate \
  --source-lang en --target-lang ja \
  --asr whisper --model small \
  --voicevox
```

**期待値：** 精度と速度のバランス

---

## 実際の使用例

### 例 1：YouTube 動画の翻訳

**目標：** 英語の TED トークを日本語で聞く

1. YouTube で TED トークを再生
2. 起動コマンド：
   ```bash
   python main.py --mode translate --source-lang en --target-lang ja --voicevox
   ```
3. GUI で入力デバイスをループバックに設定
4. 「開始」をクリック
5. 英語が日本語に翻訳されて読み上げられます

### 例 2：国際会議の翻訳

**目標：** スペイン語スピーチをリアルタイム翻訳

1. 起動コマンド：
   ```bash
   python main.py --mode translate --source-lang es --target-lang ja --coeiroink
   ```
2. スピーカーをマイクの近くに配置（または ZOOM などで共有）
3. 「開始」をクリック
4. リアルタイムで日本語に翻訳されます

### 例 3：映画・ドラマの音声翻訳

**目標：** フランス映画を日本語で鑑賞

1. 起動コマンド：
   ```bash
   python main.py --mode translate --source-lang fr --target-lang ja --voicevox
   ```
2. 映画の音声をシステム出力に設定
3. Voice Bridge で複合デバイスをリッスン
4. 「開始」をクリック
5. フランス語が日本語に翻訳されます

---

## トラブルシューティング

### 音声がキャプチャできない

**Windows：**
- 出力デバイスが Stereo Mix（またはループバック）に設定されているか
- サウンド設定で確認し、ループバックを有効化

**macOS：**
- BlackHole 2ch がインストールされているか
- Audio MIDI 設定で複合デバイスが作成されているか
- Voice Bridge で複合デバイスを選択しているか

詳しくは [BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md)

**Linux：**
```bash
# モニターデバイスを確認
python main.py --list-devices

# 「Monitor of ...」がない場合は PulseAudio/PipeWire 設定を確認
```

詳しくは [Linux トラブルシューティング](../troubleshooting/LINUX_TROUBLESHOOTING.md)

### 翻訳が正確でない

**対処：**

1. **ASR モデルを大きくする**
   ```bash
   python main.py --mode translate --model medium
   ```

2. **言語設定を確認**
   - ソース言語が正しく設定されているか

3. **音声認識の精度を上げる**
   - バックグラウンドノイズを減らす
   - スピーカーボリュームを調整

詳しくは [FAQ — 翻訳が正確でない](../troubleshooting/FAQ.md#q-翻訳が正確でない)

### 音声が出力されない

**対処：**

1. 「声」（TTS エンジン）が選択されているか確認
2. スピーカーが接続されているか、音量が上げられているか
3. VOICEVOX / CoeiroInk が起動しているか（指定している場合）

詳しくは [FAQ — TTS が動作しない](../troubleshooting/FAQ.md#q-coeiroink-が検出されない)

### Moonshine で日本語が認識されない

**対処：** Moonshine は英語特化のため、日本語の精度が低いです。

```bash
# Whisper に変更（推奨）
python main.py --mode translate --asr whisper --source-lang ja --target-lang en
```

詳しくは [FAQ — Moonshine で日本語](../troubleshooting/FAQ.md#q-moonshine-で日本語が認識されない)

---

## よくある質問

### Q: リアルタイムですか？遅延はどのくらい？

**A:** ほぼリアルタイムです。遅延は環境により異なりますが、一般的には 1-3 秒です。

**低遅延化：**
```bash
python main.py --mode translate --asr moonshine --chunk 2.0 --voicevox
```

### Q: 複数言語に同時翻訳できますか？

**A:** いいえ、一度に 1 言語ペアのみです。言語を切り替える場合は、設定を変更して再起動してください。

### Q: オフライン（インターネットなし）で動作しますか？

**A:** 翻訳には Google Translate API が使用されるため、インターネット接続が必須です。

音声認識（ASR）と音声合成は一部ローカル対応：
- **ASR：** Whisper / Moonshine（ローカル）
- **TTS：** VOICEVOX（ローカル） / CoeiroInk（ネット） / Edge TTS（ネット）

### Q: 複数の言語ペアでテストできますか？

**A:** はい。コマンドラインで言語を指定して何度でも起動できます。

```bash
# 英語 → 日本語
python main.py --mode translate --source-lang en --target-lang ja

# 後で別のターミナルから
python main.py --mode translate --source-lang ja --target-lang en
```

### Q: 字幕を表示することはできますか？

**A:** 現在は音声翻訳のみです。字幕表示はサポートされていません。

---

## 関連ドキュメント

- [モード別ガイド](./MODES_OVERVIEW.md) — チャット vs 翻訳
- [チャットモードガイド](./CHAT_MODE_GUIDE.md) — チャットモード
- [GUI ガイド](./GUI_GUIDE.md) — GUI 詳細設定
- [CLI リファレンス](../reference/CLI_REFERENCE.md) — コマンドライン完全リファレンス
- [BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md) — macOS セットアップ
- [Linux トラブルシューティング](../troubleshooting/LINUX_TROUBLESHOOTING.md) — Linux セットアップ
- [FAQ](../troubleshooting/FAQ.md) — トラブルシューティング
- [システムアーキテクチャ](../reference/ARCHITECTURE.md) — 技術詳細
