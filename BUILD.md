# Voice Bridge - ビルド手順

Python インストール無しで実行できるスタンドアロン版を作成する手順です。

---

## 概要

PyInstaller を使って、Python ランタイムとすべての依存ライブラリを1つのフォルダにバンドルします。

| 項目 | 内容 |
|------|------|
| ビルドツール | PyInstaller |
| 出力形式 | フォルダ（--onedir） |
| 出力先 | `dist/VoiceBridge/` |
| 推定サイズ | 150〜300MB（Whisperモデル含まず） |
| macOS 出力 | `VoiceBridge.app` |
| Windows 出力 | `VoiceBridge/VoiceBridge.exe` |

### なぜ --onefile ではなく --onedir か

--onefile は起動のたびに一時フォルダへ展開するため、起動に数秒〜十数秒かかります。音声アプリでは起動速度が重要なため、--onedir（フォルダ形式）を推奨します。配布時は ZIP にまとめてください。

---

## ビルド手順

### 1. ビルド環境の準備

ビルドは **配布先と同じ OS** で行う必要があります（macOS用はmacOSで、Windows用はWindowsでビルド）。

```bash
# 仮想環境を作成（推奨）
python -m venv build_env
source build_env/bin/activate    # macOS/Linux
# build_env\Scripts\activate     # Windows

# アプリの依存ライブラリをインストール
pip install -r requirements.txt

# PyInstaller をインストール
pip install pyinstaller
```

### 2. ビルドの実行

```bash
pyinstaller voice_bridge.spec
```

成功すると `dist/VoiceBridge/` フォルダが生成されます。

macOS の場合は `dist/VoiceBridge.app` も生成されます。

### 3. 動作確認

```bash
# macOS
./dist/VoiceBridge/VoiceBridge
# または
open dist/VoiceBridge.app

# Windows
dist\VoiceBridge\VoiceBridge.exe
```

---

## Whisper モデルについて

Whisper モデル（数百MB〜数GB）はビルドに**含まれません**。初回起動時に自動ダウンロードされます。

| モデル | サイズ | 精度 |
|--------|--------|------|
| tiny | ~75MB | 低 |
| base | ~140MB | 中低 |
| small | ~500MB | 中（デフォルト） |
| medium | ~1.5GB | 高 |

### オフライン配布したい場合

モデルを事前にダウンロードして同梱することも可能です:

```python
# 事前ダウンロードスクリプト
from faster_whisper import WhisperModel
model = WhisperModel("small", download_root="./models")
```

ダウンロードされた `models/` フォルダごと配布し、起動時に `--model-dir` で指定する仕組みを追加する必要があります（現在の main.py には未実装）。

---

## VOICEVOX について

VOICEVOX は別アプリとして起動する必要があります（バンドルに含まれません）。
VOICEVOX が起動していない場合は Edge TTS（インターネット経由）にフォールバックします。

---

## プラットフォーム別の注意事項

### macOS

**コード署名（配布時に推奨）:**

```bash
codesign --deep --force --sign "Developer ID Application: ..." dist/VoiceBridge.app
```

署名しない場合、Gatekeeper の警告が表示されます。ユーザーは「システム設定 → プライバシーとセキュリティ」から許可できます。

**音声キャプチャの権限:**

BlackHole を使ったシステム音声キャプチャには特別な権限は不要です（仮想デバイス経由のため）。

### Windows

**ウイルス対策ソフトの誤検知:**

PyInstaller で作成した exe はウイルス対策ソフトに誤検知されることがあります。これは PyInstaller の既知の問題です。

対策:
- UPX 圧縮を使わない（.spec で `upx=False` に設定済み）
- Inno Setup 等でインストーラーを作成する
- コード署名証明書で署名する

**Visual C++ ランタイム:**

PyInstaller がランタイム DLL を自動でバンドルしますが、環境によっては Microsoft Visual C++ 再頒布可能パッケージが必要な場合があります。

---

## トラブルシューティング

### ビルドが失敗する場合

```bash
# デバッグモードでビルド（詳細ログ表示）
pyinstaller voice_bridge.spec --log-level DEBUG

# 隠れたインポートの問題を調査
pyinstaller voice_bridge.spec --debug imports
```

### CTranslate2 関連のエラー

```bash
# CTranslate2 のバージョンを確認
pip show ctranslate2

# 互換性のあるバージョンに固定（例）
pip install ctranslate2==4.4.0
```

### 起動時に「モジュールが見つからない」エラー

.spec ファイルの `hiddenimports` に不足しているモジュール名を追加してリビルドしてください。

---

## 配布

### ZIP 配布（シンプル）

```bash
# macOS
cd dist && zip -r VoiceBridge-mac.zip VoiceBridge.app

# Windows
# dist\VoiceBridge フォルダを ZIP に圧縮
```

### インストーラー作成（Windows）

[Inno Setup](https://jrsoftware.org/isinfo.php) を使うと、インストーラー（.exe）を作成できます。ウイルス対策ソフトの誤検知も軽減されます。
