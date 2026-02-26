# BlackHole トラブルシューティングガイド

問題が発生した場合の診断と解決方法

---

## 診断フローチャート

```
入力レベルバーが動く？
├─ YES → 英語が認識される？
│         ├─ YES → 日本語が表示される？
│         │         ├─ YES → TTS 音声が出力される？
│         │         │         ├─ YES → 正常動作 ✓
│         │         │         └─ NO  → TTS 設定確認 [Q3]
│         │         └─ NO  → 翻訳設定確認 [Q2]
│         └─ NO  → Whisper 設定確認 [Q1]
└─ NO  → BlackHole 設定確認 [Q0]
```

---

## Q0: 入力レベルが反応しない

### 症状
- **入力レベルバーが全く動かない**
- **YouTube など音声を再生しているのに反応なし**

### チェックリスト

#### 1. YouTube 音声が実際に出力されているか？

```bash
# スピーカーボリュームを確認
# macOS メニューバーの音量アイコンをクリック → 最大に設定
```

スピーカーから音が聞こえない場合 → Apple Support に相談

---

#### 2. macOS の出力デバイスが複合デバイスになっているか？

```bash
# メニューバー → 音量アイコン → 出力デバイスを確認
```

出力デバイスが「Voice Bridge Output」（複合デバイス）になっていない場合：

1. System Settings → Sound → Output
2. 複合デバイスを選択
3. Voice Bridge GUI を再起動

---

#### 3. Audio MIDI Setup で複合デバイスが正しく作成されているか？

Audio MIDI Setup を開いて確認：

```
左側パネル：
  Device Browser を表示 (Cmd+Ctrl+D)

  デバイスリストを確認：
  ├─ Input Devices
  │  └─ BlackHole 2ch （← 見つかるか？）
  ├─ Output Devices
  │  └─ MacBook Pro のスピーカー
  └─ Aggregate Devices
     └─ Voice Bridge Output （← ここに複合デバイスがあるか？）
```

