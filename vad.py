"""
Silero VAD (Voice Activity Detection) ラッパーモジュール

RMS閾値ベースの無音検知をニューラルネットベースの音声活動検知に置き換え、
発話の開始・終了検知を大幅に改善する。

RCLIの設計（Silero VAD によるリアルタイム無音フィルタリング）を参考にした。
"""

import numpy as np


class SileroVAD:
    """Silero VAD によるリアルタイム音声活動検知"""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        """
        Args:
            threshold: スピーチ判定の確率閾値 (0.0〜1.0)。
                       高くすると誤検知が減るが、小声を見逃しやすくなる。
            sample_rate: サンプリングレート（16000 推奨）
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.model = None
        self._torch = None
        self._loaded = False

    def load(self):
        """モデルをロード"""
        if self._loaded:
            return

        try:
            import torch
            self._torch = torch
        except ImportError:
            raise ImportError(
                "Silero VAD には PyTorch が必要です: pip install torch"
            )

        try:
            model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True,
            )
            self.model = model
            self._loaded = True
            print("[VAD] Silero VAD ロード完了")
        except Exception as e:
            raise RuntimeError(f"Silero VAD ロード失敗: {e}")

    def speech_probability(self, audio: np.ndarray) -> float:
        """
        音声データのスピーチ確率を取得

        Args:
            audio: float32 の音声データ (1次元)

        Returns:
            スピーチ確率 (0.0〜1.0)。複数ウィンドウの最大値。
        """
        if not self._loaded:
            self.load()

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        tensor = self._torch.from_numpy(audio)

        # Silero VAD は 512 サンプル単位で処理 (16kHz で 32ms)
        window_size = 512
        max_prob = 0.0

        for i in range(0, len(tensor) - window_size + 1, window_size):
            chunk = tensor[i:i + window_size]
            prob = self.model(chunk, self.sample_rate).item()
            max_prob = max(max_prob, prob)

        return max_prob

    def is_speech(self, audio: np.ndarray) -> bool:
        """音声データに人の声が含まれているか"""
        return self.speech_probability(audio) > self.threshold

    def reset(self):
        """内部状態をリセット（発話の区切りで呼ぶ）"""
        if self.model is not None:
            self.model.reset_states()


def is_available() -> bool:
    """Silero VAD が利用可能か（PyTorch がインストールされているか）"""
    try:
        import torch
        return True
    except ImportError:
        return False
