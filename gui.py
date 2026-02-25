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

    def __init__(self, on_start=None, on_stop=None, on_clear=None, on_model_change=None, on_device_change=None, on_voice_change=None, on_rate_change=None):
        """
        Args:
            on_start: 開始ボタン押下時のコールバック
            on_stop: 停止ボタン押下時のコールバック
            on_clear: クリアボタン押下時のコールバック
            on_model_change: モデル変更時のコールバック (model_size: str)
            on_device_change: デバイス変更時のコールバック (device_name: str)
            on_voice_change: 音声変更時のコールバック (voice: str)
            on_rate_change: 速度変更時のコールバック (rate: str)
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_clear = on_clear
        self.on_model_change = on_model_change
        self.on_device_change = on_device_change
        self.on_voice_change = on_voice_change
        self.on_rate_change = on_rate_change

        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self.root = None
        self._level_canvas = None
        self._latency_var = None

    def build(self, devices: list[str] = None, voices: list[str] = None, default_voice: str = None):
        """GUI を構築"""
        self.root = tk.Tk()
        self.root.title("Voice Bridge - リアルタイム英日翻訳")
        self.root.geometry("700x600")
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

        # --- ボタンエリア ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = tk.Button(
            btn_frame, text="▶ 開始", command=self._on_start,
            bg="#a6e3a1", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
            width=12, height=1, relief=tk.FLAT, cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame, text="■ 停止", command=self._on_stop,
            bg="#f38ba8", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
            width=12, height=1, relief=tk.FLAT, cursor="hand2", state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = tk.Button(
            btn_frame, text="🗑 クリア", command=self._on_clear,
            bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
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

        # --- 英語テキスト表示 ---
        ttk.Label(main_frame, text="🇺🇸 English").pack(anchor=tk.W, pady=(5, 2))
        self.en_text = scrolledtext.ScrolledText(
            main_frame, height=8, wrap=tk.WORD,
            bg="#313244", fg="#cdd6f4", font=("Helvetica", 12),
            insertbackground="#cdd6f4", relief=tk.FLAT, padx=10, pady=8
        )
        self.en_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.en_text.configure(state=tk.DISABLED)

        # --- 日本語テキスト表示 ---
        ttk.Label(main_frame, text="🇯🇵 日本語").pack(anchor=tk.W, pady=(0, 2))
        self.ja_text = scrolledtext.ScrolledText(
            main_frame, height=8, wrap=tk.WORD,
            bg="#313244", fg="#f9e2af", font=("Helvetica", 12),
            insertbackground="#f9e2af", relief=tk.FLAT, padx=10, pady=8
        )
        self.ja_text.pack(fill=tk.BOTH, expand=True)
        self.ja_text.configure(state=tk.DISABLED)

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

    def set_credit(self, text: str):
        """クレジット表記を設定"""
        if self._credit_var:
            self._credit_var.set(text)

    def run(self):
        """GUI メインループを開始"""
        if self.root:
            self.root.mainloop()
