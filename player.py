"""
音声再生モジュール
pygame.mixer を使って生成された音声ファイルを順次再生する
"""

import queue
import threading
import time
import os

try:
    import pygame
except ImportError:
    raise ImportError("pygame が必要です: pip install pygame")


class AudioPlayer:
    """音声ファイルをキュー管理で順次再生するクラス"""

    def __init__(self):
        self._play_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread = None
        self._initialized = False

    def _init_mixer(self):
        """pygame mixer を初期化"""
        if not self._initialized:
            pygame.mixer.init(frequency=24000)
            self._initialized = True

    def _play_loop(self):
        """再生ループ（別スレッドで実行）"""
        self._init_mixer()

        while self._running:
            try:
                file_path = self._play_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if file_path is None:  # 終了シグナル
                break

            try:
                if os.path.exists(file_path):
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()

                    # 再生完了を待つ
                    while pygame.mixer.music.get_busy() and self._running:
                        time.sleep(0.1)

                    # 再生済みファイルを削除
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            except Exception as e:
                print(f"[AudioPlayer] 再生エラー: {e}")

    def start(self):
        """再生スレッドを開始"""
        self._running = True
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()
        print("[AudioPlayer] 再生スレッド開始")

    def stop(self):
        """再生を停止"""
        self._running = False
        self._play_queue.put(None)  # 終了シグナル

        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # キューをクリア
        while not self._play_queue.empty():
            try:
                f = self._play_queue.get_nowait()
                if f and os.path.exists(f):
                    os.remove(f)
            except queue.Empty:
                break

        print("[AudioPlayer] 再生停止")

    def enqueue(self, file_path: str):
        """再生キューにファイルを追加"""
        self._play_queue.put(file_path)

    @property
    def queue_size(self) -> int:
        return self._play_queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._running
