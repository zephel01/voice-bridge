#!/usr/bin/env python3
"""
Voice Bridge - リアルタイム英日翻訳アプリ
YouTubeの英語音声をリアルタイムで日本語音声に翻訳する

使い方:
  python main.py          # GUI モード（Whisper）
  python main.py --asr moonshine  # Moonshine で起動
  python main.py --cli    # CLI モード（デバッグ用）
  python main.py --list-devices  # 入力デバイス一覧を表示
"""

import argparse
import os
import platform
import queue
import sys
import threading
import signal
import time

# OS に応じた AudioCapture を選択
_SYSTEM = platform.system()
IS_WINDOWS = _SYSTEM == "Windows"
IS_LINUX = _SYSTEM == "Linux"

if IS_WINDOWS:
    from audio_capture_win import WindowsAudioCapture as AudioCapture
    DEFAULT_DEVICE = "default"
elif IS_LINUX:
    from audio_capture import AudioCapture
    DEFAULT_DEVICE = "default"
else:
    # macOS
    from audio_capture import AudioCapture
    DEFAULT_DEVICE = "BlackHole 2ch"

# ASR エンジンは --asr オプションで選択（デフォルト: whisper）
# main() の argparse で切り替え、VoiceBridge に注入する
from transcriber import Transcriber as WhisperTranscriber
from translator import Translator
from tts_engine import TTSEngine
from tts_voicevox import VoicevoxTTS
from tts_coeiroink import CoeiroinkTTS
from player import AudioPlayer
from translation_logger import TranslationLogger
from ai_chat import AiChat, load_dotenv
from latency_tracker import LatencyTracker

# Live2D ブリッジ（オプション）。websockets 未インストール環境でも動くよう遅延ロード。
try:
    from live2d_bridge import Live2DBridge, infer_emotion
except Exception as _e:  # pragma: no cover
    Live2DBridge = None  # type: ignore

    def infer_emotion(text: str) -> tuple[str, float]:  # type: ignore
        return ("neutral", 1.0)

# .env から環境変数をロード
load_dotenv()


