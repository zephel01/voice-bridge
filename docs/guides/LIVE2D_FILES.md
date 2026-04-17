# Live2D ファイル・フォルダ構成ガイド

voice-bridge の Live2D 連携に必要なファイルと、それを `live2d-ui/public/` 配下に
どう配置するかの完全リファレンス。

新しいモデルを追加したい、何のファイルが必須なのかを確認したい、PSD やワークファイルは
どこに置くべきか迷っている、といったときに参照するドキュメント。

全体セットアップ手順は [`LIVE2D_SETUP.md`](./LIVE2D_SETUP.md)、`main.py` への組み込み
詳細は [`LIVE2D_INTEGRATION_PATCH.md`](./LIVE2D_INTEGRATION_PATCH.md) を参照。

---

## 1. 全体のフォルダツリー

Live2D 関連でユーザーが触るのは基本的に `live2d-ui/public/` 配下だけ。Vite は
`public/` の中身を開発サーバ・ビルド後の `dist/` にそのまま `/...` として配信する。

```
voice-bridge/
├── main.py                          # --live2d フラグでブリッジ起動
├── live2d_bridge.py                 # WebSocket サーバ（Python 側）
└── live2d-ui/
    ├── public/                      # ← Live2D アセット配置場所（配信対象）
    │   ├── live2dcubismcore.min.js  # Cubism Core ランタイム（必須・1個）
    │   └── live2d/
    │       ├── README.md            # 配置についての簡易メモ
    │       └── <model_name>/        # モデル1体ごとに1フォルダ
    │           ├── runtime/         # ← pixi-live2d-display がロードする中身
    │           │   ├── *.model3.json
    │           │   ├── *.moc3
    │           │   ├── *.physics3.json
    │           │   ├── *.pose3.json
    │           │   ├── *.cdi3.json
    │           │   ├── <tex>.2048/
    │           │   │   ├── texture_00.png
    │           │   │   └── texture_01.png
    │           │   └── motion/
    │           │       └── *.motion3.json
    │           ├── <workfile>.cmo3  # Cubism Editor のワークファイル（任意）
    │           ├── <workfile>.can3  # アニメーションのワークファイル（任意）
    │           ├── *.psd            # 元絵（任意・サイズ大）
    │           └── ReadMe.txt       # 配布元の README（任意）
    ├── src/
    │   ├── Live2DAvatar.ts          # モデルの読み込み・口パク・感情補間
    │   ├── emotionMap.ts            # 感情プリセットのパラメータ定義
    │   └── App.tsx                  # DEFAULT_MODEL_URL を設定
    └── electron/
        └── main.ts                  # Electron のエントリ
```

---

## 2. 必須ファイル

### 2.1 Cubism Core ランタイム

Live2D モデルを実行するために必須のライブラリ。pixi-live2d-display は
**グローバルに `window.Live2DCubismCore` が読み込まれている前提** で動作する。

| 項目 | 値 |
| --- | --- |
| ファイル名 | `live2dcubismcore.min.js` |
| 配置先 | `live2d-ui/public/live2dcubismcore.min.js` |
| 入手元 | Live2D 公式 SDK for Web（ https://www.live2d.com/sdk/download/web/ ） |
| 入手先のパス | 解凍後 `CubismSdkForWeb-*/Core/live2dcubismcore.min.js` |
| 使い方 | `live2d-ui/index.html` から `<script src="/live2dcubismcore.min.js"></script>` で読み込む |

Cubism SDK は再配布条件があるため、**Git には入れず各人が DL して配置**する想定。
`live2d-ui/.gitignore` に入れておくと安全。

### 2.2 Live2D モデル本体

モデル1体につき `runtime/` フォルダに以下が揃っている必要がある。
（これは Cubism Editor の「組込み用ファイルの書き出し」で生成される標準構成）

| 拡張子 / 名称 | 必須 | 役割 |
| --- | --- | --- |
| `*.model3.json` | ✅ | モデルのエントリポイント。他ファイルへの参照を持つ |
| `*.moc3` | ✅ | メッシュ・デフォーマ等のバイナリ本体 |
| `*.<size>/texture_NN.png` | ✅ | テクスチャ画像（通常 1〜4 枚） |
| `*.physics3.json` | ⬜ 推奨 | 髪・胸・服など揺れ物の物理演算 |
| `*.pose3.json` | ⬜ | パーツの排他表示（例: 左右の目を切り替え） |
| `*.cdi3.json` | ⬜ | パラメータ・パーツの表示名（Editor 由来） |
| `motion/*.motion3.json` | ⬜ | モーションデータ（アイドル・感情モーション等） |
| `*.exp3.json` | ⬜ | 表情差分（`model3.json` 内の `Expressions` から参照） |
| `*.userdata3.json` | ⬜ | モーションに付随するイベントタグ等 |

