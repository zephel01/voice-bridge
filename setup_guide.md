# Voice Bridge - セットアップガイド

Voice Bridge は macOS と Windows の両方で動作します。OS に応じた手順に従ってください。

---

## macOS セットアップ

### 1. BlackHole のインストール

BlackHole は macOS でシステム音声をキャプチャするための仮想オーディオデバイスです。

#### Homebrew でインストール（推奨）

```bash
brew install blackhole-2ch
```

#### 手動インストール

1. [BlackHole の公式サイト](https://existential.audio/blackhole/) にアクセス
2. メールアドレスを入力してダウンロードリンクを取得
3. BlackHole 2ch をダウンロード・インストール

### 2. 複合デバイスの作成

YouTube の音声を **スピーカーで聞きながら** アプリでもキャプチャするために、複合デバイスを作成します。

1. **Audio MIDI 設定** を開く（Spotlight で「Audio MIDI 設定」と検索）
2. 左下の **＋ボタン** をクリック → 「**複合デバイスを作成**」
3. 以下のデバイスにチェックを入れる：
   - ✅ **BlackHole 2ch**
   - ✅ **MacBook Pro のスピーカー**（または使用中の出力デバイス）
4. デバイス名を **「Voice Bridge Output」** に変更（任意）
5. **マスターデバイス** を「MacBook Pro のスピーカー」に設定

### 3. macOS のサウンド設定

1. **システム設定** → **サウンド** → **出力**
2. 出力デバイスを **「Voice Bridge Output」**（作成した複合デバイス）に変更

これで YouTube の音声がスピーカーから聞こえつつ、BlackHole 経由でアプリにも届くようになります。

---

## Windows セットアップ

### 1. 音声キャプチャについて

Windows では **WASAPI ループバック** を使用するため、仮想オーディオデバイスのインストールは不要です。アプリが自動的にスピーカー出力をキャプチャします。

特別な設定は必要ありません。アプリ起動時にデフォルトの出力デバイスのループバックが自動選択されます。

### 2. 注意事項

- Windows 10 / 11 が必要です
- `pip install PyAudioWPatch` で自動インストールされます（requirements.txt に含まれています）
- 一部の環境では、サウンド設定で「ステレオミキサー」を有効にする必要がある場合があります

---

## 共通セットアップ

### VOICEVOX のセットアップ（推奨）

VOICEVOX を使うと、ずんだもん・四国めたん等のキャラクターボイスで翻訳音声を再生できます。
VOICEVOX を起動せずにアプリを起動した場合は、Edge TTS（nanami / keita）にフォールバックします。

#### インストール

1. [VOICEVOX 公式サイト](https://voicevox.hiroshiba.jp/) にアクセス
2. OS に合わせて選択：
   - **macOS**: Mac / CPU / インストーラー
   - **Windows**: Windows / GPU or CPU / インストーラー
3. インストーラーを実行

#### macOS 初回起動時の注意（Gatekeeper）

macOS のセキュリティ機能により初回起動がブロックされる場合があります。

- Finder で VOICEVOX を **Ctrl + クリック** →「**開く**」→ 確認ダイアログで「**開く**」
- または「システム設定」→「プライバシーとセキュリティ」→「このまま開く」
- Apple Silicon Mac の場合、Rosetta のインストールを求められたら案内に従ってください

#### 使い方

1. VOICEVOX アプリを起動する（バックグラウンドで API サーバーが `http://localhost:50021` で起動します）
2. Voice Bridge を起動する → 自動的に VOICEVOX を検出
3. GUI の「声」プルダウンからキャラクターを選択

### Python 環境のセットアップ

```bash
# Python 3.9+ が必要
python3 --version    # macOS
python --version     # Windows

# 仮想環境の作成（推奨）
cd voice-bridge
python3 -m venv venv          # macOS
python -m venv venv            # Windows

source venv/bin/activate       # macOS
venv\Scripts\activate          # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

### アプリの起動

```bash
# GUI モード（デフォルト）
python main.py

# CLI モード（デバッグ用）
python main.py --cli

# オプション一覧
python main.py --help
```

### 起動オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--cli` | - | CLI モードで起動（コンソール出力） |
| `--list-devices` | - | 利用可能な入力デバイスを表示 |
| `--device` | OS依存 | 入力デバイス名（macOS: BlackHole 2ch / Windows: default） |
| `--model` | `small` | Whisper モデル（tiny / base / small / medium） |
| `--voice` | `nanami` | Edge TTS 音声（VOICEVOX 未使用時） |
| `--speaker-id` | `3` | VOICEVOX speaker ID（CLIモード用） |
| `--chunk` | `4.0` | 音声チャンク長（秒） |

### GUI の見方

#### 設定エリア（上部）

- **入力デバイス**: 音声入力元を選択（macOS: BlackHole 2ch / Windows: Loopback デバイス）
- **Whisper**: 認識モデルのサイズ（精度と速度のトレードオフ）
- **声**: 読み上げ音声の選択（VOICEVOX 起動時はキャラクター一覧が表示される）

#### モニターエリア（中部）

- **入力レベル**: リアルタイムの音声レベルバー。赤い縦線が無音閾値
  - バーが全く動かない → 音声が入力デバイスに届いていない
  - バーが動くが赤線を超えない → 音量が小さすぎる
  - 緑色のバーが赤線を超える → 正常に入力されている
- **遅延**: 実質的な処理遅延（チャンク蓄積 + 認識 + 翻訳 + TTS の合計）

#### テキストエリア（下部）

- **English**: 認識された英語テキスト
- **日本語**: 翻訳された日本語テキスト

### 使い終わったら

- **macOS**: サウンド出力を通常のスピーカー/ヘッドフォンに戻してください
- **Windows**: 特に元に戻す操作は不要です

---

## トラブルシューティング

### 共通

#### 音声認識の精度が低い
- Whisper モデルサイズを `small` → `medium` に変更してみる（ただし処理速度は遅くなる）

#### 遅延が大きい
- Whisper モデルサイズを `tiny` や `base` に変更
- チャンクサイズを小さくする: `--chunk 2.0`
- 遅延表示で各ステージのボトルネックを確認

#### VOICEVOX が検出されない
- VOICEVOX アプリが起動しているか確認
- ブラウザで `http://localhost:50021/version` にアクセスしてバージョンが表示されるか確認
- ファイアウォールで localhost:50021 がブロックされていないか確認

#### VOICEVOX の音声合成エラー
- VOICEVOX アプリが起動したままか確認（スリープ復帰後に切断される場合あり）
- 一時ファイルディレクトリが削除されている場合は自動復旧されます

### macOS 固有

#### 音声がキャプチャされない
- macOS のサウンド出力が複合デバイスになっているか確認
- アプリ内で BlackHole 2ch が入力デバイスとして選択されているか確認
- `python main.py --list-devices` で BlackHole 2ch が表示されるか確認

#### 入力レベルバーが動かない
- macOS の「システム設定」→「サウンド」→「出力」が複合デバイスになっているか確認
- YouTube 等で音声を再生中か確認

### Windows 固有

#### 音声がキャプチャされない
- `python main.py --list-devices` で `[Loopback]` デバイスが表示されるか確認
- 表示されない場合は PyAudioWPatch が正しくインストールされているか確認: `pip install PyAudioWPatch`
- サウンド設定でデフォルトの出力デバイスが正しく設定されているか確認

#### PyAudioWPatch のインストールに失敗する
- Visual C++ Build Tools が必要な場合があります
- Python のバージョンが 3.7〜3.12 であることを確認

---

## VOICEVOX 利用表記

本アプリケーションでは音声合成に [VOICEVOX](https://voicevox.hiroshiba.jp/) を使用しています。

VOICEVOX を利用する場合、利用規約に基づきクレジット表記が必要です。
GUI 画面の下部に「VOICEVOX:キャラクター名」の形式で自動表示されます。

### 利用規約

- VOICEVOX ソフトウェア利用規約: https://voicevox.hiroshiba.jp/term/
- 各キャラクターの利用条件は、キャラクターごとの利用規約に従ってください
- 商用・非商用問わずクレジット表記（「VOICEVOX:キャラクター名」）が必須です

### 配信・動画等で使用する場合

Voice Bridge の出力を配信や動画に使用する場合は、概要欄やクレジットに以下を記載してください:

```
VOICEVOX:（使用キャラクター名）
```

例: `VOICEVOX:ずんだもん`、`VOICEVOX:四国めたん` など
