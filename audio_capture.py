"""
音声キャプチャモジュール
BlackHole経由でmacOSのシステム音声をキャプチャする
"""

import threading
import queue
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    raise ImportError("sounddevice が必要です: pip install sounddevice")


class AudioCapture:
    """システム音声をキャプチャしてチャンクに分割するクラス"""

    def __init__(
        self,
        device_name: str = "BlackHole 2ch",
        sample_rate: int = 16000,
        chunk_duration: float = 4.0,
        silence_threshold: float = 0.01,
    ):
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold

        self.audio_queue: queue.Queue = queue.Queue()
        self._buffer: list = []
        self._buffer_samples = 0
        self._running = False
        self._stream = None
        self._thread = None

        self.chunk_samples = int(sample_rate * chunk_duration)

        # RMS レベルコールバック (rms: float, is_above_threshold: bool)
        self.on_level = None

    @staticmethod
    def list_devices() -> list[dict]:
        """利用可能なオーディオデバイスの一覧を返す"""
        devices = sd.query_devices()
        result = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append({
                    "index": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                })
        return result

    def _find_device(self) -> int | None:
        """デバイス名からデバイスインデックスを検索"""
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if self.device_name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
        return None

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice のコールバック。音声データをバッファに追加"""
        if status:
            print(f"[AudioCapture] Status: {status}")

        audio_data = indata[:, 0].copy()  # モノラルに変換
        self._buffer.append(audio_data)
        self._buffer_samples += len(audio_data)

        # チャンクサイズに達したらキューに投入
        if self._buffer_samples >= self.chunk_samples:
            chunk = np.concatenate(self._buffer)
            # チャンクサイズ分だけ取り出す
            audio_chunk = chunk[: self.chunk_samples]
            remaining = chunk[self.chunk_samples :]

            # 無音チェック: RMS が閾値以上ならキューに追加
            rms = np.sqrt(np.mean(audio_chunk**2))
            if self.on_level:
                self.on_level(rms, rms > self.silence_threshold)
            if rms > self.silence_threshold:
                self.audio_queue.put(audio_chunk)

            # 残りをバッファに戻す
            self._buffer = [remaining] if len(remaining) > 0 else []
            self._buffer_samples = len(remaining)

    def start(self):
        """音声キャプチャを開始"""
        device_index = self._find_device()
        if device_index is None:
            available = self.list_devices()
            device_names = [d["name"] for d in available]
            raise RuntimeError(
                f"デバイス '{self.device_name}' が見つかりません。\n"
                f"利用可能な入力デバイス: {device_names}\n"
                f"BlackHole がインストールされているか確認してください。"
            )

        self._running = True
        self._buffer = []
        self._buffer_samples = 0

        self._stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=int(self.sample_rate * 0.5),  # 0.5秒ごとにコールバック
            callback=self._audio_callback,
        )
        self._stream.start()
        print(f"[AudioCapture] キャプチャ開始: {self.device_name} (index={device_index})")

    def stop(self):
        """音声キャプチャを停止"""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # 残りのバッファをフラッシュ
        if self._buffer:
            chunk = np.concatenate(self._buffer)
            rms = np.sqrt(np.mean(chunk**2))
            if rms > self.silence_threshold and len(chunk) > self.sample_rate * 0.5:
                self.audio_queue.put(chunk)
            self._buffer = []
            self._buffer_samples = 0
        print("[AudioCapture] キャプチャ停止")

    def get_chunk(self, timeout: float = 1.0) -> np.ndarray | None:
        """キューから音声チャンクを取得（ブロッキング）"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running and self._stream is not None


if __name__ == "__main__":
    # テスト: 利用可能なデバイスを表示
    print("利用可能な入力デバイス:")
    for d in AudioCapture.list_devices():
        print(f"  [{d['index']}] {d['name']} (ch={d['channels']})")
