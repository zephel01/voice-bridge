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
        # フィードバックループ防止コールバック（VoiceBridge が設定する）
        self.on_play_start = None  # () -> None
        self.on_play_end = None    # () -> None

    def _init_mixer(self):
        """pygame mixer を初期化"""
        if not self._initialized:
            pygame.mixer.init(frequency=24000)
            self._initialized = True

    def _fire(self, cb, label: str):
        """コールバックを安全に呼ぶ（None チェック + 例外捕捉）"""
        if cb is None:
            return
        try:
            cb()
        except Exception as e:
            print(f"[AudioPlayer] {label} エラー: {e}")

    def _cleanup_file(self, path: str):
        """一時ファイルを安全に削除"""
        try:
            os.remove(path)
        except OSError:
            pass

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

            if not os.path.exists(file_path):
                continue

            # 再生開始を通知（キャプチャ抑制）— コールバック例外でも次段は動かす
            self._fire(self.on_play_start, "on_play_start")

            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()

                # 再生完了を待つ
                while pygame.mixer.music.get_busy() and self._running:
                    time.sleep(0.1)
            except Exception as e:
                print(f"[AudioPlayer] 再生エラー: {e}")
            finally:
                # 再生終了を通知（キャプチャ再開）— 例外時も必ず呼ぶ
                self._fire(self.on_play_end, "on_play_end")
                # 再生済みファイルを削除
                self._cleanup_file(file_path)

    def start(self):
        """再生スレッドを開始"""
        self._running = True
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()
        print("[AudioPlayer] 再生スレッド開始")

    def stop(self):
        """再生を停止

        停止処理:
          1. _running=False でループに終了シグナル
          2. キューに None を投げて get 待ちを起こす
          3. 現在再生中ファイルを止める
          4. 再生スレッドの終了を待つ
          5. キュー残留ファイルを削除
          6. pygame.mixer.quit() を呼んで再起動時の hang を防ぐ
        """
        self._running = False
        self._play_queue.put(None)  # 終了シグナル

        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception as e:
                print(f"[AudioPlayer] mixer.music.stop エラー: {e}")

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # キューをクリア（未再生の一時ファイルを削除）
        while not self._play_queue.empty():
            try:
                f = self._play_queue.get_nowait()
            except queue.Empty:
                break
            if f and os.path.exists(f):
                self._cleanup_file(f)

        # mixer を後片付け — init/quit のペアが崩れると次回 init で hang することがある
        if pygame.mixer.get_init():
            try:
                pygame.mixer.quit()
            except Exception as e:
                print(f"[AudioPlayer] pygame.mixer.quit エラー: {e}")
        self._initialized = False

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
