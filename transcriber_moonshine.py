"""
音声認識モジュール（Moonshine版）
moonshine-voice を使って複数言語の音声をテキストに変換する

使い方:
  pip install moonshine-voice

  # main.py の import を変更:
  # from transcriber import Transcriber
  # ↓
  # from transcriber_moonshine import Transcriber

対応言語: en, ja, zh, es, ko (Moonshine がサポートする言語のみ)
※ fr, de は Moonshine 未対応のため、この版では使用不可
"""

import numpy as np
import threading

try:
    import moonshine_voice
except ImportError:
    raise ImportError(
        "moonshine-voice が必要です: pip install moonshine-voice"
    )


class Transcriber:
    """moonshine-voice を使った複数言語音声認識（faster-whisper 互換インターフェース）"""

    # Moonshine 対応言語のみ（fr, de は未対応）
    SUPPORTED_LANGUAGES = ["en", "ja", "zh", "es", "ko"]
    LANGUAGE_NAMES = {
        "en": "English",
        "ja": "日本語",
        "zh": "中国語",
        "es": "スペイン語",
        "ko": "韓国語",
    }

    # Moonshine でも念のためハルシネーションチェックを残す
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

    # model_size は互換性のために受け取るが、Moonshine では言語ごとにモデルが決まる
    # device, compute_type も互換性のために受け取るが無視する（Moonshine は CPU 自動最適化）
    AVAILABLE_MODELS = ["tiny", "base", "small", "medium"]

    def __init__(
        self,
        model_size: str = "small",
        language: str = "en",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """
        Args:
            model_size: 互換性のため受け取るが Moonshine では使用しない
            language: 認識言語 (en/ja/zh/es/ko)
            device: 互換性のため受け取るが Moonshine では無視（常に CPU 最適化）
            compute_type: 互換性のため受け取るが Moonshine では無視
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._transcriber = None
        self._model_path = None
        self._model_arch = None

    def load_model(self):
        """モデルをロード（初回のみ）"""
        if self._transcriber is None:
            print(
                f"[Transcriber/Moonshine] モデルをロード中: language={self.language}"
            )
            try:
                self._model_path, self._model_arch = (
                    moonshine_voice.get_model_for_language(self.language)
                )
                self._transcriber = moonshine_voice.Transcriber(
                    model_path=self._model_path,
                    model_arch=self._model_arch,
                )
                print(f"[Transcriber/Moonshine] モデルロード完了")
            except Exception as e:
                print(f"[Transcriber/Moonshine] モデルロード失敗: {e}")
                raise

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        音声データからテキストを生成する（faster-whisper 互換インターフェース）

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

        # Moonshine のバッチ認識（ストリーミングなし版）
        try:
            transcript = self._transcriber.transcribe_without_streaming(
                audio, sample_rate
            )
        except Exception as e:
            print(f"[Transcriber/Moonshine] 認識エラー: {e}")
            return ""

        # TranscriptLine のリストからテキストを結合
        text_parts = []
        seen_texts = set()

        for line in transcript.lines:
            text = line.text.strip()
            if text and text not in seen_texts:
                text_parts.append(text)
                seen_texts.add(text)
            elif text and text in seen_texts:
                print(
                    f"[Transcriber/Moonshine] 重複行検出（スキップ）: {text[:50]}..."
                )

        result = " ".join(text_parts)

        # ハルシネーションチェック
        if self._is_hallucination(result):
            print(
                f"[Transcriber/Moonshine] ハルシネーション検出（スキップ）: {result[:80]}"
            )
            return ""

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
            print(f"[Transcriber/Moonshine] 短すぎるテキスト検出: '{text}'")
            return True

        # 同じフレーズの繰り返し検出
        words = text.strip().split(".")
        words = [w.strip() for w in words if w.strip()]
        if len(words) >= 2 and len(set(w.lower() for w in words)) == 1:
            return True

        return False

    def change_model(self, model_size: str):
        """モデルサイズ変更（互換性のため。Moonshine では言語変更で再ロード）"""
        if model_size != self.model_size:
            self.model_size = model_size
            # Moonshine ではモデルサイズの概念が異なるため、
            # 実際にはリロードしないが、ログは出す
            print(
                f"[Transcriber/Moonshine] model_size={model_size} を受け取りましたが、"
                f"Moonshine では言語ごとに最適なモデルが自動選択されます"
            )

    def set_language(self, language: str) -> bool:
        """認識言語を変更（言語変更時にモデルを再ロード）"""
        if language not in self.SUPPORTED_LANGUAGES:
            print(f"[Transcriber/Moonshine] サポートされていない言語: {language}")
            print(
                f"[Transcriber/Moonshine] 対応言語: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
            print(
                f"[Transcriber/Moonshine] ※ fr, de は Moonshine 未対応です"
            )
            return False

        if language != self.language:
            self.language = language
            self._transcriber = None  # 次回 transcribe で再ロード
            lang_name = self.LANGUAGE_NAMES.get(language, language)
            print(
                f"[Transcriber/Moonshine] 認識言語を {lang_name} ({language}) に変更"
                f"（次回ロード時に適用）"
            )
        return True


class StreamingTranscriber:
    """
    Moonshine のストリーミング機能を活用した高度な音声認識クラス

    将来的に main.py のパイプラインをストリーミング対応にする際に使用。
    イベントドリブンで、音声チャンクを逐次追加しながらリアルタイムに
    テキストを取得できる。

    使用例:
        def on_text(text, is_final):
            print(f"{'[確定]' if is_final else '[途中]'} {text}")

        st = StreamingTranscriber(language="en", on_text=on_text)
        st.load_model()
        st.start()
        # 音声チャンクを逐次追加
        st.add_audio(audio_chunk, sample_rate=16000)
        # ...
        st.stop()
    """

    SUPPORTED_LANGUAGES = Transcriber.SUPPORTED_LANGUAGES

    def __init__(
        self,
        language: str = "en",
        on_text=None,
        on_line_completed=None,
        update_interval: float = 0.3,
    ):
        """
        Args:
            language: 認識言語
            on_text: テキスト更新コールバック (text: str, is_final: bool) -> None
            on_line_completed: 行確定コールバック (text: str) -> None
            update_interval: 更新間隔（秒）。小さいほど応答性が高いが CPU 負荷増
        """
        self.language = language
        self.on_text = on_text
        self.on_line_completed = on_line_completed
        self.update_interval = update_interval
        self._transcriber = None
        self._listener = None
        self._running = False

    def load_model(self):
        """モデルをロード"""
        if self._transcriber is None:
            print(
                f"[StreamingTranscriber] モデルをロード中: language={self.language}"
            )
            model_path, model_arch = moonshine_voice.get_model_for_language(
                self.language
            )
            self._transcriber = moonshine_voice.Transcriber(
                model_path=model_path,
                model_arch=model_arch,
                update_interval=self.update_interval,
            )

            # イベントリスナーを登録
            self._listener = _TranscriptHandler(
                on_text=self.on_text,
                on_line_completed=self.on_line_completed,
            )
            self._transcriber.add_listener(self._listener)
            print(f"[StreamingTranscriber] モデルロード完了")

    def start(self):
        """ストリーミング開始"""
        self.load_model()
        self._transcriber.start()
        self._running = True
        print("[StreamingTranscriber] ストリーミング開始")

    def stop(self):
        """ストリーミング停止"""
        if self._transcriber and self._running:
            self._transcriber.stop()
            self._running = False
            print("[StreamingTranscriber] ストリーミング停止")

    def add_audio(self, audio: np.ndarray, sample_rate: int = 16000):
        """音声チャンクを追加（リアルタイムで逐次呼び出し）"""
        if not self._running:
            return
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        self._transcriber.add_audio(audio, sample_rate)

    def set_language(self, language: str) -> bool:
        """言語を変更（ストリーミング再起動が必要）"""
        if language not in self.SUPPORTED_LANGUAGES:
            return False
        was_running = self._running
        if was_running:
            self.stop()
        self.language = language
        self._transcriber = None
        self._listener = None
        if was_running:
            self.start()
        return True


class _TranscriptHandler(moonshine_voice.TranscriptEventListener):
    """Moonshine イベントを Voice Bridge のコールバックに変換する内部クラス"""

    def __init__(self, on_text=None, on_line_completed=None):
        super().__init__()
        self._on_text = on_text
        self._on_line_completed = on_line_completed

    def on_line_started(self, event):
        """新しい行の認識が開始された"""
        if self._on_text and event.line.text:
            self._on_text(event.line.text, False)

    def on_line_text_changed(self, event):
        """認識中のテキストが更新された（途中経過）"""
        if self._on_text and event.line.text:
            self._on_text(event.line.text, False)

    def on_line_completed(self, event):
        """行の認識が確定した"""
        text = event.line.text.strip()
        if text:
            if self._on_text:
                self._on_text(text, True)
            if self._on_line_completed:
                self._on_line_completed(text)


if __name__ == "__main__":
    # テスト: モデルロードのみ
    print("=== Moonshine Transcriber テスト ===")
    t = Transcriber(language="en")
    t.load_model()
    print("モデルロード成功")

    # サポート言語の表示
    print(f"対応言語: {', '.join(Transcriber.SUPPORTED_LANGUAGES)}")
    print("※ fr, de は Moonshine 未対応のため、Whisper 版をご利用ください")
