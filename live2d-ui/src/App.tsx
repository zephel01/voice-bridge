import { useCallback, useEffect, useRef, useState } from "react";
import { Live2DAvatar } from "./Live2DAvatar";
import type { Emotion } from "./emotionMap";
import {
  useBridgeSocket,
  type BridgeMessage,
  type TtsMessage,
} from "./useBridgeSocket";
import { ModelSelector, type ModelEntry } from "./ModelSelector";

// デフォルトのモデル URL。Vite のビルド時に /public 配下が / にマウントされるため、
// public/live2d/<model_name>/.../*.model3.json に配置する想定。
const DEFAULT_MODEL_URL = "/live2d/haru/runtime/haru_greeter_t05.model3.json";
const STORAGE_KEY = "live2d_selected_model";

// Python ブリッジの待受アドレス
const BRIDGE_URL = "ws://127.0.0.1:8765";

// 許可する音声 MIME タイプ。これ以外は audio/mpeg にフォールバックする。
const ALLOWED_AUDIO_MIME_TYPES = new Set(["audio/mpeg", "audio/wav", "audio/ogg"]);
const FALLBACK_AUDIO_MIME_TYPE = "audio/mpeg";

/**
 * モデルパスとして許可する値かを検証する。
 * "/live2d/" で始まる相対パスのみを許可し、それ以外（絶対 URL、file://、
 * 上位ディレクトリへのパストラバーサル等）は拒否する。
 */
function isAllowedModelPath(candidate: string): boolean {
  if (!candidate.startsWith("/live2d/")) return false;
  // "//" によるプロトコル相対 URL や ".." によるパストラバーサルを拒否
  if (candidate.startsWith("//")) return false;
  if (candidate.includes("..")) return false;
  return true;
}

/** 現在のモデル URL を解決する（URLクエリ > localStorage > デフォルト） */
function resolveModelUrl(): string {
  const fromQuery = new URLSearchParams(window.location.search).get("model");
  if (fromQuery && isAllowedModelPath(fromQuery)) return fromQuery;
  if (fromQuery) {
    console.warn("[App] ignoring disallowed model query value:", fromQuery);
  }

  const fromStorage = localStorage.getItem(STORAGE_KEY);
  if (fromStorage && isAllowedModelPath(fromStorage)) return fromStorage;
  if (fromStorage) {
    console.warn("[App] ignoring disallowed stored model value:", fromStorage);
  }

  return DEFAULT_MODEL_URL;
}

/** モデルを切り替える（localStorage 保存 + URL を書き換えてリロード） */
function switchModel(model: ModelEntry): void {
  if (!isAllowedModelPath(model.path)) {
    console.warn("[App] refusing to switch to disallowed model path:", model.path);
    return;
  }
  localStorage.setItem(STORAGE_KEY, model.path);
  const url = new URL(window.location.href);
  url.searchParams.set("model", model.path);
  window.location.href = url.toString();
}

function base64ToBlobUrl(b64: string, mime: string): string | null {
  try {
    const safeMime = ALLOWED_AUDIO_MIME_TYPES.has(mime) ? mime : FALLBACK_AUDIO_MIME_TYPE;
    const binStr = atob(b64);
    const len = binStr.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binStr.charCodeAt(i);
    return URL.createObjectURL(new Blob([bytes], { type: safeMime }));
  } catch (e) {
    console.warn("[App] failed to decode audio_b64", e);
    return null;
  }
}

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const avatarRef = useRef<Live2DAvatar | null>(null);

  const [speaking, setSpeaking] = useState(false);
  const [subtitle, setSubtitle] = useState("");
  const [emotion, setEmotion] = useState<Emotion>("neutral");
  const [modelReady, setModelReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // 解決済みモデル URL（セレクター表示用に保持）
  const [currentModelUrl] = useState<string>(resolveModelUrl);

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
    if (!url) {
      // デコードに失敗した場合はこのメッセージをスキップして次へ進む
      processingRef.current = false;
      setSpeaking(false);
      setSubtitle("");
      sendRef.current({ type: "playback_end", id: next.id });
      processQueue();
      return;
    }

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
        modelUrl: currentModelUrl,
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
  }, [currentModelUrl]);

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
        <ModelSelector
          currentModelPath={currentModelUrl}
          onSelect={switchModel}
        />
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
