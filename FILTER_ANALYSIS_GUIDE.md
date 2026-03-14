# 🔍 ログ分析 & フィルター自動更新ガイド

## 概要

`analyze_and_update_filters.py` は、翻訳ログを自動分析して、**繰り返し出現するワードやフレーズを検出**し、translator.py のフィルターに追加するスクリプトです。

---

## 🚀 使い方

### 基本的な使い方

```bash
# 最新ログを分析（デフォルト）
python analyze_and_update_filters.py

# 特定のログファイルを分析
python analyze_and_update_filters.py --log-file logs/20260314_170201.log

# 繰り返し回数の閾値を変更（3回以上）
python analyze_and_update_filters.py --threshold 3

# 結果を別のファイルに保存
python analyze_and_update_filters.py --output my_suggestions.json
```

---

## 📊 出力例

```
📋 ログ分析レポート
======================================================================

【繰り返されている英語フレーズ】
----------------------------------------------------------------------
  4回 | Thank you very much.
  3回 | Thank you very much for watching!

【繰り返されている日本語フレーズ】
----------------------------------------------------------------------
  4回 | どうもありがとうございます。
  3回 | ご覧いただきまして誠にありがとうございます！

【検出されたキーワード（動画終了関連）】
----------------------------------------------------------------------
  29回 | you
  14回 | thank
   5回 | end

【フィルター追加候補】
----------------------------------------------------------------------
英語パターン：
  1. r"thank\s+you\s+very\s+much\."
  2. r"thank\s+you\s+very\s+much\s+for\s+watching!"

日本語パターン：
  1. r"どうもありがとうございます。"
  2. r"ご覧いただきまして誠にありがとうございます！"
```

---

## 🔧 パラメータ説明

| パラメータ | 説明 | デフォルト |
|-----------|------|---------|
| `--log-file` | 分析対象のログファイルパス | 最新ログを自動選択 |
| `--threshold` | 繰り返し回数の最小値 | 2回以上 |
| `--output` | 提案の保存ファイル | filter_suggestions.json |
| `--apply` | フィルターを実装（未実装） | - |

---

## 📈 動作フロー

```
┌─────────────────────────┐
│  ログファイル読み込み    │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  英語フレーズ分析       │
│  (完全一致で集計)        │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  日本語フレーズ分析      │
│  (完全一致で集計)        │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  キーワード抽出        │
│  (重要な動画終了関連単語) │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  フィルター提案生成      │
│  (正規表現パターン化)    │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  JSON提案ファイル作成    │
│  & レポート表示          │
└─────────────────────────┘
```

---

## 💡 実活用例

### シナリオ1: 新しい繰り返しパターンを発見

```bash
# 最新のログを分析
python analyze_and_update_filters.py

# 出力から「Subscribe to my channel」が4回繰り返されていることを発見
# → filter_suggestions.json に追加提案が含まれる

# translator.py にを手動で追加:
# WHISPER_MISTRANSLATIONS に:
#   r"subscribe\s+to\s+(?:my\s+)?channel": True,
# を追加
```

### シナリオ2: 定期的にログを分析

```bash
# 毎日ログを分析するために、cron ジョブで実行
# crontab -e で以下を追加:

# 毎日午前3時にログを分析して、結果を保存
0 3 * * * cd /path/to/voice-bridge && python analyze_and_update_filters.py --output daily_analysis.json

# 結果を確認
tail -20 daily_analysis.json | python -m json.tool
```

### シナリオ3: 複数のログを比較

```bash
# ログAを分析
python analyze_and_update_filters.py --log-file logs/20260314_170201.log --output analysis_A.json

# ログBを分析
python analyze_and_update_filters.py --log-file logs/20260314_171726.log --output analysis_B.json

# 結果を比較
cat analysis_A.json
cat analysis_B.json
```

---

## 🎯 フィルター候補の確認方法

生成された `filter_suggestions.json` を確認：

```bash
# JSON を整形して表示
python -m json.tool filter_suggestions.json

# または cat で直接確認
cat filter_suggestions.json
```

---

## 🔧 translator.py への手動追加方法

分析結果をもとに、translator.py のフィルターを手動で追加：

```python
# translator.py の WHISPER_MISTRANSLATIONS に追加:
WHISPER_MISTRANSLATIONS = {
    # ... 既存のパターン ...

    # 新しいパターンを追加:
    r"thank\s+you\s+very\s+much\.": True,
    r"thank\s+you\s+very\s+much\s+for\s+watching!": True,
}

# MISTRANSLATION_PATTERNS に追加:
MISTRANSLATION_PATTERNS = {
    # ... 既存のパターン ...

    # 新しいパターンを追加:
    r"どうもありがとうございます。",
    r"ご覧いただきまして誠にありがとうございます！",
}
```

---

## 📝 スクリプトのカスタマイズ

### 検出対象キーワードの変更

`analyze_and_update_filters.py` の `important_words` を編集：

```python
important_words = {
    "thank", "thanks", "see", "you", "next", "video", "watch", "subscribe",
    "channel", "like", "comment", "end", "goodbye", "bye", "please",
    # ここに新しいキーワードを追加:
    "donate", "sponsor", "merch",
}
```

### 繰り返し閾値の調整

デフォルトは2回以上ですが、より厳しい条件（3回以上）にしたい場合：

```bash
python analyze_and_update_filters.py --threshold 3
```

---

## ❓ トラブルシューティング

### Q: ログファイルが見つからない
```bash
# ログディレクトリを確認
ls -la logs/

# または、明示的にファイルを指定
python analyze_and_update_filters.py --log-file /path/to/log.log
```

### Q: 提案が空っぽ
- ログに繰り返しが少ない可能性
- `--threshold` を低くしてみる:
  ```bash
  python analyze_and_update_filters.py --threshold 1
  ```

### Q: JSON形式のエラー
```bash
# JSON ファイルを検証
python -m json.tool filter_suggestions.json
```

---

## 🚀 今後の拡張

- [ ] `--apply` フラグで、自動的に translator.py を更新
- [ ] フィルター設定をJSON外部ファイルで管理
- [ ] Slack/Discord への通知機能
- [ ] 定期実行のスケジューリング対応

---

## 📌 まとめ

1. **定期的に実行** - 新しいYouTube動画を翻訳するたびに実行
2. **結果を確認** - 提案されたパターンが妥当か確認
3. **手動で追加** - translator.py のフィルターに追加
4. **テスト** - 実際に翻訳してみて、フィルターが機能するか確認

これで、繰り返し問題を自動で検出 & 対応できます！
