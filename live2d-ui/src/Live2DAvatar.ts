/**
 * Live2DAvatar
 *
 * pixi-live2d-display を使って Cubism 4/5 モデルを読み込み、
 *  - 口パク (lipSync, 外部音量入力)
 *  - 自動まばたき (AutoBlink)
 *  - 呼吸 (AutoBreath)
 *  - 感情プリセットによるパラメータ補間
 *  - 指定した Web Audio の AnalyserNode と連動した口の開き
 * を提供する軽量ラッパ。
 *
 * pixi-live2d-display は内部で Cubism Core (cubismcore.min.js) が
 * グローバルに読み込まれている前提。index.html で <script> 読み込みする。
 */

import * as PIXI from "pixi.js";
// Cubism 4/5 モデル専用エントリ (pixi-live2d-display v0.4.0+)
// Haru (haru_greeter_t05) は Cubism 5 (Cubism 4 API 互換)
import { Live2DModel } from "pixi-live2d-display/cubism4";
import { EMOTION_PRESETS, type Emotion, type EmotionPose } from "./emotionMap";

// pixi-live2d-display に必要な Ticker 登録 (モジュール読み込み時に1度)
try {
  Live2DModel.registerTicker(PIXI.Ticker);
} catch (e) {
  console.warn("[Live2DAvatar] Ticker 登録に失敗:", e);
}

export interface Live2DAvatarOptions {
  canvas: HTMLCanvasElement;
  modelUrl: string;            // model3.json への URL
  mouthParamId?: string;       // 既定: ParamMouthOpenY
  lipSyncGain?: number;        // 0.0 〜 3.0 くらいで調整
  scale?: number;              // 0.0 〜 1.0 くらい
  backgroundAlpha?: number;    // 0 = 透明
}

interface TransitionState {
  from: number;
  to: number;
  startMs: number;
  durationMs: number;
}

export class Live2DAvatar {
  private app: PIXI.Application;
  private model: Live2DModel | null = null;

  private mouthParamId: string;
  private lipSyncGain: number;

  // Web Audio
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private analyserBuffer: Uint8Array | null = null;
  private currentAudio: HTMLAudioElement | null = null;
  private currentSourceNode: MediaElementAudioSourceNode | null = null;

  // 感情トランジション
  private transitions = new Map<string, TransitionState>();
  private currentEmotion: Emotion = "neutral";

  // アイドルアニメ有効フラグ
  private idleEnabled = true;

  // 口の平滑化
  private smoothedMouth = 0;

  // window の resize リスナー参照（destroy() で確実に解除するため保持）
  private onResize: (() => void) | null = null;

  constructor(private opts: Live2DAvatarOptions) {
    this.mouthParamId = opts.mouthParamId ?? "ParamMouthOpenY";
    this.lipSyncGain = opts.lipSyncGain ?? 1.6;

    const parent = opts.canvas.parentElement;
    // canvas が 0x0 だと WebGL コンテキスト生成が失敗し
    // "Invalid value of 0 passed to checkMaxIfStatementsInShader" となる。
    // PIXI に渡す前に確実に非ゼロサイズをセットしておく。
    const initW = Math.max(parent?.clientWidth || 0, 520);
    const initH = Math.max(parent?.clientHeight || 0, 760);
    opts.canvas.width = initW;
    opts.canvas.height = initH;
    opts.canvas.style.width = `${initW}px`;
    opts.canvas.style.height = `${initH}px`;

    this.app = new PIXI.Application({
      view: opts.canvas,
      width: initW,
      height: initH,
      resizeTo: parent ?? undefined,
      autoStart: true,
      antialias: true,
      backgroundAlpha: opts.backgroundAlpha ?? 0,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
    });

    if (!this.app.renderer) {
      throw new Error(
        "PIXI renderer が初期化できませんでした。WebGL が使えるか確認してください。",
      );
    }
  }

