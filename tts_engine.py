"""
TTS モジュール
edge-tts を使って日本語テキストを音声に変換する
"""

import asyncio
import tempfile
import os

try:
    import edge_tts
except ImportError:
    raise ImportError("edge-tts が必要です: pip install edge-tts")


class TTSEngine:
    """Microsoft Edge TTS を使った日本語音声合成"""

    # 利用可能な日本語音声
    VOICES = {
        "nanami": "ja-JP-NanamiNeural",   # 女性（自然で聞きやすい）
        "keita": "ja-JP-KeitaNeural",     # 男性
    }

    def __init__(self, voice: str = "nanami", rate: str = "+0%", volume: str = "+0%"):
        """
        Args:
            voice: 音声名 ("nanami" or "keita")
            rate: 速度調整 (例: "+10%", "-20%")
            volume: 音量調整 (例: "+10%", "-20%")
        """
        self.voice = self.VOICES.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_")
        self._counter = 0
        self._loop = None

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
        self.voice = self.VOICES.get(voice, voice)
        print(f"[TTSEngine] 音声を変更: {self.voice}")

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