複合デバイスがない場合：
- [クイックスタート](./BLACKHOLE_QUICK_START.md#ステップ-2-複合デバイス作成3分) に従って再作成

---

#### 4. BlackHole が入力デバイスとして見つかるか？

```bash
python main.py --list-devices
```

**BlackHole 2ch** が表示されない場合 → インストール確認 [Q0.1]

---

#### 5. Voice Bridge が正しいデバイスを使用しているか？

GUI で確認：
1. Voice Bridge GUI 上部の **「入力デバイス」** ドロップダウン
2. **「BlackHole 2ch」** が選択されているか確認
3. なっていなければドロップダウンから選択

---

### 解決方法

問題が解決しない場合：

```bash
# 診断コマンド
python main.py --list-devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# 詳細ログ出力
python main.py --cli --device "BlackHole 2ch" 2>&1 | head -50
```

出力結果に **「BlackHole 2ch」** が含まれていなければ → [Q0.1](#q01-blackhole-が-input-device-として表示されない)

---

## Q0.1: BlackHole が Input Device として表示されない

### 原因
- BlackHole がインストールされていない
- インストール失敗
- macOS 再起動後も認識されていない

### 解決方法

#### 方法 1: 再インストール（推奨）

```bash
# アンインストール
brew uninstall blackhole-2ch

# インストール
brew install blackhole-2ch

# 確認
brew list | grep blackhole
```

#### 方法 2: Mac を再起動

```bash
sudo reboot
```

再起動後、Device Browser で確認。

#### 方法 3: 手動インストール

Homebrew が上手くいかない場合：

1. [BlackHole 公式サイト](https://existential.audio/blackhole/) にアクセス
2. メールアドレスを入力してダウンロード
3. `BlackHole-2ch.pkg` をダブルクリック
4. インストールウィザードに従う
5. Mac を再起動

#### 方法 4: 手動削除と再インストール

```bash
# 既存ファイルを削除
sudo rm -rf /Library/Audio/Plug-Ins/HAL/BlackHole.driver

# 再インストール
brew install blackhole-2ch

# 再起動
sudo reboot
```

---

## Q1: Whisper が認識しない

### 症状
- **入力レベルバーが動く** ✓
- **音声が入力されている** ✓
- **しかし英語テキストが出現しない** ✗

### チェックリスト

#### 1. Whisper モデルが正常にロードされたか？

```bash
python transcriber.py
```

コンソール出力例：

```
[Transcriber] Whisper モデル (small) をロード中...
[Transcriber] モデル準備完了
```

エラーが出た場合 → インターネット接続確認（初回はモデルをダウンロード）

---

#### 2. Whisper モデルが大きすぎないか？

デフォルト `small` で上手くいかない場合、より小さいモデルを試す：

```bash
# tiny モデルで試す（最速）
python main.py --model tiny

# base モデルで試す（バランス）
python main.py --model base
```

各モデルのトレードオフ：

| モデル | サイズ | 精度 | 速度 | 初回DL時間 |
|---|---|---|---|---|
| `tiny` | 39MB | 低 | 最速 | 1秒 |
| `base` | 139MB | 中 | 高速 | 5秒 |
| `small` | 461MB | 高 | 標準 | 15秒 |
| `medium` | 1.5GB | 非常に高 | 遅い | 1分 |

---

#### 3. YouTube 音声が英語か？

Voice Bridge は英語認識を前提としています：

```bash
# 認識言語を確認（コード改修が必要）
# transcriber.py の task 設定を変更
```

日本語や他言語を認識したい場合は、開発者に相談してください。

---

#### 4. 無音検出の閾値で音声が除外されていないか？

**入力レベルが小さすぎる場合の確認方法**：

1. Voice Bridge GUI で **「入力レベル」バーを確認**
2. **赤い縦線 = 無音閾値**
3. グリーンバーが赤線を超えているか確認

超えていない場合：
- YouTube の音量を上げる
- マイクに近づく（マイク入力の場合）

---

### 解決方法

```bash
# CLI モードで詳細ログを出力
python main.py --cli --model base

# 出力を観察：
# [Transcriber] 認識: "..." → 認識成功
# 何も出ない → Whisper が認識していない（音声品質の問題）
```

---

## Q2: 翻訳されない

### 症状
- **入力レベルが動く** ✓
- **英語テキストが表示される** ✓
- **日本語テキストが表示されない** ✗

### チェックリスト

#### 1. インターネット接続があるか？

```bash
# Google Translate に接続できるか確認
curl -I https://translate.google.com
```

応答がない場合 → インターネット接続確認

---

#### 2. VPN やファイアウォールが Google Translate をブロックしていないか？

Corporate 環境の場合：
- ファイアウォール管理者に相談
- VPN を無効化して試す

---

#### 3. Translator が正常に動作しているか？

```bash
python translator.py
```

正常な出力例：

```
[Translator] "Hello" → "こんにちは"
```

エラーが出た場合 → インターネット接続確認

---

#### 4. 英語テキストが本当に正しく認識されているか？

GUI で確認：

```
English テキストボックスに "Hello, how are you?" と表示されているか？

→ YES: 翻訳ロジックの問題の可能性
→ NO:  Whisper の認識精度が低い可能性（Q1 を参照）
```

---

### 解決方法

```bash
# CLI モードで各ステージを監視
python main.py --cli

# 出力を観察：
# [Transcriber] 認識: "Hello"
# [Translator] 翻訳: "こんにちは"
# → 翻訳成功

# 翻訳が出ない場合：
# インターネット接続か Translator コードの問題
```

---

## Q3: TTS（音声出力）が出ない

### 症状
- **入力レベル** ✓
- **英語テキスト** ✓
- **日本語テキスト** ✓
- **スピーカーから音が出ない** ✗

### チェックリスト

#### 1. VOICEVOX が起動しているか？

```bash
# ターミナルで確認
curl http://localhost:50021/version
```

レスポンス例：

```json
{"version":"0.15.0","..."}
```

レスポンスなし → VOICEVOX が起動していない

**対処方法**：
1. Applications → VOICEVOX を起動
2. Voice Bridge GUI を再起動

---

#### 2. VOICEVOX が起動していない場合は Edge TTS が自動使用される

Voice Bridge は自動フォールバック機能があります：

```
VOICEVOX 起動 → VOICEVOX を使用（高品質）
VOICEVOX 未起動 → Edge TTS を使用（自動切り替え）
```

Edge TTS でも音が出ない場合 → 進行中

---

#### 3. スピーカーの音量が 0 になっていないか？

```bash
# メニューバーの音量アイコンをクリック → 最大に
```

---

#### 4. TTS エンジンが正常に動作しているか？

```bash
# Edge TTS をテスト
python tts_engine.py

# VOICEVOX をテスト
python tts_voicevox.py
```

---

### 解決方法

```bash
# VOICEVOX サーバーログを確認
# VOICEVOX アプリを起動 → Help → View Logs

# または CLI で詳細ログを出力
python main.py --cli 2>&1 | grep -i "tts\|speaker"
```

---

## 詳細な診断方法

### デバイスリストを完全に表示

```bash
python -c "
import sounddevice as sd
devices = sd.query_devices()
for i, d in enumerate(devices):
    print(f'[{i}] {d[\"name\"]}')
    print(f'    Input: {d[\"max_input_channels\"]}, Output: {d[\"max_output_channels\"]}')
    print(f'    Default SR: {d[\"default_samplerate\"]}\n')
"
```

---

### Audio MIDI Setup のコマンドライン確認

```bash
# macOS に登録されているオーディオデバイスを表示
system_profiler SPAudioDataType
```

出力に **BlackHole** が含まれているか確認。

---

### Voice Bridge のログを詳細出力

```bash
# ロギングレベルを DEBUG に設定（コード編集が必要）
# または CLI mode で実行
python main.py --cli --device "BlackHole 2ch" --model small
```

---

## よくある質問

### Q. Homebrew がない場合は？

```bash
# Homebrew をインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# BlackHole をインストール
brew install blackhole-2ch
```

### Q. M1/M2 Mac（Apple Silicon）での問題は？

BlackHole は Apple Silicon でも動作します。

上手くいかない場合：
- [BlackHole Issues](https://github.com/ExistentialAudio/BlackHole/issues) で検索
- 最新版を手動インストール

### Q. 複合デバイス削除後、音が出ない

```bash
# macOS の出力をデフォルトに戻す
System Settings → Sound → Output → MacBook Pro スピーカー
```

---

## サポートが必要な場合

1. **このガイドで解決しない場合**：
   - [詳細マニュアル](./BLACKHOLE_MANUAL.md) を確認

2. **Voice Bridge の問題の場合**：
   - GitHub Issues で報告
   - 診断ログを貼付：
     ```bash
     python main.py --list-devices 2>&1
     python transcriber.py 2>&1 | head -20
     ```

3. **BlackHole の問題の場合**：
   - [BlackHole GitHub](https://github.com/ExistentialAudio/BlackHole)
   - [BlackHole Support](https://existential.audio/contact/)

---

**最終更新**: 2026-02-26
