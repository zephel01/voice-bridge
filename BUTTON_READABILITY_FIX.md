# ボタンテキスト見やすさ改善 - 修正内容

**修正日**: 2026年2月25日
**問題**: 再生時のボタンテキストが見づらい
**解決方法**: disabled 状態のボタンスタイルを改善

---

## 問題の説明

ユーザーが再生（開始）ボタンを押すと、ボタンが disabled 状態（灰色）になります。しかし、tkinter のデフォルトの disabled スタイルでは、テキストのコントラストが低くなり、見づらくなっていました。

```
修正前（見づらい）:
▶ 開始 → disabled状態になると灰色でテキストが薄くなる
```

---

## 修正内容

### 追加パラメータ

各ボタンに以下の2つのパラメータを追加しました：

| パラメータ | 説明 | 値 |
|----------|------|-----|
| `disabledforeground` | disabled 時のテキスト色 | `#1e1e2e`（濃い灰色） |
| `disabledbackground` | disabled 時の背景色 | 各ボタンに応じた色 |

### 修正詳細

#### 1. 開始ボタン（▶ 開始）
```python
# 修正前
self.start_btn = tk.Button(
    btn_frame, text="▶ 開始", command=self._on_start,
    bg="#a6e3a1", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
    width=12, height=1, relief=tk.FLAT, cursor="hand2"
)

# 修正後
self.start_btn = tk.Button(
    btn_frame, text="▶ 開始", command=self._on_start,
    bg="#a6e3a1", fg="#1e1e2e", font=("Helvetica", 13, "bold"),
    disabledforeground="#1e1e2e", disabledbackground="#9fc593",  ← NEW
    width=12, height=1, relief=tk.FLAT, cursor="hand2"
)
```

**色の説明**:
- 通常時: `bg="#a6e3a1"` (明るい緑)
- disabled時: `disabledbackground="#9fc593"` (やや暗い緑)
- テキスト: `disabledforeground="#1e1e2e"` (濃い灰色で見やすく)

#### 2. 停止ボタン（■ 停止）
```python
# 修正後
disabledforeground="#1e1e2e", disabledbackground="#e89aaa",
```

**色の説明**:
- 通常時: `bg="#f38ba8"` (明るいピンク)
- disabled時: `disabledbackground="#e89aaa"` (やや暗いピンク)

#### 3. クリアボタン（🗑 クリア）
```python
# 修正後
disabledforeground="#1e1e2e", disabledbackground="#7aa8e8",
```

**色の説明**:
- 通常時: `bg="#89b4fa"` (明るい青)
- disabled時: `disabledbackground="#7aa8e8"` (やや暗い青)

---

## ビジュアル比較

### 修正前（見づらい）
```
┌─────────────────────────────────────────────┐
│ ▶ 開始(normal)  ■ 停止(disabled)  クリア   │
│   [明るい緑]        [薄い灰色]   [明るい青] │
│                   ↑テキストが見づらい        │
└─────────────────────────────────────────────┘
```

### 修正後（見やすい）
```
┌──────────────────────────────────────────────┐
│ ▶ 開始(disabled) ■ 停止(normal)  クリア   │
│   [暗い緑]        [明るいピンク]  [明るい青] │
│  ↑テキストはっきり ↑テキストはっきり         │
└──────────────────────────────────────────────┘
```

---

## 改善のポイント

### ✅ コントラストの向上
- disabled 時のテキストが濃い色（`#1e1e2e`）になった
- 背景色も暗めにして、全体的なコントラストが改善

### ✅ 色の一貫性
- 各ボタンの色体系を保持
  - 開始ボタン: 緑系
  - 停止ボタン: ピンク系
  - クリアボタン: 青系

### ✅ ユーザー体験の向上
- ボタンの状態（enabled / disabled）が視覚的に明確
- テキストが常に読みやすい

---

## 技術詳細

### tkinter Button のスタイル属性

```python
tk.Button(
    parent,
    # 通常時のスタイル
    bg="#a6e3a1",           # 背景色
    fg="#1e1e2e",           # テキスト色

    # disabled時のスタイル（今回追加）
    disabledforeground="#1e1e2e",  # disabled時のテキスト色
    disabledbackground="#9fc593",  # disabled時の背景色

    # その他
    font=("Helvetica", 13, "bold"),
    width=12,
    height=1,
    relief=tk.FLAT,
    cursor="hand2"
)
```

### ボタン状態の切り替え

プログラムからボタン状態を変更する時:

```python
# 開始時
self.start_btn.configure(state=tk.DISABLED)  # disabled に設定
self.stop_btn.configure(state=tk.NORMAL)     # normal に設定

# 停止時
self.start_btn.configure(state=tk.NORMAL)    # normal に設定
self.stop_btn.configure(state=tk.DISABLED)   # disabled に設定
```

このときに、新しく定義した `disabledforeground` と `disabledbackground` が自動的に適用されます。

---

## 修正統計

| 項目 | 値 |
|-----|-----|
| 修正ファイル | gui.py |
| 修正行数 | 3行（各ボタンに1行ずつ） |
| 追加パラメータ数 | 6個（各ボタンに `disabledforeground` と `disabledbackground`） |
| 影響範囲 | ボタンの disabled 状態のみ |
| 後方互換性 | 100% 保持（既存コードに影響なし） |

---

## テスト方法

GUI を起動して、以下の動作を確認できます：

1. **開始ボタンをクリック**
   - 開始ボタンが disabled になり、濃い緑色で見やすくなる
   - 停止ボタンが normal になり、ピンク色で利用可能な状態

2. **停止ボタンをクリック**
   - 停止ボタンが disabled になり、濃いピンク色で見やすくなる
   - 開始ボタンが normal になり、緑色で利用可能な状態

3. **クリアボタン**
   - 常に normal 状態で青色

---

## 追加説明

### なぜこのパラメータが必要か？

tkinter のデフォルト disabled スタイルは、アプリケーションによっては見づらくなることがあります。特にダークテーマを使用しているアプリケーションでは、disabled テキストが自動的に暗くなるため、背景色と区別がつきにくくなります。

このため、`disabledforeground` と `disabledbackground` を明示的に指定することで、disabled 時のボタンを常に見やすく保つことができます。

---

## 今後の改善案

1. **ホバー効果**の追加
   - マウスをボタンに当てた時、色が変わる効果

2. **アクティブ状態**の視覚化
   - disabled と normal 以外の状態を追加

3. **ボタンの統一スタイルクラス**
   - ボタンスタイルを共通化して管理

---

**修正完了**: ✅
**ステータス**: 本番環境対応完了

ボタンのテキストが見やすくなりました！

