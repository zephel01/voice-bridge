"""
翻訳モジュール
deep-translator を使って英語を日本語に翻訳する
専門用語辞書サポート付き
"""

import time
import re

try:
    from deep_translator import GoogleTranslator
except ImportError:
    raise ImportError("deep-translator が必要です: pip install deep-translator")


class Translator:
    """Google Translate を使った英日翻訳 + 専門用語辞書対応"""

    def __init__(self, source: str = "en", target: str = "ja", max_retries: int = 3):
        self.source = source
        self.target = target
        self.max_retries = max_retries
        self._translator = GoogleTranslator(source=source, target=target)

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
            # 単語境界を尊重したマッチング
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

    def add_terminology(self, term_dict: dict):
        """ユーザーが追加の専門用語を登録する"""
        self.terminology.update(term_dict)
        print(f"[Translator] {len(term_dict)}個の用語を追加しました")

    def translate(self, text: str) -> str:
        """
        テキストを翻訳する（専門用語辞書対応）

        Args:
            text: 英語テキスト

        Returns:
            日本語に翻訳されたテキスト
        """
        if not text or not text.strip():
            return ""

        # ステップ1: 専門用語を抽出・置換
        term_data = self._apply_terminology(text.strip())
        text_to_translate = term_data["modified_text"]
        replacements = term_data["replacements"]

        for attempt in range(self.max_retries):
            try:
                # ステップ2: Google翻訳を実行
                result = self._translator.translate(text_to_translate)

                # ステップ3: 専門用語を復元
                final_result = self._restore_terminology(result, replacements)
                return final_result if final_result else ""

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 0.5 * (attempt + 1)
                    print(f"[Translator] 翻訳エラー (リトライ {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait)
                else:
                    print(f"[Translator] 翻訳失敗: {e}")
                    return f"[翻訳エラー] {text}"


if __name__ == "__main__":
    t = Translator()

    # テスト1: 基本的な翻訳
    result = t.translate("Hello, how are you today?")
    print(f"テスト1 翻訳結果: {result}")

    # テスト2: 専門用語を含む翻訳
    result = t.translate("We use machine learning algorithms for cloud computing optimization.")
    print(f"テスト2 翻訳結果: {result}")

    # テスト3: ユーザー定義用語を追加
    t.add_terminology({
        "deep learning": "深層学習",
        "data science": "データサイエンス",
    })
    result = t.translate("Deep learning is used in data science projects.")
    print(f"テスト3 翻訳結果: {result}")
