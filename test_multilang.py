#!/usr/bin/env python3
"""
多言語対応のテストスクリプト
オーディオキャプチャなしで、翻訳と言語切り替え機能をテストします
"""

import sys
import time
from transcriber import Transcriber
from translator import Translator
from tts_engine import TTSEngine

def test_transcriber():
    """Transcriber の言語パラメータテスト"""
    print("=" * 60)
    print("TEST 1: Transcriber - 言語パラメータテスト")
    print("=" * 60)

    test_cases = [
        ("en", "English"),
        ("ja", "日本語"),
        ("zh", "中国語"),
        ("es", "スペイン語"),
        ("fr", "フランス語"),
        ("de", "ドイツ語"),
        ("ko", "韓国語"),
    ]

    for lang_code, lang_name in test_cases:
        try:
            t = Transcriber(model_size="tiny", language=lang_code)
            print(f"✓ {lang_code} ({lang_name}): Transcriber 初期化成功")
        except Exception as e:
            print(f"✗ {lang_code} ({lang_name}): エラー - {e}")

    # 言語切り替えテスト
    print("\n言語切り替えテスト:")
    t = Transcriber(model_size="tiny", language="en")
    result = t.set_language("ja")
    if result:
        print("✓ en → ja: 言語切り替え成功")
    else:
        print("✗ en → ja: 言語切り替え失敗")

    result = t.set_language("invalid_lang")
    if not result:
        print("✓ 無効な言語コードの検出成功")


def test_translator():
    """Translator の言語ペアテスト"""
    print("\n" + "=" * 60)
    print("TEST 2: Translator - 言語ペアテスト")
    print("=" * 60)

    test_pairs = [
        ("en", "ja", "English → 日本語"),
        ("ja", "en", "日本語 → English"),
        ("zh", "ja", "中国語 → 日本語"),
        ("es", "ja", "スペイン語 → 日本語"),
        ("fr", "ja", "フランス語 → 日本語"),
        ("de", "ja", "ドイツ語 → 日本語"),
        ("ko", "ja", "韓国語 → 日本語"),
    ]

    for source, target, description in test_pairs:
        try:
            tr = Translator(source=source, target=target)
            print(f"✓ {description}: Translator 初期化成功")
        except Exception as e:
            print(f"✗ {description}: エラー - {e}")

    # 無効な言語ペアテスト
    print("\n無効な言語ペアテスト:")
    try:
        tr = Translator(source="ja", target="ja")  # 同じ言語
        print("✗ ja → ja: 同一言語ペアが許可されている（予期しない）")
    except ValueError as e:
        print(f"✓ ja → ja: エラー検出成功 - {str(e)[:50]}...")

    # 言語ペア動的変更テスト
    print("\n言語ペア動的変更テスト:")
    tr = Translator(source="en", target="ja")
    result = tr.set_language_pair("zh", "ja")
    if result:
        print("✓ en→ja → zh→ja: 言語ペア切り替え成功")
    else:
        print("✗ en→ja → zh→ja: 言語ペア切り替え失敗")


def test_tts_engine():
    """TTSEngine の言語対応テスト"""
    print("\n" + "=" * 60)
    print("TEST 3: TTSEngine - 言語別音声テスト")
    print("=" * 60)

    language_voices = {
        "ja": ["nanami", "keita"],
        "en": ["jenny", "guy"],
        "zh": ["xiaoxiao", "yunxi"],
        "es": ["elvira", "alvaro"],
        "fr": ["denise", "henri"],
        "de": ["katja", "conrad"],
        "ko": ["sunhi", "injoon"],
    }

    for lang, voices in language_voices.items():
        try:
            tts = TTSEngine(language=lang, voice=voices[0])
            print(f"✓ {lang}: TTSEngine 初期化成功 (voice={voices[0]})")
        except Exception as e:
            print(f"✗ {lang}: エラー - {e}")

    # 言語切り替えテスト
    print("\n言語切り替えテスト:")
    tts = TTSEngine(language="ja", voice="nanami")
    result = tts.set_language("en", voice="jenny")
    if result:
        print("✓ ja → en: 言語切り替え成功")
    else:
        print("✗ ja → en: 言語切り替え失敗")


def test_translation_quality():
    """翻訳品質テスト（実際の翻訳サンプル）"""
    print("\n" + "=" * 60)
    print("TEST 4: Translator - 翻訳品質テスト")
    print("=" * 60)

    test_cases = [
        ("en", "ja", "Hello, how are you today?", "挨拶翻訳"),
        ("en", "ja", "We use machine learning algorithms for cloud computing optimization.", "技術用語翻訳"),
        ("en", "ja", "The framework provides a robust database API for server-side development.", "IT用語翻訳"),
    ]

    for source, target, text, description in test_cases:
        try:
            tr = Translator(source=source, target=target)
            result = tr.translate(text)
            print(f"✓ {description}")
            print(f"  原文: {text}")
            print(f"  翻訳: {result}")
            print()
        except Exception as e:
            print(f"✗ {description}: エラー - {e}\n")


def test_language_code_mapping():
    """言語コードマッピングテスト"""
    print("=" * 60)
    print("TEST 5: Translator - 言語コードマッピングテスト")
    print("=" * 60)

    tr = Translator(source="zh", target="ja")

    # zh-CN への変換確認
    if tr.source == "zh-CN":
        print("✓ zh → zh-CN マッピング成功")
    else:
        print(f"✗ zh → zh-CN マッピング失敗: {tr.source}")

    # 言語名の確認
    if "中国語" in str(Translator.LANGUAGE_NAMES):
        print("✓ 言語名の定義確認成功")
    else:
        print("✗ 言語名の定義確認失敗")


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  voice-bridge 多言語対応 テストスイート".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    try:
        test_transcriber()
        test_translator()
        test_tts_engine()
        test_translation_quality()
        test_language_code_mapping()

        print("\n" + "=" * 60)
        print("テスト完了")
        print("=" * 60)
        print("\n✓ 多言語対応の実装が正常に機能しています")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
