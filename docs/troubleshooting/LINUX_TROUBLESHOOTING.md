# Linux トラブルシューティング

Voice Bridge の Linux 環境でのセットアップとトラブル対応ガイド。

## 前提条件

Voice Bridge は PulseAudio または PipeWire を使用してシステム音声をキャプチャします。

```bash
# 現在の音声サーバーを確認
pacmd stat | grep "Server"  # PulseAudio
pw-status                    # PipeWire
```

## よくある問題と対処方法

### 1. モニターデバイスが見つからない

**症状:** `--list-devices` でモニターデバイス（`Monitor of ...`）が表示されない

**原因:** PulseAudio の loopback モジュールが読み込まれていない

**対処:**

```bash
# モニターデバイスの確認
pactl list sources | grep Monitor

# ない場合：loopback モジュールを読み込む
pactl load-module module-loopback latency_msec=1

# 確認
pactl list sources short
```

モニターデバイスが作成されたら、以下で使用できます：

```bash
python main.py --device "Monitor of Built-in Audio"
```

**永続化の設定:**

`~/.config/pulse/default.pa` に以下を追加して、起動時に自動読み込みするようにできます：

```conf
### loopback module
load-module module-loopback latency_msec=1
```

### 2. PipeWire 環境でモニターデバイスが動作しない

**症状:** PipeWire を使用しているが、モニターデバイスが認識されない

**原因:** `pipewire-pulse` ブリッジが起動していない、または不足している

**対処:**

```bash
# 現在のセッションを確認
echo $XDG_SESSION_TYPE  # "wayland" または "x11"

# pipewire-pulse がインストール済みか確認
apt list --installed | grep pipewire-pulse

# インストール
sudo apt install pipewire-pulse

# PipeWire サービスを再起動
systemctl restart --user pipewire pipewire-pulse

# 確認
pactl list sources short
```

### 3. 権限エラーで音声キャプチャができない

**症状:** `Permission denied` または `Device not found`

**原因:** ユーザーが `audio` グループに属していない

**対処:**

```bash
# 現在のユーザーを audio グループに追加
sudo usermod -a -G audio $USER

# グループの変更を反映（再ログインまたは以下を実行）
newgrp audio

# 確認
groups
```

**PulseAudio デーモンの再起動:**

```bash
pulseaudio -k  # デーモン終了
pulseaudio --start  # デーモン再起動
```

### 4. 特定のデバイスで音声が出力されない

**症状:** モニターデバイスは見つかるが、音声がキャプチャされない

**原因:** デフォルト出力がモニターデバイスに設定されていない

**対処:**

```bash
# デバイス一覧を確認
python main.py --list-devices

# デフォルト出力デバイスを設定（PulseAudio）
pactl set-default-sink "DEVICE_NAME"

# 例
pactl set-default-sink "alsa_output.pci-0000_00_1f.3.analog-stereo"
```

ALSA がシステム音声を出力している場合、PulseAudio でそれを監視するようにします：

```bash
# PulseAudio のモジュールを確認
pactl list modules | head -20

# ALSA ソースが見つからない場合は読み込む
pactl load-module module-alsa-source
```

### 5. レイテンシが大きい

**症状:** 音声が飛び飛びになったり、遅延が大きい

**対処:**

```bash
# Moonshine と低レイテンシ設定で実行
python main.py --asr moonshine --chunk 2.0

# または小さいモデルを使用
python main.py --model tiny

# チャットモードで VAD を有効化
python main.py --mode chat --vad
```

PulseAudio のバッファを調整：

```bash
# レイテンシを減らす（デフォルト: 2000ms）
pactl set-sink-input-latency 0 100
```

### 6. 複数の音声デバイスがある場合の選択

**症状:** 間違ったデバイスで音声がキャプチャされている

**対処:**

```bash
# デバイス一覧を確認
python main.py --list-devices

# 特定のデバイスを指定
python main.py --device "USB Microphone"
python main.py --device "Monitor of Built-in Audio"
```

デバイス名の一部でも指定可能です：

```bash
python main.py --device "USB"    # "USB Microphone" を選択
python main.py --device "Monitor"  # モニターデバイスを選択
```

## Ubuntu / Debian での標準インストール

```bash
# 基本パッケージ
sudo apt install portaudio19-dev python3-tk

# PulseAudio 関連（Ubuntu 20.04 LTS の場合）
sudo apt install pulseaudio pulseaudio-utils

# PipeWire 関連（Ubuntu 22.04 LTS+）
sudo apt install pipewire pipewire-pulse

# 音声デバイスのモニタリング
sudo apt install pavucontrol  # GUI ツール
apt install pulseaudio-utils  # コマンドラインツール
```

## Fedora / RHEL での標準インストール

```bash
sudo dnf install portaudio-devel python3-tkinter

# PulseAudio
sudo dnf install pulseaudio pulseaudio-utils

# PipeWire（Fedora 34+）
sudo dnf install pipewire pipewire-pulseaudio
```

## デバッグ情報の収集

トラブル報告時に以下の情報を含めてください：

```bash
# PulseAudio / PipeWire の確認
pacmd stat
pw-status

# 音声デバイス一覧
python main.py --list-devices

# Voice Bridge のモニターデバイス認識状況
python main.py --list-devices | grep Monitor

# システム音声の確認
speaker-test -t wav -c 2  # 5秒間テスト音声を再生

# ログ
python main.py --mode chat --vad 2>&1 | head -50
```

## 参考リンク

- [PulseAudio 公式ドキュメント](https://www.freedesktop.org/wiki/Software/PulseAudio/)
- [PipeWire 公式ドキュメント](https://gitlab.freedesktop.org/pipewire/pipewire)
- [ALSA プロジェクト](https://www.alsa-project.org/)