  /** モデルをロードしてステージに配置 */
  async load(): Promise<void> {
    console.log("[Live2D] load() start:", this.opts.modelUrl);

    this.model = await Live2DModel.from(this.opts.modelUrl, {
      autoInteract: false,
      // 初回の詰まりを避けるため、起動時はモーションをプリロードしない
      motionPreload: "NONE" as unknown as undefined,
      // 内部エラーの可視化
      onError: (e: unknown) => console.error("[Live2D inner error]", e),
    });
    console.log("[Live2D] from() done", {
      width: (this.model as unknown as { width?: number }).width,
      height: (this.model as unknown as { height?: number }).height,
      internalModel: !!(this.model as unknown as { internalModel?: unknown })
        .internalModel,
    });

    // 先に stage に追加して、1フレーム描画させてから bounds を測る
    this.app.stage.addChild(this.model);

    const applyLayout = () => {
      if (!this.model) return;
      // renderer.screen はCSSピクセル単位で統一されているので autoDensity と相性が良い
      const stageW = this.app.renderer.screen.width || 520;
      const stageH = this.app.renderer.screen.height || 760;

      // まずスケール 1.0 にして、getBounds() で実際の描画範囲（キャラ本体）を測る。
      // Live2DModel の width/height はキャンバスサイズ (Haru=2400x4500) を返すが、
      // 実際のキャラクターはその 25% くらいしか占めていない。
      this.model.scale.set(1.0);
      this.model.anchor.set(0.5, 1.0);
      this.model.position.set(stageW / 2, stageH - 10);
      // update() で drawables のバウンディングを更新させる
      try {
        (this.model as any).update?.(16);
      } catch {}

      // Live2DModel は PIXI.Container 継承なので getBounds() が使える
      let measuredW = 0;
      let measuredH = 0;
      try {
        const b = this.model.getBounds();
        if (b && b.width > 0 && b.height > 0) {
          measuredW = b.width;
          measuredH = b.height;
        }
      } catch (e) {
        console.warn("[Live2D] getBounds() 失敗:", e);
      }

      const internalModel: any = (this.model as any).internalModel;
      const canvasW =
        internalModel?.originalWidth ??
        (this.model as unknown as { width?: number }).width ??
        2400;
      const canvasH =
        internalModel?.originalHeight ??
        (this.model as unknown as { height?: number }).height ??
        4500;

      // getBounds() がキャンバス全体を返したり、うまく測れていない場合は
      // 「キャラクター本体はキャンバスの約 30% 程度を占める」という経験則を適用
      const CHARACTER_FILL_RATIO = 0.3;
      if (measuredH <= 0 || measuredH >= canvasH * 0.85) {
        measuredW = canvasW * CHARACTER_FILL_RATIO;
        measuredH = canvasH * CHARACTER_FILL_RATIO;
      }

      // ウィンドウ内にフィットする最大スケール（幅・高さどちらもはみ出さない）。
      const fitScale = Math.min(stageW / measuredW, stageH / measuredH);
      const desiredScale = (this.opts.scale ?? 0.9) * fitScale;
      this.model.scale.set(desiredScale);

      // 足元基準で再配置
      this.model.anchor.set(0.5, 1.0);
      this.model.position.set(stageW / 2, stageH - 10);

      console.log("[Live2D] layout", {
        stageW,
        stageH,
        canvasW,
        canvasH,
        measuredW,
        measuredH,
        fitScale,
        desiredScale,
      });
    };
    applyLayout();

    // リサイズ対応（ウィンドウサイズ変更時も再配置）
    // ハンドラをフィールドに保持し、destroy() で確実に removeEventListener できるようにする。
    this.onResize = () => applyLayout();
    window.addEventListener("resize", this.onResize);

    // 毎フレーム処理: 感情補間 + 口パク + アイドル補助
    this.app.ticker.add(this._tick);
  }

  /** 感情プリセットを設定（transitionMs 掛けて補間） */
  setEmotion(emotion: Emotion, intensity = 1.0): void {
    const preset: EmotionPose =
      EMOTION_PRESETS[emotion] ?? EMOTION_PRESETS.neutral;
    this.currentEmotion = emotion;

    const now = performance.now();
    for (const [paramId, target] of Object.entries(preset.params)) {
      const current = this._readParam(paramId) ?? 0;
      this.transitions.set(paramId, {
        from: current,
        to: target * intensity,
        startMs: now,
        durationMs: preset.transitionMs,
      });
    }
  }

  getCurrentEmotion(): Emotion {
    return this.currentEmotion;
  }

  /** アイドル（呼吸/まばたき）の有効切替 */
  setIdleEnabled(enabled: boolean): void {
    this.idleEnabled = enabled;
  }

