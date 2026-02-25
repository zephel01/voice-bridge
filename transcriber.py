"""
音声認識モジュール
faster-whisper を使って英語音声をテキストに変換する
"""

import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise ImportError("faster-whisper が必要です: pip install faster-whisper")


class Transcriber:
    """faster-whisper を使った英語音声認識"""

    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2"]

    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        """
        Args:
            model_size: Whisper モデルサイズ (tiny/base/small/medium/large-v2)
            device: "cpu" or "cuda"
            compute_type: "int8" (高速/CPU推奨) or "float16" (GPU) or "float32"
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def load_model(self):
        """モデルをロード（初回のみ）"""
        if self._model is None:
            print(f"[Transcriber] モデルをロード中: {self.model_size} (device={self.device}, compute_type={self.compute_type})")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            print(f"[Transcriber] モデルロード完了")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        音声データからテキストを生成する

        Args:
            audio: numpy 配列の音声データ (float32, -1.0 ~ 1.0)
            sample_rate: サンプルレート

        Returns:
            認識されたテキスト
        """
        self.load_model()

        # float32 に変換
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # 音声の正規化（レベルを-1.0～1.0に調整）
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.95  # クリッピング防止

        # 音声認識実行
        # VAD フィルタは無効化（audio_capture 側で既に音声検出を行っているため）
        # 重複VAD処理による無音繰り返し問題を解決
        segments, info = self._model.transcribe(
            audio,
            language="en",
            beam_size=5,  # 安定性重視
            vad_filter=False,  # 改善：True → False（audio_capture側で管理）
        )

        # セグメントを結合（重複排除）
        text_parts = []
        seen_texts = set()  # 既に追加したテキストを追跡

        for segment in segments:
            text = segment.text.strip()
            if text and text not in seen_texts:  # 重複を除外
                text_parts.append(text)
                seen_texts.add(text)
            elif text and text in seen_texts:
                # 重複を検出した場合はログ出力
                print(f"[Transcriber] 重複セグメント検出（スキップ）: {text[:50]}...")

        result = " ".join(text_parts)
        return result

    def change_model(self, model_size: str):
        """モデルサイズを変更"""
        if model_size != self.model_size:
            self.model_size = model_size
            self._model = None  # 次回の transcribe で再ロード
            print(f"[Transcriber] モデルサイズを {model_size} に変更（次回ロード時に適用）")


if __name__ == "__main__":
    # テスト: モデルロードのみ
    t = Transcriber(model_size="tiny")
    t.load_model()
    print("モデルロード成功")
