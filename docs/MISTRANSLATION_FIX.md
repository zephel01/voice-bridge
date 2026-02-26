# 誤訳改善ガイド - voice-bridge v2.0

## 問題点
リアルタイム翻訳中に以下のような定型句が繰り返し挿入される：
- 「次のビデオでお会いしましょう」
- 「また次の動画でお会いしましょう」
- その他の動画終了フレーズ

**原因の仮説：**
1. Whisper が実際に話されていない「See you in the next video!」を誤認識している可能性
2. Google Translator が文脈を誤解して定型句を生成している可能性
3. または両方の組み合わせ

---

## 解決策（3段階アプローチ）

### ステップ1: デバッグモードの有効化
何が起こっているかを把握するため、デバッグ・ログ機能を追加しました。

**改善版ファイル：** `translator_improved.py`

**追加機能：**
- ✅ **デバッグモード** - 認識・翻訳の各段階をコンソール出力
- ✅ **ログファイル出力** - JSON形式で認識→翻訳の全過程を記録
- ✅ **Whisper誤認識フィルター** - 既知のパターンをブロック
- ✅ **日本語誤訳フィルター** - 動画終了フレーズをブロック

**使い方：**

```python
# デバッグモード有効 + ログファイル出力
translator = Translator(
    source="en",
    target="ja",
    debug=True,  # コンソール出力有効
    log_file="translator_debug.log"  # ログファイル指定
)

# 翻訳実行
result = translator.translate("Hello world")
# コンソールに詳細情報が出力され、ログファイルに全記録が保存される
```

**ログファイルの形式：**

```json
{
  "timestamp": "2026-02-26T10:30:45.123456",
  "stage": "success",
  "original": "Hello, how are you?",
  "translated": "こんにちは、お元気ですか？",
  "duration_sec": 0.85,
  "attempt": 1
}
```

---

### ステップ2: 誤訳フィルター

#### 2-1. Whisper 誤認識フィルター

**既知のパターン：**
```python
WHISPER_MISTRANSLATIONS = {
    r"see you in the next video": True,
    r"see you next time": True,
    r"thanks for watching": True,
    r"subscribe.*channel": True,
    r"like.*comment.*subscribe": True,
}
```

これらのパターンが認識されたら、自動的にフィルターされて翻訳されません。

#### 2-2. 日本語誤訳フィルター

**ブロック対象：**
- 「次のビデオでお会いしましょう」
- 「また次の動画で会いましょう」
- 「このビデオの終わり」
- など、動画終了関連フレーズ

**正規表現パターン例：**
```python
r"(?:次|次回|また)\s*(?:の\s*)?(?:ビデオ|動画|映像|レッスン|回)(?:で|で\s*)(?:お会いしましょう|会いましょう|お目にかかりましょう)"
```

---

### ステップ3: テキスト処理の強化

改善内容：

1. **より詳細な重複排除**
   - 従来：句点「。」でのみ分割
   - 改善：「。」「！」「？」「\n」で分割

2. **短い文の結合**
   - 5文字以下の短い文は前の文に結合
   - 例：「はじめに。テスト。」→「はじめにテスト。」

3. **翻訳前後のスキップ機能**
   - 必要に応じてフィルターを無効化
   - `translate(text, skip_filter=True)`

---

## 使い方（main.py への統合）

### オプション1: 既存コードをそのまま使う（推奨：最初）

```python
# main.py の line 64 を修正

# 修正前:
# self.translator = Translator(source=source_language, target=target_language)

# 修正後（デバッグモード有効）:
self.translator = Translator(
    source=source_language,
    target=target_language,
    debug=True,
    log_file="voice_bridge_translation.log"
)
```

### オプション2: 本格的に置き換える

```python
# translator.py を translator_improved.py にリネーム
# または、translator_improved.py から translator.py にコピー

cp translator_improved.py translator.py
```

---

## デバッグ・ログの確認

### ログファイルの読み方

