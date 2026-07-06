"""
GUI モジュール
tkinter を使ったシンプルな操作ウィンドウ
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue


class VoiceBridgeGUI:
    """Voice Bridge の GUI"""

    # 言語コード → 表示用言語名（emoji付き）のマッピング
    LANGUAGE_DISPLAY = {
        "auto": "🔍 自動検出",
        "en": "🇺🇸 English",
        "ja": "🇯🇵 日本語",
        "zh": "🇨🇳 中国語",
        "es": "🇪🇸 スペイン語",
        "fr": "🇫🇷 フランス語",
        "de": "🇩🇪 ドイツ語",
        "ko": "🇰🇷 韓国語",
    }

    # 言語コード → ドロップダウン表示用（言語名付き）のマッピング
    LANGUAGE_DROPDOWN = {
        "auto": "auto (自動検出)",
        "en": "en (English)",
        "ja": "ja (日本語)",
        "zh": "zh (中国語)",
        "es": "es (スペイン語)",
        "fr": "fr (フランス語)",
        "de": "de (ドイツ語)",
        "ko": "ko (韓国語)",
    }

    def __init__(self, on_start=None, on_stop=None, on_clear=None, on_model_change=None, on_device_change=None, on_voice_change=None, on_rate_change=None, on_language_pair_change=None, on_chat_text=None, on_chunk_duration_change=None):
        """
        Args:
            on_start: 開始ボタン押下時のコールバック
            on_stop: 停止ボタン押下時のコールバック
            on_clear: クリアボタン押下時のコールバック
            on_model_change: モデル変更時のコールバック (model_size: str)
            on_device_change: デバイス変更時のコールバック (device_name: str)
            on_voice_change: 音声変更時のコールバック (voice: str)
            on_rate_change: 速度変更時のコールバック (rate: str)
            on_language_pair_change: 言語ペア変更時のコールバック (source: str, target: str)
            on_chat_text: チャットテキスト送信時のコールバック (text: str)
            on_chunk_duration_change: チャンク長変更時のコールバック (duration: float)
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_clear = on_clear
        self.on_model_change = on_model_change
        self.on_device_change = on_device_change
        self.on_voice_change = on_voice_change
        self.on_rate_change = on_rate_change
        self.on_language_pair_change = on_language_pair_change
        self.on_chat_text = on_chat_text
        self.on_chunk_duration_change = on_chunk_duration_change

        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self.root = None
        self._level_canvas = None
        self._latency_var = None
        self._source_lang_label = None  # ソース言語のテキストボックスラベル
        self._target_lang_label = None  # ターゲット言語のテキストボックスラベル

    def build(self, devices: list[str] = None, voices: list[str] = None, default_voice: str = None, default_source_lang: str = "en", default_target_lang: str = "ja", default_mode: str = "translate", default_asr: str = "whisper", default_vad: bool = False, ai_models: list[str] = None, default_ai_model: str = "", default_chunk_duration: float = 4.0):
        """GUI を構築"""
        self.root = tk.Tk()
        self.root.title("Voice Bridge - リアルタイム多言語翻訳")
        self.root.geometry("800x650")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use("clam")

        # ダークテーマ設定
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Helvetica", 12))
        style.configure("TButton", font=("Helvetica", 12, "bold"), padding=8)
        style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), foreground="#89b4fa")
        style.configure("Status.TLabel", font=("Helvetica", 11), foreground="#a6adc8")
        style.configure("TCombobox", font=("Helvetica", 11))

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- ヘッダー ---
        header = ttk.Label(main_frame, text="🌉 Voice Bridge", style="Header.TLabel")
        header.pack(pady=(0, 10))

        # --- 設定エリア ---
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # デバイス選択
        ttk.Label(settings_frame, text="入力デバイス:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        device_list = devices or ["default"]
        self.device_var = tk.StringVar(value=device_list[0])
        self.device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var, values=device_list, width=30)
        self.device_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_changed)

        # モデル選択
        ttk.Label(settings_frame, text="Whisper:").grid(row=0, column=2, sticky=tk.W, padx=(0, 8))
        self.model_var = tk.StringVar(value="small")
        model_combo = ttk.Combobox(
            settings_frame, textvariable=self.model_var,
            values=["tiny", "base", "small", "medium"], width=10
        )
        model_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 15))
        model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        # 音声選択（2行目に配置）
        voice_list = voices or ["nanami（女性）", "keita（男性）"]
        voice_default = default_voice or voice_list[0]
        ttk.Label(settings_frame, text="声:").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        self.voice_var = tk.StringVar(value=voice_default)
        voice_combo = ttk.Combobox(
            settings_frame, textvariable=self.voice_var,
            values=voice_list, width=30, state="readonly"
        )
        voice_combo.grid(row=1, column=1, columnspan=5, sticky=tk.W, pady=(8, 0))
        voice_combo.bind("<<ComboboxSelected>>", self._on_voice_changed)

        # 言語選択（3行目に配置）
        lang_label_text = "会話言語:" if default_mode == "chat" else "言語:"
        self._lang_label = ttk.Label(settings_frame, text=lang_label_text)
        self._lang_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))

        # ソース言語選択（"auto" = 自動検出を先頭に配置）
        self.source_lang_var = tk.StringVar(value=default_source_lang)
        source_lang_dropdown_values = [self.LANGUAGE_DROPDOWN[lang] for lang in ["auto", "en", "ja", "zh", "es", "fr", "de", "ko"]]
        self._source_lang_combo = ttk.Combobox(
            settings_frame, textvariable=self.source_lang_var,
            values=source_lang_dropdown_values, width=15, state="readonly"
        )
        self._source_lang_combo.set(self.LANGUAGE_DROPDOWN[default_source_lang])
        self._source_lang_combo.grid(row=2, column=1, sticky=tk.W, pady=(8, 0))
        self._source_lang_combo.bind("<<ComboboxSelected>>", self._on_language_pair_changed)

        # ↔ 矢印ラベル
        self._lang_arrow = ttk.Label(settings_frame, text="↔")
        self._lang_arrow.grid(row=2, column=2, padx=5, pady=(8, 0))

        # ターゲット言語選択
        self.target_lang_var = tk.StringVar(value=default_target_lang)
        target_lang_dropdown_values = [self.LANGUAGE_DROPDOWN[lang] for lang in ["en", "ja", "zh", "es", "fr", "de", "ko"]]
        self._target_lang_combo = ttk.Combobox(
            settings_frame, textvariable=self.target_lang_var,
            values=target_lang_dropdown_values, width=15, state="readonly"
        )
        self._target_lang_combo.set(self.LANGUAGE_DROPDOWN[default_target_lang])
        self._target_lang_combo.grid(row=2, column=3, sticky=tk.W, pady=(8, 0))
        self._target_lang_combo.bind("<<ComboboxSelected>>", self._on_language_pair_changed)

        # チャットモードではソース言語を非表示にして、ターゲット言語 = 会話言語
        if default_mode == "chat":
            self._source_lang_combo.set(self.LANGUAGE_DROPDOWN[default_target_lang])
            self._source_lang_combo.grid_remove()
            self._lang_arrow.grid_remove()

        # モード・ASR・VAD 選択（4行目に配置）
        ttk.Label(settings_frame, text="モード:").grid(row=3, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        self.mode_var = tk.StringVar(value=default_mode)
        mode_combo = ttk.Combobox(
            settings_frame, textvariable=self.mode_var,
            values=["translate", "chat"], width=10, state="readonly"
        )
        mode_combo.grid(row=3, column=1, sticky=tk.W, pady=(8, 0))
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        ttk.Label(settings_frame, text="ASR:").grid(row=3, column=2, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        self.asr_var = tk.StringVar(value=default_asr)
        asr_combo = ttk.Combobox(
            settings_frame, textvariable=self.asr_var,
            values=["whisper", "moonshine", "qwen3"], width=12, state="readonly"
        )
        asr_combo.grid(row=3, column=3, sticky=tk.W, pady=(8, 0))

        self.vad_var = tk.BooleanVar(value=default_vad)
        self._vad_check = tk.Checkbutton(
            settings_frame, text="VAD", variable=self.vad_var,
            bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
            activebackground="#1e1e2e", activeforeground="#cdd6f4",
            font=("Helvetica", 11)
        )
        self._vad_check.grid(row=3, column=4, sticky=tk.W, padx=(10, 0), pady=(8, 0))

        # LLM モデル選択（5行目に配置）
        ttk.Label(settings_frame, text="LLM:").grid(row=4, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        model_list = ai_models or []
        self.ai_model_var = tk.StringVar(value=default_ai_model)
        self._ai_model_combo = ttk.Combobox(
            settings_frame, textvariable=self.ai_model_var,
            values=model_list, width=40,
        )
        self._ai_model_combo.grid(row=4, column=1, columnspan=4, sticky=tk.W, pady=(8, 0))

        # チャンク長調整スライダー（6行目に配置）
        ttk.Label(settings_frame, text="チャンク長:").grid(row=5, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        self._chunk_duration_var = tk.DoubleVar(value=default_chunk_duration)
        self._chunk_slider = tk.Scale(
            settings_frame,
            variable=self._chunk_duration_var,
            from_=1.5, to=6.0, resolution=0.5,
            orient=tk.HORIZONTAL, length=200,
            bg="#1e1e2e", fg="#cdd6f4", troughcolor="#313244",
            highlightthickness=0, font=("Helvetica", 10),
            command=self._on_chunk_duration_changed,
        )
        self._chunk_slider.grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=(8, 0))
        self._chunk_label_var = tk.StringVar(value=f"{default_chunk_duration:.1f}秒 標準")
        ttk.Label(settings_frame, textvariable=self._chunk_label_var,
                  font=("Helvetica", 10), foreground="#a6adc8").grid(
            row=5, column=3, columnspan=2, sticky=tk.W, padx=(5, 0), pady=(8, 0))

        # 入力ゲイン調整（7行目に配置）
        ttk.Label(settings_frame, text="入力ゲイン:").grid(row=6, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 0))
        self._input_gain_var = tk.DoubleVar(value=1.0)
        self._gain_slider = tk.Scale(
            settings_frame,
            variable=self._input_gain_var,
            from_=1.0, to=10.0, resolution=0.5,
            orient=tk.HORIZONTAL, length=200,
            bg="#1e1e2e", fg="#cdd6f4", troughcolor="#313244",
            highlightthickness=0, font=("Helvetica", 10),
            command=self._on_gain_changed,
        )
        self._gain_slider.grid(row=6, column=1, columnspan=2, sticky=tk.W, pady=(8, 0))
        self._gain_label_var = tk.StringVar(value="1.0x（標準）")
        ttk.Label(settings_frame, textvariable=self._gain_label_var,
                  font=("Helvetica", 10), foreground="#a6adc8").grid(
            row=6, column=3, sticky=tk.W, padx=(5, 0), pady=(8, 0))
        self._auto_gain_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            settings_frame, text="自動", variable=self._auto_gain_var,
        ).grid(row=6, column=4, sticky=tk.W, padx=(4, 0), pady=(8, 0))

        # --- ボタンエリア ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = tk.Button(
            btn_frame, text="▶ 開始", command=self._on_start,
            bg="#a6e3a1", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
            activebackground="#9fc593", activeforeground="#1e1e2e",
            width=12, height=1, relief=tk.FLAT, cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame, text="■ 停止", command=self._on_stop,
            bg="#f38ba8", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
            activebackground="#e89aaa", activeforeground="#1e1e2e",
            width=12, height=1, relief=tk.FLAT, cursor="hand2", state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = tk.Button(
            btn_frame, text="🗑 クリア", command=self._on_clear,
            bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
            activebackground="#7aa8e8", activeforeground="#1e1e2e",
            width=12, height=1, relief=tk.FLAT, cursor="hand2"
        )
        self.clear_btn.pack(side=tk.LEFT)

        # ステータス
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = ttk.Label(btn_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(side=tk.RIGHT)

        # --- 音声レベル＆遅延表示 ---
        monitor_frame = ttk.Frame(main_frame)
        monitor_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(monitor_frame, text="入力レベル:", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self._level_canvas = tk.Canvas(
            monitor_frame, width=200, height=16,
            bg="#313244", highlightthickness=0, relief=tk.FLAT
        )
        self._level_canvas.pack(side=tk.LEFT, padx=(0, 15))
        # 閾値ライン（赤い縦線）を描画
        threshold_x = int(0.01 / 0.1 * 200)  # silence_threshold=0.01, max≈0.1
        self._level_canvas.create_line(
            threshold_x, 0, threshold_x, 16, fill="#f38ba8", width=1, tags="threshold"
        )

        self._latency_var = tk.StringVar(value="遅延: --")
        ttk.Label(monitor_frame, textvariable=self._latency_var,
                  font=("Helvetica", 10), foreground="#f9e2af").pack(side=tk.LEFT, padx=(0, 10))

        self._latency_detail_var = tk.StringVar(value="")
        ttk.Label(monitor_frame, textvariable=self._latency_detail_var,
                  font=("Helvetica", 9), foreground="#a6adc8").pack(side=tk.LEFT)

        # --- ソース言語テキスト表示（動的に更新） ---
        source_label = "🎤 あなた" if default_mode == "chat" else self.LANGUAGE_DISPLAY[default_source_lang]
        self._source_lang_label = ttk.Label(main_frame, text=source_label)
        self._source_lang_label.pack(anchor=tk.W, pady=(5, 2))
        self.en_text = scrolledtext.ScrolledText(
            main_frame, height=8, wrap=tk.WORD,
            bg="#313244", fg="#cdd6f4", font=("Helvetica", 12),
            insertbackground="#cdd6f4", relief=tk.FLAT, padx=10, pady=8
        )
        self.en_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.en_text.configure(state=tk.DISABLED)

        # --- ターゲット言語テキスト表示（動的に更新） ---
        target_label = "🤖 AI" if default_mode == "chat" else self.LANGUAGE_DISPLAY[default_target_lang]
        self._target_lang_label = ttk.Label(main_frame, text=target_label)
        self._target_lang_label.pack(anchor=tk.W, pady=(0, 2))
        self.ja_text = scrolledtext.ScrolledText(
            main_frame, height=8, wrap=tk.WORD,
            bg="#313244", fg="#f9e2af", font=("Helvetica", 12),
            insertbackground="#f9e2af", relief=tk.FLAT, padx=10, pady=8
        )
        self.ja_text.pack(fill=tk.BOTH, expand=True)
        self.ja_text.configure(state=tk.DISABLED)

        # --- チャット用テキスト入力 ---
        self._chat_frame = ttk.Frame(main_frame)
        self._chat_frame.pack(fill=tk.X, pady=(8, 0))

        self._chat_entry = tk.Entry(
            self._chat_frame,
            bg="#313244", fg="#cdd6f4", font=("Helvetica", 12),
            insertbackground="#cdd6f4", relief=tk.FLAT,
        )
        self._chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=6)
        self._chat_entry.bind("<Return>", self._on_chat_submit)

        self._chat_send_btn = tk.Button(
            self._chat_frame, text="送信", command=self._on_chat_submit,
            bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 11, "bold"),
            activebackground="#7aa8e8", activeforeground="#1e1e2e",
            width=6, relief=tk.FLAT, cursor="hand2"
        )
        self._chat_send_btn.pack(side=tk.RIGHT)

        # モードに応じてチャット入力の表示切り替え
        if default_mode != "chat":
            self._chat_frame.pack_forget()

        # --- VOICEVOX 利用表記 ---
        self._credit_var = tk.StringVar(value="")
        self._credit_label = ttk.Label(
            main_frame, textvariable=self._credit_var,
            font=("Helvetica", 9), foreground="#7f849c"
        )
        self._credit_label.pack(anchor=tk.W, pady=(6, 0))

        # メッセージキュー処理
        self.root.after(100, self._process_messages)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_start(self):
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._running = True
        self.set_status("キャプチャ中...")
        if self.on_start:
            threading.Thread(target=self.on_start, daemon=True).start()

    def _on_stop(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self._running = False
        self.set_status("停止")
        if self.on_stop:
            self.on_stop()

    def _on_clear(self):
        self._clear_text(self.en_text)
        self._clear_text(self.ja_text)
        if self.on_clear:
            self.on_clear()

    def _on_model_changed(self, event=None):
        if self.on_model_change:
            self.on_model_change(self.model_var.get())

    def _on_device_changed(self, event=None):
        if self.on_device_change:
            self.on_device_change(self.device_var.get())

    def _on_voice_changed(self, event=None):
        if self.on_voice_change:
            self.on_voice_change(self.voice_var.get())

    def _on_language_pair_changed(self, event=None):
        """言語ペア変更イベント"""
        source_display = self.source_lang_var.get()
        target_display = self.target_lang_var.get()

        # ドロップダウン表示形式から言語コードを抽出 (e.g., "en (English)" → "en")
        source = source_display.split()[0] if source_display else "en"
        target = target_display.split()[0] if target_display else "ja"

        mode = self.mode_var.get()

        # チャットモードではソース = ターゲットに自動同期
        if mode == "chat":
            self._source_lang_combo.set(target_display)
            return

        # 言語ペアの妥当性チェック（auto 以外で同じ言語の場合は警告）
        if source != "auto" and source == target:
            print(f"[GUI] 警告: ソース言語とターゲット言語が同じです")
            return

        # テキストボックスのラベルを動的に更新
        self._source_lang_label.configure(text=self.LANGUAGE_DISPLAY.get(source, source))
        self._target_lang_label.configure(text=self.LANGUAGE_DISPLAY[target])

        if self.on_language_pair_change:
            self.on_language_pair_change(source, target)

    def _on_mode_changed(self, event=None):
        """モード変更時にチャット入力欄の表示とラベルを切り替え"""
        mode = self.mode_var.get()
        if mode == "chat":
            # チャット入力欄を表示
            self._chat_frame.pack(fill=tk.X, pady=(8, 0), before=self._credit_label)
            # ラベルをチャット用に変更
            self._source_lang_label.configure(text="🎤 あなた")
            self._target_lang_label.configure(text="🤖 AI")
            # チャットモードでは認識言語 = 応答言語に自動同期
            target_display = self.target_lang_var.get()
            self._source_lang_combo.set(target_display)
            self._lang_label.configure(text="会話言語:")
            self._source_lang_combo.grid_remove()
            self._lang_arrow.grid_remove()
        else:
            self._chat_frame.pack_forget()
            # ラベルを翻訳用に戻す
            source = self.source_lang_var.get().split()[0] if self.source_lang_var.get() else "en"
            target = self.target_lang_var.get().split()[0] if self.target_lang_var.get() else "ja"
            self._source_lang_label.configure(text=self.LANGUAGE_DISPLAY.get(source, source))
            self._target_lang_label.configure(text=self.LANGUAGE_DISPLAY.get(target, target))
            self._lang_label.configure(text="言語:")
            self._source_lang_combo.grid()
            self._lang_arrow.grid()

    def _on_chunk_duration_changed(self, value=None):
        """チャンク長スライダー変更イベント"""
        duration = self._chunk_duration_var.get()
        # ラベル更新：短い/長いの目安を表示
        if duration <= 2.0:
            hint = "短い（低遅延・認識精度↓）"
        elif duration <= 3.0:
            hint = "やや短い（バランス型）"
        elif duration <= 4.0:
            hint = "標準"
        else:
            hint = "長い（高精度・遅延↑）"
        self._chunk_label_var.set(f"{duration:.1f}秒 {hint}")

        if self.on_chunk_duration_change:
            self.on_chunk_duration_change(duration)

    def _on_gain_changed(self, value=None):
        """入力ゲインスライダー変更イベント"""
        gain = self._input_gain_var.get()
        if gain <= 1.0:
            hint = "（標準）"
        elif gain <= 3.0:
            hint = "（やや増幅）"
        elif gain <= 6.0:
            hint = "（増幅）"
        else:
            hint = "（強い増幅）"
        self._gain_label_var.set(f"{gain:.1f}x{hint}")

    def _on_chat_submit(self, event=None):
        """チャットテキスト送信"""
        text = self._chat_entry.get().strip()
        if text and self.on_chat_text:
            self._chat_entry.delete(0, tk.END)
            self.on_chat_text(text)

    def get_settings(self) -> dict:
        """現在の GUI 設定を取得（VoiceBridge 作成時に使用）"""
        # ドロップダウン表示 "en (English)" → "en" に変換
        source_display = self.source_lang_var.get()
        target_display = self.target_lang_var.get()
        source_lang = source_display.split()[0] if source_display else "en"
        target_lang = target_display.split()[0] if target_display else "ja"

        mode = self.mode_var.get()
        # チャットモードでは認識言語 = 会話言語（ターゲット言語）
        if mode == "chat":
            source_lang = target_lang

        return {
            "mode": mode,
            "asr": self.asr_var.get(),
            "vad": self.vad_var.get(),
            "device": self.device_var.get(),
            "voice": self.voice_var.get(),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "ai_model": self.ai_model_var.get(),
            "chunk_duration": self._chunk_duration_var.get(),
            "input_gain": self._input_gain_var.get(),
            "auto_gain": self._auto_gain_var.get(),
        }

    def _on_close(self):
        self._running = False
        if self.on_stop:
            self.on_stop()
        self.root.destroy()

    def _process_messages(self):
        """メインスレッドでメッセージを処理"""
        while not self._message_queue.empty():
            try:
                msg_type, data = self._message_queue.get_nowait()
                if msg_type == "en":
                    self._append_text(self.en_text, data)
                elif msg_type == "ja":
                    self._append_text(self.ja_text, data)
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "level":
                    self._update_level(data)
                elif msg_type == "latency":
                    latency, stage = data
                    self._latency_var.set(f"遅延: {latency:.1f}s")
                    self._latency_detail_var.set(f"({stage})")
                elif msg_type == "detected_lang":
                    detected_lang, prob = data
                    display = self.LANGUAGE_DISPLAY.get(detected_lang, detected_lang)
                    if prob is not None:
                        display += f" ({prob:.0%})"
                    if self._source_lang_label:
                        self._source_lang_label.configure(text=display)
            except queue.Empty:
                break
        if self.root:
            self.root.after(100, self._process_messages)

    def _append_text(self, widget, text: str):
        """テキストウィジェットに追記"""
        widget.configure(state=tk.NORMAL)
        widget.insert(tk.END, text + "\n")
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)

    def _clear_text(self, widget):
        """テキストウィジェットをクリア"""
        widget.configure(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.configure(state=tk.DISABLED)

    def _update_level(self, data):
        """音声レベルバーを更新"""
        rms, is_active = data
        if self._level_canvas is None:
            return
        self._level_canvas.delete("bar")
        # RMS を 0〜200px にマッピング (max≈0.1 を想定)
        bar_width = min(int(rms / 0.1 * 200), 200)
        color = "#a6e3a1" if is_active else "#585b70"
        if bar_width > 0:
            self._level_canvas.create_rectangle(
                0, 0, bar_width, 16, fill=color, outline="", tags="bar"
            )
        # 閾値ラインを再描画（バーの上に表示）
        threshold_x = int(0.01 / 0.1 * 200)
        self._level_canvas.delete("threshold")
        self._level_canvas.create_line(
            threshold_x, 0, threshold_x, 16, fill="#f38ba8", width=1, tags="threshold"
        )

    # --- 外部から呼び出すメソッド（スレッドセーフ） ---

    def add_english_text(self, text: str):
        """英語テキストを追加（スレッドセーフ）"""
        self._message_queue.put(("en", text))

    def add_japanese_text(self, text: str):
        """日本語テキストを追加（スレッドセーフ）"""
        self._message_queue.put(("ja", text))

    def set_status(self, status: str):
        """ステータスを更新（スレッドセーフ）"""
        self._message_queue.put(("status", status))

    def set_level(self, rms: float, is_active: bool):
        """音声レベルを更新（スレッドセーフ）"""
        self._message_queue.put(("level", (rms, is_active)))

    def set_latency(self, latency: float, stage: str):
        """遅延情報を更新（スレッドセーフ）"""
        self._message_queue.put(("latency", (latency, stage)))

    def set_detected_language(self, detected_lang: str, prob: float = None):
        """自動検出された言語をラベルに反映（スレッドセーフ）"""
        self._message_queue.put(("detected_lang", (detected_lang, prob)))

    def set_credit(self, text: str):
        """クレジット表記を設定"""
        if self._credit_var:
            self._credit_var.set(text)

    def run(self):
        """GUI メインループを開始"""
        if self.root:
            self.root.mainloop()
