# よくある質問（FAQ）

Voice Bridge についてのよくある質問とその回答です。

## インストール・セットアップ

### Q: インストール後、GUI が起動しない

**A:** 以下を確認してください：

1. Python 3.9+ がインストールされているか
   ```bash
   python --version
   ```

2. 仮想環境が正しく有効化されているか
   ```bash
   source venv/bin/activate  # macOS/Linux
   # venv\Scripts\activate.bat  # Windows
   ```

3. 必須ライブラリがインストールされているか
   ```bash
   pip install -r requirements.txt
   ```

4. 再度起動してみる
   ```bash
   python main.py
   ```

### Q: Linux で「PortAudio」エラーが出る

**A:** PortAudio ライブラリをインストールしてください。

**Ubuntu/Debian：**
```bash
sudo apt install portaudio19-dev
```

**Fedora：**
```bash
sudo dnf install portaudio-devel
```

### Q: macOS で BlackHole のインストール後、音声が出ない

**A:** 以下の手順で複合デバイスを作成してください：

1. Audio MIDI 設定を開く
2. 左下の「+」ボタンから「複合デバイスを作成」
3. BlackHole と Mac の組み込みオーディオを両方有効にする
4. Voice Bridge の「入力デバイス」で複合デバイスを選択

詳しくは [BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md) をご覧ください。

## 翻訳モード

### Q: 翻訳が正確でない

**A:** 以下を試してください：

1. **ASR エンジンを変更する**
   - Moonshine から Whisper へ変更（精度向上）
   ```bash
   python main.py --asr whisper --model medium
   ```

2. **言語設定を確認する**
   - 「会話言語」がソース言語に正しく設定されているか確認

3. **音声認識の精度を上げる**
   - マイクの近くで話す
   - バックグラウンドノイズを減らす

### Q: 音声がキャプチャできない

**A:** 以下を確認してください：

**Windows：**
- 出力デバイスが Loopback デバイスに設定されているか
- Stereo Mix が有効になっているか（サウンド設定で確認）

**macOS：**
- BlackHole 2ch がインストールされているか
- 複合デバイスが正しく設定されているか
- 出力デバイスが複合デバイスに設定されているか

**Linux：**
```bash
# モニターデバイスを確認
python main.py --list-devices

# 「Monitor of ...」があれば利用可能
# ない場合は PulseAudio/PipeWire の設定を確認
```

### Q: Moonshine で日本語が認識されない

**A:** Moonshine は英語に特化しているため、日本語の精度が低いです。

**対処：**
```bash
# Whisper に変更（推奨）
python main.py --asr whisper --source-lang ja --target-lang en
```

## チャットモード

### Q: AI が応答しない

**A:** 以下を確認してください：

1. **Ollama が起動しているか**
   ```bash
   ollama serve
   ```

2. **LLM モデルがダウンロードされているか**
   ```bash
   ollama list
   # gemma-2-9b-it など、何か表示されるか確認
   ```

3. **ネットワーク接続を確認**
   ```bash
   curl http://localhost:11434/api/version
   # 応答があるか確認
   ```

4. **GUI の「LLM」ドロップダウンにモデルが表示されているか**
   - 表示されていない場合、Ollama を再起動

### Q: 日本語の応答精度が低い

**A:** LLM モデルを変更してください。

**おすすめ：**
```bash
ollama pull gemma-2-9b-it
```

`.env` で指定：
```env
AI_MODEL=gemma-2-9b-it
```

または GUI で「LLM」ドロップダウンから選択

### Q: メモリ不足で動作しない

**A:** 以下を試してください：

1. **より軽量なモデルに変更**
   ```bash
   ollama pull qwen2.5-7b-instruct  # ~5GB
   ```

2. **ASR モデルを軽量化**
   ```bash
   python main.py --model tiny
   ```

3. **Moonshine で高速化**
   ```bash
   python main.py --mode chat --asr moonshine --chunk 2.0
   ```

4. **他のアプリケーションを終了**
   - Chrome、IDE など、メモリを大量消費するアプリを終了

### Q: 応答が遅い

**A:** 以下の最適化を試してください：

**優先度順：**

1. **VAD を有効化**
   ```bash
   python main.py --mode chat --vad
   ```
   発話検出を高速化

2. **ASR モデルを軽量化**
   ```bash
   python main.py --model tiny
   ```