`model3.json` のパス参照は**すべて `model3.json` からの相対パス**。
なので `runtime/` をどこに置こうが、`runtime/` 配下のファイル同士のパス関係が
壊れていなければ動く。

#### 最小構成の例

```
public/live2d/minimum/
└── runtime/
    ├── minimum.model3.json
    ├── minimum.moc3
    └── minimum.2048/
        └── texture_00.png
```

これでも表示はできるが、物理なし（髪が揺れない）・モーションなし（静止のまま）になる。

#### Haru（同梱済み）の実構成

```
public/live2d/haru/
├── runtime/
│   ├── haru_greeter_t05.model3.json
│   ├── haru_greeter_t05.moc3
│   ├── haru_greeter_t05.physics3.json
│   ├── haru_greeter_t05.pose3.json
│   ├── haru_greeter_t05.cdi3.json
│   ├── haru_greeter_t05.2048/
│   │   ├── texture_00.png
│   │   └── texture_01.png
│   └── motion/
│       ├── haru_g_idle.motion3.json
│       └── haru_g_m01.motion3.json 〜 m26.motion3.json
├── haru_greeter_t05.cmo3           # Cubism Editor ワークファイル（任意）
├── haru_greeter_t03.can3           # アニメーションワーク（任意）
├── haru_受付スーツ_*.psd            # 元絵（任意）
└── ReadMe.txt                      # 配布元 README（任意）
```

ポイント: **`pixi-live2d-display` が読み込むのは `runtime/` 配下のみ**。
外側の `.psd` / `.cmo3` / `.can3` はアプリ実行には不要。容量が大きいので、
配布時は `runtime/` だけ含めるか `.gitignore` で除外する。

---

## 3. モデル読み込み URL の決まり方

`App.tsx` で `modelUrl` を決めて `Live2DAvatar` に渡している。

```ts
// live2d-ui/src/App.tsx
const DEFAULT_MODEL_URL =
  "/live2d/haru/runtime/haru_greeter_t05.model3.json";
```

パスのルールは次のとおり。

- `/live2d/...` のルートは `live2d-ui/public/` を指す
- ファイル名は **必ず `model3.json`** のほう（`moc3` でも `cdi3` でもない）
- クエリで切替も可: `?model=/live2d/zundamon/runtime/zundamon.model3.json`

> **注意（macOS）**: macOS のファイルシステムは既定ではケースインセンシティブだが、
> 本番ビルドで配信される環境（Electron の file:// や Web サーバ）ではケース
> センシティブに扱われることがある。`Haru_Greeter` と `haru_greeter` を
> 取り違えないよう、フォルダ名・ファイル名の大文字小文字を揃えておくこと。

---

## 4. 新しいモデルを追加する手順

1. モデル一式（`runtime/` フォルダごと）を入手する。入手先の例:
   - Live2D 公式サンプル: https://www.live2d.com/download/sample-data/
     （Haru / Hiyori / Mao / Mark / Natori / Rice / Wanko など）
   - Nizima: https://nizima.com/ （有料モデルあり、ライセンス要確認）
   - 自作モデルは Cubism Editor から「組込み用ファイルの書き出し」で出力
2. `live2d-ui/public/live2d/<好きな名前>/` に置く。`runtime/` というサブフォルダは
   配布物に従う（Haru は `runtime/` 付き、モデルによっては直置きもある）。
3. `model3.json` のパスを `App.tsx` の `DEFAULT_MODEL_URL` に設定 **または**
   Electron 起動 URL にクエリで付ける。
4. モデルごとにパラメータ ID が違うので、口パク・表情が動かないときは次節の
   調整をする。

---

## 5. モデル別のパラメータ調整

Live2D のパラメータ ID はモデル作者の命名次第で変わる。voice-bridge が触るのは
主に以下。

| 役割 | Cubism 標準の ID 例 | Haru | 無償サンプル全般 |
| --- | --- | --- | --- |
| 口の開閉 | `ParamMouthOpenY` | `ParamMouthOpenY` | 同左が多い |
| 口の形 | `ParamMouthForm` | `ParamMouthForm` | |
| 目の開閉（左右） | `ParamEyeLOpen` / `ParamEyeROpen` | 同左 | |
| 笑み | `ParamEyeLSmile` / `ParamEyeRSmile` | 同左 | |
| 眉の角度 | `ParamBrowLAngle` / `ParamBrowRAngle` | 同左 | |
| 頬の赤み | （モデル依存） | `ParamTere` | `ParamCheek` が多い |
| 涙 | （モデル依存） | `ParamTear` | |
| 体の上下（呼吸） | `ParamBreath` | 同左 | |

voice-bridge 側での設定場所:

- **口パクの感度**: `src/Live2DAvatar.ts` 初期化時の `lipSyncGain`（既定 1.6）
- **口パクのパラメータ名**: 同上 `mouthParamId`（既定 `"ParamMouthOpenY"`）
- **感情プリセット**: `src/emotionMap.ts` の `EMOTION_PRESETS` マップ

