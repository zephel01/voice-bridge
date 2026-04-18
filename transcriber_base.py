"""
ASR（音声認識）エンジンの共通インターフェース

3 つの実装（faster-whisper, Moonshine, Qwen3-ASR）が揃っていて、
どれも main.py から同じように使われている。呼び出し側が if-elif-else で
3 エンジンを分岐していたのを、ここに集約されたプロトコル + ファクトリで置き換える。

Protocol を typing.runtime_checkable で提供しているので、
isinstance() による実行時チェックも可能（静的型チェックの代替）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from transcribe_result import TranscribeResult


@runtime_checkable
class TranscriberProtocol(Protocol):
    """音声認識エンジンが満たすべき共通インターフェース

    3 実装（transcriber / transcriber_moonshine / transcriber_qwen3）が
    すでに提供している API を抽出したもの。既存クラスはそのまま構造的に
    適合するため、明示的な継承や変更は不要。
    """

    # --- クラス属性 ---------------------------------------------------------
    # サポートする ISO 639-1 言語コードのリスト
    SUPPORTED_LANGUAGES: list[str]
    # 利用可能なモデルサイズ名のリスト
    AVAILABLE_MODELS: list[str]

    # --- インスタンス属性 --------------------------------------------------
    # 現在の認識言語（"auto" を含む）
    language: str
    # 現在のモデルサイズ
    model_size: str

    # --- メソッド -----------------------------------------------------------
    def load_model(self) -> None:
        """モデルをロード。失敗時は RuntimeError を raise する。"""
        ...

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscribeResult:
        """音声データからテキストを生成する。"""
        ...

    def set_language(self, language: str) -> bool:
        """認識言語を変更。サポート外言語の場合は False。"""
        ...

    def change_model(self, model_size: str) -> None:
        """モデルサイズを変更（次回ロード時に適用）。"""
        ...


# --- ファクトリ -----------------------------------------------------------

# サポートするエンジン名（--asr オプションと一致）
AVAILABLE_ENGINES = ("whisper", "moonshine", "qwen3")


def create_transcriber(
    engine: str,
    *,
    model_size: str = "small",
    language: str = "en",
    device: str = "cpu",
    compute_type: str = "int8",
) -> TranscriberProtocol:
    """ASR エンジン名から対応する Transcriber インスタンスを生成する。

    呼び出し側で if-elif-else していた分岐をここに集約する。
    モジュールの import はファクトリ内で遅延行い、未インストールの
    エンジンを選ばない限り ImportError を発生させない。

    Args:
        engine: "whisper" / "moonshine" / "qwen3"
        model_size: モデルサイズ名（各エンジンで解釈）
        language: 認識言語（"auto" 含む）
        device: "cpu" / "cuda"
        compute_type: "int8" / "float16" / "bfloat16" / "float32"

    Returns:
        TranscriberProtocol に適合するインスタンス

    Raises:
        ValueError: 未知のエンジン名
        ImportError: 選んだエンジンの依存パッケージが未インストール
    """
    engine = (engine or "whisper").lower()

    if engine == "moonshine":
        # 遅延 import: 未インストール環境でも他のエンジンは動かせる
        from transcriber_moonshine import Transcriber as MoonshineTranscriber

        return MoonshineTranscriber(
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type,
        )

    if engine == "qwen3":
        from transcriber_qwen3 import Transcriber as Qwen3Transcriber

        return Qwen3Transcriber(
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type,
        )

    if engine == "whisper":
        from transcriber import Transcriber as WhisperTranscriber

        return WhisperTranscriber(
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type,
        )

    raise ValueError(
        f"未知の ASR エンジン: {engine!r}。"
        f"対応: {', '.join(AVAILABLE_ENGINES)}"
    )