class VoiceBridge:
    """メインアプリケーションクラス"""

    def __init__(
        self,
        device_name: str = DEFAULT_DEVICE,
        model_size: str = "small",
        source_language: str = "en",
        target_language: str = "ja",
        tts_language: str = None,
        voice: str = "nanami",
        chunk_duration: float = 4.0,
        use_voicevox: bool = False,
        voicevox_speaker_id: int = 3,
        use_coeiroink: bool = False,
        coeiroink_speaker_id: int = 0,
        asr_engine: str = "whisper",
        asr_device: str = "cpu",
        mode: str = "translate",
        ai_base_url: str = "https://api.openai.com/v1",
        ai_api_key: str = None,
        ai_model: str = "gpt-4o-mini",
        use_vad: bool = False,
        live2d_enabled: bool = False,
        live2d_host: str = "127.0.0.1",
        live2d_port: int = 8765,
    ):
        # TTS言語はデフォルトで翻訳言語と同じ
        if tts_language is None:
            tts_language = target_language

        self.source_language = source_language
        self.target_language = target_language
        self.tts_language = tts_language

        self.asr_engine = asr_engine
        self.use_vad = use_vad

        # VAD はチャットモードでのみ有効（発話単位のセグメンテーション）
        enable_vad = use_vad and mode == "chat"
        self.capture = AudioCapture(
            device_name=device_name,
            chunk_duration=chunk_duration,
            use_vad=enable_vad,
        )
        if enable_vad:
            print(f"[VoiceBridge] VAD: Silero VAD（発話単位検出）")

        # ASR エンジンの選択
        if asr_engine == "moonshine":
            from transcriber_moonshine import Transcriber as MoonshineTranscriber
            self.transcriber = MoonshineTranscriber(model_size=model_size, language=source_language)
            print(f"[VoiceBridge] ASR: Moonshine (language={source_language})")
        elif asr_engine == "qwen3":
            from transcriber_qwen3 import Transcriber as Qwen3Transcriber
            self.transcriber = Qwen3Transcriber(model_size=model_size, language=source_language, device=asr_device)
            print(f"[VoiceBridge] ASR: Qwen3-ASR (model={model_size}, language={source_language})")
        else:
            self.transcriber = WhisperTranscriber(model_size=model_size, language=source_language)
            print(f"[VoiceBridge] ASR: faster-whisper (model={model_size}, language={source_language})")
        # チャットモードでは翻訳不要
        if mode != "chat":
            # auto モードでは検出前のデフォルトとして en→target で初期化
            translator_source = "en" if source_language == "auto" else source_language
            self.translator = Translator(source=translator_source, target=target_language)
        else:
            self.translator = None

        # TTS エンジン選択: CoeiroInk > VOICEVOX > Edge TTS
        self.use_voicevox = use_voicevox
        self._voicevox_speaker_id = voicevox_speaker_id

        if use_coeiroink and tts_language == "ja":
            self.tts = CoeiroinkTTS(speaker_id=coeiroink_speaker_id)
            print(f"[VoiceBridge] TTS: CoeiroInk (speaker_id={coeiroink_speaker_id})")
        elif use_voicevox and tts_language == "ja":
            self.tts = VoicevoxTTS(speaker_id=voicevox_speaker_id)
            print(f"[VoiceBridge] TTS: VOICEVOX (speaker_id={voicevox_speaker_id})")
        else:
            if use_coeiroink and tts_language != "ja":
                print(f"[VoiceBridge] CoeiroInk は日本語のみ対応のため、Edge TTS にフォールバック")
            elif use_voicevox and tts_language != "ja":
                print(f"[VoiceBridge] VOICEVOX は日本語のみ対応のため、Edge TTS にフォールバック")
            self.tts = TTSEngine(language=tts_language, voice=voice)
            print(f"[VoiceBridge] TTS: Edge TTS (language={tts_language})")

        self.player = AudioPlayer()
        self.logger = TranslationLogger(log_dir="logs")

        # Live2D ブリッジ（オプション）。接続中クライアントがあれば
        # TTS を pygame ではなく Live2D フロントへ転送する。
        self.live2d = None
        self.live2d_enabled = live2d_enabled
        if live2d_enabled:
            if Live2DBridge is None:
                print("[VoiceBridge] Live2D ブリッジは websockets が未インストールのため無効")
            else:
                try:
                    self.live2d = Live2DBridge(host=live2d_host, port=live2d_port)
                    self.live2d.start()
                    print(f"[VoiceBridge] Live2D ブリッジ: ws://{live2d_host}:{live2d_port}")
                except Exception as e:
                    print(f"[VoiceBridge] Live2D ブリッジ起動失敗: {e}")
                    self.live2d = None

        # モード: "translate"（翻訳）or "chat"（AI会話）
        self.mode = mode
        self.ai_chat = None
        if mode == "chat":
            self.ai_chat = AiChat(
                base_url=ai_base_url,
                api_key=ai_api_key,
                model=ai_model,
                response_language=tts_language or target_language,
            )
            print(f"[VoiceBridge] モード: AI チャット")
        else:
            print(f"[VoiceBridge] モード: 翻訳")

        self._running = False
        self._pipeline_thread = None
        self._is_playing = False  # TTS再生中フラグ（フィードバックループ防止）

        # ストリーミング ASR（Moonshine + VAD 時に有効）
        self._streaming_asr = None
        self._streaming_lines = None  # queue.Queue for thread-safe line collection
        self._streaming_partial = ""  # 途中経過テキスト
        if enable_vad and asr_engine == "moonshine":
            self._setup_streaming_asr()

        # レイテンシ計測
        self.latency_tracker = LatencyTracker(max_history=100)

        # GUI コールバック用
        self.on_english_text = None
        self.on_japanese_text = None
        self.on_status_change = None
        self.on_level = None       # (rms: float, is_active: bool)
        self.on_latency = None     # (latency_sec: float, stage: str)
        self.on_language_detected = None  # (detected_lang: str, prob: float|None)

        # 音声レベルコールバックを AudioCapture に接続
        self.capture.on_level = self._on_capture_level

        # 再生状態のコールバックを AudioPlayer に接続（フィードバックループ防止）
        self.player.on_play_start = self._on_play_start
        self.player.on_play_end = self._on_play_end

    def _on_capture_level(self, rms: float, is_active: bool):
        """AudioCapture からのレベル通知を中継"""
        if self.on_level:
            self.on_level(rms, is_active)

    def _on_play_start(self):
        """TTS 再生開始時 — キャプチャを抑制"""
        self._is_playing = True
        print("[VoiceBridge] TTS再生開始 → キャプチャ抑制")

    def _on_play_end(self):
        """TTS 再生終了時 — キャプチャを再開（少し待ってバッファに残るTTS音声を捨てる）"""
        # 再生終了直後のバッファにTTS音声の残りが入っている可能性があるので少し待つ
        # 0.5秒: BlackHole等のループバックデバイスのバッファ遅延を考慮
        time.sleep(0.5)
        # バッファに溜まったチャンクを捨てる
        while not self.capture.audio_queue.empty():
            try:
                self.capture.audio_queue.get_nowait()
            except Exception:
                break
        self._is_playing = False
        print("[VoiceBridge] TTS再生終了 → キャプチャ再開")

    def _setup_streaming_asr(self):
        """ストリーミング ASR を初期化（Moonshine + VAD 時のみ）

        AudioCapture の on_audio コールバック経由で 100ms ブロックを
        StreamingTranscriber にリアルタイムで流す。
        確定したテキスト行を _streaming_lines キューに蓄積し、
        VAD が発話終了を検出した時点でまとめて取り出す。
        """
        from transcriber_moonshine import StreamingTranscriber

        self._streaming_lines = queue.Queue()
        self._streaming_partial = ""

        def on_text(text, is_final):
            """途中経過テキストを更新"""
            if not is_final:
                self._streaming_partial = text

        def on_line_completed(text):
            """確定テキストをキューに追加"""
            if text.strip():
                self._streaming_lines.put(text.strip())
                self._streaming_partial = ""

        self._streaming_asr = StreamingTranscriber(
            language=self.source_language,
            on_text=on_text,
            on_line_completed=on_line_completed,
        )

        # AudioCapture の生オーディオをストリーミング ASR に接続
        def on_audio(audio_data):
            if self._streaming_asr and not self._is_playing:
                self._streaming_asr.add_audio(audio_data, self.capture.sample_rate)

        self.capture.on_audio = on_audio
        print(f"[VoiceBridge] ストリーミング ASR: Moonshine (リアルタイム認識)")

    def _collect_streaming_text(self) -> str:
        """ストリーミング ASR の確定テキストをまとめて取得"""
        lines = []
        while not self._streaming_lines.empty():
            try:
                lines.append(self._streaming_lines.get_nowait())
            except queue.Empty:
                break

        # 確定行 + 途中経過を結合
        text = " ".join(lines)
        if self._streaming_partial.strip():
            if text:
                text += " " + self._streaming_partial.strip()
            else:
                text = self._streaming_partial.strip()

        self._streaming_partial = ""
        return text

    def _notify_latency(self, latency: float, stage: str):
        """遅延情報を通知"""
        if self.on_latency:
            self.on_latency(latency, stage)

    def _pipeline_loop(self):
        """メインパイプラインループ（モードに応じて分岐）"""
        if self.mode == "chat":
            self._chat_pipeline_loop()
        else:
            self._translate_pipeline_loop()

    def _translate_pipeline_loop(self):
        """翻訳パイプラインループ"""
        self._notify_status("モデルロード中...")
        self.transcriber.load_model()
        self._notify_status("キャプチャ中...")

        while self._running:
            # 1. 音声チャンクを取得
            audio_chunk = self.capture.get_chunk(timeout=1.0)
            if audio_chunk is None:
                continue

            # TTS 再生中はキャプチャしたチャンクを捨てる（フィードバックループ防止）
            if self._is_playing:
                print("[Pipeline] TTS再生中のため音声チャンクをスキップ")
                continue

            self._notify_status("認識中...")

            # 2. 音声認識（テキスト化）
            self.latency_tracker.start("asr")
            try:
                asr_result = self.transcriber.transcribe(audio_chunk)
            except Exception as e:
                print(f"[Pipeline] 音声認識エラー: {e}")
                self.latency_tracker.stop("asr")
                continue
            t_transcribe = self.latency_tracker.stop("asr")

            if not asr_result.strip():
                self._notify_status("キャプチャ中...")
                continue

            # 言語自動検出: source_language が "auto" の場合、検出言語で翻訳ペアを動的に切替
            detected_lang = getattr(asr_result, "detected_language", None)
            detected_prob = getattr(asr_result, "language_prob", None)
            if self.source_language == "auto" and detected_lang:
                # 診断ログ: 生の検出結果を毎回出力
                prob_pct = f"{detected_prob:.0%}" if detected_prob is not None else "?"
                text_preview = str(asr_result)[:60].replace("\n", " ")
                print(f"[AutoLang] 生検出: {detected_lang}({prob_pct}) テキスト=「{text_preview}」")
                self._auto_switch_source_language(detected_lang, detected_prob)

            # active_source: 確信度が閾値以上の検出言語、または Translator の現在のソース言語
            if self.source_language == "auto":
                if detected_lang and detected_prob is not None and detected_prob >= self.AUTO_LANG_MIN_PROB:
                    active_source = detected_lang
                else:
                    # 確信度が低い → Translator の現在のソース言語を使う
                    active_source = getattr(self.translator, "source", "en")
            else:
                active_source = self.source_language

            source_label = (active_source or "??").upper()
            print(f"[{source_label}] {asr_result}")
            if self.on_english_text:
                self.on_english_text(str(asr_result))

            # 翻訳スキップ: 検出言語 == ターゲット言語の場合（確信度が高いときのみ）
            if active_source == self.target_language:
                print(f"[Pipeline] 検出言語({active_source})=ターゲット言語 → 翻訳スキップ")
                translated_text = str(asr_result)
                t_translate = 0.0
            else:
                # 3. 翻訳
                self._notify_status("翻訳中...")
                self.latency_tracker.start("translate")
                try:
                    translated_text = self.translator.translate(str(asr_result))
                except Exception as e:
                    print(f"[Pipeline] 翻訳エラー: {e}")
                    self.latency_tracker.stop("translate")
                    continue
                t_translate = self.latency_tracker.stop("translate")

            if not translated_text.strip():
                self._notify_status("キャプチャ中...")
                continue

            target_label = self.target_language.upper()
            print(f"[{target_label}] {translated_text}")
            if self.on_japanese_text:
                self.on_japanese_text(translated_text)

            # ログ保存
            self.logger.log(
                active_source or self.source_language, self.target_language,
                str(asr_result), translated_text,
            )

            # 4. 音声合成
            self._notify_status("音声合成中...")
            self.latency_tracker.start("tts")
            try:
                audio_path = self.tts.synthesize(translated_text)
            except Exception as e:
                print(f"[Pipeline] TTS エラー: {e}")
                self.latency_tracker.stop("tts")
                continue
            t_tts = self.latency_tracker.stop("tts")

            if audio_path:
                self._dispatch_audio(audio_path, translated_text)

            # レイテンシ記録（チャンク蓄積時間を追加レイテンシとして加算）
            record = self.latency_tracker.record_cycle(
                extra_latency=self.capture.chunk_duration
            )
            print(self.latency_tracker.format_cycle(record))
            self._notify_latency(record.total_sec,
                f"認識{t_transcribe:.1f}s+翻訳{t_translate:.1f}s+TTS{t_tts:.1f}s")

            self._notify_status("キャプチャ中...")

    def _chat_pipeline_loop(self):
        """AI チャットパイプラインループ（VAD有無で分岐）"""
        print("")
        print("[1/4] モデルロード中...")
        self._notify_status("モデルロード中...")

        # ストリーミング ASR がある場合はそちらをロード & 開始
        if self._streaming_asr:
            self._streaming_asr.load_model()
            self._streaming_asr.start()
            print("[1/4] ストリーミング ASR ロード完了 ✓")
        else:
            self.transcriber.load_model()
            print("[1/4] モデルロード完了 ✓")

        if self.use_vad:
            self._chat_pipeline_vad()
        else:
            self._chat_pipeline_legacy()

        # クリーンアップ
        if self._streaming_asr:
            self._streaming_asr.stop()

    def _chat_pipeline_vad(self):
        """VAD ベースのチャットパイプライン

        AudioCapture が Silero VAD で発話の開始・終了を検出し、
        完全な発話を1つのチャンクとしてキューに投入する。

        ストリーミング ASR が有効な場合:
          - AudioCapture の on_audio 経由で 100ms ブロックを
            StreamingTranscriber にリアルタイムで流す
          - VAD が発話終了を検出 → ストリーミングの確定テキストを使用
          - バッチ ASR は不要（認識待ち時間がほぼゼロ）
          - 話しながらリアルタイムでテキストが表示される

        ストリーミング ASR が無効な場合:
          - VAD が発話を検出 → バッチ ASR で一括認識
        """
        use_streaming = self._streaming_asr is not None
        mode_str = "VAD + ストリーミング ASR" if use_streaming else "VAD"
        print(f"[====] マイク待機中... 話しかけてください ({mode_str})")
        self._notify_status("マイク待機中...")

        while self._running:
            # VAD が発話を検出してキューに入れるのを待つ
            audio_chunk = self.capture.get_chunk(timeout=1.0)
            if audio_chunk is None:
                continue

            # TTS 再生中はスキップ（フィードバックループ防止）
            if self._is_playing:
                # ストリーミング ASR のバッファもクリア
                if use_streaming:
                    self._collect_streaming_text()
                continue

            duration = len(audio_chunk) / self.capture.sample_rate

            if use_streaming:
                # ストリーミング ASR: 確定テキストを収集（認識は既にリアルタイムで完了）
                print(f"\n[1/4] ストリーミング認識結果を取得中... ({duration:.1f}s)")
                self._notify_status("認識中...")

                # VAD 発話終了後、ストリーミングの処理が追いつくのを少し待つ
                time.sleep(0.15)

                t_step = time.time()
                user_text = self._collect_streaming_text()
                t_transcribe = time.time() - t_step

                if not user_text.strip():
                    # ストリーミングが空 → フォールバックでバッチ ASR
                    print(f"[1/4] ストリーミング空 → バッチ ASR にフォールバック")
                    try:
                        self.transcriber.load_model()
                        user_text = self.transcriber.transcribe(audio_chunk)
                        t_transcribe = time.time() - t_step
                    except Exception as e:
                        print(f"[1/4] バッチ ASR エラー: {e}")
                        self._notify_status("マイク待機中...")
                        continue
            else:
                # バッチ ASR
                print(f"\n[1/4] 音声認識中... ({duration:.1f}s)")
                self._notify_status("認識中...")

                t_step = time.time()
                try:
                    user_text = self.transcriber.transcribe(audio_chunk)
                except Exception as e:
                    print(f"[1/4] 音声認識エラー: {e}")
                    self._notify_status("マイク待機中...")
                    continue
                t_transcribe = time.time() - t_step

            if not user_text.strip():
                print(f"[1/4] (空テキスト — スキップ)")
                self._notify_status("マイク待機中...")
                continue

            print(f"[1/4] 認識完了 ({t_transcribe:.2f}s) ✓")

            # AI に送信
            self._chat_send_to_ai(user_text.strip())

    def _chat_pipeline_legacy(self):
        """従来のチャットパイプライン（VAD なし — 固定チャンク + 無音カウント方式）"""
        print("[====] マイク待機中... 話しかけてください")
        self._notify_status("マイク待機中...")

        # 発話バッファ: 無音が続くまでテキストを溜める
        utterance_buffer = []
        silence_count = 0
        SILENCE_THRESHOLD = 2  # 無音チャンクが連続N回で発話終了と判定

        while self._running:
            # 1. 音声チャンクを取得
            audio_chunk = self.capture.get_chunk(timeout=1.0)
            if audio_chunk is None:
                # タイムアウト = 無音扱い
                if utterance_buffer:
                    silence_count += 1
                    if silence_count >= SILENCE_THRESHOLD:
                        user_text = " ".join(utterance_buffer)
                        utterance_buffer.clear()
                        silence_count = 0
                        self._chat_send_to_ai(user_text)
                continue

            # TTS 再生中はスキップ（フィードバックループ防止）
            if self._is_playing:
                continue

            # 2. 音声認識（テキスト化）
            if not utterance_buffer:
                print("")
                print("[1/4] 音声認識中...")
            self._notify_status("認識中...")
            t_step = time.time()
            try:
                chunk_text = self.transcriber.transcribe(audio_chunk)
            except Exception as e:
                print(f"[1/4] 音声認識エラー: {e}")
                continue
            t_transcribe = time.time() - t_step

            if not chunk_text.strip():
                # 無音チャンク → バッファに溜まっていれば発話終了判定
                if utterance_buffer:
                    silence_count += 1
                    if silence_count >= SILENCE_THRESHOLD:
                        user_text = " ".join(utterance_buffer)
                        utterance_buffer.clear()
                        silence_count = 0
                        self._chat_send_to_ai(user_text)
                    else:
                        print(f"[1/4] (無音 {silence_count}/{SILENCE_THRESHOLD}...)")
                continue

            # 音声あり → バッファに追加、無音カウントリセット
            silence_count = 0
            utterance_buffer.append(chunk_text.strip())
            print(f"[1/4] 認識: \"{chunk_text.strip()}\" (バッファ: {len(utterance_buffer)}件)")
            self._notify_status(f"聞いてます... ({len(utterance_buffer)})")

    def _chat_send_to_ai(self, user_text: str):
        """バッファに溜まったテキストをまとめてAIに送信（ストリーミング / バッチ自動選択）"""
        t_start = time.time()
        print(f"[1/4] 認識完了 ✓")
        print(f"  YOU: {user_text}")
        if self.on_english_text:
            self.on_english_text(user_text)

        # ストリーミング対応: 文単位で TTS に渡してダブルバッファリング
        if self.use_vad:
            self._chat_ai_streaming(user_text, t_start)
        else:
            self._chat_ai_batch(user_text, t_start)

    def _chat_ai_streaming(self, user_text: str, t_start: float):
        """ストリーミング応答 + 文単位 TTS パイプライン

        LLM からトークン単位で応答を受信し、句点（。！？）で文を区切って
        即座に TTS に渡す。再生キューに順次追加することで、
        1文目を再生しながら2文目を合成する「ダブルバッファリング」を実現。

        従来: AI全文待ち(3s) → TTS全文(1s) → 再生 = 4s後に音声開始
        改善: AI1文目(0.5s) → TTS1文目(0.3s) → 再生開始 = 0.8s後に音声開始
        """
        print(f"[2/4] AI 応答待ち (streaming, {self.ai_chat.model})...")
        self._notify_status("AI 応答中...")

        # 文の区切り文字
        SENTENCE_ENDINGS = frozenset("。！？!?\n")

        sentence_buffer = ""
        full_response = ""
        sentence_count = 0
        t_first_audio = None
        t_tts_total = 0.0

        try:
            for delta in self.ai_chat.chat_stream(user_text):
                full_response += delta
                sentence_buffer += delta

                # 文末を検出したら即座に TTS に渡す
                last_char = sentence_buffer.rstrip()[-1] if sentence_buffer.strip() else ""
                if last_char in SENTENCE_ENDINGS:
                    sentence = sentence_buffer.strip()
                    if sentence:
                        sentence_count += 1
                        t_tts_step = time.time()
                        self._synthesize_and_enqueue(sentence, sentence_count)
                        t_tts_total += time.time() - t_tts_step

                        if t_first_audio is None:
                            t_first_audio = time.time() - t_start
                            print(f"[2/4] 初回音声キュー投入 ({t_first_audio:.2f}s)")

                    sentence_buffer = ""

        except Exception as e:
            print(f"[2/4] ストリーミングエラー: {e}")

        # 残りのバッファ（文末記号なしで終わった場合）
        if sentence_buffer.strip():
            sentence_count += 1
            t_tts_step = time.time()
            self._synthesize_and_enqueue(sentence_buffer.strip(), sentence_count)
            t_tts_total += time.time() - t_tts_step
            if t_first_audio is None:
                t_first_audio = time.time() - t_start

        # 結果表示 & ログ
        if full_response.strip():
            print(f"  AI:  {full_response.strip()}")
            if self.on_japanese_text:
                self.on_japanese_text(full_response.strip())

            self.logger.log("user", "ai", user_text, full_response.strip())

        t_total = time.time() - t_start
        first_str = f", 初回音声={t_first_audio:.2f}s" if t_first_audio else ""
        print(f"[====] 合計 {t_total:.1f}s ({sentence_count}文, TTS計{t_tts_total:.1f}s{first_str})")
        self._notify_latency(t_total, f"{sentence_count}文, 初回{t_first_audio:.1f}s" if t_first_audio else f"{t_total:.1f}s")

        print("[====] マイク待機中... 話しかけてください")
        self._notify_status("マイク待機中...")

    def _synthesize_and_enqueue(self, text: str, index: int):
        """テキストを TTS で音声合成し、再生キューに追加"""
        try:
            audio_path = self.tts.synthesize(text)
            if audio_path:
                self._dispatch_audio(audio_path, text)
                print(f"  [TTS #{index}] \"{text[:30]}{'...' if len(text) > 30 else ''}\"")
        except Exception as e:
            print(f"  [TTS #{index}] エラー: {e}")

    def _dispatch_audio(self, audio_path: str, text: str = "") -> None:
        """TTS 音声ファイルの再生先を振り分ける。

        - Live2D フロントが接続中: Live2D へ送信（pygame 再生はスキップ）
          * フロント側が HTML5 Audio で再生 + AnalyserNode で口パク
          * 再生中は `_on_play_start/_on_play_end` でキャプチャ抑制を維持
        - 未接続・無効: 従来どおり pygame の再生キューに投入
        """
        if not audio_path:
            return

        # Live2D クライアント接続中ならそちらへ優先転送
        if self.live2d is not None and self.live2d.has_client():
            try:
                emotion, intensity = infer_emotion(text or "")
                pid = self.live2d.send_tts(
                    audio_path,
                    text=text or "",
                    emotion=emotion,
                    intensity=intensity,
                )
            except Exception as e:
                print(f"[Live2D] 送信失敗、pygame にフォールバック: {e}")
                pid = None

            if pid:
                # pygame 側と同じくキャプチャ抑制
                self._on_play_start()

                def _wait_end(pid_=pid, path_=audio_path):
                    try:
                        self.live2d.wait_playback_end(pid_, timeout=60.0)
                    finally:
                        self._on_play_end()
                        try:
                            os.remove(path_)
                        except OSError:
                            pass

                threading.Thread(
                    target=_wait_end,
                    name="Live2DPlaybackWait",
                    daemon=True,
                ).start()
                return

        # フォールバック: 従来の pygame 再生
        self.player.enqueue(audio_path)

    def _chat_ai_batch(self, user_text: str, t_start: float):
        """従来のバッチ応答（ストリーミングなし）"""
        print(f"[2/4] AI 応答待ち ({self.ai_chat.model})...")
        self._notify_status("AI 応答中...")
        t_step = time.time()
        try:
            ai_response = self.ai_chat.chat(user_text)
        except Exception as e:
            print(f"[2/4] AI エラー: {e}")
            return
        t_ai = time.time() - t_step

        if not ai_response.strip():
            print("[2/4] (空応答スキップ)")
            self._notify_status("マイク待機中...")
            return

        print(f"[2/4] AI 応答完了 ({t_ai:.1f}s) ✓")
        print(f"  AI:  {ai_response}")
        if self.on_japanese_text:
            self.on_japanese_text(ai_response)

        # ログ保存
        self.logger.log("user", "ai", user_text, ai_response)

        # 音声合成
        print("[4/4] 音声合成中...")
        self._notify_status("音声合成中...")
        t_step = time.time()
        try:
            audio_path = self.tts.synthesize(ai_response)
        except Exception as e:
            print(f"[4/4] TTS エラー: {e}")
            return
        t_tts = time.time() - t_step

        if audio_path:
            self._dispatch_audio(audio_path, ai_response)

        t_total = time.time() - t_start
        print(f"[====] 合計 {t_total:.1f}s (AI{t_ai:.1f}s + TTS{t_tts:.1f}s)")
        self._notify_latency(t_total, f"AI{t_ai:.1f}s+TTS{t_tts:.1f}s")

        print("[====] マイク待機中... 話しかけてください")
        self._notify_status("マイク待機中...")

    def chat_text(self, text: str):
        """テキスト入力から AI チャット（GUI のテキストボックス用）"""
        if not self.ai_chat or not text.strip():
            return

        def _process():
            print(f"[YOU] {text}")
            if self.on_english_text:
                self.on_english_text(text)

            self._notify_status("AI 応答中...")

            if self.use_vad:
                # ストリーミング + 文単位 TTS
                SENTENCE_ENDINGS = frozenset("。！？!?\n")
                sentence_buffer = ""
                full_response = ""
                sentence_count = 0

                try:
                    for delta in self.ai_chat.chat_stream(text):
                        full_response += delta
                        sentence_buffer += delta

                        last_char = sentence_buffer.rstrip()[-1] if sentence_buffer.strip() else ""
                        if last_char in SENTENCE_ENDINGS:
                            sentence = sentence_buffer.strip()
                            if sentence:
                                sentence_count += 1
                                self._synthesize_and_enqueue(sentence, sentence_count)
                            sentence_buffer = ""

                    if sentence_buffer.strip():
                        sentence_count += 1
                        self._synthesize_and_enqueue(sentence_buffer.strip(), sentence_count)

                except Exception as e:
                    print(f"[Chat] AI ストリーミングエラー: {e}")

                if full_response.strip():
                    print(f"[AI] {full_response.strip()}")
                    if self.on_japanese_text:
                        self.on_japanese_text(full_response.strip())
                    self.logger.log("user", "ai", text, full_response.strip())

                self._notify_status("マイク待機中..." if self._running else "停止中")
                return

            # 従来のバッチ処理
            try:
                ai_response = self.ai_chat.chat(text)
            except Exception as e:
                print(f"[Chat] AI エラー: {e}")
                self._notify_status("マイク待機中..." if self._running else "停止中")
                return

            if not ai_response.strip():
                return

            print(f"[AI] {ai_response}")
            if self.on_japanese_text:
                self.on_japanese_text(ai_response)

            # ログ保存
            self.logger.log("user", "ai", text, ai_response)

            # 音声合成
            self._notify_status("音声合成中...")
            try:
                audio_path = self.tts.synthesize(ai_response)
                if audio_path:
                    self._dispatch_audio(audio_path, ai_response)
            except Exception as e:
                print(f"[Chat] TTS エラー: {e}")

            self._notify_status("マイク待機中..." if self._running else "停止中")

        threading.Thread(target=_process, daemon=True).start()

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
        self.logger.close()

        # Live2D ブリッジ停止
        if self.live2d is not None:
            try:
                self.live2d.stop()
            except Exception as e:
                print(f"[VoiceBridge] Live2D ブリッジ停止時エラー: {e}")
            self.live2d = None

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

    def set_chunk_duration(self, duration: float):
        """チャンク長を動的に変更する（秒）

        AudioCapture のチャンク蓄積サイズをリアルタイムで更新。
        短くすると低遅延だが ASR 精度が落ちる可能性あり。
        """
        duration = max(1.5, min(6.0, duration))  # 安全範囲にクランプ
        self.capture.chunk_duration = duration
        self.capture.chunk_samples = int(self.capture.sample_rate * duration)
        print(f"[VoiceBridge] チャンク長を {duration:.1f}秒 に変更")

    def change_voice(self, voice_key: str):
        """声を変更する（Edge TTS の場合はキー名、VOICEVOX の場合は speaker_id）"""
        if self.use_voicevox:
            try:
                speaker_id = int(voice_key)
                self._voicevox_speaker_id = speaker_id
                if isinstance(self.tts, VoicevoxTTS):
                    self.tts.set_speaker(speaker_id)
            except ValueError:
                print(f"[VoiceBridge] 無効な speaker_id: {voice_key}")
        else:
            self.tts.set_voice(voice_key)

    # --- 言語自動検出の安定化パラメータ ---
    AUTO_LANG_MIN_PROB = 0.75        # この確信度未満の検出は無視
    AUTO_LANG_SWITCH_COUNT = 2       # 同じ言語がこの回数連続で検出されたら切替

    def _auto_switch_source_language(self, detected_lang: str, prob: float = None):
        """自動検出されたソース言語に基づいて翻訳ペアを動的に切替

        安定化のため以下のフィルタを適用:
          1. 確信度が AUTO_LANG_MIN_PROB 未満の検出は無視
          2. 同じ言語が AUTO_LANG_SWITCH_COUNT 回連続で検出されて初めて切替
        """
        # voice-bridge のサポート言語に正規化
        supported = {"en", "ja", "zh", "es", "fr", "de", "ko"}
        if detected_lang not in supported:
            return

        # 1. 確信度フィルタ: 閾値未満は無視（GUI 通知も控える）
        if prob is not None and prob < self.AUTO_LANG_MIN_PROB:
            return

        # 2. 安定性フィルタ: 連続検出カウント
        if not hasattr(self, "_auto_lang_history"):
            self._auto_lang_history = []
        self._auto_lang_history.append(detected_lang)
        # 直近 N 件だけ保持
        max_keep = self.AUTO_LANG_SWITCH_COUNT + 1
        if len(self._auto_lang_history) > max_keep:
            self._auto_lang_history = self._auto_lang_history[-max_keep:]

        # 直近 N 件が全て同じ言語か判定
        recent = self._auto_lang_history[-self.AUTO_LANG_SWITCH_COUNT:]
        if len(recent) < self.AUTO_LANG_SWITCH_COUNT or len(set(recent)) != 1:
            # まだ安定していない — GUI の確信度表示だけ更新
            if self.on_language_detected:
                self.on_language_detected(detected_lang, prob)
            return

        # ここに来たら安定して同じ言語が連続検出された
        stable_lang = recent[0]

        # GUI に検出言語を通知
        if self.on_language_detected:
            self.on_language_detected(stable_lang, prob)

        # 検出言語 == ターゲット言語の場合は翻訳不要（パイプライン側でスキップする）
        if stable_lang == self.target_language:
            return

        # 現在の Translator のソース言語と同じなら何もしない
        current_source = getattr(self.translator, "source", None)
        if current_source == stable_lang:
            return

        prob_str = f" ({prob:.0%})" if prob is not None else ""
        print(f"[AutoLang] 言語確定: {stable_lang}{prob_str} ({self.AUTO_LANG_SWITCH_COUNT}回連続) → 翻訳ペアを {stable_lang}→{self.target_language} に切替")

        # Translator のソース言語のみ更新（ターゲットはそのまま）
        try:
            self.translator.set_language_pair(stable_lang, self.target_language)
        except Exception as e:
            print(f"[AutoLang] 翻訳ペア切替失敗: {e}")

    def change_language_pair(self, source: str, target: str) -> bool:
        """言語ペアを動的に変更（source="auto" で自動検出モード）"""
        # Transcriber の言語変更
        if not self.transcriber.set_language(source):
            return False

        # auto モードでは Translator はそのまま（検出時に動的更新される）
        if source == "auto":
            self.source_language = "auto"
            self.target_language = target
            self.tts_language = target
            print(f"[VoiceBridge] 言語ペアを auto→{target} に変更（検出時に自動切替）")
            return True

        # Translator の言語ペア変更
        if not self.translator.set_language_pair(source, target):
            return False

        # TTS の言語変更（ターゲット言語に合わせる）
        # VOICEVOX 使用中でターゲットが日本語以外 → Edge TTS に切り替え
        if self.use_voicevox and isinstance(self.tts, VoicevoxTTS) and target != "ja":
            self.tts.cleanup()
            self.tts = TTSEngine(language=target)
            print(f"[VoiceBridge] TTS: VOICEVOX → Edge TTS ({target})")
        # VOICEVOX が利用可能でターゲットが日本語に戻った → VOICEVOX に復帰
        elif self.use_voicevox and not isinstance(self.tts, VoicevoxTTS) and target == "ja":
            self.tts.cleanup()
            self.tts = VoicevoxTTS(speaker_id=self._voicevox_speaker_id)
            print(f"[VoiceBridge] TTS: Edge TTS → VOICEVOX")
        else:
            if not self.tts.set_language(target):
                return False

        # 内部状態を更新
        self.source_language = source
        self.target_language = target
        self.tts_language = target

        print(f"[VoiceBridge] 言語ペアを {source}→{target} に変更")
        return True


