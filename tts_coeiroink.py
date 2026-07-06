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
from urllib.parse import urlparse

import requests

# デフォルトのキャラクター一覧（CoeiroInk エンジンから取得できない場合のフォールバック）
# 形式: "キャラ名（スタイル）": "UUID:styleId"
DEFAULT_SPEAKERS = {
    "リリンちゃん（のーまる）": "cb11bdbd-78fc-4f16-b528-a400bae1782d:90",
}


class CoeiroinkTTS:
    """CoeiroInk エンジンを使った音声合成"""

    def __init__(self, speaker_id: int = 90, speaker_uuid: str = None, host: str = None):
        """
        Args:
            speaker_id: スタイルID（デフォルト: 90 = リリンちゃん・ノーマル）
            speaker_uuid: キャラクター UUID（デフォルト: リリンちゃん）
            host: CoeiroInk エンジンの URL (デフォルト: 環境変数 COEIROINK_HOST or http://localhost:50031)
        """
        import os
        if host is None:
            host = os.environ.get("COEIROINK_HOST", "http://localhost:50031")

        parsed = urlparse(host)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"host のURLスキームは http/https のみ許可されています: {host!r}"
            )

        self.speaker_id = speaker_id
        self.speaker_uuid = speaker_uuid or "cb11bdbd-78fc-4f16-b528-a400bae1782d"  # デフォルト: リリンちゃん
        self.host = host
        self.session = requests.Session()
        self._temp_dir = tempfile.mkdtemp(prefix="voice_bridge_ci_")
        self._counter = 0

    @staticmethod
    def fetch_speakers(host: str = None) -> dict[str, int]:
        """
        CoeiroInk エンジンからキャラクター一覧を取得する

        Args:
            host: CoeiroInk エンジンの URL (デフォルト: 環境変数 COEIROINK_HOST or http://localhost:50031)

        Returns:
            {"キャラ名（スタイル）": speaker_id, ...}
        """
        import os
        if host is None:
            host = os.environ.get("COEIROINK_HOST", "http://localhost:50031")
        try:
            resp = requests.get(f"{host}/v1/speakers", timeout=3)
            resp.raise_for_status()
            speakers = resp.json()
        except Exception:
            return DEFAULT_SPEAKERS

        result = {}
        for speaker in speakers:
            speaker_name = speaker.get("speakerName", "Unknown")
            speaker_uuid = speaker.get("speakerUuid", "")
            for style in speaker.get("styles", []):
                style_name = style.get("styleName", "")
                style_id = style.get("styleId", 0)
                if style_name == "ノーマル" or not style_name:
                    label = speaker_name
                else:
                    label = f"{speaker_name}（{style_name}）"
                # キャラクター情報を保存（uuid:styleId の形式で、GUI で使用）
                result[label] = f"{speaker_uuid}:{style_id}"
        return result

    @staticmethod
    def is_available(host: str = None) -> bool:
        """
        CoeiroInk エンジンが起動しているか確認

        Args:
            host: CoeiroInk エンジンの URL (デフォルト: 環境変数 COEIROINK_HOST or http://localhost:50031)
        """
        import os
        if host is None:
            host = os.environ.get("COEIROINK_HOST", "http://localhost:50031")
        try:
            resp = requests.get(f"{host}/v1/speakers", timeout=2)
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
            # CoeiroInk API: /v1/synthesis で音声合成
            payload = {
                "text": text.strip(),
                "speakerUuid": self.speaker_uuid,
                "styleId": self.speaker_id,
                "speedScale": 1.0,
                "volumeScale": 1.0,
                "pitchScale": 0.0,
                "intonationScale": 1.0,
                "prePhonemeLength": 0.0,
                "postPhonemeLength": 0.0,
                "outputSamplingRate": 44100,
            }

            print(f"[CoeiroinkTTS] リクエスト: uuid={self.speaker_uuid}, styleId={self.speaker_id}")
            resp = self.session.post(
                f"{self.host}/v1/synthesis",
                json=payload,
                headers={"Accept": "audio/wav"},
                timeout=30,
            )
            print(f"[CoeiroinkTTS] ステータスコード: {resp.status_code}")
            resp.raise_for_status()

            # WAV ファイルとして保存
            with open(output_path, "wb") as f:
                f.write(resp.content)

            return output_path

        except Exception as e:
            print(f"[CoeiroinkTTS] 音声合成エラー: {e}")
            return None

    def set_speaker(self, style_id: int):
        """スタイル（声）を変更"""
        self.speaker_id = style_id
        print(f"[CoeiroinkTTS] スタイルを変更: style_id={style_id}")

    def set_speaker_uuid(self, speaker_uuid: str):
        """キャラクターを変更"""
        self.speaker_uuid = speaker_uuid
        print(f"[CoeiroinkTTS] キャラクターを変更: speaker_uuid={speaker_uuid}")

    def cleanup(self):
        """一時ファイルを削除"""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            print(f"[CoeiroinkTTS] 一時ファイルを削除: {self._temp_dir}")
        self.session.close()


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
