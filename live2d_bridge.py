"""
Live2D ブリッジモジュール

voice-bridge の TTS 出力を Electron フロントエンド(Live2D Cubism Web SDK)へ
WebSocket で転送する。Live2D モード時はこのブリッジが pygame 再生の代わりに
mp3 をフロントへ渡し、フロント側で再生 + 口パク + 表情変化を行う。

使い方:
    bridge = Live2DBridge(host="127.0.0.1", port=8765)
    bridge.start()
    ...
    # TTS 生成後に呼び出す
    bridge.send_tts(mp3_path, text="こんにちは", emotion="happy")
    bridge.wait_playback_end(timeout=10.0)
    ...
    bridge.stop()

フロントエンドは websocket://127.0.0.1:8765 に接続し、下記のメッセージを処理する。

サーバ → クライアント:
    {"type": "tts",       "id": "<uuid>", "audio_b64": "...", "mime": "audio/mpeg",
     "text": "...",       "emotion": "happy", "intensity": 0.8}
    {"type": "emotion",   "emotion": "surprised", "intensity": 1.0}
    {"type": "idle",      "enabled": true}
    {"type": "ping"}

クライアント → サーバ:
    {"type": "playback_end", "id": "<uuid>"}  # 再生終了通知
    {"type": "ready"}                         # 接続完了
    {"type": "pong"}
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:  # pragma: no cover
    raise ImportError(
        "websockets が必要です。`pip install websockets` で追加してください。"
    )


logger = logging.getLogger("voice_bridge.live2d")


@dataclass
class _PendingPlayback:
    """再生終了を待つためのフラグ保持構造体"""
    id: str
    event: threading.Event = field(default_factory=threading.Event)
    created_at: float = field(default_factory=time.time)


class Live2DBridge:
    """
    Live2D フロントエンドとの WebSocket ブリッジ。

    - 別スレッドで asyncio + websockets サーバを起動
    - mp3 ファイルを base64 化してクライアントへ送信
    - クライアント側の再生終了通知を wait_playback_end() で待機できる
    - フロントが複数接続された場合はすべてにブロードキャスト（通常は 1 つ）
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_thread: Optional[threading.Thread] = None
        self._server_ready = threading.Event()
        self._stop_flag = threading.Event()
        self._clients: set[WebSocketServerProtocol] = set()
        self._clients_lock = threading.Lock()
        self._pending: dict[str, _PendingPlayback] = {}
        self._pending_lock = threading.Lock()

        # 接続監視
        self._client_connected = threading.Event()

    # ---------------------------------------------------------------- lifecycle

    def start(self) -> None:
        """サーバを別スレッドで起動する。"""
        if self._server_thread is not None:
            return

        self._server_thread = threading.Thread(
            target=self._run_server, name="Live2DBridgeServer", daemon=True
        )
        self._server_thread.start()

        # サーバの起動完了を最大 3 秒待つ
        if not self._server_ready.wait(timeout=3.0):
            logger.warning("[Live2DBridge] サーバ起動が遅延しています")

        logger.info(f"[Live2DBridge] ws://{self.host}:{self.port} で待受中")

    def stop(self) -> None:
        """サーバを停止する。"""
        if self._loop is None:
            return

        self._stop_flag.set()
        try:
            # すべての pending をシグナル（デッドロック防止）
            with self._pending_lock:
                for pending in self._pending.values():
                    pending.event.set()
                self._pending.clear()

            # イベントループを停止
            asyncio.run_coroutine_threadsafe(
                self._shutdown_async(), self._loop
            ).result(timeout=3.0)
        except Exception as e:
            logger.warning(f"[Live2DBridge] 停止時エラー: {e}")

        if self._server_thread:
            self._server_thread.join(timeout=3.0)

        self._server_thread = None
        self._loop = None
        logger.info("[Live2DBridge] 停止しました")

    async def _shutdown_async(self):
        # 全クライアントを閉じる
        with self._clients_lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.close()
            except Exception:
                pass

        # ループを止める
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    # ---------------------------------------------------------------- server

    def _run_server(self) -> None:
        """バックグラウンドスレッドで asyncio サーバを回す。"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def serve():
            async with websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                max_size=8 * 1024 * 1024,  # 最大 8MB メッセージ許容
                ping_interval=20,
                ping_timeout=20,
            ):
                self._server_ready.set()
                # 停止フラグがセットされるまで待機
                while not self._stop_flag.is_set():
                    await asyncio.sleep(0.2)

        try:
            self._loop.run_until_complete(serve())
        except Exception as e:
            logger.error(f"[Live2DBridge] サーバエラー: {e}")
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _handle_client(self, ws: WebSocketServerProtocol) -> None:
        """クライアント 1 接続分のハンドラ"""
        peer = ws.remote_address
        logger.info(f"[Live2DBridge] クライアント接続: {peer}")

        with self._clients_lock:
            self._clients.add(ws)
        self._client_connected.set()

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                if msg_type == "playback_end":
                    pid = data.get("id")
                    if pid:
                        with self._pending_lock:
                            pending = self._pending.pop(pid, None)
                        if pending:
                            pending.event.set()

                elif msg_type == "ready":
                    logger.debug(f"[Live2DBridge] クライアント ready: {peer}")

                elif msg_type == "pong":
                    pass

        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.warning(f"[Live2DBridge] クライアント処理エラー: {e}")
        finally:
            with self._clients_lock:
                self._clients.discard(ws)
                if not self._clients:
                    self._client_connected.clear()
            logger.info(f"[Live2DBridge] クライアント切断: {peer}")

    # ---------------------------------------------------------------- public API

    def has_client(self) -> bool:
        """Live2D フロントが少なくとも 1 つ接続されているか"""
        return self._client_connected.is_set()

    def wait_for_client(self, timeout: float = 0.0) -> bool:
        """フロントの接続を待つ。timeout=0 なら即時"""
        if timeout <= 0:
            return self.has_client()
        return self._client_connected.wait(timeout=timeout)

    def send_tts(
        self,
        mp3_path: str,
        text: str = "",
        emotion: str = "neutral",
        intensity: float = 1.0,
    ) -> Optional[str]:
        """
        mp3 ファイルをフロントへ送信して再生させる。
        返り値は再生ID（wait_playback_end に渡せる）。失敗時は None。
        """
        if not os.path.exists(mp3_path):
            logger.warning(f"[Live2DBridge] ファイルが存在しません: {mp3_path}")
            return None

        if not self.has_client():
            # フロント未接続のまま大量バッファしないよう警告
            logger.debug("[Live2DBridge] クライアント未接続のため送信スキップ")
            return None

        try:
            with open(mp3_path, "rb") as f:
                audio_bytes = f.read()
        except OSError as e:
            logger.warning(f"[Live2DBridge] ファイル読み込み失敗: {e}")
            return None

        pid = uuid.uuid4().hex[:12]
        pending = _PendingPlayback(id=pid)
        with self._pending_lock:
            self._pending[pid] = pending

        message = {
            "type": "tts",
            "id": pid,
            "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _guess_mime(mp3_path),
            "text": text,
            "emotion": emotion,
            "intensity": max(0.0, min(1.5, intensity)),
        }
        self._broadcast(message)
        return pid

    def send_emotion(self, emotion: str, intensity: float = 1.0) -> None:
        """TTS なしで表情だけ変える（待機時・相槌時など）"""
        self._broadcast({
            "type": "emotion",
            "emotion": emotion,
            "intensity": max(0.0, min(1.5, intensity)),
        })

    def set_idle(self, enabled: bool = True) -> None:
        """まばたき/呼吸などのアイドルアニメを on/off"""
        self._broadcast({"type": "idle", "enabled": enabled})

    def wait_playback_end(self, playback_id: str, timeout: float = 15.0) -> bool:
        """
        指定した再生 ID の終了を待つ。タイムアウトした場合 False。
        """
        with self._pending_lock:
            pending = self._pending.get(playback_id)
        if pending is None:
            return True
        ok = pending.event.wait(timeout=timeout)
        if not ok:
            # タイムアウトしたら登録を除去
            with self._pending_lock:
                self._pending.pop(playback_id, None)
        return ok

    # ---------------------------------------------------------------- internal

    def _broadcast(self, message: dict) -> None:
        """接続中の全クライアントへ送信（イベントループへ投げる）"""
        if self._loop is None or self._loop.is_closed():
            return

        raw = json.dumps(message, ensure_ascii=False)

        async def _send():
            with self._clients_lock:
                clients = list(self._clients)
            for ws in clients:
                try:
                    await ws.send(raw)
                except Exception as e:
                    logger.debug(f"[Live2DBridge] 送信失敗: {e}")

        asyncio.run_coroutine_threadsafe(_send(), self._loop)


def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(ext, "application/octet-stream")


# ---------------------------------------------------------------- 感情解析ヘルパー

_EMOTION_KEYWORDS = {
    "happy":     ["嬉しい", "たのしい", "楽しい", "うれしい", "やった", "すごい", "最高", "ありがとう", "笑", "!", "！"],
    "sad":       ["悲しい", "さみしい", "寂しい", "つらい", "辛い", "泣", "しょんぼり"],
    "angry":     ["怒", "ムカ", "腹立", "許せ", "いい加減"],
    "surprised": ["びっくり", "驚", "えっ", "まさか", "ほんと", "まじ"],
    "thinking":  ["うーん", "そうですね", "考え", "えーと", "なるほど"],
    "shy":       ["///", "はずかし", "恥ずかし"],
}


def infer_emotion(text: str) -> tuple[str, float]:
    """
    テキストから簡易的に感情ラベルと強度(0.0〜1.0)を推定する。
    LLM による本格的な感情分析に置き換えやすい形にしている。
    """
    if not text:
        return "neutral", 0.5

    scores: dict[str, int] = {}
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[emotion] = scores.get(emotion, 0) + 1

    if not scores:
        return "neutral", 0.5

    emotion, hits = max(scores.items(), key=lambda kv: kv[1])
    intensity = min(1.0, 0.5 + 0.25 * hits)
    return emotion, intensity


# ---------------------------------------------------------------- 動作確認

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    bridge = Live2DBridge()
    bridge.start()
    print("Live2D ブリッジ起動中 (ws://127.0.0.1:8765). Ctrl+C で終了")

    try:
        while True:
            time.sleep(1.0)
            if bridge.has_client():
                bridge.send_emotion("happy", 1.0)
                time.sleep(3)
                bridge.send_emotion("neutral", 0.5)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
