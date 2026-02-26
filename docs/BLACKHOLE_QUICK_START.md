# BlackHole クイックスタートガイド

初めてで、とにかく素早く始めたい方向け（5分で完了）

---

## ステップ 1: インストール（1分）

```bash
brew install blackhole-2ch
```

Homebrew がない場合：[公式サイト](https://existential.audio/blackhole/) からダウンロード

---

## ステップ 2: 複合デバイス作成（3分）

1. **Spotlight で「Audio MIDI 設定」と検索**（または Cmd+Space → "Audio MIDI"）

2. **左下の「+」→「複合デバイスを作成」**

3. **チェックボックスを ON にする**：
   - ✅ BlackHole 2ch
   - ✅ MacBook Pro のスピーカー（※ご自身の出力デバイス）

4. **右側パネルでマスターデバイスを「スピーカー」に設定**

5. **名前を変更**（任意）：例「Voice Bridge Output」

---

## ステップ 3: macOS 設定（1分）

1. **System Settings → Sound → Output**

2. **出力デバイスを複合デバイスに変更**

---

## ステップ 4: 動作確認（5秒）

```bash
# Device を確認
python main.py --list-devices

# BlackHole 2ch が表示されたら成功！
```

---

## ステップ 5: アプリを起動

```bash
python main.py
```

GUI が開いたら：
1. **YouTube で英語動画を再生**
2. **入力レベルバーが動くか確認**
3. **英語が認識されるか確認**

---

## よくある問題と解決方法

| 問題 | 解決方法 |
|---|---|
| 入力レベルが動かない | macOS の出力が複合デバイスになっているか確認 |
| BlackHole が見つからない | `brew list \| grep blackhole` で確認、なければ再インストール |
| 音が出ない | YouTube で音声を再生中か確認、スピーカーの音量確認 |

---

## 次のステップ

- [詳細マニュアル](./BLACKHOLE_MANUAL.md)
- [セットアップガイド](../setup_guide.md)
- [トラブルシューティング](./BLACKHOLE_MANUAL.md#トラブルシューティング)

---

**困った？ → [詳細マニュアル](./BLACKHOLE_MANUAL.md) を読んでください**
