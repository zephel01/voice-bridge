"""
TTS モジュール
edge-tts を使って複数言語のテキストを音声に変換する
対応言語: ja, en, zh, es, fr, de, ko
"""

import asyncio
import tempfile
import os

try:
    import edge_tts
except ImportError:
    raise ImportError("edge-tts が必要です: pip install edge-tts")


class TTSEngine:
    """Microsoft Edge TTS を使った複数言語音声合成"""

    # 言語別の利用可能な音声
    LANGUAGE_VOICES = {
        "ja": {  # 日本語
            "nanami": "ja-JP-NanamiNeural",   # 女性（自然で聞きやすい）
            "keita": "ja-JP-KeitaNeural",     # 男性
        },
        "en": {  # 英語
            "jenny": "en-US-JennyNeural",     # 女性
            "guy": "en-US-GuyNeural",         # 男性
        },
        "zh": {  # 中国語
            "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # 女性
            "yunxi": "zh-CN-YunxiNeural",        # 男性
        },
        "es": {  # スペイン語
            "elvira": "es-ES-ElviraNeural",   # 女性
            "alvaro": "es-ES-AlvaroNeural",   # 男性
        },
        "fr": {  # フランス語
            "denise": "fr-FR-DeniseNeural",   # 女性
            "henri": "fr-FR-HenriNeural",     # 男性
        },
        "de": {  # ドイツ語
            "katja": "de-DE-KatjaNeural",     # 女性
            "conrad": "de-DE-ConradNeural",   # 男性
        },
        "ko": {  # 韓国語
            "sunhi": "ko-KR-SunHiNeural",     # 女性
            "injoon": "ko-KR-InJoonNeural",   # 男性
        },
    }

    # 後方互換性のため、従来の VOICES 名前も保持
    VOICES = LANGUAGE_VOICES.get("ja", {})

    def __init__(self, language: str = "ja", voice: str = "nanami", rate: str = "+0%", volume: str = "+0%"):
        """
        Args:
            language: 対象言語 (ja/en/zh/es/fr/de/ko, default: ja)
            voice: 言語別の音声名 (例: 日本語は "nanami"/"keita")
            rate: 速度調整 (例: "+10%", "-20%")
            volume: 音量調整 (例: "+10%", "-20%")
        """
        self.language = language

        # 言語別の音声を選択
        if language not in self.LANGUAGE_VOICES:
            raise ValueError(f"サポートされていない言語: {language}")

        language_voices = self.LANGUAGE_VOICES[language]
        self.voice = language_voices.get(voice, list(language_voices.values())[0])

        self.rate = rate
        self.volume = volume
        self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_")
        self._counter = 0
        self._loop = None

        print(f"[TTSEngine] 言語: {language}, 音声: {self.voice}")

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """イベントループを取得（なければ新規作成）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    async def _synthesize_async(self, text: str, output_path: str):
        """非同期で音声合成を実行"""
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
        )
        await communicate.save(output_path)

    def synthesize(self, text: str) -> str | None:
        """
        テキストを音声ファイル（mp3）に変換する

        Args:
            text: 日本語テキスト

        Returns:
            生成された mp3 ファイルのパス。エラー時は None
        """
        if not text or not text.strip():
            return None

        self._counter += 1
        output_path = os.path.join(self._temp_dir, f"tts_{self._counter:06d}.mp3")

        try:
            loop = self._get_loop()
            loop.run_until_complete(self._synthesize_async(text, output_path))
            return output_path
        except Exception as e:
            print(f"[TTSEngine] 音声合成エラー: {e}")
            return None

    def set_voice(self, voice: str):
        """音声を変更"""
        language_voices = self.LANGUAGE_VOICES.get(self.language, {})
        self.voice = language_voices.get(voice, voice)
        print(f"[TTSEngine] 音声を変更: {self.voice}")

    def set_language(self, language: str, voice: str = None) -> bool:
        """言語を変更"""
        if language not in self.LANGUAGE_VOICES:
            print(f"[TTSEngine] サポートされていない言語: {language}")
            return False

        self.language = language
        language_voices = self.LANGUAGE_VOICES[language]

        # 音声が指定されている場合
        if voice and voice in language_voices:
            self.voice = language_voices[voice]
        else:
            # 指定されていない場合は、言語のデフォルト音声を使用
            self.voice = list(language_voices.values())[0]

        print(f"[TTSEngine] 言語を {language} に変更、音声: {self.voice}")
        return True

    def set_rate(self, rate: str):
        """速度を変更"""
        self.rate = rate

    def cleanup(self):
        """一時ファイルを削除"""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            print(f"[TTSEngine] 一時ファイルを削除: {self._temp_dir}")


if __name__ == "__main__":
    engine = TTSEngine()
    path = engine.synthesize("こんにちは、これはテストです。")
    if path:
        print(f"音声ファイル生成: {path}")
    engine.cleanup()
