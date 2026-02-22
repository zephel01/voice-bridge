#!/usr/bin/env python3
"""
Voice Bridge - リアルタイム英日翻訳アプリ
YouTubeの英語音声をリアルタイムで日本語音声に翻訳する

使い方:
  python main.py          # GUI モード
  python main.py --cli    # CLI モード（デバッグ用）
  python main.py --list-devices  # 入力デバイス一覧を表示
"""

import argparse
import platform
import sys
import threading
import signal
import time

# OS に応じた AudioCapture を選択
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    from audio_capture_win import WindowsAudioCapture as AudioCapture
    DEFAULT_DEVICE = "default"
else:
    from audio_capture import AudioCapture
    DEFAULT_DEVICE = "BlackHole 2ch"

from transcriber import Transcriber
from translator import Translator
from tts_engine import TTSEngine
from tts_voicevox import VoicevoxTTS
from player import AudioPlayer


class VoiceBridge:
    """メインアプリケーションクラス"""

    def __init__(
        self,
        device_name: str = DEFAULT_DEVICE,
        model_size: str = "small",
        voice: str = "nanami",
        chunk_duration: float = 4.0,
        use_voicevox: bool = False,
        voicevox_speaker_id: int = 3,
    ):
        self.capture = AudioCapture(
            device_name=device_name,
            chunk_duration=chunk_duration,
        )
        self.transcriber = Transcriber(model_size=model_size)
        self.translator = Translator()

        # TTS エンジン: VOICEVOX が利用可能ならそちらを使う
        self.use_voicevox = use_voicevox
        if use_voicevox:
            self.tts = VoicevoxTTS(speaker_id=voicevox_speaker_id)
            print(f"[VoiceBridge] TTS: VOICEVOX (speaker_id={voicevox_speaker_id})")
        else:
            self.tts = TTSEngine(voice=voice)
            print(f"[VoiceBridge] TTS: Edge TTS (voice={voice})")

        self.player = AudioPlayer()

        self._running = False
        self._pipeline_thread = None

        # GUI コールバック用
        self.on_english_text = None
        self.on_japanese_text = None
        self.on_status_change = None
        self.on_level = None       # (rms: float, is_active: bool)
        self.on_latency = None     # (latency_sec: float, stage: str)

        # 音声レベルコールバックを AudioCapture に接続
        self.capture.on_level = self._on_capture_level

    def _on_capture_level(self, rms: float, is_active: bool):
        """AudioCapture からのレベル通知を中継"""
        if self.on_level:
            self.on_level(rms, is_active)

    def _notify_latency(self, latency: float, stage: str):
        """遅延情報を通知"""
        if self.on_latency:
            self.on_latency(latency, stage)

    def _pipeline_loop(self):
        """メインパイプラインループ"""
        self._notify_status("モデルロード中...")
        self.transcriber.load_model()
        self._notify_status("キャプチャ中...")

        while self._running:
            # 1. 音声チャンクを取得
            audio_chunk = self.capture.get_chunk(timeout=1.0)
            if audio_chunk is None:
                continue

            t_start = time.time()
            self._notify_status("認識中...")

            # 2. 音声認識（英語テキスト化）
            t_step = time.time()
            try:
                english_text = self.transcriber.transcribe(audio_chunk)
            except Exception as e:
                print(f"[Pipeline] 音声認識エラー: {e}")
                continue
            t_transcribe = time.time() - t_step

            if not english_text.strip():
                self._notify_status("キャプチャ中...")
                continue

            print(f"[EN] {english_text}")
            if self.on_english_text:
                self.on_english_text(english_text)

            # 3. 翻訳（英→日）
            self._notify_status("翻訳中...")
            t_step = time.time()
            try:
                japanese_text = self.translator.translate(english_text)
            except Exception as e:
                print(f"[Pipeline] 翻訳エラー: {e}")
                continue
            t_translate = time.time() - t_step

            if not japanese_text.strip():
                self._notify_status("キャプチャ中...")
                continue

            print(f"[JA] {japanese_text}")
            if self.on_japanese_text:
                self.on_japanese_text(japanese_text)

            # 4. 日本語音声合成
            self._notify_status("音声合成中...")
            t_step = time.time()
            try:
                audio_path = self.tts.synthesize(japanese_text)
            except Exception as e:
                print(f"[Pipeline] TTS エラー: {e}")
                continue
            t_tts = time.time() - t_step

            if audio_path:
                self.player.enqueue(audio_path)

            t_total = time.time() - t_start
            # チャンク蓄積時間も加算した実質遅延
            total_with_chunk = t_total + self.capture.chunk_duration
            print(f"[Latency] 認識={t_transcribe:.1f}s 翻訳={t_translate:.1f}s TTS={t_tts:.1f}s "
                  f"処理計={t_total:.1f}s 実質遅延={total_with_chunk:.1f}s")
            self._notify_latency(total_with_chunk,
                f"認識{t_transcribe:.1f}s+翻訳{t_translate:.1f}s+TTS{t_tts:.1f}s")

            self._notify_status("キャプチャ中...")

    def _notify_status(self, status: str):
        if self.on_status_change:
            self.on_status_change(status)

    def start(self):
        """翻訳パイプラインを開始"""
        if self._running:
            return

        self._running = True
        self.capture.start()
        self.player.start()
        self._pipeline_thread = threading.Thread(target=self._pipeline_loop, daemon=True)
        self._pipeline_thread.start()
        print("[VoiceBridge] パイプライン開始")

    def stop(self):
        """翻訳パイプラインを停止"""
        self._running = False
        self.capture.stop()
        self.player.stop()
        self.tts.cleanup()

        if self._pipeline_thread:
            self._pipeline_thread.join(timeout=3.0)
            self._pipeline_thread = None

        print("[VoiceBridge] パイプライン停止")

    def change_model(self, model_size: str):
        self.transcriber.change_model(model_size)

    def change_device(self, device_name: str):
        was_running = self._running
        if was_running:
            self.capture.stop()
        self.capture.device_name = device_name
        if was_running:
            self.capture.start()

    def change_voice(self, voice_key: str):
        """声を変更する（Edge TTS の場合はキー名、VOICEVOX の場合は speaker_id）"""
        if self.use_voicevox:
            try:
                speaker_id = int(voice_key)
                self.tts.set_speaker(speaker_id)
            except ValueError:
                print(f"[VoiceBridge] 無効な speaker_id: {voice_key}")
        else:
            self.tts.set_voice(voice_key)