  /**
   * 音声再生 + 口パク同期を開始する。
   *   - HTMLAudioElement を AudioContext に接続し、
   *     AnalyserNode で音量を取り出して mouthParam に反映する。
   *   - 再生終了時に onEnded が呼ばれる。
   */
  async playAudio(audioDataUrl: string, onEnded?: () => void): Promise<void> {
    this._stopAudio();

    const ctx =
      this.audioCtx ??
      new (window.AudioContext || (window as any).webkitAudioContext)();
    this.audioCtx = ctx;
    if (ctx.state === "suspended") await ctx.resume();

    const audio = new Audio(audioDataUrl);
    audio.crossOrigin = "anonymous";
    audio.preload = "auto";

    const source = ctx.createMediaElementSource(audio);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.4;
    source.connect(analyser);
    analyser.connect(ctx.destination);

    this.analyser = analyser;
    this.analyserBuffer = new Uint8Array(analyser.fftSize);
    this.currentAudio = audio;
    this.currentSourceNode = source;

    const finish = () => {
      this._stopAudio();
      onEnded?.();
    };
    audio.addEventListener("ended", finish, { once: true });
    audio.addEventListener("error", finish, { once: true });

    try {
      await audio.play();
    } catch (e) {
      console.warn("[Live2DAvatar] 再生失敗:", e);
      finish();
    }
  }

  private _stopAudio(): void {
    try {
      this.currentAudio?.pause();
    } catch {}
    try {
      this.currentSourceNode?.disconnect();
    } catch {}
    try {
      this.analyser?.disconnect();
    } catch {}
    this.currentAudio = null;
    this.currentSourceNode = null;
    this.analyser = null;
    this.analyserBuffer = null;
    this.smoothedMouth = 0;
  }

  /** 外部から単発で表情だけ戻したい時のヘルパー */
  resetToNeutral(): void {
    this.setEmotion("neutral", 1.0);
  }

  /** 終了処理 */
  destroy(): void {
    this._stopAudio();
    this.audioCtx?.close().catch(() => {});
    this.app.ticker.remove(this._tick);
    if (this.onResize) {
      window.removeEventListener("resize", this.onResize);
      this.onResize = null;
    }
    if (this.model) {
      this.app.stage.removeChild(this.model);
      this.model.destroy({ children: true });
      this.model = null;
    }
    this.app.destroy(true, { children: true });
  }

  // -------------------------------------------------------------- internal

  private _tick = (): void => {
    if (!this.model) return;

    const now = performance.now();

    // 感情パラメータ補間
    if (this.transitions.size > 0) {
      const done: string[] = [];
      for (const [paramId, st] of this.transitions) {
        const t = Math.min(1, (now - st.startMs) / st.durationMs);
        const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        const v = st.from + (st.to - st.from) * eased;
        this._writeParam(paramId, v, 1.0);
        if (t >= 1) done.push(paramId);
      }
      for (const p of done) this.transitions.delete(p);
    }

    // 口パク: AnalyserNode → RMS
    if (this.analyser && this.analyserBuffer) {
      this.analyser.getByteTimeDomainData(this.analyserBuffer);
      let sum = 0;
      for (let i = 0; i < this.analyserBuffer.length; i++) {
        const v = (this.analyserBuffer[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / this.analyserBuffer.length);
      const target = Math.min(1.0, rms * this.lipSyncGain * 2.2);

      // 平滑化（口が震えないように）
      this.smoothedMouth = this.smoothedMouth * 0.6 + target * 0.4;
      this._writeParam(this.mouthParamId, this.smoothedMouth, 0.9);
    } else {
      // 音声なしの時はゆっくり口を閉じる
      this.smoothedMouth *= 0.85;
      if (this.smoothedMouth > 0.01) {
        this._writeParam(this.mouthParamId, this.smoothedMouth, 0.9);
      }
    }

    // アイドル: Cubism 標準の AutoBlink / Breath は internalModel に組み込み済み。
    // 無効化要求が来た時だけ切り替える。
    if (!this.idleEnabled) {
      // 目を強制的に開いたままにする（待機しないモード）
      this._writeParam("ParamEyeLOpen", 1.0, 0.3);
      this._writeParam("ParamEyeROpen", 1.0, 0.3);
    }
  };

  private _writeParam(id: string, value: number, weight = 1.0): void {
    try {
      const core: any = (this.model as any)?.internalModel?.coreModel;
      core?.setParameterValueById?.(id, value, weight);
    } catch {
      /* パラメータが存在しないモデルでは無視 */
    }
  }

  private _readParam(id: string): number | null {
    try {
      const core: any = (this.model as any)?.internalModel?.coreModel;
      return core?.getParameterValueById?.(id) ?? null;
    } catch {
      return null;
    }
  }
}
