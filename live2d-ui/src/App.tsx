import { useCallback, useEffect, useRef, useState } from "react";
import { Live2DAvatar } from "./Live2DAvatar";
import type { Emotion } from "./emotionMap";
import {
  useBridgeSocket,
  type BridgeMessage,
  type TtsMessage,
} from "./useBridgeSocket";

// デフォルトのモデル URL。Vite のビルド時に /public 配下が / にマウントされるため、
// public/live2d/<model_name>/.../*.model3.json に配置する想定。
// 公式サンプル Haru Greeter (haru_greeter_t05) を既定にする。
const DEFAULT_MODEL_URL = "/live2d/haru/runtime/haru_greeter_t05.model3.json";

// Python ブリッジの待受アドレス
const BRIDGE_URL = "ws://127.0.0.1:8765";

function base64ToBlobUrl(b64: string, mime: string): string {
  const binStr = atob(b64);
  const len = binStr.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binStr.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const avatarRef = useRef<Live2DAvatar | null>(null);

  const [speaking, setSpeaking] = useState(false);
  const [subtitle, setSubtitle] = useState("");
  const [emotion, setEmotion] = useState<Emotion>("neutral");
  const [modelReady, setModelReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // TTS キュー: フロントで順次再生
  const ttsQueueRef = useRef<TtsMessage[]>([]);
  const processingRef = useRef(false);

  const sendRef = useRef<(payload: unknown) => void>(() => {});

  const processQueue = useCallback(() => {
    if (processingRef.current) return;
    const next = ttsQueueRef.current.shift();
    if (!next) return;

    processingRef.current = true;
    const avatar = avatarRef.current;
    if (!avatar) {
      processingRef.current = false;
      sendRef.current({ type: "playback_end", id: next.id });
      return;
    }

    const emo = (next.emotion || "neutral") as Emotion;
    avatar.setEmotion(emo, next.intensity ?? 1.0);
    setEmotion(emo);
    setSpeaking(true);
    setSubtitle(next.text || "");

    const url = base64ToBlobUrl(next.audio_b64, next.mime || "audio/mpeg");
    avatar.playAudio(url, () => {
      URL.revokeObjectURL(url);
      setSpeaking(false);
      setSubtitle("");
      // Neutral には戻さず、直前の表情を軽く保持
      processingRef.current = false;
      sendRef.current({ type: "playback_end", id: next.id });
      processQueue();
    });
  }, []);

  // ---------------- WebSocket メッセージハンドラ ----------------
  const onBridge = useCallback(
    (msg: BridgeMessage) => {
      if (msg.type === "tts") {
        ttsQueueRef.current.push(msg);
        processQueue();
      } else if (msg.type === "emotion") {
        const emo = (msg.emotion || "neutral") as Emotion;
        avatarRef.current?.setEmotion(emo, msg.intensity ?? 1.0);
        setEmotion(emo);
      } else if (msg.type === "idle") {
        avatarRef.current?.setIdleEnabled(msg.enabled);
      }
    },
    [processQueue],
  );

  const { connected, send } = useBridgeSocket(BRIDGE_URL, onBridge);
  useEffect(() => {
    sendRef.current = send;
  }, [send]);

  // ---------------- Live2D 初期化 ----------------
  useEffect(() => {
    if (!canvasRef.current) return;

    const modelUrl =
      new URLSearchParams(window.location.search).get("model") ||
      DEFAULT_MODEL_URL;

    // Cubism Core が読み込まれているかの事前チェック
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (!(window as any).Live2DCubismCore) {
      setLoadError(
        "Live2DCubismCore が読み込まれていません。public/live2dcubismcore.min.js の配置を確認してください。",
      );
      return;
    }

    let avatar: Live2DAvatar | null = null;
    try {
      avatar = new Live2DAvatar({
        canvas: canvasRef.current,
        modelUrl,
        scale: 0.28,
        lipSyncGain: 1.6,
        backgroundAlpha: 0,
      });
      avatarRef.current = avatar;

      avatar
        .load()
        .then(() => setModelReady(true))
        .catch((err) => {
          console.error("[Live2D] load error", err);
          setLoadError(String(err?.message ?? err));
        });
    } catch (e) {
      console.error("[Live2D] init error", e);
      setLoadError(String((e as Error)?.message ?? e));
    }

    return () => {
      avatar?.destroy();
      avatarRef.current = null;
    };
  }, []);

  // 接続直後に Neutral に揃えておく
  useEffect(() => {
    if (connected && modelReady) {
      avatarRef.current?.setEmotion("neutral", 1.0);
    }
  }, [connected, modelReady]);

  const statusClass = [
    "status",
    connected ? "connected" : "",
    speaking ? "speaking" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="app">
      <div className="stage">
        <canvas ref={canvasRef} />
        <div className={statusClass}>
          <span className="dot" />
          {connected ? (speaking ? "Speaking..." : "Connected") : "Connecting..."}
        </div>
        <div className="emotion-badge">
          {emotion} {modelReady ? "" : "(loading)"}
        </div>
        {subtitle && <div className="subtitle">{subtitle}</div>}
        {loadError && (
          <div className="subtitle" style={{ color: "#ff9090" }}>
            モデルの読み込みに失敗しました: {loadError}
          </div>
        )}
      </div>
    </div>
  );
}
