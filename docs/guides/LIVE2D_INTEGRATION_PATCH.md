# main.py への Live2D 統合パッチ

voice-bridge の既存 TTS → pygame 再生フローを壊さず、
`--live2d` フラグ指定時のみ Electron フロントへ mp3 を転送する
最小差分パッチ例です。

## 方針

- pygame の `AudioPlayer` は従来どおり使う（Live2D 無効時の既定）
- `--live2d` フラグが指定されたときは、`VoiceBridge.__init__` で
  `Live2DBridge` を起動し、TTS 生成後の `enqueue()` の前にフロントへ送信
- フロント側の再生完了を待ってから次へ進めたい場合は
  `wait_playback_end()` を使う（最初は待たずでもOK）

## 1) requirements の追加

```txt
# requirements.txt
websockets>=12.0
```

## 2) 引数追加 (main.py, argparse 付近)

```python
parser.add_argument(
    "--live2d",
    action="store_true",
    help="Live2D フロント (live2d-ui/) へ TTS を転送するモード",
)
parser.add_argument(
    "--live2d-host", default="127.0.0.1",
    help="Live2D ブリッジの待受ホスト",
)
parser.add_argument(
    "--live2d-port", type=int, default=8765,
    help="Live2D ブリッジの待受ポート",
)
```

渡す側:

```python
bridge = VoiceBridge(
    ...
    live2d_enabled=args.live2d,
    live2d_host=args.live2d_host,
    live2d_port=args.live2d_port,
)
```

## 3) VoiceBridge.__init__ へ追加

```python
from live2d_bridge import Live2DBridge, infer_emotion

class VoiceBridge:
    def __init__(self, ..., live2d_enabled=False, live2d_host="127.0.0.1", live2d_port=8765):
        ...
        self.live2d: Live2DBridge | None = None
        if live2d_enabled:
            self.live2d = Live2DBridge(host=live2d_host, port=live2d_port)
            self.live2d.start()
            print("[VoiceBridge] Live2D ブリッジを起動しました (ws://"
                  f"{live2d_host}:{live2d_port})")
```

## 4) TTS 生成 → エンキュー箇所にフック

既存の `_synthesize_and_enqueue` (main.py:643 付近) を以下に差し替え:

```python
def _synthesize_and_enqueue(self, text: str, index: int):
    audio_path = self.tts.synthesize(text)
    if not audio_path:
        return

    # Live2D モード: フロントで再生するので pygame enqueue はスキップ
    if self.live2d and self.live2d.has_client():
        emotion, intensity = infer_emotion(text)
        pid = self.live2d.send_tts(audio_path, text=text,
                                   emotion=emotion, intensity=intensity)
        # フロントで再生するため pygame 側は呼ばない。
        # 再生終了を同期的に待ちたい場合（順次再生保証）:
        if pid:
            self.live2d.wait_playback_end(pid, timeout=30.0)
        # 元の mp3 ファイルを削除（pygame が削除してくれない経路のため）
        try:
            import os
            os.remove(audio_path)
        except OSError:
            pass
        return

    # 通常モード: 従来どおり pygame で再生
    self.player.enqueue(audio_path)
```

同じく `_synthesize_and_enqueue` を使わず直接 `self.player.enqueue()` を呼んでいる
箇所 (例: 下記) は同じロジックでラップします。

- main.py:379 付近: `self.player.enqueue(audio_path)` （翻訳モード）
- main.py:690 付近: `self.player.enqueue(audio_path)` （チャット応答）
- main.py:770 付近: `self.player.enqueue(audio_path)` （非ストリーミング応答）

ラップ関数を 1 つ作ると楽です:

```python
def _play_or_forward(self, audio_path: str, text: str = ""):
    if not audio_path:
        return
    if self.live2d and self.live2d.has_client():
        emotion, intensity = infer_emotion(text)
        pid = self.live2d.send_tts(audio_path, text=text,
                                   emotion=emotion, intensity=intensity)
        if pid:
            self.live2d.wait_playback_end(pid, timeout=30.0)
        try:
            import os; os.remove(audio_path)
        except OSError:
            pass
        return
    self.player.enqueue(audio_path)
```

そして 3 箇所の `self.player.enqueue(audio_path)` を
`self._play_or_forward(audio_path, text=translated_text)` 等に置換します。

## 5) シャットダウン時

```python
def stop(self):
    ...
    if self.live2d:
        self.live2d.stop()
```

## 動作確認手順

1. `pip install websockets`
2. `cd live2d-ui && npm install && npm start`（Electron 起動）
3. 別ターミナルで `python main.py --mode chat --vad --live2d`
4. フロント右上のステータスが `Connected` になったら喋らせる

## トラブルシュート

- フロントに何も届かない: `has_client()` が False のまま
  → Electron を先に立ち上げ、右上バッジが `Connected` になってから TTS
- 口が動かない: `mouthParamId` がモデルに合っていない
  → `live2d-ui/src/App.tsx` の `Live2DAvatar` の `mouthParamId` をモデルの
    実際のパラメータ ID に変更 (`ParamMouthOpenY` or `PARAM_MOUTH_OPEN_Y`)
- 表情が変わらない: モデル側の `ParamMouthForm` 等が無い
  → `emotionMap.ts` でモデルのパラメータ ID に書き換え
- 音声が 2 重に鳴る: `--live2d` なのに pygame が再生している
  → `_play_or_forward` への差し替え漏れの可能性。Grep で
    `self.player.enqueue` を全て確認。