```bash
# リアルタイムで監視
tail -f voice_bridge_translation.log | jq '.'

# または JSON として解析
python << 'EOF'
import json
with open("voice_bridge_translation.log") as f:
    for line in f:
        data = json.loads(line)
        print(f"{data['stage']:10} | {data['original'][:30]:30} → {data.get('translated', '[ERROR]')[:30]}")
EOF
```

### パターン分析

誤訳が多い場合、ログから以下を確認：

1. **Whisper の出力**
   - 「See you in the next video」が認識されているか？
   - 異なるバリエーションが認識されているか？

2. **Google 翻訳の結果**
   - フィルターされずに通った場合、何に翻訳されているか？

3. **タイミング**
   - どの場面で繰り返されているか？

---

## パターンの追加方法

独自のフィルターパターンを追加したい場合：

```python
# Whisper 誤認識パターンを追加
translator.WHISPER_MISTRANSLATIONS[r"your_pattern"] = True

# 日本語誤訳パターンを追加
translator.MISTRANSLATION_PATTERNS.add(r"あなたのパターン")
```

または、カスタムフィルター関数を実装：

```python
class MyTranslator(Translator):
    def _should_block_ja_mistranslation(self, text: str) -> bool:
        # 親クラスのチェック
        if super()._should_block_ja_mistranslation(text):
            return True

        # 独自チェック追加
        if "あなたのパターン" in text:
            return True

        return False
```

---

## テスト方法

### Unit テスト

```bash
cd /Users/h.yamamoto/works/project/voice-bridge
python translator_improved.py
```

出力例：
```
[Translator] English (en) → 日本語 (ja)
[Translator] デバッグモード: 有効
[Translator] ログファイル: /tmp/translator_debug.log
[Translator] 🚫 Whisper 誤認識フィルター: See you in the next video!
テスト2 結果: '' (ブロックされたため空文字)
[Translator] ✅ 翻訳成功 (0.85s): Hello, how are you today? → こんにちは、お元気ですか？
```

### 実アプリケーションでのテスト

```bash
python main.py --cli
# または
python main.py
```

ログファイルを監視：
```bash
tail -f voice_bridge_translation.log
```

---

## 改善効果の測定

### Before/After 比較

**修正前：**
```
[EN] See you in the next video!
[JA] 次のビデオでお会いしましょう。
[EN] Hello, world.
[JA] こんにちは、世界。
[EN] See you in the next video!
[JA] 次のビデオでお会いしましょう。  ← 繰り返し
```

**修正後：**
```
[EN] See you in the next video!
[JA] (フィルター）  ← ブロック
[EN] Hello, world.
[JA] こんにちは、世界。
[EN] See you in the next video!
[JA] (フィルター)  ← ブロック
```

---

## トラブルシューティング

### 問題1: フィルターが機能していない
- ログファイルを確認して、何が認識・翻訳されているか確認
- パターンが正規表現として正しいか確認
- 大文字小文字の問題がないか確認

### 問題2: 正常なテキストもフィルターされてしまう
- パターンが広すぎないか確認
- `skip_filter=True` で一時的に無効化してテスト

### 問題3: パフォーマンスが低下した
- ログファイル出力をオフに（`log_file=None`）
- デバッグモードをオフに（`debug=False`）

---

## 推奨される段階的な改善

1. **第1段階：デバッグ・ログ収集**
   - `translator_improved.py` を導入
   - デバッグモード有効で実行
   - ログを分析して誤訳パターンを特定

2. **第2段階：フィルター追加**
   - ログから見つかった具体的なパターンをフィルターに追加
   - テストして効果を測定

3. **第3段階：翻訳モデルの最適化**
   - 必要に応じて Google Translate のパラメータを調整
   - または別の翻訳エンジンへの移行を検討

---

## 次のステップ

改善版を試していただいて、以下をお知らせください：

1. ログファイルの内容（何が認識・翻訳されているか）
2. 実際に改善効果が見られたか
3. 新しく見つかった誤訳パターン

これらの情報があれば、さらに細かいチューニングができます！

