import { useEffect, useRef, useState } from "react";

export interface TtsMessage {
  type: "tts";
  id: string;
  audio_b64: string;
  mime: string;
  text: string;
  emotion: string;
  intensity: number;
}

export interface EmotionMessage {
  type: "emotion";
  emotion: string;
  intensity: number;
}

export interface IdleMessage {
  type: "idle";
  enabled: boolean;
}

export type BridgeMessage = TtsMessage | EmotionMessage | IdleMessage;

export interface BridgeSocketHandle {
  connected: boolean;
  send: (payload: unknown) => void;
}

const KNOWN_MESSAGE_TYPES = new Set(["tts", "emotion", "idle"]);

const INITIAL_RECONNECT_DELAY_MS = 1500;
const MAX_RECONNECT_DELAY_MS = 30000;
const RECONNECT_BACKOFF_FACTOR = 2;

/**
 * 受信した JSON をランタイムで検証し、BridgeMessage として扱って良いかを判定する。
 * 想定外の type や必須フィールドの型不一致がある場合は null を返す。
 */
function validateBridgeMessage(data: unknown): BridgeMessage | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }

  const obj = data as Record<string, unknown>;
  const { type } = obj;

  if (typeof type !== "string" || !KNOWN_MESSAGE_TYPES.has(type)) {
    return null;
  }

  if (type === "tts") {
    if (typeof obj.audio_b64 !== "string") {
      return null;
    }
    if (typeof obj.id !== "string") {
      return null;
    }
    return {
      type: "tts",
      id: obj.id,
      audio_b64: obj.audio_b64,
      mime: typeof obj.mime === "string" ? obj.mime : "",
      text: typeof obj.text === "string" ? obj.text : "",
      emotion: typeof obj.emotion === "string" ? obj.emotion : "",
      intensity: typeof obj.intensity === "number" ? obj.intensity : 1.0,
    };
  }

  if (type === "emotion") {
    if (typeof obj.emotion !== "string") {
      return null;
    }
    return {
      type: "emotion",
      emotion: obj.emotion,
      intensity: typeof obj.intensity === "number" ? obj.intensity : 1.0,
    };
  }

  // type === "idle"
  if (typeof obj.enabled !== "boolean") {
    return null;
  }
  return { type: "idle", enabled: obj.enabled };
}

/**
 * Python 側 live2d_bridge.py の WebSocket に接続し、
 * 再接続（指数バックオフ）やハートビートを管理するフック。
 */
export function useBridgeSocket(
  url: string,
  onMessage: (msg: BridgeMessage) => void,
): BridgeSocketHandle {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let stopped = false;
    let retryTimer: number | null = null;
    let reconnectDelayMs = INITIAL_RECONNECT_DELAY_MS;

    const connect = () => {
      if (stopped) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setConnected(true);
        // 接続成功したのでバックオフをリセット
        reconnectDelayMs = INITIAL_RECONNECT_DELAY_MS;
        ws.send(JSON.stringify({ type: "ready" }));
      });

      ws.addEventListener("message", (ev) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(ev.data);
        } catch (e) {
          console.warn("[bridge] parse error", e);
          return;
        }

        const msg = validateBridgeMessage(parsed);
        if (!msg) {
          console.warn("[bridge] received message failed validation, ignoring", parsed);
          return;
        }

        onMessageRef.current(msg);
      });

      const scheduleReconnect = () => {
        setConnected(false);
        wsRef.current = null;
        if (stopped) return;
        const delay = reconnectDelayMs;
        reconnectDelayMs = Math.min(
          reconnectDelayMs * RECONNECT_BACKOFF_FACTOR,
          MAX_RECONNECT_DELAY_MS,
        );
        retryTimer = window.setTimeout(connect, delay);
      };

      ws.addEventListener("close", scheduleReconnect);
      ws.addEventListener("error", () => {
        try {
          ws.close();
        } catch {}
      });
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      try {
        wsRef.current?.close();
      } catch {}
    };
  }, [url]);

  return {
    connected,
    send: (payload) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload));
      }
    },
  };
}