def run_cli(args):
    """CLI モードで実行"""
    use_coeiroink = args.coeiroink or CoeiroinkTTS.is_available()
    use_voicevox = (not use_coeiroink) and (args.voicevox or VoicevoxTTS.is_available())
    bridge = VoiceBridge(
        device_name=args.device,
        model_size=args.model,
        source_language=args.source_lang,
        target_language=args.target_lang,
        tts_language=args.tts_lang,
        voice=args.voice,
        chunk_duration=args.chunk,
        use_voicevox=use_voicevox,
        voicevox_speaker_id=args.speaker_id if use_voicevox else 3,
        use_coeiroink=use_coeiroink,
        coeiroink_speaker_id=args.coeiroink_speaker_id if use_coeiroink else 0,
        asr_engine=args.asr,
        asr_device=args.asr_device,
        mode=args.mode,
        ai_base_url=args.ai_base_url,
        ai_model=args.ai_model,
        use_vad=args.vad,
        live2d_enabled=args.live2d,
        live2d_host=args.live2d_host,
        live2d_port=args.live2d_port,
    )

    # Ctrl+C で停止
    def signal_handler(sig, frame):
        print("\n[CLI] 停止中...")
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    tts_name = "VOICEVOX" if use_voicevox else "Edge TTS"
    if IS_WINDOWS:
        os_name = "Windows (WASAPI)"
    elif IS_LINUX:
        os_name = "Linux (PulseAudio/PipeWire)"
    else:
        os_name = "macOS (BlackHole)"
    asr_name = "Moonshine" if args.asr == "moonshine" else f"faster-whisper ({args.model})"
    mode_name = "AI チャット" if args.mode == "chat" else "翻訳"
    vad_name = "Silero VAD" if args.vad and args.mode == "chat" else "RMS"
    print("=" * 50)
    print(f"  Voice Bridge - CLI モード（{mode_name}）")
    print(f"  OS: {os_name}")
    print(f"  ASR: {asr_name}")
    if args.mode == "chat":
        print(f"  AI: {args.ai_model}")
        print(f"  VAD: {vad_name}")
    print(f"  デバイス: {args.device}")
    print(f"  TTS: {tts_name}")
    if not (args.vad and args.mode == "chat"):
        print(f"  チャンク: {args.chunk}秒")
    print("  Ctrl+C で停止")
    print("=" * 50)

    # CLI 音声レベル表示
    def on_cli_level(rms: float, is_active: bool):
        bar_len = int(min(rms * 200, 30))
        bar = "█" * bar_len + "░" * (30 - bar_len)
        marker = " 🎤" if is_active else ""
        print(f"\r  [{bar}] {rms:.3f}{marker}  ", end="", flush=True)

    bridge.on_level = on_cli_level

    bridge.start()

    # チャットモードではテキスト入力も受け付ける
    if args.mode == "chat":
        print("  テキスト入力も可能です（Enter で送信）")
        print("=" * 50)

    # メインスレッドを生かしておく
    try:
        if args.mode == "chat":
            # チャットモード: テキスト入力も受け付ける
            while True:
                try:
                    user_input = input()
                    if user_input.strip():
                        bridge.chat_text(user_input.strip())
                except EOFError:
                    break
        else:
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

    # CoeiroInk が起動しているか確認
    coeiroink_available = CoeiroinkTTS.is_available()
    coeiroink_speakers = {}
    if coeiroink_available:
        coeiroink_speakers = CoeiroinkTTS.fetch_speakers()
        print(f"[VoiceBridge] CoeiroInk 検出: {len(coeiroink_speakers)}キャラ")

    # VOICEVOX が起動しているか確認
    voicevox_available = (not coeiroink_available) and VoicevoxTTS.is_available()
    voicevox_speakers = {}
    if voicevox_available:
        voicevox_speakers = VoicevoxTTS.fetch_speakers()
        print(f"[VoiceBridge] VOICEVOX 検出: {len(voicevox_speakers)}話者")
    elif not coeiroink_available:
        print("[VoiceBridge] CoeiroInk・VOICEVOX 未検出 → Edge TTS を使用")

    # デフォルトの speaker_id
    default_speaker_id = 3  # VOICEVOX: ずんだもん ノーマル
    default_coeiroink_id = 90  # CoeiroInk: リリンちゃん ノーマル（styleId=90）

    # ローカル LLM サーバーから利用可能なモデル一覧を取得
    ai_models = AiChat.fetch_models(base_url=args.ai_base_url)
    if ai_models:
        print(f"[VoiceBridge] LLM モデル: {len(ai_models)} 件検出")
    else:
        print(f"[VoiceBridge] LLM モデル一覧取得失敗（サーバー未起動？）")

    # VoiceBridge は開始時に GUI 設定を読んで作成する（遅延作成）
    bridge_holder = {"bridge": None}

    def create_bridge():
        """GUI の現在の設定で VoiceBridge を作成"""
        settings = gui.get_settings()
        mode = settings["mode"]
        asr = settings["asr"]
        vad = settings["vad"]

        bridge = VoiceBridge(
            device_name=settings["device"],
            model_size=args.model,
            source_language=settings["source_lang"],
            target_language=settings["target_lang"],
            tts_language=settings["target_lang"],
            voice=args.voice,
            chunk_duration=settings.get("chunk_duration", args.chunk),
            use_coeiroink=coeiroink_available,
            coeiroink_speaker_id=default_coeiroink_id,
            use_voicevox=voicevox_available,
            voicevox_speaker_id=default_speaker_id,
            asr_engine=asr,
            asr_device=args.asr_device,
            mode=mode,
            ai_base_url=args.ai_base_url,
            ai_model=settings.get("ai_model") or args.ai_model,
            use_vad=vad,
            live2d_enabled=args.live2d,
            live2d_host=args.live2d_host,
            live2d_port=args.live2d_port,
        )

        # GUI コールバックを接続
        bridge.on_english_text = gui.add_english_text
        bridge.on_japanese_text = gui.add_japanese_text
        bridge.on_status_change = gui.set_status
        bridge.on_level = gui.set_level
        bridge.on_latency = gui.set_latency
        bridge.on_language_detected = gui.set_detected_language

        bridge_holder["bridge"] = bridge
        return bridge

    def on_start():
        """開始ボタン — VoiceBridge を（再）作成して開始"""
        # 既存の bridge があれば停止
        if bridge_holder["bridge"]:
            try:
                bridge_holder["bridge"].stop()
            except Exception:
                pass

        bridge = create_bridge()
        bridge.start()

    def on_stop():
        """停止ボタン"""
        if bridge_holder["bridge"]:
            bridge_holder["bridge"].stop()
            bridge_holder["bridge"] = None

    # 声変更のコールバック
    def on_voice_change(voice_key: str):
        bridge = bridge_holder["bridge"]
        if not bridge:
            return

        if coeiroink_available:
            # CoeiroInk: UUID:styleId 形式で取得
            uuid_style = coeiroink_speakers.get(voice_key)
            if uuid_style:
                # UUID と styleId を分離
                parts = str(uuid_style).split(":")
                if len(parts) == 2:
                    uuid, style_id = parts
                    bridge.tts.set_speaker_uuid(uuid)
                    bridge.tts.set_speaker(int(style_id))
                    # CoeiroInk クレジット表記を更新
                    char_name = voice_key.split("（")[0]
                    gui.set_credit(f"CoeiroInk:{char_name} | https://coeiroink.com/")
                    print(f"[GUI] CoeiroInk変更: {voice_key} (UUID={uuid}, styleId={style_id})")
            else:
                print(f"[GUI] 不明なキャラクター: {voice_key}")
        elif voicevox_available:
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

    # 言語ペア変更のコールバック
    def on_language_pair_change(source: str, target: str):
        if bridge_holder["bridge"]:
            bridge_holder["bridge"].change_language_pair(source, target)

    # チャットテキスト送信のコールバック
    def on_chat_text(text: str):
        if bridge_holder["bridge"]:
            bridge_holder["bridge"].chat_text(text)

    # チャンク長変更のコールバック
    def on_chunk_duration_change(duration: float):
        if bridge_holder["bridge"]:
            bridge_holder["bridge"].set_chunk_duration(duration)

    gui = VoiceBridgeGUI(
        on_start=on_start,
        on_stop=on_stop,
        on_clear=None,
        on_model_change=lambda m: bridge_holder["bridge"] and bridge_holder["bridge"].change_model(m),
        on_device_change=lambda d: bridge_holder["bridge"] and bridge_holder["bridge"].change_device(d),
        on_voice_change=on_voice_change,
        on_language_pair_change=on_language_pair_change,
        on_chat_text=on_chat_text,
        on_chunk_duration_change=on_chunk_duration_change,
    )

    # 声のリストを構築
    if coeiroink_available:
        voice_list = list(coeiroink_speakers.keys())
        default_voice = "リリンちゃん" if "リリンちゃん" in voice_list else voice_list[0]
    elif voicevox_available:
        voice_list = list(voicevox_speakers.keys())
        default_voice = "ずんだもん（ノーマル）" if "ずんだもん（ノーマル）" in voice_list else voice_list[0]
    else:
        voice_list = ["nanami（女性）", "keita（男性）"]
        default_voice = "nanami（女性）"

    gui.build(
        devices=devices,
        voices=voice_list,
        default_voice=default_voice,
        default_source_lang=args.source_lang,
        default_target_lang=args.target_lang,
        default_mode=args.mode,
        default_asr=args.asr,
        default_vad=args.vad,
        ai_models=ai_models,
        default_ai_model=args.ai_model,
        default_chunk_duration=args.chunk,
    )

    # TTS クレジット表記
    if coeiroink_available:
        credit = f"CoeiroInk:{default_voice} | https://coeiroink.com/"
        gui.set_credit(credit)
    elif voicevox_available:
        credit = f"VOICEVOX:{default_voice.split('（')[0]} | https://voicevox.hiroshiba.jp/"
        gui.set_credit(credit)

    gui.run()


