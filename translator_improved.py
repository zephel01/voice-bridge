"""
翻訳モジュール（改善版）
deep-translator を使って複数言語間の翻訳を行う
専門用語辞書サポート付き + デバッグ＆フィルター機能搭載
"""

import time
import re
import json
from datetime import datetime
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    raise ImportError("deep-translator が必要です: pip install deep-translator")


class Translator:
    """Google Translate を使った複数言語翻訳 + 専門用語辞書対応 + デバッグ機能"""

    # サポートされている言語ペア
    SUPPORTED_LANGUAGE_PAIRS = {
        ("en", "ja"), ("ja", "en"),
        ("zh-CN", "ja"), ("ja", "zh-CN"),
        ("es", "ja"), ("ja", "es"),
        ("fr", "ja"), ("ja", "fr"),
        ("de", "ja"), ("ja", "de"),
        ("ko", "ja"), ("ja", "ko"),
    }

    # 言語コードのマッピング（UI用）
    LANGUAGE_CODE_MAP = {
        "zh": "zh-CN",
    }

    LANGUAGE_NAMES = {
        "en": "English",
        "ja": "日本語",
        "zh": "中国語",
        "es": "スペイン語",
        "fr": "フランス語",
        "de": "ドイツ語",
        "ko": "韓国語",
    }

    # 既知の誤訳パターン（ブロックリスト）
    MISTRANSLATION_PATTERNS = {
        # 動画の終了・次回フレーズ
        r"(?:次|次回|また)\s*(?:の\s*)?(?:ビデオ|動画|映像|レッスン|回)(?:で|で\s*)(?:お会いしましょう|会いましょう|お目にかかりましょう)",
        r"(?:次\s*(?:の|の\s*))?(?:ビデオ|動画|映像|レッスン)(?:で|で\s*)(?:お会いしましょう|会いましょう)",
        r"(?:それでは|では|それでは)|(?:次\s*(?:まで|まで\s*)?|じゃあ|では)\s*(?:また|またね|またあした|また明日|じゃあ|では)",
        r"終わり|おわり|この動画はここまで",
        r"(?:このビデオ|この動画|ここ)で(?:終わり|終了|終わります)",
    }

    # 英語の既知の誤認識パターン（Whisper から）
    WHISPER_MISTRANSLATIONS = {
        r"see you in the next video": True,  # ブロック
        r"see you next time": True,          # ブロック
        r"thanks for watching": True,        # ブロック
        r"thanks for watching.*video": True, # ブロック
        r"subscribe.*channel": True,         # ブロック（チャンネル登録促進は誤認識しやすい）
        r"like.*comment.*subscribe": True,   # ブロック
    }

    def __init__(self, source: str = "en", target: str = "ja", max_retries: int = 3, debug: bool = False, log_file: str = None):
        """
        Args:
            source: ソース言語 (default: en)
            target: ターゲット言語 (default: ja)
            max_retries: 翻訳失敗時のリトライ回数 (default: 3)
            debug: デバッグモード有効化 (default: False)
            log_file: ログファイルパス (default: None - ログ無効)
        """
        # 言語コード変換
        source = self.LANGUAGE_CODE_MAP.get(source, source)
        target = self.LANGUAGE_CODE_MAP.get(target, target)

        # 言語ペアの検証
        if (source, target) not in self.SUPPORTED_LANGUAGE_PAIRS:
            raise ValueError(
                f"サポートされていない言語ペア: {source}→{target}\n"
                f"対応ペア: {self.SUPPORTED_LANGUAGE_PAIRS}"
            )

        self.source = source
        self.target = target
        self.max_retries = max_retries
        self.debug = debug
        self._translator = GoogleTranslator(source=source, target=target)

        source_name = self.LANGUAGE_NAMES.get(source, source)
        target_name = self.LANGUAGE_NAMES.get(target, target)
        print(f"[Translator] {source_name} ({source}) → {target_name} ({target})")
        if self.debug:
            print(f"[Translator] デバッグモード: 有効")

        # ログファイル設定
        self.log_file = log_file
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            print(f"[Translator] ログファイル: {self.log_file}")

        # 専門用語辞書（分野別）
        self.terminology = {
            # IT・テクノロジー用語
            "framework": "フレームワーク",
            "database": "データベース",
            "API": "API",
            "machine learning": "機械学習",
            "artificial intelligence": "人工知能",
            "neural network": "ニューラルネットワーク",
            "algorithm": "アルゴリズム",
            "data structure": "データ構造",
            "cloud computing": "クラウドコンピューティング",
            "cybersecurity": "サイバーセキュリティ",
            "blockchain": "ブロックチェーン",
            "cryptocurrency": "暗号資産",
            "web development": "ウェブ開発",
            "server": "サーバー",
            "client": "クライアント",

            # ビジネス用語
            "stakeholder": "ステークホルダー",
            "revenue": "収益",
            "profit margin": "利幅",
            "supply chain": "サプライチェーン",
            "ROI": "投資対効果",
            "KPI": "重要業績評価指標",

            # その他一般的な誤りやすい用語
            "infrastructure": "インフラストラクチャー",
            "optimization": "最適化",
            "implementation": "実装",
        }

    def _write_log(self, log_data: dict):
        """デバッグログをファイルに書き込み"""
        if not self.log_file:
            return

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[Translator] ログ書き込みエラー: {e}")

    def _should_block_whisper_mistranslation(self, text: str) -> bool:
        """Whisper の既知誤認識パターンをチェック"""
        text_lower = text.lower().strip()
        for pattern in self.WHISPER_MISTRANSLATIONS.keys():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def _should_block_ja_mistranslation(self, text: str) -> bool:
        """日本語の既知誤訳パターンをチェック"""
        for pattern in self.MISTRANSLATION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _apply_terminology(self, text: str) -> dict:
        """
        テキストに対して専門用語辞書を適用
        Returns:
            {
                "modified_text": 辞書語を<TERM_ID>で置換したテキスト,
                "replacements": {"<TERM_ID>": "日本語"}
            }
        """
        replacements = {}
        modified_text = text
        term_id = 0

        # 用語マッチング（大文字小文字を区別しない）
        for en_term, ja_term in self.terminology.items():
            pattern = r'\b' + re.escape(en_term) + r'\b'
            if re.search(pattern, modified_text, re.IGNORECASE):
                placeholder = f"<TERM_{term_id}>"
                modified_text = re.sub(pattern, placeholder, modified_text, flags=re.IGNORECASE)
                replacements[placeholder] = ja_term
                term_id += 1

        return {
            "modified_text": modified_text,
            "replacements": replacements
        }

    def _restore_terminology(self, text: str, replacements: dict) -> str:
        """翻訳後、専門用語プレースホルダーを日本語に復元"""
        result = text
        for placeholder, ja_term in replacements.items():
            result = result.replace(placeholder, ja_term)
        return result

    def _remove_duplicate_sentences(self, text: str) -> str:
        """
        連続する重複した文を削除
        より詳細な区切り文字に対応（句点、ゲル、感嘆符）
        """
        # 複数の区切り文字に対応
        sentences = re.split(r'[。！？\n]', text)
        unique_sentences = []
        last_sentence = ""

        for sent in sentences:
            sent = sent.strip()
            if sent and sent != last_sentence:
                unique_sentences.append(sent)
                last_sentence = sent

        # 区切り文字の復元（簡易版：句点で統一）
        result = '。'.join(unique_sentences)
        if text.endswith('。') or text.endswith('！') or text.endswith('？'):
            result += '。'
        return result

    def _merge_short_sentences(self, text: str) -> str:
        """
        短すぎる文（5文字以下）を前の文と結合
        例: "はじめに。テスト。" → "はじめにテスト。"
        """
        sentences = text.split('。')
        merged = []

        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue

            # 短い文は前の文と結合
            if merged and len(sent) <= 5:
                merged[-1] = merged[-1] + sent
            else:
                merged.append(sent)

        return '。'.join(merged) + ('。' if text.endswith('。') else '')

    def add_terminology(self, term_dict: dict):
        """ユーザーが追加の専門用語を登録する"""
        self.terminology.update(term_dict)
        print(f"[Translator] {len(term_dict)}個の用語を追加しました")

    def set_language_pair(self, source: str, target: str) -> bool:
        """言語ペアを動的に変更"""
        source = self.LANGUAGE_CODE_MAP.get(source, source)
        target = self.LANGUAGE_CODE_MAP.get(target, target)

        if (source, target) not in self.SUPPORTED_LANGUAGE_PAIRS:
            print(f"[Translator] サポートされていない言語ペア: {source}→{target}")
            return False

        self.source = source
        self.target = target
        self._translator = GoogleTranslator(source=source, target=target)

        source_name = self.LANGUAGE_NAMES.get(source, source)
        target_name = self.LANGUAGE_NAMES.get(target, target)
        print(f"[Translator] 言語ペアを変更: {source_name} ({source}) → {target_name} ({target})")
        return True

    def translate(self, text: str, skip_filter: bool = False) -> str:
        """
        テキストを翻訳する（専門用語辞書対応 + 誤訳フィルター対応）

        Args:
            text: 英語テキスト
            skip_filter: フィルターをスキップするか (default: False)

        Returns:
            日本語に翻訳されたテキスト
        """
        if not text or not text.strip():
            return ""

        original_text = text.strip()

        # ステップ1: Whisper の誤認識をチェック（英語の場合）
        if self.source == "en" and self._should_block_whisper_mistranslation(original_text):
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "stage": "whisper_filter",
                "original": original_text,
                "filtered": True,
                "reason": "既知の誤認識パターン"
            }
            self._write_log(log_data)
            if self.debug:
                print(f"[Translator] 🚫 Whisper 誤認識フィルター: {original_text}")
            return ""

        # ステップ2: 専門用語を抽出・置換
        term_data = self._apply_terminology(original_text)
        text_to_translate = term_data["modified_text"]
        replacements = term_data["replacements"]

        for attempt in range(self.max_retries):
            try:
                t_start = time.time()

                # ステップ3: Google翻訳を実行
                result = self._translator.translate(text_to_translate)
                t_translate = time.time() - t_start

                # ステップ4: 専門用語を復元
                final_result = self._restore_terminology(result, replacements)

                # ステップ5: 日本語の誤訳をチェック
                if not skip_filter and self._should_block_ja_mistranslation(final_result):
                    log_data = {
                        "timestamp": datetime.now().isoformat(),
                        "stage": "ja_filter",
                        "original": original_text,
                        "translated": final_result,
                        "filtered": True,
                        "reason": "既知の誤訳パターン"
                    }
                    self._write_log(log_data)
                    if self.debug:
                        print(f"[Translator] 🚫 日本語誤訳フィルター: {final_result}")
                    return ""

                # ステップ6: 重複した文を削除
                cleaned_result = self._remove_duplicate_sentences(final_result)
                cleaned_result = self._merge_short_sentences(cleaned_result)

                # ログ出力
                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "stage": "success",
                    "original": original_text,
                    "translated": cleaned_result,
                    "duration_sec": t_translate,
                    "attempt": attempt + 1
                }
                self._write_log(log_data)

                if self.debug:
                    print(f"[Translator] ✅ 翻訳成功 ({t_translate:.2f}s): {original_text[:50]} → {cleaned_result[:50]}")

                return cleaned_result if cleaned_result else ""

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 0.5 * (attempt + 1)
                    print(f"[Translator] 翻訳エラー (リトライ {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait)
                else:
                    print(f"[Translator] 翻訳失敗: {e}")
                    log_data = {
                        "timestamp": datetime.now().isoformat(),
                        "stage": "error",
                        "original": original_text,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                    self._write_log(log_data)
                    return f"[翻訳エラー] {text}"


if __name__ == "__main__":
    # テスト1: 基本的な翻訳（デバッグモード有効）
    t = Translator(debug=True, log_file="/tmp/translator_debug.log")

    # テスト2: 誤認識パターンをフィルター
    result = t.translate("See you in the next video!")
    print(f"テスト2 結果: '{result}' (ブロックされたため空文字)")

    # テスト3: 正常な翻訳
    result = t.translate("Hello, how are you today?")
    print(f"テスト3 結果: {result}")

    # テスト4: 専門用語を含む翻訳
    result = t.translate("We use machine learning algorithms for cloud computing optimization.")
    print(f"テスト4 結果: {result}")
