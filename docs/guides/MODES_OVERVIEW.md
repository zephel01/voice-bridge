# モード選択ガイド — どのモードを選ぶ？

Voice Bridge には「チャットモード」と「翻訳モード」の 2 つのモードがあります。このガイドで目的に合ったモードを選択してください。

---

## 🎯 クイック比較

| 項目 | チャットモード | 翻訳モード |
|---|---|---|
| **目的** | AI と会話 | リアルタイム翻訳 |
| **入力** | マイク | マイク or システム音声 |
| **出力** | AI の音声応答 | 翻訳結果の音声 |
| **キャラクター** | ずんだもん・リリンちゃん等 | 各言語のナレーター |
| **必須準備** | Ollama（LLM） | OS ごとのセットアップ |
| **インターネット** | 不要（完全ローカル） | 翻訳に必要 |
| **用途** | 雑談・質問・指示 | YouTube・会議・映画 |

---

## 💬 チャットモード

**AI ロボットと音声で会話するモード**

### こんな人におすすめ

✅ AI との自然な音声対話が欲しい
✅ ずんだもん・リリンちゃんなどのキャラと話したい
✅ AI に質問や指示を出したい
✅ 完全ローカルで動作させたい（プライバシー重視）

### 使用シーン

```
💭 雑談：「今日の天気は？」
📚 学習：「Python について教えて」
📋 タスク：「今週の TODO を作って」
🎨 創作：「面白い話を作ってよ」
```

### セットアップ難易度

🟡 **中程度** — Ollama のセットアップが必要

### 詳細ガイド

👉 **[チャットモード完全ガイド](./CHAT_MODE_GUIDE.md)** を参照

---

## 🌍 翻訳モード

**リアルタイム音声翻訳モード**

### こんな人におすすめ

✅ YouTube などの動画を別言語で聞きたい
✅ 国際会議をリアルタイム翻訳したい
✅ 映画・ドラマを翻訳したい
✅ 複数言語の翻訳が必要

### 使用シーン

```
📺 YouTube 英語動画を日本語で視聴
🎤 国際会議のスペイン語を日本語に翻訳
🎬 フランス映画をリアルタイム翻訳
📞 国際電話を中国語から日本語に翻訳
```

### 対応言語

英語 / 日本語 / 中国語 / スペイン語 / フランス語 / ドイツ語 / 韓国語

### セットアップ難易度

🟢 **簡単** （Windows なら不要）

| OS | セットアップ |
|---|---|
| **Windows** | ✅ 不要（WASAPI 自動対応） |
| **macOS** | 🟡 BlackHole インストール |
| **Linux** | 🟡 PulseAudio/PipeWire 設定 |

### 詳細ガイド

👉 **[翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md)** を参照

---

## 🔄 モード選択フロー

```
Voice Bridge を使いたい
  │
  ├─ AI と会話したい？
  │   ├─ YES → チャットモード ✅
  │   │        [チャットモード完全ガイド](./CHAT_MODE_GUIDE.md)
  │   │
  │   └─ NO ↓
  │
  └─ 動画・会議を翻訳したい？
      ├─ YES → 翻訳モード ✅
      │        [翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md)
      │
      └─ 迷ったら → [モード別ガイド](./MODES_OVERVIEW.md)で再確認
```

---

## ⚡ クイックスタート

### チャットモード（30 秒）

1. **Ollama を起動**
   ```bash
   ollama serve
   ```

2. **Voice Bridge を起動（別ターミナル）**
   ```bash
   python main.py --mode chat --vad
   ```

3. **マイクで話しかける**

詳しくは [チャットモード完全ガイド](./CHAT_MODE_GUIDE.md#クイックスタート3ステップ)

### 翻訳モード（30 秒）

1. **Voice Bridge を起動**
   ```bash
   python main.py --mode translate --source-lang en --target-lang ja
   ```

2. **YouTube などで再生**

3. **「開始」をクリック**

詳しくは [翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md#クイックスタート3ステップ)

---

## 📚 モード別ドキュメント

### チャットモード関連

| ドキュメント | 内容 |
|---|---|
| [チャットモード完全ガイド](./CHAT_MODE_GUIDE.md) | 詳細セットアップ・最適化・トラブル対応 |
| [Ollama セットアップガイド](../setup/OLLAMA_SETUP.md) | ローカル LLM サーバーのセットアップ |
| [GUI ガイド](./GUI_GUIDE.md) | GUI 設定の詳細（LLM 選択等） |

### 翻訳モード関連

| ドキュメント | 内容 |
|---|---|
| [翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md) | 詳細セットアップ・最適化・トラブル対応 |
| [BlackHole クイックスタート](../setup/BLACKHOLE_QUICK_START.md) | macOS のセットアップ |
| [Linux トラブルシューティング](../troubleshooting/LINUX_TROUBLESHOOTING.md) | Linux のセットアップ |

### 共通ドキュメント

| ドキュメント | 内容 |
|---|---|
| [GUI ガイド](./GUI_GUIDE.md) | GUI 全般の設定方法 |
| [CLI リファレンス](../reference/CLI_REFERENCE.md) | コマンドラインオプション |
| [FAQ](../troubleshooting/FAQ.md) | よくある質問とトラブル対応 |
| [システムアーキテクチャ](../reference/ARCHITECTURE.md) | 技術詳細 |

---

## 💡 モード切り替え

GUI なら「モード」ドロップダウンで簡単に切り替え可能です。

または、起動時のコマンドで指定：

```bash
# チャットモード
python main.py --mode chat --vad

# 翻訳モード
python main.py --mode translate --source-lang en --target-lang ja
```

---

## ❓ さらに詳しく知りたい場合

- **チャットモード詳細** → [チャットモード完全ガイド](./CHAT_MODE_GUIDE.md)
- **翻訳モード詳細** → [翻訳モード完全ガイド](./TRANSLATE_MODE_GUIDE.md)
- **技術詳細** → [システムアーキテクチャ](../reference/ARCHITECTURE.md)
- **トラブル対応** → [FAQ](../troubleshooting/FAQ.md)
