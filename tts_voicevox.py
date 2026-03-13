"""
VOICEVOX TTS モジュール
ローカルで起動中の VOICEVOX エンジン (http://localhost:50021) を使って
日本語テキストを音声に変換する

事前に VOICEVOX アプリを起動しておく必要がある。
"""

import json
import os
import tempfile

import requests

# デフォルトの話者一覧（VOICEVOX エンジンから取得できない場合のフォールバック）
DEFAULT_SPEAKERS = {
    "四国めたん（ノーマル）": 2,
    "四国めたん（あまあま）": 0,
    "四国めたん（ツンツン）": 6,
    "四国めたん（セクシー）": 4,
    "ずんだもん（ノーマル）": 3,
    "ずんだもん（あまあま）": 1,
    "ずんだもん（ツンツン）": 7,
    "ずんだもん（セクシー）": 5,
    "ずんだもん（ささやき）": 22,
    "ずんだもん（ヒソヒソ）": 38,
    "春日部つむぎ": 8,
    "波音リツ": 9,
    "雨晴はう": 10,
    "玄野武宏": 11,
    "白上虎太郎": 12,
    "青山龍星": 13,
    "冥鳴ひまり": 14,
    "九州そら（ノーマル）": 16,
    "もち子さん": 20,
    "剣崎雌雄": 21,
    "WhiteCUL": 23,
    "No.7（ノーマル）": 29,
    "ちび式じい": 42,
    "櫻歌ミコ": 43,
    "小夜/SAYO": 46,
    "ナースロボ＿タイプＴ": 47,
}


class VoicevoxTTS:
    """VOICEVOX エンジンを使った日本語音声合成"""

    def __init__(self, speaker_id: int = 3, host: str = "http://localhost:50021"):
        """
        Args:
            speaker_id: 話者ID（デフォルト: 3 = ずんだもん ノーマル）
            host: VOICEVOX エンジンの URL
        """
        self.speaker_id = speaker_id
        self.host = host
        self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_vv_")
        self._counter = 0

    @staticmethod
    def fetch_speakers(host: str = "http://localhost:50021") -> dict[str, int]:
        """
        VOICEVOX エンジンから話者一覧を取得する

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
            name = speaker["name"]
            for style in speaker["styles"]:
                style_name = style["name"]
                sid = style["id"]
                if style_name == "ノーマル" or style_name == name:
                    label = name
                else:
                    label = f"{name}（{style_name}）"
                result[label] = sid
        return result

    @staticmethod
    def is_available(host: str = "http://localhost:50021") -> bool:
        """VOICEVOX エンジンが起動しているか確認"""
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
            self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_vv_")

        output_path = os.path.join(self._temp_dir, f"vv_{self._counter:06d}.wav")

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
            print(f"[VoicevoxTTS] 音声合成エラー: {e}")
            return None

    def set_speaker(self, speaker_id: int):
        """話者を変更"""
        self.speaker_id = speaker_id
        print(f"[VoicevoxTTS] 話者を変更: speaker_id={speaker_id}")

    def cleanup(self):
        """一時ファイルを削除"""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            print(f"[VoicevoxTTS] 一時ファイルを削除: {self._temp_dir}")


if __name__ == "__main__":
    if VoicevoxTTS.is_available():
        print("VOICEVOX エンジンに接続OK")
        speakers = VoicevoxTTS.fetch_speakers()
        print(f"利用可能な話者 ({len(speakers)}件):")
        for name, sid in speakers.items():
            print(f"  [{sid:3d}] {name}")
    else:
        print("VOICEVOX エンジンが起動していません")
        print("VOICEVOXアプリを起動してから再実行してください")
