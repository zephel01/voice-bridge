# Voice Bridge

リアルタイム多言語音声翻訳アプリ。システム音声をキャプチャして、音声認識 → 翻訳 → 音声合成をリアルタイムに行います。

YouTube の英語動画を日本語音声で聞く、といった使い方ができます。

## 対応言語

英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

GUI上でソース言語とターゲット言語を選択でき、リアルタイムに切り替え可能です。

> **Note:** Moonshine エンジン使用時は en / ja / zh / es / ko の5言語に対応（fr, de は未対応）。

## 動作環境

- Python 3.9+
- macOS 10.12+ / Windows 10・11
- メモリ 4GB以上（8GB推奨）

## セットアップ

### 1. インストール

```bash
git clone https://github.com/zephel01/voice-bridge.git
cd voice-bridge
python3 -m venv venv && source venv/bin/activate   # macOS
# python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. 音声キャプチャの準備

**Windows** — 設定不要（WASAPIループバックで自動キャプチャ）

**macOS** — BlackHole（仮想オーディオデバイス）が必要です。

```bash
brew install blackhole-2ch
```

インストール後、Audio MIDI設定で複合デバイスを作成してください。詳細は [docs/BLACKHOLE_QUICK_START.md](docs/BLACKHOLE_QUICK_START.md) を参照。

### 3. VOICEVOX（任意）

[VOICEVOX](https://voicevox.hiroshiba.jp/) をインストール・起動しておくと、ずんだもん等のキャラクターボイスで読み上げます。未起動時は Edge TTS にフォールバックします。

### 4. 起動

```bash
python main.py                                     # GUI モード（Whisper）
python main.py --cli                               # CLI モード
python main.py --source-lang fr --target-lang ja   # フランス語→日本語
python main.py --model medium                      # 高精度モデル
python main.py --list-devices                      # デバイス一覧
```

#### デバイス一覧の確認（`--list-devices`）

`--list-devices` を実行すると、利用可能な音声入力デバイスの一覧が表示されます。

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

各項目の意味：

- `[番号]` — `--device` オプションに指定するインデックス番号
- `デバイス名` — マイクや仮想デバイスの名称
- `ch=N` — チャンネル数（1=モノラル、2=ステレオ）
- `[LOOPBACK]` — システム音声をキャプチャできるデバイス（Windows の WASAPI ループバック等）

翻訳モード（システム音声キャプチャ）では BlackHole や複合デバイス、LOOPBACK デバイスを選択してください。チャットモード（マイク入力）ではマイクデバイスを選択します。

```bash
# 例: BlackHole でシステム音声をキャプチャ（翻訳モード）
python main.py --device 1

# 例: AirPods のマイクで音声入力（チャットモード）
python main.py --mode chat --device 2 --source-lang ja
```

#### Moonshine エンジンで起動

[Moonshine](https://github.com/moonshine-ai/moonshine) はストリーミング対応の軽量 ASR エンジンです。Whisper と比べて低レイテンシ・高精度で、ハルシネーション（無音時の幻聴テキスト）も大幅に減少します。`--chunk 2.0` との併用で応答速度がさらに向上します。

```bash
pip install moonshine-voice
python main.py --asr moonshine                     # GUI モード（Moonshine）
python main.py --asr moonshine --chunk 2.0         # 低レイテンシ（推奨）
python main.py --asr moonshine --cli               # CLI モード（Moonshine）
```

`--asr` を省略すると従来通り Whisper で動作します。

## 処理パイプライン

```
音声キャプチャ → ASR認識 → Google翻訳 → TTS音声合成 → 再生
```

| コンポーネント | 技術 |
|---|---|
| 音声認識 | Faster-Whisper（デフォルト）/ Moonshine（`--asr moonshine`） |
| 翻訳 | Google Translate（deep-translator） |
| 音声合成 | VOICEVOX（日本語）/ Edge TTS（7言語） |
| 音声キャプチャ | BlackHole + sounddevice（macOS）/ WASAPI（Windows） |
| GUI | tkinter |

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 入力レベルが動かない（macOS） | サウンド出力が複合デバイスか確認 |
| 入力レベルが動かない（Windows） | `--list-devices` で Loopback デバイスを確認 |
| 認識精度が低い | `--model medium` に変更、または `--asr moonshine` を試す |
| VOICEVOX が検出されない | VOICEVOX アプリが起動しているか確認 |
| 遅延が大きい | `--model tiny` や `--chunk 2.0` に変更、または `--asr moonshine` を試す |

詳しくは [docs/BLACKHOLE_TROUBLESHOOTING.md](docs/BLACKHOLE_TROUBLESHOOTING.md) を参照してください。

## ドキュメント

- [BlackHole クイックスタート](docs/BLACKHOLE_QUICK_START.md) — macOS 音声キャプチャの設定（5分）
- [BlackHole 詳細マニュアル](docs/BLACKHOLE_MANUAL.md) — 詳しい設定方法
- [BlackHole トラブルシューティング](docs/BLACKHOLE_TROUBLESHOOTING.md) — 問題解決

## VOICEVOX 利用表記

本アプリケーションでは音声合成に [VOICEVOX](https://voicevox.hiroshiba.jp/) を使用しています。
配信・動画で使用する場合はクレジット表記（`VOICEVOX:キャラクター名`）をお願いします。

## ライセンス

MIT License
