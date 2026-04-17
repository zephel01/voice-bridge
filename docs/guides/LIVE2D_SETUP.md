# Live2D 統合セットアップガイド

voice-bridge に Live2D キャラクター表示 + 口パク + まばたき + 感情連動を
追加するためのセットアップ手順です。

## アーキテクチャ

```
┌───────────────────────── voice-bridge (Python) ──────────────────────────┐
│  ASR / LLM / Translator / TTS (edge-tts / VOICEVOX / CoeiroInk)          │
│                              │                                             │
│                              ▼                                             │
│                        mp3 ファイル生成                                      │
│                              │                                             │
│      ┌───────────┬──────────┴──────────┬──────────┐                        │
│      ▼           ▼                     ▼          ▼                        │
│  (従来)      Live2DBridge          infer_emotion                           │
│ pygame 再生   WebSocket(8765)       → emotion tag                          │
└───────────────────┬──────────────────────────────────────────────────────┘
                    │ ws://127.0.0.1:8765
                    ▼
┌────────── live2d-ui (Electron + React + TypeScript) ──────────┐
│   pixi-live2d-display で Cubism 4/5 モデルを表示                  │
│   ├ Web Audio で mp3 再生 + AnalyserNode → lip sync            │
│   ├ AutoBlink / AutoBreath (Cubism 標準)                        │
│   ├ emotionMap.ts: 感情プリセット → パラメータ補間                  │
│   └ 再生完了を WebSocket で Python に通知                          │
└────────────────────────────────────────────────────────────────┘
```

**ポイント**: mp3 を Python → Electron に転送して、フロント側で再生しつつ
`AnalyserNode` でリアルタイム音量を取り出して口パクに反映するため、
音と口の動きがずれません。

## 1. Live2D Cubism SDK for Web のダウンロード

1. https://www.live2d.com/sdk/download/web/ から Cubism 5 SDK for Web を DL
2. 解凍したフォルダから `Core/live2dcubismcore.min.js` を
   `live2d-ui/public/live2dcubismcore.min.js` にコピー

## 2. Live2D モデルの配置

サンプルモデル（公式の Haru / Hiyori 等、または ずんだもん / リリンちゃん等）を
`live2d-ui/public/live2d/<name>/` に展開します。

例:
```
live2d-ui/public/live2d/
  sample/
    sample.model3.json
    sample.moc3
    sample.physics3.json
    textures/
      texture_00.png
    motions/*.motion3.json
```

既定では `/live2d/sample/sample.model3.json` が読まれます。
他の場所にする場合は `live2d-ui/src/App.tsx` の `DEFAULT_MODEL_URL` を変更するか、
Electron 起動時の URL に `?model=/live2d/your-model/xxx.model3.json` を付けます。

## 3. Python 側の依存追加

```bash
cd voice-bridge
source .venv/bin/activate   # Windows は .venv\Scripts\activate
pip install websockets
```

（`requirements.txt` にも `websockets>=12.0` を追記すると再現性が上がります）

## 4. Electron UI のセットアップ

```bash
cd voice-bridge/live2d-ui
npm install
```

初回のみ `npm install` で数分かかります。

## 5. main.py のパッチ

`docs/guides/LIVE2D_INTEGRATION_PATCH.md` の手順に従って
`main.py` へ `--live2d` フラグと `_play_or_forward` ラッパーを追加します。

## 6. 起動

### ターミナル A: Electron UI
```bash
cd voice-bridge/live2d-ui
npm start
```
右上のステータスバッジが **灰 (Connecting)** → **緑 (Connected)** になるまで待ちます。

### ターミナル B: voice-bridge
```bash
cd voice-bridge
source .venv/bin/activate
python main.py --mode chat --vad --live2d
```

マイクに話しかけると、Electron ウィンドウのキャラクターが口を動かして喋ります。

## 口パク・表情の調整

### 口パクが動かない / 弱すぎ・強すぎ

モデルによって口のパラメータ名や感度が違います。
`live2d-ui/src/App.tsx` の Live2DAvatar 初期化部分で調整:

```ts
new Live2DAvatar({
  canvas: canvasRef.current,
  modelUrl,
  mouthParamId: "ParamMouthOpenY",  // ← モデルに合わせて
  lipSyncGain: 1.6,                  // ← 大きいほど口が動く
  scale: 0.28,
});
```

よくある ID: `ParamMouthOpenY`, `PARAM_MOUTH_OPEN_Y`

### 感情パラメータの調整

`live2d-ui/src/emotionMap.ts` を直接編集します。
各感情の `params` マップのキー（パラメータ ID）をモデル側に合わせ、
値は -1.0 〜 1.0 の範囲で増減させるとキャラがキビキビ変わります。

### モデルのパラメータ ID を確認する方法

Electron の DevTools (npm start なら自動で開きます) のコンソールで:

```js
// Pixi ステージに載ってる Live2D モデル経由で
const m = document.querySelector("canvas")?.__pixi?.stage?.children?.[0]
            ?.internalModel?.coreModel;
// パラメータ ID 一覧
for (let i = 0; i < m.getParameterCount(); i++) console.log(m.getParameterId(i));
```

実装詳細によっては上記で取れない場合があります。その場合は
`live2d-ui/src/Live2DAvatar.ts` の `_tick` 内で `core.getParameterCount()` を
ログに流すコードを一時的に足すと確実です。

## チェックリスト

- [ ] `public/live2dcubismcore.min.js` が配置されている
- [ ] `public/live2d/sample/sample.model3.json` が存在する
- [ ] `pip install websockets` 完了
- [ ] `cd live2d-ui && npm install` 完了
- [ ] `main.py` に `--live2d` フラグを追加済み
- [ ] Electron 起動後、右上バッジが **Connected** になる
- [ ] 発話すると口が動く
- [ ] 感情プリセットで表情が変わる

## 参考

- Live2D Cubism SDK for Web:
  https://docs.live2d.com/en/cubism-sdk-manual/sdk-web/
- pixi-live2d-display:
  https://github.com/guansss/pixi-live2d-display
- voice-bridge × Live2D パッチ詳細:
  [LIVE2D_INTEGRATION_PATCH.md](./LIVE2D_INTEGRATION_PATCH.md)
