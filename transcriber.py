"""
音声認識モジュール
faster-whisper を使って複数言語の音声をテキストに変換する
対応言語: en, ja, zh, es, fr, de, ko
"""

import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise ImportError("faster-whisper が必要です: pip install faster-whisper")

from transcribe_result import TranscribeResult


class Transcriber:
    """faster-whisper を使った複数言語音声認識"""

    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2"]
    SUPPORTED_LANGUAGES = ["en", "ja", "zh", "es", "fr", "de", "ko"]
    LANGUAGE_NAMES = {
        "en": "English",
        "ja": "日本語",
        "zh": "中国語",
        "es": "スペイン語",
        "fr": "フランス語",
        "de": "ドイツ語",
        "ko": "韓国語",
    }

    # Whisper が無音時に出力しがちなハルシネーション（幻聴）パターン
    HALLUCINATION_PATTERNS = [
        "thank you",
        "thanks for watching",
        "subscribe",
        "like and subscribe",
        "please subscribe",
        "see you next time",
        "bye bye",
        "goodbye",
        "thank you for watching",
        "thanks for listening",
        "the end",
        "you",
        "...",
        "ご視聴ありがとうございました",
        "おやすみなさい",
        "ではまた",
        "お疲れ様でした",
    ]

    def __init__(self, model_size: str = "small", language: str = "en", device: str = "cpu", compute_type: str = "int8"):
        """
        Args:
            model_size: Whisper モデルサイズ (tiny/base/small/medium/large-v2)
            language: 認識言語 (en/ja/zh/es/fr/de/ko, default: en)
            device: "cpu" or "cuda"
            compute_type: "int8" (高速/CPU推奨) or "float16" (GPU) or "float32"
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def load_model(self):
        """モデルをロード（初回のみ）

        失敗時は self._model を None のままにして RuntimeError を raise する。
        呼び出し側はこれを捕捉して明示的にパイプラインを停止すること。
        """
        if self._model is not None:
            return
        print(f"[Transcriber] モデルをロード中: {self.model_size} (device={self.device}, compute_type={self.compute_type})")
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            print(f"[Transcriber] モデルロード完了")
        except Exception as e:
            self._model = None
            print(f"[Transcriber] モデルロード失敗: {e}")
            raise RuntimeError(
                f"Whisper モデルのロードに失敗しました (model={self.model_size}, "
                f"device={self.device}): {e}"
            ) from e

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscribeResult:
        """
        音声データからテキストを生成する

        Args:
            audio: numpy 配列の音声データ (float32, -1.0 ~ 1.0)
            sample_rate: サンプルレート

        Returns:
            TranscribeResult: 認識テキスト（str互換）+ detected_language, language_prob
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
        # language=None の場合、faster-whisper が自動検出する
        # VAD フィルタは無効化（audio_capture 側で既に音声検出を行っているため）
        lang_param = None if self.language == "auto" else self.language
        segments, info = self._model.transcribe(
            audio,
            language=lang_param,
            beam_size=5,  # 安定性重視
            vad_filter=False,  # 改善：True → False（audio_capture側で管理）
        )

        # 言語検出情報を取得
        detected_language = info.language  # faster-whisper は常に検出言語を返す
        language_prob = info.language_probability

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

        result_text = " ".join(text_parts)

        # ハルシネーション（幻聴）チェック
        if self._is_hallucination(result_text):
            print(f"[Transcriber] ハルシネーション検出（スキップ）: {result_text[:80]}")
            return TranscribeResult("", detected_language=detected_language, language_prob=language_prob)

        return TranscribeResult(result_text, detected_language=detected_language, language_prob=language_prob)

    def _is_hallucination(self, text: str) -> bool:
        """Whisper のハルシネーション（無音時の幻聴テキスト）を検出"""
        if not text:
            return False

        text_lower = text.strip().lower().rstrip(".!?,。！？、")

        # 完全一致 or ほぼ一致チェック
        for pattern in self.HALLUCINATION_PATTERNS:
            if text_lower == pattern.lower():
                return True

        # 非常に短いテキスト（3文字以下）はハルシネーションの可能性が高い
        if len(text.strip()) <= 3:
            print(f"[Transcriber] 短すぎるテキスト検出: '{text}'")
            return True

        # 同じフレーズの繰り返し検出（例: "Thank you. Thank you. Thank you."）
        words = text.strip().split('.')
        words = [w.strip() for w in words if w.strip()]
        if len(words) >= 2 and len(set(w.lower() for w in words)) == 1:
            return True

        return False

    def change_model(self, model_size: str):
        """モデルサイズを変更"""
        if model_size != self.model_size:
            self.model_size = model_size
            self._model = None  # 次回の transcribe で再ロード
            print(f"[Transcriber] モデルサイズを {model_size} に変更（次回ロード時に適用）")

    def set_language(self, language: str) -> bool:
        """認識言語を変更（"auto" で自動検出モード）"""
        if language == "auto":
            self.language = "auto"
            print(f"[Transcriber] 認識言語を自動検出モードに変更")
            return True

        if language not in self.SUPPORTED_LANGUAGES:
            print(f"[Transcriber] サポートされていない言語: {language}")
            print(f"[Transcriber] 対応言語: {', '.join(self.SUPPORTED_LANGUAGES)}")
            return False

        self.language = language
        lang_name = self.LANGUAGE_NAMES.get(language, language)
        print(f"[Transcriber] 認識言語を {lang_name} ({language}) に変更")
        return True


if __name__ == "__main__":
    # テスト: モデルロードのみ
    t = Transcriber(model_size="tiny")
    t.load_model()
    print("モデルロード成功")