def main():
    parser = argparse.ArgumentParser(
        description="Voice Bridge - リアルタイム多言語翻訳",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli", action="store_true", help="CLI モードで起動（デバッグ用）")
    parser.add_argument("--list-devices", action="store_true", help="入力デバイス一覧を表示")
    parser.add_argument("--asr", default="whisper", choices=["whisper", "moonshine", "qwen3"],
                        help="ASR エンジン (default: whisper)")
    parser.add_argument("--device", default=DEFAULT_DEVICE,
                        help=f"入力デバイス名 (default: {DEFAULT_DEVICE})")
    parser.add_argument("--asr-device", default="cpu", choices=["cpu", "cuda"],
                        help="ASR 推論デバイス (default: cpu, Qwen3-ASR では cuda 推奨)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"],
                        help="Whisper モデルサイズ（moonshine 使用時は無視）")
    parser.add_argument("--source-lang", default="en",
                        choices=["auto", "en", "ja", "zh", "es", "fr", "de", "ko"],
                        help="認識言語 (default: en, auto=自動検出)")
    parser.add_argument("--target-lang", default="ja",
                        choices=["en", "ja", "zh", "es", "fr", "de", "ko"],
                        help="翻訳言語 (default: ja)")
    parser.add_argument("--tts-lang", default=None,
                        choices=["en", "ja", "zh", "es", "fr", "de", "ko"],
                        help="音声合成言語 (default: target-lang と同じ)")
    parser.add_argument("--voice", default="nanami", choices=["nanami", "keita", "jenny", "guy", "xiaoxiao", "yunxi", "elvira", "alvaro", "denise", "henri", "katja", "conrad", "sunhi", "injoon"],
                        help="Edge TTS 音声 (VOICEVOX未使用時)")
    parser.add_argument("--voicevox", action="store_true",
                        help="VOICEVOX エンジンを使用（日本語のみ）")
    parser.add_argument("--speaker-id", type=int, default=3,
                        help="VOICEVOX speaker ID (default: 3 = ずんだもん)")
    parser.add_argument("--coeiroink", action="store_true",
                        help="CoeiroInk エンジンを使用（日本語のみ、リリンちゃん推奨）")
    parser.add_argument("--coeiroink-speaker-id", type=int, default=0,
                        help="CoeiroInk speaker ID (default: 0 = リリンちゃん)")
    parser.add_argument("--chunk", type=float, default=4.0, help="音声チャンク長（秒）")

    # VAD (Voice Activity Detection)
    parser.add_argument("--vad", action="store_true",
                        help="Silero VAD を使用（チャットモードで発話検出を改善）")

    # AI チャットモード
    parser.add_argument("--mode", default="translate", choices=["translate", "chat"],
                        help="動作モード: translate（翻訳）/ chat（AI会話）")
    parser.add_argument("--ai-base-url", default=None,
                        help="AI API ベース URL (default: .env の AI_BASE_URL or OpenAI)")
    parser.add_argument("--ai-model", default=None,
                        help="AI モデル名 (default: .env の AI_MODEL or gpt-4o-mini)")

    # Live2D 連携
    parser.add_argument("--live2d", action="store_true",
                        help="Live2D ブリッジ（WebSocket）を起動し、TTS をフロントへ転送")
    parser.add_argument("--live2d-host", default="127.0.0.1",
                        help="Live2D ブリッジ host (default: 127.0.0.1)")
    parser.add_argument("--live2d-port", type=int, default=8765,
                        help="Live2D ブリッジ port (default: 8765)")

    args = parser.parse_args()

    # .env / 環境変数からデフォルト値を補完
    if args.ai_base_url is None:
        args.ai_base_url = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
    if args.ai_model is None:
        args.ai_model = os.environ.get("AI_MODEL", "gpt-4o-mini")

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
