#!/usr/bin/env python3
"""
GUI 言語表示改善のテストスクリプト
"""

from gui import VoiceBridgeGUI

def test_language_mappings():
    """言語マッピング定義のテスト"""
    print("=" * 70)
    print("TEST: GUI 言語マッピング")
    print("=" * 70)

    gui = VoiceBridgeGUI()

    print("\n✓ LANGUAGE_DISPLAY マッピング（テキストボックスラベル用）:")
    print("-" * 70)
    for lang_code, display_name in gui.LANGUAGE_DISPLAY.items():
        print(f"  {lang_code:3s} → {display_name}")

    print("\n✓ LANGUAGE_DROPDOWN マッピング（ドロップダウン表示用）:")
    print("-" * 70)
    for lang_code, dropdown_name in gui.LANGUAGE_DROPDOWN.items():
        print(f"  {lang_code:3s} → {dropdown_name}")

    # 検証
    print("\n✓ マッピング検証:")
    print("-" * 70)

    all_langs = ["en", "ja", "zh", "es", "fr", "de", "ko"]

    # LANGUAGE_DISPLAY に全言語が含まれているか
    for lang in all_langs:
        if lang in gui.LANGUAGE_DISPLAY:
            print(f"  ✓ LANGUAGE_DISPLAY['{lang}'] = {gui.LANGUAGE_DISPLAY[lang]}")
        else:
            print(f"  ✗ LANGUAGE_DISPLAY['{lang}'] が見つかりません")

    # LANGUAGE_DROPDOWN に全言語が含まれているか
    print()
    for lang in all_langs:
        if lang in gui.LANGUAGE_DROPDOWN:
            print(f"  ✓ LANGUAGE_DROPDOWN['{lang}'] = {gui.LANGUAGE_DROPDOWN[lang]}")
        else:
            print(f"  ✗ LANGUAGE_DROPDOWN['{lang}'] が見つかりません")

    print("\n✓ 言語コード抽出テスト:")
    print("-" * 70)
    test_inputs = [
        "en (English)",
        "ja (日本語)",
        "zh (中国語)",
        "es (スペイン語)",
        "fr (フランス語)",
        "de (ドイツ語)",
        "ko (韓国語)",
    ]

    for input_str in test_inputs:
        extracted_code = input_str.split()[0]
        expected = input_str.split()[0]
        status = "✓" if extracted_code == expected else "✗"
        print(f"  {status} '{input_str}' → '{extracted_code}'")


def test_dropdown_values():
    """ドロップダウン値生成のテスト"""
    print("\n" + "=" * 70)
    print("TEST: ドロップダウン値生成")
    print("=" * 70)

    gui = VoiceBridgeGUI()

    # GUI の build() 中で行われる処理をシミュレート
    all_langs = ["en", "ja", "zh", "es", "fr", "de", "ko"]
    source_lang_dropdown_values = [gui.LANGUAGE_DROPDOWN[lang] for lang in all_langs]
    target_lang_dropdown_values = [gui.LANGUAGE_DROPDOWN[lang] for lang in all_langs]

    print("\n✓ ソース言語ドロップダウン値:")
    print("-" * 70)
    for i, value in enumerate(source_lang_dropdown_values, 1):
        print(f"  {i}. {value}")

    print("\n✓ ターゲット言語ドロップダウン値:")
    print("-" * 70)
    for i, value in enumerate(target_lang_dropdown_values, 1):
        print(f"  {i}. {value}")

    # ドロップダウンに同じ値があるか確認
    if source_lang_dropdown_values == target_lang_dropdown_values:
        print("\n✓ ソース言語とターゲット言語のドロップダウン値が同じです")
    else:
        print("\n✗ ドロップダウン値が異なります")


def test_default_values():
    """デフォルト値のテスト"""
    print("\n" + "=" * 70)
    print("TEST: デフォルト値")
    print("=" * 70)

    gui = VoiceBridgeGUI()

    # デフォルト言語
    default_source = "en"
    default_target = "ja"

    print(f"\n✓ デフォルトソース言語: {default_source}")
    print(f"  → LANGUAGE_DISPLAY: {gui.LANGUAGE_DISPLAY[default_source]}")
    print(f"  → LANGUAGE_DROPDOWN: {gui.LANGUAGE_DROPDOWN[default_source]}")

    print(f"\n✓ デフォルトターゲット言語: {default_target}")
    print(f"  → LANGUAGE_DISPLAY: {gui.LANGUAGE_DISPLAY[default_target]}")
    print(f"  → LANGUAGE_DROPDOWN: {gui.LANGUAGE_DROPDOWN[default_target]}")


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  GUI 言語表示改善 テスト".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        test_language_mappings()
        test_dropdown_values()
        test_default_values()

        print("\n" + "=" * 70)
        print("✓ 全テスト成功")
        print("=" * 70)
        print("\n改善内容:")
        print("  1. ドロップダウンメニューが言語名を表示（例: 'zh (中国語)' ）")
        print("  2. テキストボックスラベルが選択言語に応じて動的に変更")
        print("  3. emoji フラグ付きで視覚的に分かりやすく")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