3. **Moonshine + チャンクサイズ調整**
   ```bash
   python main.py --mode chat --asr moonshine --chunk 2.0 --vad
   ```

4. **GPU を活用**
   - NVIDIA GPU 搭載の場合、CUDA でも実行（Ollama が自動検出）

### Q: マイクが入力レベルを拾わない

**A:** OS ごとの対処方法：

**macOS：**
- サウンド出力が複合デバイスになっているか確認

**Windows：**
```bash
python main.py --list-devices
# Loopback デバイスの入力を確認
```

**Linux：**
- PulseAudio でモニターモジュールが読み込まれているか確認
```bash
pactl list modules | grep loopback
```

## 音声合成（TTS）

### Q: CoeiroInk が検出されない

**A:** 以下を確認してください：

1. **CoeiroInk アプリが起動しているか**
   - CoeiroInk Desktop を起動しているか確認

2. **ポート番号が正しいか**
   ```bash
   curl http://localhost:50031/version
   # デフォルトポート: 50031
   # 別ポートの場合: curl http://localhost:ポート番号/version
   ```

3. **.env で正しいポートを指定**
   ```env
   COEIROINK_HOST=http://localhost:50031
   ```

### Q: CoeiroInk ポート番号が違う

**A:** CoeiroInk 起動時の表示でポート番号を確認し、`.env` で指定してください。

```env
# ポート 50021 の場合
COEIROINK_HOST=http://localhost:50021

# ポート 8000 の場合
COEIROINK_HOST=http://localhost:8000
```

または CLI で指定：
```bash
export COEIROINK_HOST=http://localhost:50021
python main.py --mode chat --vad --coeiroink
```

### Q: VOICEVOX が検出されない

**A:** 以下を確認してください：

1. **VOICEVOX アプリが起動しているか**
   - VOICEVOX を起動しているか確認

2. **GUI でエンジンを選択し直す**
   - 「声」ドロップダウンを開き直すと検出される場合がある

VOICEVOX が起動していない場合、Edge TTS に自動フォールバックします。

### Q: Edge TTS が遅い

**A:** 以下の方法で高速化できます：

1. **CoeiroInk または VOICEVOX を起動**
   - Edge TTS よりローカルエンジンの方が高速

2. **ネットワーク接続を確認**
   - Edge TTS はオンライン接続が必要です

## パフォーマンス

### Q: 低遅延で実行するにはどうすればいい？

**A:** 以下の設定を推奨します：

**チャットモード：**
```bash
python main.py \
  --mode chat \
  --vad \
  --asr moonshine \
  --chunk 2.0 \
  --model tiny \
  --coeiroink
```

または `.env` で設定：
```env
AI_MODEL=qwen2.5-7b-instruct  # 軽量モデル
```

### Q: 高精度で実行するにはどうすればいい？

**A:** 以下の設定を推奨します：

```bash
python main.py \
  --mode chat \
  --vad \
  --asr whisper \
  --model medium \
  --voicevox
```

`.env` で LLM を指定：
```env
AI_MODEL=qwen2.5-14b-instruct  # 高精度モデル
```

## その他

### Q: ファイルから音声を読み込める？

**A:** はい、`--file` オプションで指定できます：

```bash
python main.py --file input.wav
```

### Q: CLI モード（GUI なし）で実行できる？

**A:** はい、`--cli` オプションで実行できます：

```bash
python main.py --mode chat --vad --cli
```

### Q: トラブルシューティング情報はどこにある？

**A:** 以下のドキュメントをご覧ください：

- [macOS BlackHole トラブルシューティング](./BLACKHOLE_TROUBLESHOOTING.md)
- [Linux トラブルシューティング](./LINUX_TROUBLESHOOTING.md)
- [システムアーキテクチャ](../reference/ARCHITECTURE.md)

### Q: バグを報告したい・機能をリクエストしたい

**A:** GitHub Issues で報告してください：

[Voice Bridge Issues](https://github.com/zephel01/voice-bridge/issues)

報告時は以下の情報を含めると助かります：

- OS（macOS/Windows/Linux）とバージョン
- Python バージョン
- エラーメッセージの全文
- 再現手順

### Q: ライセンスは何ですか？

**A:** Voice Bridge は MIT License で公開されています。

商用利用も可能です。詳しくは [LICENSE](../../LICENSE) をご覧ください。
