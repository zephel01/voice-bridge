"""
翻訳モジュール
deep-translator を使って英語を日本語に翻訳する
"""

import time

try:
    from deep_translator import GoogleTranslator
except ImportError:
    raise ImportError("deep-translator が必要です: pip install deep-translator")


class Translator:
    """Google Translate を使った英日翻訳"""

    def __init__(self, source: str = "en", target: str = "ja", max_retries: int = 3):
        self.source = source
        self.target = target
        self.max_retries = max_retries
        self._translator = GoogleTranslator(source=source, target=target)

    def translate(self, text: str) -> str:
        """
        テキストを翻訳する

        Args:
            text: 英語テキスト

        Returns:
            日本語に翻訳されたテキスト
        """
        if not text or not text.strip():
            return ""

        for attempt in range(self.max_retries):
            try:
                result = self._translator.translate(text.strip())
                return result if result else ""
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 0.5 * (attempt + 1)
                    print(f"[Translator] 翻訳エラー (リトライ {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait)
                else:
                    print(f"[Translator] 翻訳失敗: {e}")
                    return f"[翻訳エラー] {text}"


if __name__ == "__main__":
    t = Translator()
    result = t.translate("Hello, how are you today?")
    print(f"翻訳結果: {result}")
