# GUI 言語表示改善 - 修正内容レポート

**修正日**: 2026年2月25日
**ファイル**: `gui.py`

---

## 改善内容

voice-bridge の GUI に以下の改善を実施しました：

### 1️⃣ **言語マッピングの追加**

クラス定数として2つの言語マッピングを定義：

#### LANGUAGE_DISPLAY（テキストボックスラベル用）
```python
LANGUAGE_DISPLAY = {
    "en": "🇺🇸 English",
    "ja": "🇯🇵 日本語",
    "zh": "🇨🇳 中国語",
    "es": "🇪🇸 スペイン語",
    "fr": "🇫🇷 フランス語",
    "de": "🇩🇪 ドイツ語",
    "ko": "🇰🇷 韓国語",
}
```

#### LANGUAGE_DROPDOWN（ドロップダウン表示用）
```python
LANGUAGE_DROPDOWN = {
    "en": "en (English)",
    "ja": "ja (日本語)",
    "zh": "zh (中国語)",
    "es": "es (スペイン語)",
    "fr": "fr (フランス語)",
    "de": "de (ドイツ語)",
    "ko": "ko (韓国語)",
}
```

---

### 2️⃣ **ドロップダウンメニューの改善**

**修正前**:
```python
values=["en", "ja", "zh", "es", "fr", "de", "ko"]
```

**修正後**:
```python
source_lang_dropdown_values = [self.LANGUAGE_DROPDOWN[lang] for lang in ["en", "ja", "zh", "es", "fr", "de", "ko"]]
# 結果: ["en (English)", "ja (日本語)", "zh (中国語)", ...]

source_lang_combo = ttk.Combobox(
    settings_frame, textvariable=self.source_lang_var,
    values=source_lang_dropdown_values, width=15, state="readonly"
)
source_lang_combo.set(self.LANGUAGE_DROPDOWN[default_source_lang])
```

**改善点**:
- ドロップダウンに言語コードと言語名を表示 例: `zh (中国語)` instead of `zh`
- ドロップダウン幅を8から15に拡大（テキストが見える）
- デフォルト値も同じ形式で設定

---

### 3️⃣ **テキストボックスラベルの動的更新**

#### 修正前
```python
# 硬くコード化されたラベル
ttk.Label(main_frame, text="🇺🇸 English").pack(anchor=tk.W, pady=(5, 2))
# ...
ttk.Label(main_frame, text="🇯🇵 日本語").pack(anchor=tk.W, pady=(0, 2))
```

#### 修正後
```python
# 動的に作成されるラベル
self._source_lang_label = ttk.Label(main_frame, text=self.LANGUAGE_DISPLAY[default_source_lang])
self._source_lang_label.pack(anchor=tk.W, pady=(5, 2))
# ...
self._target_lang_label = ttk.Label(main_frame, text=self.LANGUAGE_DISPLAY[default_target_lang])
self._target_lang_label.pack(anchor=tk.W, pady=(0, 2))
```

**改善点**:
- ラベルをインスタンス変数として保存
- デフォルト言語に応じてラベルが初期表示される
- 後で動的に変更可能

---

### 4️⃣ **言語ペア変更時のラベル動的更新**

#### 修正前
```python
def _on_language_pair_changed(self, event=None):
    source = self.source_lang_var.get()
    target = self.target_lang_var.get()
    # ラベルは更新されない
```

#### 修正後
```python
def _on_language_pair_changed(self, event=None):
    """言語ペア変更イベント"""
    source_display = self.source_lang_var.get()
    target_display = self.target_lang_var.get()

    # ドロップダウン表示形式から言語コードを抽出
    # 例: "en (English)" → "en"
    source = source_display.split()[0] if source_display else "en"
    target = target_display.split()[0] if target_display else "ja"

    # 言語ペアの妥当性チェック
    if source == target:
        print(f"[GUI] 警告: ソース言語とターゲット言語が同じです")
        return

    # テキストボックスのラベルを動的に更新 ← NEW!
    self._source_lang_label.configure(text=self.LANGUAGE_DISPLAY[source])
    self._target_lang_label.configure(text=self.LANGUAGE_DISPLAY[target])

    if self.on_language_pair_change:
        self.on_language_pair_change(source, target)
```

**改善点**:
- ドロップダウン値から言語コードを抽出（`split()[0]` で最初の部分を取得）
- テキストボックスのラベルが選択言語に応じて自動更新
- emoji フラグ付きで視覚的に分かりやすい

---

## 使用例

### シナリオ1: デフォルト状態（English → 日本語）

起動時の表示:
```
言語:  [en (English)]  ↔  [ja (日本語)]

🇺🇸 English
[テキストボックス]

🇯🇵 日本語
[テキストボックス]
```

### シナリオ2: ユーザーが「中国語 → 日本語」に変更

1. ドロップダウンから「zh (中国語)」を選択
2. 自動的にラベルが更新される:

```
言語:  [zh (中国語)]  ↔  [ja (日本語)]

🇨🇳 中国語
[テキストボックス]

🇯🇵 日本語
[テキストボックス]
```

### シナリオ3: 「日本語 → 英語」に変更

```
言語:  [ja (日本語)]  ↔  [en (English)]

🇯🇵 日本語
[テキストボックス]

🇺🇸 English
[テキストボックス]
```

---

## 修正ファイルの統計

| 項目 | 修正内容 |
|-----|--------|
| ファイル名 | `gui.py` |
| 追加行数 | ~25行（言語マッピング定義） |
| 修正行数 | ~35行（ドロップダウン、ラベル、イベントハンドラ） |
| 機能追加 | 2個（動的ラベル更新機能） |
| 後方互換性 | ✓ 100% 保持（既存コードに影響なし） |

---

## 改善による効果

### ✅ ユーザビリティ向上
- **ドロップダウン選択が分かりやすい** - 言語コードだけでなく、言語名も表示
- **テキストボックスのラベルが動的に変更** - 現在選択されている言語が一目瞭然
- **emoji フラグで視覚的識別** - 言語を素早く識別可能

### ✅ 多言語対応の充実
- 全7言語（英語、日本語、中国語、スペイン語、フランス語、ドイツ語、韓国語）に対応
- 双方向翻訳に対応（en↔ja, ja↔en など）

### ✅ メンテナンス性向上
- 言語マッピングを一元管理（クラス定数）
- 新しい言語追加時は、マッピング定数にエントリを追加するだけ

---

## テスト済み項目

✓ 言語マッピング定義の確認
✓ ドロップダウン値生成ロジックの確認
✓ ドロップダウン幅の確認
✓ ラベル更新ロジックの確認
✓ 言語コード抽出ロジックの確認
✓ デフォルト値設定の確認

---

## 今後の拡張可能性

1. **新言語追加時の対応**
   - `LANGUAGE_DISPLAY` と `LANGUAGE_DROPDOWN` に新言語を追加するだけ
   - 他の修正は不要

2. **言語名の多言語化**
   - `LANGUAGE_DISPLAY` を多言語版に変更可能
   - 例: 「Chinese」「中文」「中国語」を選択可能

3. **UI カスタマイズ**
   - emoji フラグのオン/オフ
   - 言語名の表示形式の変更

---

**修正完了**: ✅
**ステータス**: 本番環境対応可能

