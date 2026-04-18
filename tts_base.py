"""
TTS（音声合成）エンジンの共通インターフェース

3 実装（Edge TTS / VOICEVOX / CoeiroInk）に共通のプロトコルと、
VoiceBridge 起動時の TTS 選択ロジックをファクトリに集約する。

主な利用ポイント:
  - TTSBackend Protocol:    呼び出し側（main.py / gui.py）は engine
    の種別を気にせず synthesize / cleanup を呼べる。
  - create_tts(...):        use_coeiroink / use_voicevox / tts_language から
    適切なバックエンドを生成する。優先順位は CoeiroInk > VOICEVOX > Edge TTS
    （従来の main.py と同じ）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSBackend(Protocol):
    """音声合成エンジンが満たすべき共通インターフェース

    3 実装（TTSEngine / VoicevoxTTS / CoeiroinkTTS）がすでに提供している
    API を抽出したもの。既存クラスはそのまま構造的に適合するため、
    明示的な継承や変更は不要。
    """

    def synthesize(self, text: str) -> str | None:
        """テキストを音声ファイル（パス）に変換する。失敗時は None。"""
        ...

    def cleanup(self) -> None:
        """一時ファイルを後片付けする。"""
        ...


# --- ファクトリ -----------------------------------------------------------


def create_tts(
    *,
    tts_language: str,
    voice: str = "nanami",
    use_voicevox: bool = False,
    voicevox_speaker_id: int = 3,
    use_coeiroink: bool = False,
    coeiroink_speaker_id: int = 0,
) -> TTSBackend:
    """TTS バックエンドを選択・生成する。

    優先順位: CoeiroInk > VOICEVOX > Edge TTS。
    CoeiroInk / VOICEVOX はどちらも日本語専用のため、tts_language != "ja"
    の場合は自動的に Edge TTS にフォールバックする（従来と同じ挙動）。

    Args:
        tts_language: 合成言語（ja / en / zh / es / fr / de / ko）
        voice: Edge TTS 選択時の音声名（例: "nanami", "keita", "jenny"）
        use_voicevox: VOICEVOX 利用フラグ
        voicevox_speaker_id: VOICEVOX の話者 ID
        use_coeiroink: CoeiroInk 利用フラグ
        coeiroink_speaker_id: CoeiroInk のスタイル ID

    Returns:
        TTSBackend に適合するインスタンス。print 副作用として
        選択結果とフォールバック理由をログ出力する。
    """
    # CoeiroInk (日本語のみ)
    if use_coeiroink and tts_language == "ja":
        # 遅延 import: 依存が無い環境でも他バックエンドは動く
        from tts_coeiroink import CoeiroinkTTS

        tts = CoeiroinkTTS(speaker_id=coeiroink_speaker_id)
        print(f"[VoiceBridge] TTS: CoeiroInk (speaker_id={coeiroink_speaker_id})")
        return tts

    # VOICEVOX (日本語のみ)
    if use_voicevox and tts_language == "ja":
        from tts_voicevox import VoicevoxTTS

        tts = VoicevoxTTS(speaker_id=voicevox_speaker_id)
        print(f"[VoiceBridge] TTS: VOICEVOX (speaker_id={voicevox_speaker_id})")
        return tts

    # フォールバック理由をユーザーに通知（従来と同じ）
    if use_coeiroink and tts_language != "ja":
        print(
            "[VoiceBridge] CoeiroInk は日本語のみ対応のため、Edge TTS にフォールバック"
        )
    elif use_voicevox and tts_language != "ja":
        print(
            "[VoiceBridge] VOICEVOX は日本語のみ対応のため、Edge TTS にフォールバック"
        )

    # Edge TTS (全言語対応)
    from tts_engine import TTSEngine

    tts = TTSEngine(language=tts_language, voice=voice)
    print(f"[VoiceBridge] TTS: Edge TTS (language={tts_language})")
    return tts
