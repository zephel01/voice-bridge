#!/usr/bin/env python3
"""
誤訳改善テストスクリプト
translator_improved.py の動作確認
"""

import sys
import json
from pathlib import Path
from translator_improved import Translator

# テストケース定義
TEST_CASES = [
    {
        "name": "Whisper誤認識 - See you in the next video",
        "input": "See you in the next video!",
        "expected_block": True,
        "category": "whisper_filter"
    },
    {
        "name": "Whisper誤認識 - Thanks for watching",
        "input": "Thanks for watching this video",
        "expected_block": True,
        "category": "whisper_filter"
    },
    {
        "name": "正常な翻訳 - Hello",
        "input": "Hello, how are you today?",
        "expected_block": False,
        "category": "normal"
    },
    {
        "name": "正常な翻訳 - Explanation",
        "input": "This is a Python tutorial about machine learning algorithms.",
        "expected_block": False,
        "category": "normal"
    },
    {
        "name": "IT用語 - Framework",
        "input": "We use the Django framework for web development.",
        "expected_block": False,
        "category": "terminology"
    },
    {
        "name": "重複排除テスト",
        "input": "Hello. Hello. How are you?",
        "expected_block": False,
        "category": "dedup"
    },
]


def print_header(text):
    """ヘッダー出力"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_test_result(name, input_text, output, expected_block, actual_block):
    """テスト結果を見やすく出力"""
    status = "✅ PASS" if expected_block == actual_block else "❌ FAIL"

    print(f"\n{status} {name}")
    print(f"   入力: {input_text[:50]}{'...' if len(input_text) > 50 else ''}")

    if actual_block:
        print(f"   結果: 🚫 フィルター（ブロック）")
    else:
        print(f"   結果: ✅ 翻訳実行")
        print(f"   出力: {output[:60]}{'...' if len(output) > 60 else ''}")

    print(f"   期待: {'ブロック' if expected_block else '翻訳実行'}")


def main():
    """メインテスト実行"""

    print_header("Voice Bridge - 誤訳改善テスト")
    print("\n⚙️  テスト設定:")
    print("  • デバッグモード: ON")
    print("  • ログファイル: /tmp/test_mistranslation.log")

    # テスト用トランスレーター初期化
    log_file = "/tmp/test_mistranslation.log"
    translator = Translator(
        source="en",
        target="ja",
        debug=True,
        log_file=log_file
    )

    # 既存のログをクリア
    if Path(log_file).exists():
        Path(log_file).unlink()

    # テスト実行
    results = {
        "total": len(TEST_CASES),
        "passed": 0,
        "failed": 0,
        "by_category": {}
    }

    for test in TEST_CASES:
        name = test["name"]
        input_text = test["input"]
        expected_block = test["expected_block"]
        category = test["category"]

        # 実行
        output = translator.translate(input_text)
        actual_block = (output == "")

        # 結果評価
        print_test_result(name, input_text, output, expected_block, actual_block)

        if expected_block == actual_block:
            results["passed"] += 1
        else:
            results["failed"] += 1

        if category not in results["by_category"]:
            results["by_category"][category] = {"passed": 0, "failed": 0}

        if expected_block == actual_block:
            results["by_category"][category]["passed"] += 1
        else:
            results["by_category"][category]["failed"] += 1

    # 最終結果
    print_header("テスト結果サマリー")

    print(f"\n📊 全体結果:")
    print(f"   合計: {results['total']} テスト")
    print(f"   成功: {results['passed']} ✅")
    print(f"   失敗: {results['failed']} ❌")
    print(f"   成功率: {results['passed']/results['total']*100:.1f}%")

    print(f"\n📂 カテゴリ別結果:")
    for category, count in results["by_category"].items():
        total = count["passed"] + count["failed"]
        rate = count["passed"] / total * 100
        print(f"   {category:20} {count['passed']}/{total} ({rate:.0f}%)")

    # ログファイルの内容を表示
    print_header("ログファイル内容（最初の5行）")

    if Path(log_file).exists():
        print(f"\n📝 ファイル: {log_file}\n")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                data = json.loads(line)
                print(f"  [{i+1}] {data['stage']:12} | {data['original'][:30]:30} → {data.get('translated', '[ERROR]')[:30]}")

        if len(lines) > 5:
            print(f"\n  ... その他 {len(lines) - 5} 行")

    # テストコマンドのヒント
    print_header("デバッグ用コマンド")

    print("\n📋 ログファイルを確認:")
    print(f"  tail -f {log_file}")

    print("\n📋 JSON 形式で解析:")
    print(f"  python << 'EOF'")
    print(f"  import json")
    print(f"  with open('{log_file}') as f:")
    print(f"      for line in f:")
    print(f"          data = json.loads(line)")
    print(f"          print(f\"{{data['stage']}} | {{data['original']}} → {{data.get('translated')}}\")")
    print(f"  EOF")

    print("\n")

    # 終了コード
    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
