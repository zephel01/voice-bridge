"""
Windows 音声キャプチャモジュール
PyAudioWPatch の WASAPI ループバックを使って Windows のシステム音声をキャプチャする

必要パッケージ: pip install PyAudioWPatch
"""

import threading
import queue
import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    raise ImportError(
        "PyAudioWPatch が必要です: pip install PyAudioWPatch\n"
        "（Windows でのシステム音声キャプチャに使用します）"
    )


class WindowsAudioCapture:
    """WASAPI ループバックでシステム音声をキャプチャするクラス（Windows 専用）"""

    def __init__(
        self,
        device_name: str = "default",
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
        self._pa = None
        self._thread = None

        self.chunk_samples = int(sample_rate * chunk_duration)

        # RMS レベルコールバック (rms: float, is_above_threshold: bool)
        self.on_level = None

        # デバイスのネイティブ設定（start 時に決定）
        self._device_sample_rate = None
        self._device_channels = None

    @staticmethod
    def list_devices() -> list[dict]:
        """利用可能なオーディオデバイスの一覧を返す（ループバックデバイス含む）"""
        pa = pyaudio.PyAudio()
        result = []
        try:
            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                if d["maxInputChannels"] > 0:
                    name = d["name"]
                    # ループバックデバイスを識別
                    is_loopback = d.get("isLoopbackDevice", False)
                    if is_loopback:
                        name = f"[Loopback] {name}"
                    result.append({
                        "index": i,
                        "name": name,
                        "channels": d["maxInputChannels"],
                        "sample_rate": d["defaultSampleRate"],
                        "is_loopback": is_loopback,
                    })
        finally:
            pa.terminate()
        return result

    def _find_loopback_device(self) -> dict | None:
        """WASAPI ループバックデバイスを検索"""
        pa = self._pa
        if pa is None:
            return None

        # "default" の場合はデフォルトループバックを使用
        if self.device_name == "default":
            try:
                return pa.get_default_wasapi_loopback()
            except Exception:
                pass

        # デバイス名で検索
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d.get("isLoopbackDevice", False):
                if self.device_name.lower() in d["name"].lower():
                    return d

        # ループバックが見つからなければ最初のループバックデバイスを使用
        try:
            return pa.get_default_wasapi_loopback()
        except Exception:
            return None

    def _capture_thread(self):
        """録音スレッド"""
        device = self._find_loopback_device()
        if device is None:
            print("[WindowsAudioCapture] WASAPI ループバックデバイスが見つかりません")
            self._running = False
            return

        self._device_sample_rate = int(device["defaultSampleRate"])
        self._device_channels = device["maxInputChannels"]

        print(f"[WindowsAudioCapture] キャプチャ開始: {device['name']}")
        print(f"  ネイティブ: {self._device_sample_rate}Hz, {self._device_channels}ch")
        print(f"  出力: {self.sample_rate}Hz, 1ch")

        # ストリームのフレームサイズ（0.5秒ごと）
        frames_per_buffer = int(self._device_sample_rate * 0.5)

        try:
            self._stream = self._pa.open(
                format=pyaudio.paFloat32,
                channels=self._device_channels,
                rate=self._device_sample_rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=frames_per_buffer,
            )
        except Exception as e:
            print(f"[WindowsAudioCapture] ストリーム開始エラー: {e}")
            self._running = False
            return

        while self._running:
            try:
                data = self._stream.read(frames_per_buffer, exception_on_overflow=False)
            except Exception as e:
                if self._running:
                    print(f"[WindowsAudioCapture] 読み取りエラー: {e}")
                break

            # バイトデータを numpy 配列に変換
            audio_data = np.frombuffer(data, dtype=np.float32)

            # マルチチャンネルならモノラルに変換
            if self._device_channels > 1:
                audio_data = audio_data.reshape(-1, self._device_channels)
                audio_data = audio_data.mean(axis=1)

            # リサンプリング（デバイスのサンプルレートがターゲットと異なる場合）
            if self._device_sample_rate != self.sample_rate:
                ratio = self.sample_rate / self._device_sample_rate
                new_length = int(len(audio_data) * ratio)
                indices = np.linspace(0, len(audio_data) - 1, new_length).astype(int)
                audio_data = audio_data[indices]

            # バッファに追加
            self._buffer.append(audio_data)
            self._buffer_samples += len(audio_data)

            # チャンクサイズに達したらキューに投入
            if self._buffer_samples >= self.chunk_samples:
                chunk = np.concatenate(self._buffer)
                audio_chunk = chunk[: self.chunk_samples]
                remaining = chunk[self.chunk_samples :]

                # 無音チェック
                rms = np.sqrt(np.mean(audio_chunk**2))
                if self.on_level:
                    self.on_level(rms, rms > self.silence_threshold)
                if rms > self.silence_threshold:
                    self.audio_queue.put(audio_chunk)

                self._buffer = [remaining] if len(remaining) > 0 else []
                self._buffer_samples = len(remaining)

        # クリーンアップ
        if self._stream and self._stream.is_active():
            self._stream.stop_stream()
        if self._stream:
            self._stream.close()
        self._stream = None

    def start(self):
        """音声キャプチャを開始"""
        self._running = True
        self._buffer = []
        self._buffer_samples = 0

        self._pa = pyaudio.PyAudio()
        self._thread = threading.Thread(target=self._capture_thread, daemon=True)
        self._thread.start()

    def stop(self):
        """音声キャプチャを停止"""
        self._running = False

        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

        if self._pa:
            self._pa.terminate()
            self._pa = None

        # 残りのバッファをフラッシュ
        if self._buffer:
            chunk = np.concatenate(self._buffer)
            rms = np.sqrt(np.mean(chunk**2))
            if rms > self.silence_threshold and len(chunk) > self.sample_rate * 0.5:
                self.audio_queue.put(chunk)
            self._buffer = []
            self._buffer_samples = 0

        print("[WindowsAudioCapture] キャプチャ停止")

    def get_chunk(self, timeout: float = 1.0) -> np.ndarray | None:
        """キューから音声チャンクを取得（ブロッキング）"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None


if __name__ == "__main__":
    print("利用可能な入力デバイス (Windows WASAPI):")
    for d in WindowsAudioCapture.list_devices():
        loopback = " [LOOPBACK]" if d.get("is_loopback") else ""
        print(f"  [{d['index']}] {d['name']} (ch={d['channels']}){loopback}")
