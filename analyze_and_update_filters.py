#!/usr/bin/env python3
"""
ログ分析 & フィルター自動更新スクリプト

最新のログファイルを分析して：
1. 繰り返し出現するフレーズを検出
2. translator.py のフィルターに自動追加
3. 統計情報を表示

使い方：
    python analyze_and_update_filters.py              # 最新ログを分析
    python analyze_and_update_filters.py --log-file logs/20260314_170201.log  # 特定ファイルを分析
    python analyze_and_update_filters.py --threshold 2  # 繰り返し回数の閾値を指定
    python analyze_and_update_filters.py --apply    # フィルターに自動追加
"""

import ast
import os
import sys
import re
import json
import argparse
import shutil
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple


class LogAnalyzer:
    """翻訳ログを分析して繰り返しパターンを検出"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_format = r"(\d{2}:\d{2}:\d{2})\t\[EN→JA\]\t(.+?)\t(.+)$"

    def get_latest_log(self) -> Path:
        """最新のログファイルを取得"""
        if not self.log_dir.exists():
            raise FileNotFoundError(f"ログディレクトリが見つかりません: {self.log_dir}")

        log_files = sorted(self.log_dir.glob("*.log"))
        if not log_files:
            raise FileNotFoundError(f"{self.log_dir} にログファイルがありません")

        latest = log_files[-1]
        print(f"📄 分析対象: {latest.name}")
        return latest

    def parse_log(self, log_path: Path) -> List[Tuple[str, str, str]]:
        """ログファイルをパース"""
        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(self.log_format, line.strip())
                if match:
                    timestamp, en_text, ja_text = match.groups()
                    entries.append((timestamp, en_text.strip(), ja_text.strip()))

        print(f"📊 ログエントリ数: {len(entries)}")
        return entries

    def analyze_english_phrases(
        self, entries: List[Tuple[str, str, str]], threshold: int = 2
    ) -> Dict[str, int]:
        """
        英語フレーズの出現頻度を分析
        threshold回以上出現したものを抽出
        """
        # 完全一致で集計
        en_phrases = Counter([en for _, en, _ in entries])

        # threshold回以上出現したものをフィルター
        repeated_en = {phrase: count for phrase, count in en_phrases.items()
                       if count >= threshold}

        # 出現回数でソート
        sorted_en = sorted(repeated_en.items(), key=lambda x: x[1], reverse=True)

        return dict(sorted_en)

    def analyze_japanese_phrases(
        self, entries: List[Tuple[str, str, str]], threshold: int = 2
    ) -> Dict[str, int]:
        """
        日本語フレーズの出現頻度を分析
        threshold回以上出現したものを抽出
        """
        ja_phrases = Counter([ja for _, _, ja in entries])

        repeated_ja = {phrase: count for phrase, count in ja_phrases.items()
                       if count >= threshold}

        sorted_ja = sorted(repeated_ja.items(), key=lambda x: x[1], reverse=True)

        return dict(sorted_ja)

    def analyze_partial_patterns(
        self, entries: List[Tuple[str, str, str]], min_length: int = 5
    ) -> Dict[str, int]:
        """
        部分一致パターンを分析
        似たフレーズをグループ化（例: "Thank you" + "Thank you for watching"）
        """
        en_texts = [en for _, en, _ in entries]

        # キーワード抽出（重要な単語）
        keywords = defaultdict(int)
        important_words = {
            "thank", "thanks", "see", "you", "next", "video", "watch", "subscribe",
            "channel", "like", "comment", "end", "goodbye", "bye", "please"
        }

        for text in en_texts:
            words = text.lower().split()
            for word in words:
                # 句読点を削除
                word_clean = re.sub(r"[,!?.;:]", "", word)
                if word_clean in important_words:
                    keywords[word_clean] += 1

        # 出現頻度でソート
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)

        return dict(sorted_keywords)

    def suggest_filters(
        self, repeated_en: Dict[str, int], repeated_ja: Dict[str, int]
    ) -> Dict[str, List[str]]:
        """
        フィルター候補を提案
        """
        suggestions = {
            "english_patterns": [],
            "japanese_patterns": [],
        }

        # 英語パターンの提案
        for phrase, count in repeated_en.items():
            # 動画終了関連のキーワードをチェック
            if any(
                kw in phrase.lower()
                for kw in [
                    "thank", "thanks", "see", "subscribe", "like", "comment",
                    "next", "video", "watch", "end", "goodbye", "bye",
                ]
            ):
                # 正規表現パターンに変換
                pattern = re.escape(phrase.lower()).replace("\\ ", "\\s+")
                suggestions["english_patterns"].append(f'r"{pattern}"')

        # 日本語パターンの提案
        for phrase, count in repeated_ja.items():
            if any(
                kw in phrase
                for kw in [
                    "ありがとう", "ご覧", "次", "動画", "ビデオ", "登録", "いいね",
                    "終わり", "終了", "さようなら", "バイ", "チャンネル",
                ]
            ):
                # 正規表現パターンに変換
                pattern = re.escape(phrase)
                suggestions["japanese_patterns"].append(f'r"{pattern}"')

        return suggestions

    def print_report(
        self,
        repeated_en: Dict[str, int],
        repeated_ja: Dict[str, int],
        keywords: Dict[str, int],
        suggestions: Dict[str, List[str]],
    ):
        """分析結果をレポート出力"""
        print("\n" + "=" * 70)
        print("📋 ログ分析レポート")
        print("=" * 70)

        # 繰り返し英語フレーズ
        print("\n【繰り返されている英語フレーズ】")
        print("-" * 70)
        for phrase, count in repeated_en.items():
            print(f"  {count}回 | {phrase}")

        # 繰り返し日本語フレーズ
        print("\n【繰り返されている日本語フレーズ】")
        print("-" * 70)
        for phrase, count in repeated_ja.items():
            print(f"  {count}回 | {phrase}")

        # 重要キーワード
        print("\n【検出されたキーワード（動画終了関連）】")
        print("-" * 70)
        for keyword, count in list(keywords.items())[:15]:
            print(f"  {count}回 | {keyword}")

        # フィルター提案
        print("\n【フィルター追加候補】")
        print("-" * 70)

        if suggestions["english_patterns"]:
            print("\n英語パターン：")
            for i, pattern in enumerate(suggestions["english_patterns"][:5], 1):
                print(f"  {i}. {pattern}")

        if suggestions["japanese_patterns"]:
            print("\n日本語パターン：")
            for i, pattern in enumerate(suggestions["japanese_patterns"][:5], 1):
                print(f"  {i}. {pattern}")

        print("\n" + "=" * 70)

    def save_suggestions(self, suggestions: Dict[str, List[str]], output_file: str = "filter_suggestions.json"):
        """提案をJSONファイルに保存"""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
        print(f"💾 提案を保存しました: {output_file}")


class FilterUpdater:
    """translator.py のフィルターを自動更新"""

    def __init__(self, translator_path: str = "translator.py"):
        self.translator_path = Path(translator_path)

    def update_filters(self, suggestions: Dict[str, List[str]], apply: bool = False):
        """
        提案されたフィルターを translator.py に追加

        Args:
            suggestions: フィルター提案
            apply: True の場合、実際にファイルに反映
        """
        if not self.translator_path.exists():
            print(f"❌ {self.translator_path} が見つかりません")
            return

        with open(self.translator_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 新しいパターンを生成
        english_patterns = suggestions.get("english_patterns", [])
        japanese_patterns = suggestions.get("japanese_patterns", [])

        print("\n【更新内容（プレビュー）】")
        print("-" * 70)

        if english_patterns:
            print(f"\n追加する英語パターン:")
            for pattern in english_patterns[:5]:
                print(f"  {pattern}")

        if japanese_patterns:
            print(f"\n追加する日本語パターン:")
            for pattern in japanese_patterns[:5]:
                print(f"  {pattern}")

        if not english_patterns and not japanese_patterns:
            print("\n📝 追加するパターンがありません")
            return

        if apply:
            print("\n✅ フィルターを実装中...")
            self._apply_filters_to_file(english_patterns, japanese_patterns)
        else:
            print("\n💡 ドライラン完了。--apply フラグで実装します")
            print("例: python analyze_and_update_filters.py --apply")

    def _apply_filters_to_file(self, english_patterns: List[str], japanese_patterns: List[str]):
        """
        実際に translator.py を修正

        冪等性: 追加しようとしているパターンが既にファイル内に存在する場合は
        重複追加を避けるためスキップする。
        安全性: 書き込み前に .bak バックアップを作成し、書き込み後に
        ast.parse() で構文検証を行う。検証に失敗した場合はバックアップから
        ロールバックする（成功時のみ確定）。
        """
        with open(self.translator_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        with open(self.translator_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 冪等性チェック: 既存内容に含まれているパターンは追加候補から除外
        def _not_already_present(pattern: str) -> bool:
            return pattern not in original_content

        filtered_english_patterns = [
            p for p in english_patterns if _not_already_present(p)
        ]
        filtered_japanese_patterns = [
            p for p in japanese_patterns if _not_already_present(p)
        ]

        skipped_english = len(english_patterns) - len(filtered_english_patterns)
        skipped_japanese = len(japanese_patterns) - len(filtered_japanese_patterns)
        if skipped_english or skipped_japanese:
            print(
                f"ℹ️  既に存在するため追加をスキップしたパターン: "
                f"英語 {skipped_english}個 / 日本語 {skipped_japanese}個"
            )

        if not filtered_english_patterns and not filtered_japanese_patterns:
            print("📝 追加するパターンはすべて既存のため、更新は行いません")
            return

        # WHISPER_MISTRANSLATIONS と MISTRANSLATION_PATTERNS のセクションを見つけて追加
        new_lines = []
        in_whisper_section = False
        in_ja_section = False
        whisper_updated = False
        ja_updated = False

        for i, line in enumerate(lines):
            # WHISPER_MISTRANSLATIONS セクション内か判定
            if "WHISPER_MISTRANSLATIONS = {" in line:
                in_whisper_section = True
                new_lines.append(line)
            elif in_whisper_section and line.strip() == "}":
                # 英語パターンを追加
                if filtered_english_patterns and not whisper_updated:
                    for pattern in filtered_english_patterns[:3]:  # 最大3つまで
                        new_lines.append(f"        {pattern}: True,\n")
                    whisper_updated = True
                in_whisper_section = False
                new_lines.append(line)

            # MISTRANSLATION_PATTERNS セクション内か判定
            elif "MISTRANSLATION_PATTERNS = {" in line:
                in_ja_section = True
                new_lines.append(line)
            elif in_ja_section and line.strip() == "}":
                # 日本語パターンを追加
                if filtered_japanese_patterns and not ja_updated:
                    for pattern in filtered_japanese_patterns[:3]:  # 最大3つまで
                        new_lines.append(f"        {pattern},\n")
                    ja_updated = True
                in_ja_section = False
                new_lines.append(line)

            else:
                new_lines.append(line)

        # 書き込み前に .bak バックアップを作成（同じディレクトリに配置）
        # 注: このメソッドはロジックとして実装するのみで、本タスクの中では
        # 実際に呼び出し・実行しない。
        backup_path = self.translator_path.with_suffix(
            self.translator_path.suffix + ".bak"
        )
        try:
            shutil.copy2(self.translator_path, backup_path)
        except Exception as e:
            print(f"❌ バックアップ作成に失敗したため更新を中止します: {e}")
            return

        # ファイルを上書き
        try:
            with open(self.translator_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            # 書き込み後に構文検証。失敗したらバックアップからロールバック。
            with open(self.translator_path, "r", encoding="utf-8") as f:
                written_content = f.read()

            try:
                ast.parse(written_content)
            except SyntaxError as e:
                print(f"❌ 構文検証に失敗したためロールバックします: {e}")
                shutil.copy2(backup_path, self.translator_path)
                return

            print(f"✅ {self.translator_path} を更新しました")
            print(f"   - 英語パターン: {len(filtered_english_patterns)}個追加")
            print(f"   - 日本語パターン: {len(filtered_japanese_patterns)}個追加")
        except Exception as e:
            print(f"❌ 更新に失敗しました: {e}")
            # 書き込み自体が失敗した場合もバックアップから復元を試みる
            try:
                shutil.copy2(backup_path, self.translator_path)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="ログ分析 & フィルター自動更新"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="分析対象のログファイルパス（デフォルト: 最新ログ）"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=2,
        help="繰り返し回数の閾値（デフォルト: 2回以上）"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="フィルターを translator.py に実装（慎重に使用）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="filter_suggestions.json",
        help="提案の保存ファイル（デフォルト: filter_suggestions.json）"
    )

    args = parser.parse_args()

    try:
        # ログ分析
        analyzer = LogAnalyzer()
        log_path = (
            Path(args.log_file) if args.log_file else analyzer.get_latest_log()
        )

        entries = analyzer.parse_log(log_path)

        # フレーズ分析
        repeated_en = analyzer.analyze_english_phrases(entries, args.threshold)
        repeated_ja = analyzer.analyze_japanese_phrases(entries, args.threshold)
        keywords = analyzer.analyze_partial_patterns(entries)

        # フィルター提案
        suggestions = analyzer.suggest_filters(repeated_en, repeated_ja)

        # レポート出力
        analyzer.print_report(repeated_en, repeated_ja, keywords, suggestions)

        # 提案を保存
        analyzer.save_suggestions(suggestions, args.output)

        # フィルター更新（オプション）
        updater = FilterUpdater()
        updater.update_filters(suggestions, args.apply)

        print("\n✅ 分析完了")

    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
