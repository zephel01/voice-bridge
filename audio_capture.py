"""
音声キャプチャモジュール
sounddevice を使用してシステム音声・マイク入力をキャプチャする
macOS: BlackHole経由 / Linux: PulseAudio/PipeWire モニター

VAD（Voice Activity Detection）モード:
  Silero VAD を使い、発話の開始・終了をニューラルネットで検出。
  チャットモードでは発話単位でキューに投入し、
  固定チャンクサイズに依存しない自然な発話区切りを実現する。
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
        silence_threshold: float = 0.03,
        # --- ゲイン設定 ---
        input_gain: float = 1.0,        # 入力ゲイン倍率（1.0 = 変更なし）
        auto_gain: bool = False,         # オートゲイン（自動音量正規化）
        auto_gain_target: float = 0.08,  # オートゲインのターゲット RMS
        # --- VAD 設定 ---
        use_vad: bool = False,
        vad_threshold: float = 0.5,
        vad_hold_ms: int = 800,        # 発話終了判定の無音保持時間 (ms)
        vad_max_duration: float = 30.0, # 最大発話長（秒）— 安全リミット
        vad_min_duration: float = 0.3,  # 最小発話長（秒）— 短すぎるノイズを除外
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

        # --- ゲイン ---
        self.input_gain = input_gain
        self.auto_gain = auto_gain
        self._auto_gain_target = auto_gain_target
        self._current_gain = input_gain  # オートゲイン時の動的ゲイン値
        self._gain_smoothing = 0.05      # ゲイン変化の平滑化係数（小さいほど緩やか）
        self._gain_max = 20.0            # オートゲインの最大倍率
        self._gain_min = 1.0             # オートゲインの最小倍率
        self._noise_floor = 0.002        # これ以下の RMS はノイズとみなしゲイン更新しない

        if input_gain != 1.0 or auto_gain:
            gain_info = f"gain={input_gain:.1f}x"
            if auto_gain:
                gain_info += f", auto_gain=ON (target_rms={auto_gain_target})"
            print(f"[AudioCapture] {gain_info}")

        # レベルコールバック (rms: float, is_active: bool)
        self.on_level = None

        # 生オーディオコールバック (audio_data: np.ndarray)
        # ストリーミング ASR 用: 全ブロックをそのまま渡す
        self.on_audio = None

        # --- VAD ---
        self.use_vad = use_vad
        self._vad = None
        self._vad_threshold = vad_threshold

        if use_vad:
            from vad import SileroVAD
            self._vad = SileroVAD(threshold=vad_threshold, sample_rate=sample_rate)
            self._vad.load()

            # VAD ブロックは 100ms (1600 samples @ 16kHz)
            self._vad_block_duration = 0.1
            self._vad_block_samples = int(sample_rate * self._vad_block_duration)

            # 発話終了判定: 無音が hold_frames 回続いたら発話終了
            self._vad_hold_frames = max(1, int(vad_hold_ms / (self._vad_block_duration * 1000)))
            self._vad_max_samples = int(vad_max_duration * sample_rate)
            self._vad_min_samples = int(vad_min_duration * sample_rate)

            # VAD 状態
            self._speech_active = False
            self._speech_buffer: list = []
            self._speech_buffer_samples = 0
            self._silence_frame_count = 0

            print(f"[AudioCapture] VAD: threshold={vad_threshold}, "
                  f"hold={vad_hold_ms}ms ({self._vad_hold_frames}frames), "
                  f"min={vad_min_duration}s, max={vad_max_duration}s")

    @staticmethod
    def list_devices() -> list[dict]:
        """利用可能なオーディオデバイスの一覧を返す"""
        devices = sd.query_devices()
        result = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                name = d["name"]
                # Linux: PulseAudio/PipeWire の Monitor デバイスを検出
                is_loopback = "monitor" in name.lower() or "loopback" in name.lower()
                result.append({
                    "index": i,
                    "name": name,
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                    "is_loopback": is_loopback,
                })
        return result

    def _find_device(self) -> int | None:
        """デバイス名からデバイスインデックスを検索"""
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if self.device_name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
        return None

    # ===== ゲイン処理 =====

    def _apply_gain(self, audio_data: np.ndarray) -> np.ndarray:
        """入力音声にゲインを適用する。

        手動ゲイン: 固定倍率で増幅
        オートゲイン: 直近の RMS に基づきゲインを動的に調整し、
                      ターゲット RMS に近づける（AGC）
        """
        if self.auto_gain:
            rms = np.sqrt(np.mean(audio_data**2))
            if rms > self._noise_floor:
                # ターゲット RMS に到達するための理想ゲインを計算
                desired_gain = self._auto_gain_target / rms
                desired_gain = np.clip(desired_gain, self._gain_min, self._gain_max)
                # 急激な変化を避けるため指数移動平均で平滑化
                self._current_gain += self._gain_smoothing * (desired_gain - self._current_gain)
                self._current_gain = np.clip(self._current_gain, self._gain_min, self._gain_max)
            # ゲイン適用（ノイズフロア以下でも現在のゲインで増幅）
            audio_data = audio_data * self._current_gain
        elif self.input_gain != 1.0:
            audio_data = audio_data * self.input_gain

        # クリッピング防止: -1.0 〜 1.0 に収める
        np.clip(audio_data, -1.0, 1.0, out=audio_data)
        return audio_data

    # ===== コールバック =====

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice のコールバック。モードに応じて処理を分岐"""
        if status:
            print(f"[AudioCapture] Status: {status}")

        audio_data = indata[:, 0].copy()  # モノラルに変換

        # ゲイン適用（RMS/VAD 判定の前に増幅する）
        audio_data = self._apply_gain(audio_data)

        # 生オーディオを外部に通知（ストリーミング ASR 用）
        if self.on_audio:
            try:
                self.on_audio(audio_data)
            except Exception:
                pass  # コールバックのエラーでキャプチャを止めない

        if self.use_vad:
            self._vad_callback(audio_data)
        else:
            self._rms_callback(audio_data)

    def _rms_callback(self, audio_data):
        """従来の RMS ベース処理（固定チャンク + RMS 閾値）"""
        self._buffer.append(audio_data)
        self._buffer_samples += len(audio_data)

        # チャンクサイズに達したらキューに投入
        if self._buffer_samples >= self.chunk_samples:
            chunk = np.concatenate(self._buffer)
            audio_chunk = chunk[: self.chunk_samples]
            remaining = chunk[self.chunk_samples:]

            # 無音チェック: RMS が閾値以上ならキューに追加
            rms = np.sqrt(np.mean(audio_chunk**2))
            if self.on_level:
                self.on_level(rms, rms > self.silence_threshold)
            if rms > self.silence_threshold:
                self.audio_queue.put(audio_chunk)

            # 残りをバッファに戻す
            self._buffer = [remaining] if len(remaining) > 0 else []
            self._buffer_samples = len(remaining)

    def _vad_callback(self, audio_data):
        """VAD ベースの発話検出処理（発話単位でキューに投入）"""
        is_speech = self._vad.is_speech(audio_data)

        # RMS も計算（レベルメーター表示用）
        rms = np.sqrt(np.mean(audio_data**2))
        if self.on_level:
            self.on_level(rms, is_speech)

        if is_speech:
            # 音声あり → バッファに追加
            self._speech_active = True
            self._silence_frame_count = 0
            self._speech_buffer.append(audio_data)
            self._speech_buffer_samples += len(audio_data)

            # 最大長チェック（安全リミット）
            if self._speech_buffer_samples >= self._vad_max_samples:
                print(f"[VAD] 最大長到達 ({self._vad_max_samples / self.sample_rate:.0f}s)")
                self._emit_utterance()

        else:
            if self._speech_active:
                # 音声なし + 発話中 → 無音フレームをカウント
                # 自然さのために無音部分もバッファに含める
                self._speech_buffer.append(audio_data)
                self._speech_buffer_samples += len(audio_data)
                self._silence_frame_count += 1

                if self._silence_frame_count >= self._vad_hold_frames:
                    # 無音が十分続いた → 発話終了
                    self._emit_utterance()

    def _emit_utterance(self):
        """バッファに溜まった発話音声をキューに投入"""
        if self._speech_buffer_samples < self._vad_min_samples:
            # 短すぎる音声は無視（咳やクリック音など）
            duration = self._speech_buffer_samples / self.sample_rate
            print(f"[VAD] 短い音声をスキップ ({duration:.2f}s < {self._vad_min_samples / self.sample_rate:.1f}s)")
        else:
            utterance = np.concatenate(self._speech_buffer)
            duration = len(utterance) / self.sample_rate
            print(f"[VAD] 発話検出 ({duration:.1f}s)")
            self.audio_queue.put(utterance)

        # 状態リセット
        self._speech_buffer = []
        self._speech_buffer_samples = 0
        self._speech_active = False
        self._silence_frame_count = 0
        self._vad.reset()

    # ===== 制御 =====

    def start(self):
        """音声キャプチャを開始"""
        device_index = self._find_device()
        if device_index is None:
            available = self.list_devices()
            device_names = [d["name"] for d in available]
            raise RuntimeError(
                f"デバイス '{self.device_name}' が見つかりません。\n"
                f"利用可能な入力デバイス: {device_names}\n"
                f"--list-devices でデバイスを確認してください。"
            )

        self._running = True
        self._buffer = []
        self._buffer_samples = 0

        # オートゲイン状態をリセット
        if self.auto_gain:
            self._current_gain = self.input_gain

        # VAD 状態をリセット
        if self.use_vad:
            self._speech_buffer = []
            self._speech_buffer_samples = 0
            self._speech_active = False
            self._silence_frame_count = 0
            self._vad.reset()

        # VAD モードでは 100ms ブロック（細かい粒度で検出）
        # 通常モードでは 0.5s ブロック
        block_duration = self._vad_block_duration if self.use_vad else 0.5

        self._stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=int(self.sample_rate * block_duration),
            callback=self._audio_callback,
        )
        self._stream.start()
        mode = "VAD" if self.use_vad else "RMS"
        print(f"[AudioCapture] キャプチャ開始: {self.device_name} "
              f"(index={device_index}, mode={mode}, block={block_duration}s)")

    def stop(self):
        """音声キャプチャを停止"""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self.use_vad:
            # VAD: 残りの発話をフラッシュ
            if self._speech_buffer and self._speech_buffer_samples >= self._vad_min_samples:
                utterance = np.concatenate(self._speech_buffer)
                self.audio_queue.put(utterance)
            self._speech_buffer = []
            self._speech_buffer_samples = 0
        else:
            # RMS: 残りのバッファをフラッシュ
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
