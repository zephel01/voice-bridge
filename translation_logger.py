"""
翻訳ログモジュール
認識テキストと翻訳テキストを YYYYMMDD.log として保存する

ログ形式:
  HH:MM:SS [EN→JA] source_text | translated_text

負荷について:
  1行のテキスト追記（バッファリングI/O）なので 0.1ms 以下。
  パイプラインの認識・翻訳・TTS（合計2〜3秒）に対して無視できるレベル。
"""

import os
import threading
from datetime import datetime


class TranslationLogger:
    """翻訳結果を日付別ログファイルに保存する"""

    def __init__(self, log_dir: str = "logs"):
        """
        Args:
            log_dir: ログフォルダのパス（デフォルト: ./logs）
        """
        self.log_dir = log_dir
        self._current_date = None
        self._file = None
        self._lock = threading.Lock()

        # ログフォルダを作成
        os.makedirs(self.log_dir, exist_ok=True)
        print(f"[Logger] ログフォルダ: {os.path.abspath(self.log_dir)}")

    def _ensure_file(self):
        """日付が変わったらファイルを切り替える"""
        today = datetime.now().strftime("%Y%m%d")
        if today != self._current_date:
            if self._file:
                self._file.close()
            filepath = os.path.join(self.log_dir, f"{today}.log")
            self._file = open(filepath, "a", encoding="utf-8")
            self._current_date = today
            print(f"[Logger] ログファイル: {filepath}")

    def log(self, source_lang: str, target_lang: str,
            source_text: str, translated_text: str):
        """
        翻訳結果を1行追記する

        Args:
            source_lang: ソース言語コード (例: "en")
            target_lang: ターゲット言語コード (例: "ja")
            source_text: 認識されたテキスト
            translated_text: 翻訳されたテキスト
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = (
            f"{timestamp}\t"
            f"[{source_lang.upper()}→{target_lang.upper()}]\t"
            f"{source_text}\t"
            f"{translated_text}\n"
        )

        with self._lock:
            self._ensure_file()
            self._file.write(line)
            self._file.flush()

    def close(self):
        """ファイルを閉じる"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None
                self._current_date = None
                print("[Logger] ログファイルを閉じました")
