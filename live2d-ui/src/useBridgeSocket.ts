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

/**
 * Python 側 live2d_bridge.py の WebSocket に接続し、
 * 再接続やハートビートを管理するフック。
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

    const connect = () => {
      if (stopped) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setConnected(true);
        ws.send(JSON.stringify({ type: "ready" }));
      });

      ws.addEventListener("message", (ev) => {
        try {
          const msg = JSON.parse(ev.data) as BridgeMessage;
          onMessageRef.current(msg);
        } catch (e) {
          console.warn("[bridge] parse error", e);
        }
      });

      const scheduleReconnect = () => {
        setConnected(false);
        wsRef.current = null;
        if (stopped) return;
        retryTimer = window.setTimeout(connect, 1500);
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