パラメータ ID を確認するには DevTools コンソールで:

```js
const m = document.querySelector("canvas")?.__pixi?.stage?.children?.[0]
            ?.internalModel?.coreModel;
for (let i = 0; i < m.getParameterCount(); i++)
  console.log(m.getParameterId(i));
```

---

## 6. Cubism 2 と Cubism 4/5 の違い

pixi-live2d-display は Cubism 2 (`.moc`) と Cubism 4/5 (`.moc3`) の両方に対応
しているが、**import するエントリが違う**。

| バージョン | 拡張子 | import 文 |
| --- | --- | --- |
| Cubism 2 | `.moc` + `model.json`（末尾に3なし） | `import { Live2DModel } from "pixi-live2d-display/cubism2"` |
| Cubism 4 / 5 | `.moc3` + `.model3.json` | `import { Live2DModel } from "pixi-live2d-display/cubism4"` |

voice-bridge は Cubism 4/5 を前提にしている（`Live2DAvatar.ts` は `/cubism4` を import）。
Cubism 2 モデルを混在させたい場合は両方 import する必要がある。

Haru は配布形式 `haru_greeter_t05.moc3` = Cubism 5 SDK 付属の Cubism 4 API 互換なので、
`/cubism4` エントリでそのまま動く。

---

## 7. .gitignore 推奨設定

モデルファイルはサイズが大きく、かつ Live2D サンプルは再配布条件がある。
リポジトリに含めない運用が無難。

`live2d-ui/.gitignore` に追加推奨:

```gitignore
# Live2D Cubism Core（各人が SDK から DL）
public/live2dcubismcore.min.js

# Live2D モデル本体（容量大・ライセンス要確認）
public/live2d/*/
!public/live2d/README.md
```

必ず含めたいモデルだけネガテーションで許可する例:

```gitignore
public/live2d/*/
!public/live2d/README.md
!public/live2d/sample/
!public/live2d/sample/**
```

---

## 8. トラブルシュート（ファイル配置まわり）

### 「モデルをロードしようとすると 404」

- ブラウザ DevTools の Network タブで 404 になっているファイル名を確認
- 大文字小文字を実ファイルと揃える（特に macOS → Electron 配信時のケース差）
- `model3.json` を開いて `FileReferences` のパスを見て、全ファイルが同階層に
  存在するか確かめる

### 「真っ黒なキャンバスが出るだけでモデルが見えない」

- `live2dcubismcore.min.js` が `public/` 直下に置かれているか
- `index.html` の `<script src="/live2dcubismcore.min.js">` が壊れていないか
- DevTools Console に `Live2D Cubism Core version: ...` が出ているか
- モデルが大きすぎて画面外にいる可能性もある。`Live2DAvatar.ts` の `applyLayout`
  のログ（`[Live2D] layout { ... }`）で `desiredScale` をチェック

### 「ロードは通るのに口が動かない・表情が変わらない」

- モデルのパラメータ ID を DevTools で確認（本ドキュメント §5 参照）
- `emotionMap.ts` のキーが一致しているか
- `lipSyncGain` を 2.0〜3.0 に上げて様子を見る

---

## 9. 公開サンプルモデル早見表

Live2D 公式の無償サンプル（商用可・条件付き）：

| 名前 | 年齢層・雰囲気 | 特徴 |
| --- | --- | --- |
| Haru | 女性・受付スーツ | 本プロジェクトで使用中。全身 |
| Hiyori | 女性・制服 | 定番。上半身 |
| Mao | 女性・ポップ | カラフル |
| Mark | 男性 | 上半身の男性モデル |
| Natori | 男性・スーツ | 上半身のビジネスマン |
| Rice | 女児 | 幼めキャラ |
| Wanko | 犬（獣人） | マスコット系 |

ライセンス: 個人利用は無償、商用は別途ライセンス契約が必要。
必ず同梱の利用規約を確認すること。

---

## 10. まとめ

- 必須は **`live2dcubismcore.min.js` 1個** と **モデルの `runtime/` フォルダ**
- `public/live2d/<name>/runtime/*.model3.json` を `App.tsx` で指定するだけで動く
- PSD / cmo3 / can3 はアプリ実行には不要
- モデルごとにパラメータ ID が違うので、動かないときは DevTools で確認 →
  `emotionMap.ts` と `Live2DAvatar.ts` を調整

関連ドキュメント:

- 全体セットアップ: [`LIVE2D_SETUP.md`](./LIVE2D_SETUP.md)
- `main.py` パッチ詳細: [`LIVE2D_INTEGRATION_PATCH.md`](./LIVE2D_INTEGRATION_PATCH.md)
- アーキテクチャ全体: [`MODES_OVERVIEW.md`](./MODES_OVERVIEW.md)
