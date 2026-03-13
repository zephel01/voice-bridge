"""
CoeiroInk TTS モジュール
ローカルで起動中の CoeiroInk エンジン (http://localhost:50031) を使って
テキストを音声に変換する

事前に CoeiroInk アプリを起動しておく必要がある。
対応キャラクター: リリンちゃん、他
"""

import json
import os
import tempfile

import requests

# デフォルトのキャラクター一覧（CoeiroInk エンジンから取得できない場合のフォールバック）
DEFAULT_SPEAKERS = {
    "リリンちゃん": 0,
}


class CoeiroinkTTS:
    """CoeiroInk エンジンを使った音声合成"""

    def __init__(self, speaker_id: int = 0, host: str = "http://localhost:50031"):
        """
        Args:
            speaker_id: キャラクターID（デフォルト: 0 = リリンちゃん）
            host: CoeiroInk エンジンの URL
        """
        self.speaker_id = speaker_id
        self.host = host
        self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_ci_")
        self._counter = 0

    @staticmethod
    def fetch_speakers(host: str = "http://localhost:50031") -> dict[str, int]:
        """
        CoeiroInk エンジンからキャラクター一覧を取得する

        Returns:
            {"キャラ名（スタイル）": speaker_id, ...}
        """
        try:
            resp = requests.get(f"{host}/speakers", timeout=3)
            resp.raise_for_status()
            speakers = resp.json()
        except Exception:
            return DEFAULT_SPEAKERS

        result = {}
        for speaker in speakers:
            name = speaker.get("name", "Unknown")
            for style in speaker.get("styles", []):
                style_name = style.get("name", "")
                sid = style.get("id", 0)
                if style_name == "ノーマル" or style_name == name or not style_name:
                    label = name
                else:
                    label = f"{name}（{style_name}）"
                result[label] = sid
        return result

    @staticmethod
    def is_available(host: str = "http://localhost:50031") -> bool:
        """CoeiroInk エンジンが起動しているか確認"""
        try:
            resp = requests.get(f"{host}/version", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def synthesize(self, text: str) -> str | None:
        """
        テキストを音声ファイル（wav）に変換する

        Args:
            text: 日本語テキスト

        Returns:
            生成された wav ファイルのパス。エラー時は None
        """
        if not text or not text.strip():
            return None

        self._counter += 1

        # 一時ディレクトリが消えていたら再作成
        if not os.path.exists(self._temp_dir):
            self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_ci_")

        output_path = os.path.join(self._temp_dir, f"ci_{self._counter:06d}.wav")

        try:
            # 1. audio_query: 読み上げクエリを作成
            resp = requests.post(
                f"{self.host}/audio_query",
                params={"text": text.strip(), "speaker": self.speaker_id},
                timeout=10,
            )
            resp.raise_for_status()
            query = resp.json()

            # 2. synthesis: 音声合成
            resp = requests.post(
                f"{self.host}/synthesis",
                params={"speaker": self.speaker_id},
                json=query,
                timeout=30,
            )
            resp.raise_for_status()

            # 3. WAV ファイルとして保存
            with open(output_path, "wb") as f:
                f.write(resp.content)

            return output_path

        except Exception as e:
            print(f"[CoeiroinkTTS] 音声合成エラー: {e}")
            return None

    def set_speaker(self, speaker_id: int):
        """キャラクターを変更"""
        self.speaker_id = speaker_id
        print(f"[CoeiroinkTTS] キャラクターを変更: speaker_id={speaker_id}")

    def cleanup(self):
        """一時ファイルを削除"""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            print(f"[CoeiroinkTTS] 一時ファイルを削除: {self._temp_dir}")


if __name__ == "__main__":
    if CoeiroinkTTS.is_available():
        print("CoeiroInk エンジンに接続OK")
        speakers = CoeiroinkTTS.fetch_speakers()
        print(f"利用可能なキャラクター ({len(speakers)}件):")
        for name, sid in speakers.items():
            print(f"  [{sid:3d}] {name}")
    else:
        print("CoeiroInk エンジンが起動していません")
        print("CoeiroInk Desktop アプリを起動してから再実行してください")
