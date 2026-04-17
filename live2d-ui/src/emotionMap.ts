/**
 * 感情 → Live2D パラメータマッピング
 *
 * パラメータ ID はモデルによって異なるため、手元のモデルに合わせて
 * 値を調整してください。代表的な Cubism 標準パラメータを既定値にしています。
 *
 * - ParamEyeLSmile / ParamEyeRSmile : 目元の笑い
 * - ParamMouthForm                  : 口の形 (-1.0: ∧, 1.0: ∪)
 * - ParamMouthOpenY                 : 口の開き
 * - ParamBrowLY / ParamBrowRY       : 眉の高さ
 * - ParamBrowLAngle / ParamBrowRAngle: 眉の角度
 * - ParamTere                       : 頬の赤み (公式Haruモデル。他モデルでは ParamCheek が多い)
 * - ParamTear                       : 涙 (Haruモデル専用。無いモデルでは自動で無視される)
 */

export type Emotion =
  | "neutral"
  | "happy"
  | "sad"
  | "angry"
  | "surprised"
  | "thinking"
  | "shy";

export interface EmotionPose {
  /** パラメータ名 → 目標値 */
  params: Record<string, number>;
  /** 目標に到達するまでの時間(ms)。短いほどキビキビ変わる */
  transitionMs: number;
}

export const EMOTION_PRESETS: Record<Emotion, EmotionPose> = {
  neutral: {
    transitionMs: 400,
    params: {
      ParamEyeLSmile: 0.0,
      ParamEyeRSmile: 0.0,
      ParamMouthForm: 0.0,
      ParamBrowLY: 0.0,
      ParamBrowRY: 0.0,
      ParamBrowLAngle: 0.0,
      ParamBrowRAngle: 0.0,
      ParamTere: 0.0,
    },
  },
  happy: {
    transitionMs: 300,
    params: {
      ParamEyeLSmile: 1.0,
      ParamEyeRSmile: 1.0,
      ParamMouthForm: 1.0,
      ParamBrowLY: 0.4,
      ParamBrowRY: 0.4,
      ParamBrowLAngle: -0.2,
      ParamBrowRAngle: 0.2,
      ParamTere: 0.6,
    },
  },
  sad: {
    transitionMs: 500,
    params: {
      ParamEyeLSmile: 0.0,
      ParamEyeRSmile: 0.0,
      ParamMouthForm: -0.8,
      ParamBrowLY: -0.4,
      ParamBrowRY: -0.4,
      ParamBrowLAngle: 0.6,
      ParamBrowRAngle: -0.6,
      ParamTere: 0.0,
      ParamTear: 0.6, // Haru では涙パラメータあり（他モデルでは無視される）
    },
  },
  angry: {
    transitionMs: 250,
    params: {
      ParamEyeLSmile: 0.0,
      ParamEyeRSmile: 0.0,
      ParamMouthForm: -0.6,
      ParamBrowLY: -0.6,
      ParamBrowRY: -0.6,
      ParamBrowLAngle: -0.8,
      ParamBrowRAngle: 0.8,
      ParamTere: 0.2,
    },
  },
  surprised: {
    transitionMs: 150,
    params: {
      ParamEyeLSmile: 0.0,
      ParamEyeRSmile: 0.0,
      ParamMouthForm: 0.3,
      ParamBrowLY: 0.8,
      ParamBrowRY: 0.8,
      ParamBrowLAngle: 0.0,
      ParamBrowRAngle: 0.0,
      ParamTere: 0.2,
    },
  },
  thinking: {
    transitionMs: 400,
    params: {
      ParamEyeLSmile: 0.2,
      ParamEyeRSmile: 0.2,
      ParamMouthForm: -0.2,
      ParamBrowLY: -0.2,
      ParamBrowRY: 0.2,
      ParamBrowLAngle: 0.3,
      ParamBrowRAngle: -0.1,
      ParamTere: 0.0,
    },
  },
  shy: {
    transitionMs: 350,
    params: {
      ParamEyeLSmile: 0.6,
      ParamEyeRSmile: 0.6,
      ParamMouthForm: 0.4,
      ParamBrowLY: -0.1,
      ParamBrowRY: -0.1,
      ParamBrowLAngle: 0.4,
      ParamBrowRAngle: -0.4,
      ParamTere: 1.0,
    },
  },
};
