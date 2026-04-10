"""
音声認識結果クラス
str を継承して後方互換を保ちつつ、検出言語情報を追加する

使い方:
    # str として使える
    result = TranscribeResult("Hello world", detected_language="en")
    print(result)           # "Hello world"
    print(len(result))      # 11
    if result.strip():      # True
        ...

    # 言語情報にアクセス
    print(result.detected_language)  # "en"
    print(result.language_prob)      # 0.95
"""


class TranscribeResult(str):
    """音声認識の結果。str を継承しているのでテキストとして直接使える。

    追加属性:
        detected_language: 検出された言語コード (例: "en", "ja")。
                          言語検出非対応のエンジンでは None。
        language_prob:    言語検出の確信度 (0.0-1.0)。不明時は None。
    """

    def __new__(cls, text: str = "", detected_language: str = None, language_prob: float = None):
        instance = super().__new__(cls, text)
        instance.detected_language = detected_language
        instance.language_prob = language_prob
        return instance

    def __repr__(self) -> str:
        lang_info = ""
        if self.detected_language:
            lang_info = f", lang={self.detected_language!r}"
            if self.language_prob is not None:
                lang_info += f"({self.language_prob:.0%})"
        return f"TranscribeResult({str(self)!r}{lang_info})"