def run_cli(args):
    """CLI モードで実行"""
    use_voicevox = VoicevoxTTS.is_available()
    bridge = VoiceBridge(
        device_name=args.device,
        model_size=args.model,
        voice=args.voice,
        chunk_duration=args.chunk,
        use_voicevox=use_voicevox,
        voicevox_speaker_id=args.speaker_id if use_voicevox else 3,
    )

    # Ctrl+C で停止
    def signal_handler(sig, frame):
        print("\n[CLI] 停止中...")
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    tts_name = "VOICEVOX" if use_voicevox else "Edge TTS"
    os_name = "Windows (WASAPI)" if IS_WINDOWS else "macOS (BlackHole)"
    print("=" * 50)
    print("  Voice Bridge - CLI モード")
    print(f"  OS: {os_name}")
    print(f"  デバイス: {args.device}")
    print(f"  モデル: {args.model}")
    print(f"  TTS: {tts_name}")
    print(f"  チャンク: {args.chunk}秒")
    print("  Ctrl+C で停止")
    print("=" * 50)

    bridge.start()

    # メインスレッドを生かしておく
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        bridge.stop()


def run_gui(args):
    """GUI モードで実行"""
    from gui import VoiceBridgeGUI

    # 利用可能なデバイス一覧を取得
    try:
        devices = [d["name"] for d in AudioCapture.list_devices()]
    except Exception:
        devices = [DEFAULT_DEVICE]

    # VOICEVOX が起動しているか確認
    voicevox_available = VoicevoxTTS.is_available()
    voicevox_speakers = {}
    if voicevox_available:
        voicevox_speakers = VoicevoxTTS.fetch_speakers()
        print(f"[VoiceBridge] VOICEVOX 検出: {len(voicevox_speakers)}話者")
    else:
        print("[VoiceBridge] VOICEVOX 未検出 → Edge TTS を使用")

    # デフォルトの speaker_id（ずんだもん ノーマル）
    default_speaker_id = 3

    bridge = VoiceBridge(
        device_name=args.device,
        model_size=args.model,
        voice=args.voice,
        chunk_duration=args.chunk,
        use_voicevox=voicevox_available,
        voicevox_speaker_id=default_speaker_id,
    )

    # 声変更のコールバック
    def on_voice_change(voice_key: str):
        if voicevox_available:
            sid = voicevox_speakers.get(voice_key)
            if sid is not None:
                bridge.change_voice(str(sid))
                # VOICEVOX 利用表記を更新（キャラクター名を反映）
                char_name = voice_key.split("（")[0]
                gui.set_credit(f"VOICEVOX:{char_name} | https://voicevox.hiroshiba.jp/")
            else:
                print(f"[GUI] 不明な話者: {voice_key}")
        else:
            bridge.change_voice(voice_key)

    gui = VoiceBridgeGUI(
        on_start=bridge.start,
        on_stop=bridge.stop,
        on_model_change=bridge.change_model,
        on_device_change=bridge.change_device,
        on_voice_change=on_voice_change,
    )

    # GUI にテキストを表示するコールバック
    bridge.on_english_text = gui.add_english_text
    bridge.on_japanese_text = gui.add_japanese_text
    bridge.on_status_change = gui.set_status
    bridge.on_level = gui.set_level
    bridge.on_latency = gui.set_latency

    # 声のリストを構築
    if voicevox_available:
        voice_list = list(voicevox_speakers.keys())
        default_voice = "ずんだもん（ノーマル）" if "ずんだもん（ノーマル）" in voice_list else voice_list[0]
    else:
        voice_list = ["nanami（女性）", "keita（男性）"]
        default_voice = "nanami（女性）"

    gui.build(devices=devices, voices=voice_list, default_voice=default_voice)

    # VOICEVOX 利用表記（利用規約に基づくクレジット表記）
    if voicevox_available:
        credit = f"VOICEVOX:{default_voice.split('（')[0]} | https://voicevox.hiroshiba.jp/"
        gui.set_credit(credit)

    gui.run()


def main():
    parser = argparse.ArgumentParser(
        description="Voice Bridge - リアルタイム英日翻訳",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli", action="store_true", help="CLI モードで起動（デバッグ用）")
    parser.add_argument("--list-devices", action="store_true", help="入力デバイス一覧を表示")
    parser.add_argument("--device", default=DEFAULT_DEVICE,
                        help=f"入力デバイス名 (default: {DEFAULT_DEVICE})")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"],
                        help="Whisper モデルサイズ")
    parser.add_argument("--voice", default="nanami", choices=["nanami", "keita"],
                        help="Edge TTS 音声 (VOICEVOX未使用時)")
    parser.add_argument("--speaker-id", type=int, default=3,
                        help="VOICEVOX speaker ID (default: 3 = ずんだもん)")
    parser.add_argument("--chunk", type=float, default=4.0, help="音声チャンク長（秒）")

    args = parser.parse_args()

    if args.list_devices:
        print("利用可能な入力デバイス:")
        for d in AudioCapture.list_devices():
            extra = ""
            if d.get("is_loopback"):
                extra = " [LOOPBACK]"
            print(f"  [{d['index']}] {d['name']} (ch={d['channels']}){extra}")
        return

    if args.cli:
        run_cli(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
