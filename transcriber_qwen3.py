"""
音声認識モジュール（Qwen3-ASR版）
qwen-asr パッケージを使って複数言語の音声をテキストに変換する

使い方:
  pip install qwen-asr

  # main.py の --asr オプションで切り替え:
  python main.py --asr qwen3

対応言語: en, ja, zh, es, fr, de, ko（52言語中、voice-bridge で使う7言語すべてをカバー）
※ Moonshine と違い、fr/de にも対応
"""

import re
import numpy as np

from transcribe_result import TranscribeResult

try:
    from qwen_asr import Qwen3ASRModel
except ImportError:
    raise ImportError(
        "qwen-asr が必要です: pip install qwen-asr\n"
        "GPU使用時は PyTorch (CUDA) も必要です"
    )


class Transcriber:
    """Qwen3-ASR を使った複数言語音声認識（faster-whisper 互換インターフェース）"""

    # voice-bridge の7言語すべてをサポート
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

    # Qwen3-ASR の言語名マッピング（voice-bridge の言語コード → Qwen3-ASR の言語名）
    LANGUAGE_MAP = {
        "en": "English",
        "ja": "Japanese",
        "zh": "Chinese",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ko": "Korean",
    }

    # モデルサイズのマッピング（互換性のため）
    MODEL_SIZE_MAP = {
        "tiny": "Qwen/Qwen3-ASR-0.6B",
        "base": "Qwen/Qwen3-ASR-0.6B",
        "small": "Qwen/Qwen3-ASR-0.6B",
        "medium": "Qwen/Qwen3-ASR-1.7B",
        "large": "Qwen/Qwen3-ASR-1.7B",
        "large-v2": "Qwen/Qwen3-ASR-1.7B",
        # 直接モデル名を指定することも可能
        "0.6b": "Qwen/Qwen3-ASR-0.6B",
        "1.7b": "Qwen/Qwen3-ASR-1.7B",
    }

    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "0.6b", "1.7b"]

    # ハルシネーションパターン（Whisper/Moonshine と同じフィルタ）
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

    def __init__(
        self,
        model_size: str = "small",
        language: str = "en",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """
        Args:
            model_size: モデルサイズ名 (tiny/base/small → 0.6B, medium/large → 1.7B)
                        または直接 "0.6b", "1.7b" を指定
            language: 認識言語 (en/ja/zh/es/fr/de/ko)
            device: "cpu" or "cuda" (Qwen3-ASR は GPU推奨だが CPU でも動作)
            compute_type: "int8", "float16", "bfloat16", "float32"
                          ※ Qwen3-ASR では dtype として変換して使用
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._model_name = self.MODEL_SIZE_MAP.get(
            model_size.lower(), "Qwen/Qwen3-ASR-0.6B"
        )

    def _get_torch_dtype(self):
        """compute_type から torch.dtype を決定"""
        import torch
        dtype_map = {
            "int8": torch.float32,  # int8 量子化は Qwen3-ASR 非対応のため float32 にフォールバック
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        return dtype_map.get(self.compute_type, torch.float32)

    def _get_device_map(self) -> str:
        """device からデバイスマップ文字列を決定"""
        if self.device == "cuda":
            return "cuda:0"
        return "cpu"

    def load_model(self):
        """モデルをロード（初回のみ）"""
        if self._model is None:
            import torch

            dtype = self._get_torch_dtype()
            device_map = self._get_device_map()

            print(
                f"[Transcriber/Qwen3-ASR] モデルをロード中: {self._model_name} "
                f"(device={device_map}, dtype={dtype})"
            )
            try:
                self._model = Qwen3ASRModel.from_pretrained(
                    self._model_name,
                    dtype=dtype,
                    device_map=device_map,
                    max_new_tokens=256,
                )
                print(f"[Transcriber/Qwen3-ASR] モデルロード完了")
            except Exception as e:
                print(f"[Transcriber/Qwen3-ASR] モデルロード失敗: {e}")
                raise

    # Qwen3-ASR の言語名 → voice-bridge の言語コード（逆引き）
    LANGUAGE_REVERSE_MAP = {
        "English": "en",
        "Japanese": "ja",
        "Chinese": "zh",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Korean": "ko",
    }

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscribeResult:
        """
        音声データからテキストを生成する（faster-whisper 互換インターフェース）

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

        # Qwen3-ASR で音声認識
        # language=None の場合、Qwen3-ASR が自動検出する
        qwen_language = None if self.language == "auto" else self.LANGUAGE_MAP.get(self.language)
        try:
            results = self._model.transcribe(
                audio=(audio, sample_rate),
                language=qwen_language,
                return_time_stamps=False,
            )
        except Exception as e:
            print(f"[Transcriber/Qwen3-ASR] 認識エラー: {e}")
            return TranscribeResult("")

        if not results:
            return TranscribeResult("")

        # 結果からテキストを取得（バッチ対応だが、ここでは1つのみ）
        text_parts = []
        seen_texts = set()
        detected_language = None
        for r in results:
            text = r.text.strip() if r.text else ""
            if text and text not in seen_texts:
                text_parts.append(text)
                seen_texts.add(text)
            # Qwen3-ASR は result.language に検出言語名を返す
            if r.language and detected_language is None:
                detected_language = self.LANGUAGE_REVERSE_MAP.get(r.language, r.language)

        result_text = " ".join(text_parts)

        # CJK テキストの場合、不要なスペースを除去
        active_lang = detected_language or self.language
        if active_lang in ("ja", "zh", "ko"):
            result_text = self._clean_cjk_text(result_text)

        # ハルシネーションチェック
        if self._is_hallucination(result_text):
            print(
                f"[Transcriber/Qwen3-ASR] ハルシネーション検出（スキップ）: {result_text[:80]}"
            )
            return TranscribeResult("", detected_language=detected_language)

        return TranscribeResult(result_text, detected_language=detected_language)

    @staticmethod
    def _clean_cjk_text(text: str) -> str:
        """CJK テキストの文字間スペースを除去する"""
        if not text:
            return text

        # CJK文字の範囲
        cjk_char = (
            r'[\u3000-\u303F'   # 句読点・記号
            r'\u3040-\u309F'    # ひらがな
            r'\u30A0-\u30FF'    # カタカナ
            r'\u4E00-\u9FFF'    # CJK統合漢字
            r'\uFF00-\uFFEF'    # 全角英数・記号
            r'\u3400-\u4DBF'    # CJK拡張A
            r'\uAC00-\uD7AF'    # ハングル音節
            r'？！。、]'
        )

        # CJK文字の間のスペースを除去（2回適用）
        result = re.sub(f'({cjk_char})\\s+({cjk_char})', r'\1\2', text)
        result = re.sub(f'({cjk_char})\\s+({cjk_char})', r'\1\2', result)
        return result

    def _is_hallucination(self, text: str) -> bool:
        """ハルシネーション（無音時の幻聴テキスト）を検出"""
        if not text:
            return False

        text_lower = text.strip().lower().rstrip(".!?,。！？、")

        for pattern in self.HALLUCINATION_PATTERNS:
            if text_lower == pattern.lower():
                return True

        # 非常に短いテキスト（3文字以下）
        if len(text.strip()) <= 3:
            print(f"[Transcriber/Qwen3-ASR] 短すぎるテキスト検出: '{text}'")
            return True

        # 同じフレーズの繰り返し検出
        words = text.strip().split(".")
        words = [w.strip() for w in words if w.strip()]
        if len(words) >= 2 and len(set(w.lower() for w in words)) == 1:
            return True

        return False

    def change_model(self, model_size: str):
        """モデルサイズ変更"""
        new_model_name = self.MODEL_SIZE_MAP.get(
            model_size.lower(), self._model_name
        )
        if new_model_name != self._model_name:
            self.model_size = model_size
            self._model_name = new_model_name
            self._model = None  # 次回の transcribe で再ロード
            print(
                f"[Transcriber/Qwen3-ASR] モデルを {new_model_name} に変更"
                f"（次回ロード時に適用）"
            )
        else:
            self.model_size = model_size
            print(
                f"[Transcriber/Qwen3-ASR] model_size={model_size} → "
                f"{new_model_name}（変更なし）"
            )

    def set_language(self, language: str) -> bool:
        """認識言語を変更（"auto" で自動検出モード）"""
        if language == "auto":
            self.language = "auto"
            print(f"[Transcriber/Qwen3-ASR] 認識言語を自動検出モードに変更")
            return True

        if language not in self.SUPPORTED_LANGUAGES:
            print(f"[Transcriber/Qwen3-ASR] サポートされていない言語: {language}")
            print(
                f"[Transcriber/Qwen3-ASR] 対応言語: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
            return False

        self.language = language
        lang_name = self.LANGUAGE_NAMES.get(language, language)
        print(
            f"[Transcriber/Qwen3-ASR] 認識言語を {lang_name} ({language}) に変更"
        )
        return True


if __name__ == "__main__":
    # テスト: モデルロードのみ
    print("=== Qwen3-ASR Transcriber テスト ===")
    t = Transcriber(model_size="small", language="en", device="cpu")
    print(f"モデル: {t._model_name}")
    print(f"対応言語: {', '.join(Transcriber.SUPPORTED_LANGUAGES)}")
    print("※ Moonshine と違い、fr/de にも対応しています")

    # GPU が使える場合のみモデルロードテスト
    try:
        import torch
        if torch.cuda.is_available():
            t_gpu = Transcriber(model_size="small", language="en", device="cuda")
            t_gpu.load_model()
            print("GPU モデルロード成功")
        else:
            print("GPU が利用できないため、モデルロードテストはスキップ")
            print("CPU でのロードは pip install qwen-asr 後にお試しください")
    except ImportError:
        print("PyTorch が見つかりません。モデルロードテストをスキップ")
