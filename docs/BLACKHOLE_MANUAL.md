# BlackHole マニュアル

## 目次
1. [概要](#概要)
2. [システム要件](#システム要件)
3. [インストール](#インストール)
4. [複合デバイスの作成](#複合デバイスの作成)
5. [設定確認](#設定確認)
6. [使用方法](#使用方法)
7. [トラブルシューティング](#トラブルシューティング)
8. [技術詳細](#技術詳細)
9. [FAQ](#faq)

---

## 概要

### BlackHole とは

**BlackHole** は macOS 上で「仮想オーディオケーブル」として機能するフリーソフトウェアです。スピーカーから出力される音声をアプリケーションに取り込むことができます。

### なぜ必要か？

通常、macOS ではスピーカーから出力される音声（システム音声）をアプリケーションで直接キャプチャできません。例えば：
- YouTube の動画音声をアプリで認識させたい
- ブラウザの音声を翻訳したい
- Zoom 通話を記録・翻訳したい

このような場合、BlackHole を使って仮想的に音声を「抜き出す」必要があります。

### Voice Bridge での役割

Voice Bridge では BlackHole を使って：
1. **YouTube の動画音声をキャプチャ** → 英語音声をキャプチャ
2. **Whisper で認識** → 英語テキストに変換
3. **翻訳** → 日本語に翻訳
4. **TTS で再生** → 日本語音声を出力

このパイプラインが実現します。

---

## システム要件

### 対応 OS
- **macOS 10.12** 以上

### 不要なもの
- ❌ 専門知識不要
- ❌ 追加のハードウェア不要
- ❌ コマンドライン操作ほぼ不要（GUI で完結）

---

## インストール

### 方法 1: Homebrew（推奨）

最も簡単な方法です。

```bash
# Homebrew がインストール済みか確認
brew --version

# BlackHole をインストール
brew install blackhole-2ch
```

インストール後、以下を実行して確認：

```bash
# インストール確認
brew list | grep blackhole
```

出力例：
```
blackhole-2ch
```

### 方法 2: 手動インストール

Homebrew がない場合や、最新版を使いたい場合：

1. [BlackHole 公式サイト](https://existential.audio/blackhole/) にアクセス
2. **メールアドレス** を入力
3. ダウンロードリンクをメールで受け取る
4. **BlackHole-2ch.pkg** をダウンロード
5. `BlackHole-2ch.pkg` をダブルクリックしてインストール
6. パスワードを入力して完了

### インストール確認

```bash
# Audio MIDI Setup で確認
# Spotlight で「Audio MIDI 設定」と検索して開く
# または以下を実行
open /Applications/Utilities/Audio\ MIDI\ Setup.app
```

Audio MIDI Setup が開き、デバイス一覧に **BlackHole 2ch** が表示されれば成功です。

---

## 複合デバイスの作成

### なぜ複合デバイスが必要か？

BlackHole は**入力専用の仮想デバイス**で、スピーカーから出力される音声をキャプチャします。しかし、BlackHole を macOS の出力デバイスに設定すると、**スピーカーから音が出なくなります**。

**複合デバイス** を使うことで：
- ✅ YouTube の音声を **スピーカーで聞きながら**
- ✅ 同時に BlackHole で **アプリがキャプチャ** できます

### 複合デバイス作成手順

#### ステップ 1: Audio MIDI Setup を開く

1. **Spotlight** で「Audio MIDI 設定」と検索
2. **Audio MIDI Setup.app** をクリック

または、Finder → Applications → Utilities → Audio MIDI Setup.app

#### ステップ 2: デバイスブラウザを表示

- メニューバー → **Window** → **Show Device Browser**
- または `Cmd + Ctrl + D`

#### ステップ 3: 複合デバイスを作成

左下の **「+」ボタン** をクリック → **「複合デバイスを作成」** を選択

![複合デバイス作成](https://via.placeholder.com/400x200?text=Create+Composite+Device)

#### ステップ 4: デバイスを追加

左側のデバイスリストから以下をチェック：

- ✅ **BlackHole 2ch** （必須）
- ✅ **MacBook Pro のスピーカー**（または使用中の出力デバイス）
  - iMac → iMac スピーカー
  - Mac mini → HDMI / オーディオケーブル接続先
  - MacBook Air/Pro → スピーカー

チェック例：
```
☐ AirPods
☐ External Microphone
☑ BlackHole 2ch
☑ MacBook Pro のスピーカー
☐ ...
```

#### ステップ 5: マスターデバイスを設定

1. 作成した複合デバイス（自動的に「Aggregate Device」と名付けられた）を選択
2. 右側パネルで **「マスターデバイス」** の欄を確認
3. **「MacBook Pro のスピーカー」** を選択（スピーカーから音を出すため）

#### ステップ 6: 名前を変更（任意）

複合デバイスの名前を「Aggregate Device」から分かりやすい名前に変更：

1. 複合デバイスを右クリック（または長押し）
2. **「名前を編集」**
3. **「Voice Bridge Output」** などに変更

完了後、Audio MIDI Setup は閉じても構いません。

---

## 設定確認

### macOS のサウンド設定

1. **System Preferences** → **Sound** → **Output**
2. **出力デバイス** が作成した複合デバイスになっているか確認

出力が複合デバイスになると：
- スピーカーアイコン → 複合デバイス名が表示される
- YouTube などを再生 → スピーカーから音が聞こえる
- アプリのレベルメーターが反応 → BlackHole がキャプチャしている

### Voice Bridge での確認

```bash
# 利用可能なデバイスを表示
python main.py --list-devices
```

出力例：
```
利用可能な入力デバイス:
  [5] BlackHole 2ch (ch=2)
  [6] MacBook Pro マイク (ch=1)
  ...
```

**BlackHole 2ch** がリストに表示されていることを確認してください。

---

## 使用方法

### 基本的な流れ

#### 準備

1. **YouTube やブラウザで音声を再生するタブを開く**
   - 例：YouTube の英語動画

2. **Voice Bridge を起動**
   ```bash
   python main.py
   ```

3. **GUI の設定確認**
   - **入力デバイス** が **BlackHole 2ch** になっているか確認
   - なっていなければドロップダウンで選択

4. **YouTube の音声を再生**
   - スピーカーから音が聞こえることを確認
   - GUI の入力レベルバーが動くことを確認

#### 実行

- **入力レベルバー** が赤線を超える → 英語を認識
- **English テキスト** に認識結果が表示される
- **日本語テキスト** に翻訳結果が表示される
- **TTS 出力** で日本語音声が再生される（VOICEVOX または Edge TTS）

### CLI モード での実行

```bash
# シンプルな出力
python main.py --cli

# カスタム設定
python main.py --cli --device "BlackHole 2ch" --model small
```

CLI モードでは、ターミナルに以下のような出力が表示されます：

```
[Transcriber] Whisper モデル (small) をロード中...
[VoicevoxTTS] VOICEVOX サーバーに接続中 (localhost:50021)...
[VoiceBridge] キャプチャ開始: BlackHole 2ch
[Transcriber] 認識: "Hello, how are you?"
[Translator] 翻訳: "こんにちは、お元気ですか？"
[VoicevoxTTS] 再生: こんにちは、お元気ですか？ (Speaker: nanami)
```

### 終了

- **GUI モード**: ウィンドウを閉じる → 自動停止
- **CLI モード**: `Ctrl + C` で停止

---

## トラブルシューティング

### 問題: 音声がキャプチャされない

#### 症状
- 入力レベルバーが全く動かない
- 英語が認識されない

#### 対処法

**1. macOS の出力設定を確認**

```bash
# 出力デバイスを確認
system_profiler SPAudioDataType | grep "Output Source" -A 10
```

Audio MIDI Setup で作成した複合デバイスが **出力デバイス** になっているか確認：

1. System Preferences → Sound → Output
2. 複合デバイス名を選択

**2. BlackHole 2ch が入力デバイスに表示されているか確認**

```bash
python main.py --list-devices
```

BlackHole 2ch が表示されない場合 → インストール失敗の可能性

**3. YouTube などで音声を再生中か確認**

BlackHole は **出力される音声をキャプチャ** するため、音声が出力されていないと何もキャプチャできません。

**4. 入力レベルの閾値を確認**

Voice Bridge の入力レベルバーが赤線を超えていない場合：
- YouTube の音量を上げる
- Voice Bridge の無音閾値を下げる（コード編集が必要）

---

### 問題: 入力レベルバーが動くが認識されない

#### 症状
- 入力レベルバーが反応する
- しかし英語テキストが表示されない

#### 対処法

**1. Whisper モデルが正常に動作しているか確認**

```bash
python transcriber.py
```

モデルのダウンロードに時間がかかることがあります。

**2. Whisper モデルサイズを変更**

```bash
python main.py --model base
```

モデルサイズ（大きいほど精度向上）：
- `tiny` - 最速、低精度
- `base` - 高速、中精度
- `small` - 標準（デフォルト）
- `medium` - 遅い、高精度

---

### 問題: 翻訳されない

#### 症状
- 英語は認識される
- 日本語テキストが表示されない

#### 対処法

**1. インターネット接続を確認**

翻訳に Google Translate を使用しているため、インターネット接続が必須です。

**2. ファイアウォール設定を確認**

VPN や corporate firewall がGoogle Translate をブロックしていないか確認。

---

### 問題: TTS（音声出力）が出ない

#### 症状
- 英語・日本語は表示される
- スピーカーから何も聞こえない

#### 対処法

**1. VOICEVOX が起動しているか確認**

```bash
# ブラウザで確認
curl http://localhost:50021/version
```

レスポンスがない → VOICEVOX が起動していない

VOICEVOX を起動してください（Applications → VOICEVOX）。

**2. VOICEVOX がブロックされていないか確認**

ファイアウォール設定で localhost:50021 がブロックされていないか確認。

**3. VOICEVOX が起動していない場合は Edge TTS が自動使用される**

Voice Bridge は自動的にフォールバックします：
- VOICEVOX 起動時 → VOICEVOX を使用（高品質）
- VOICEVOX 未起動 → Edge TTS を使用（低遅延）

---

## 技術詳細

### BlackHole の仕組み

BlackHole は kernel extension として動作します：

```
[Application Output] → [macOS Audio System] → [BlackHole (Kernel)] → [Voice Bridge]
                                          ↓
                                    [Speaker]
```

1. アプリが音声を出力 → macOS Audio System へ送信
2. Audio System が出力を複数の宛先へ送信（複合デバイスの効果）
3. BlackHole が音声をキャプチャ
4. 同時に Speaker にも音声が送られる

### Voice Bridge での使用

```python
# audio_capture.py の一部
from sounddevice import InputStream

stream = InputStream(
    device="BlackHole 2ch",      # デバイス名（自動解決）
    channels=1,                  # モノラル
    samplerate=16000,            # Whisper の標準レート
    blocksize=8000,              # 0.5秒ごとにコールバック
    callback=self._audio_callback,
)
```

---

## FAQ

### Q. BlackHole と類似製品の違いは？

| 製品 | 価格 | 機能 | macOS バージョン |
|---|---|---|---|
| **BlackHole** | 無料 | シンプル、軽量 | 10.12+ |
| Loopback | 有料 ($99) | 高機能、複雑 | 10.4+ |
| SoundFlower | 無料 | 古い、非公式 | 10.5-10.11 |

BlackHole は最新で、最もシンプルなため推奨です。

---

### Q. BlackHole をアンインストールしたい場合は？

```bash
# Homebrew でインストールした場合
brew uninstall blackhole-2ch

# 手動インストールの場合
# Audio MIDI Setup で複合デバイスを削除してから
# 以下のファイルを削除
rm -rf /Library/Audio/Plug-Ins/HAL/BlackHole.driver
sudo kextunload -b audio.existential.BlackHole
```

---

### Q. 複合デバイスを削除したい場合は？

1. Audio MIDI Setup を開く
2. 複合デバイスを選択
3. 左下の **「−」** ボタンをクリック

削除後、macOS の出力デバイスを通常のスピーカーに戻してください。

---

### Q. 複数の スピーカー/ヘッドフォンがある場合は？

複合デバイスに複数のスピーカーを追加できます：

```
複合デバイス:
  - BlackHole 2ch
  - MacBook Pro のスピーカー
  - Bluetooth スピーカー（AUDIO-DEVICE）
```

マスターデバイスを選択すると、そこから音が出力されます。

---

### Q. BlackHole が認識されない場合は？

以下を実行して診断してください：

```bash
# デバイスリストを表示
python main.py --list-devices

# より詳細な情報を表示
python -c "import sounddevice as sd; print(sd.query_devices())"
```

出力に BlackHole が表示されない場合：

1. **Homebrew で再インストール**
   ```bash
   brew uninstall blackhole-2ch
   brew install blackhole-2ch
   ```

2. **Mac を再起動**
   ```bash
   sudo reboot
   ```

3. **手動インストール**
   公式サイトから最新版をダウンロード

---

### Q. Windows では BlackHole は使えるのか？

いいえ。BlackHole は macOS 専用です。

Windows では **WASAPI ループバック** を使用します：
- 自動的に設定されるため、手動設定は不要
- `PyAudioWPatch` ライブラリが対応
- 詳細は [setup_guide.md](./setup_guide.md#windows-セットアップ) を参照

---

## 参考資料

- [BlackHole 公式サイト](https://existential.audio/blackhole/)
- [Voice Bridge セットアップガイド](./setup_guide.md)
- [Audio MIDI Setup ユーザーガイド（Apple 公式）](https://support.apple.com/ja-jp/guide/audio-midi-setup/)

---

**最終更新**: 2026-02-26
