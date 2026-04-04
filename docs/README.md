# Voice Bridge ドキュメント索引

Voice Bridge のドキュメントは以下のカテゴリで整理されています。

## 🎯 まず最初に読むべき内容

**以下から目的に合わせて選択してください：**

| 目的 | ガイド |
|---|---|
| **AI と会話したい** 💬 | [チャットモード完全ガイド](./guides/CHAT_MODE_GUIDE.md) |
| **動画・会議を翻訳したい** 🌍 | [翻訳モード完全ガイド](./guides/TRANSLATE_MODE_GUIDE.md) |
| **どちらか迷っている** 🤔 | [モード選択ガイド](./guides/MODES_OVERVIEW.md) |

---

## セットアップ・インストール

### メモリ別セットアップ

**ご利用のメモリサイズに合わせてモデルを選択します：**

- **[メモリ別セットアップガイド](./setup/MEMORY_REQUIREMENTS.md)** ⭐
  - 8GB 以下の推奨モデル
  - 16GB の推奨モデル
  - 32GB 以上の推奨モデル

### OS ごとのセットアップ

| ドキュメント | 説明 |
|---|---|
| [BlackHole クイックスタート](./setup/BLACKHOLE_QUICK_START.md) | macOS の音声キャプチャ設定（5分） |
| [BlackHole 詳細マニュアル](./setup/BLACKHOLE_MANUAL.md) | macOS の詳細なセットアップ方法 |
| [Ollama セットアップガイド](./setup/OLLAMA_SETUP.md) | ローカル LLM サーバーのセットアップ |

> 🔗 **各 OS の詳細インストールガイド**
> - macOS: [BlackHole クイックスタート](./setup/BLACKHOLE_QUICK_START.md)
> - Windows: WASAPIループバックで自動対応
> - Linux: [Linux トラブルシューティング](./troubleshooting/LINUX_TROUBLESHOOTING.md)

## ユーザーガイド

アプリの使い方や設定方法です。

### モード別ガイド

| ドキュメント | 説明 |
|---|---|
| [モード選択ガイド](./guides/MODES_OVERVIEW.md) | チャット vs 翻訳の選択 |
| [チャットモード完全ガイド](./guides/CHAT_MODE_GUIDE.md) | チャットモードの詳細 |
| [翻訳モード完全ガイド](./guides/TRANSLATE_MODE_GUIDE.md) | 翻訳モードの詳細 |
| [翻訳モード メモリ別ガイド](./guides/TRANSLATE_MODE_MEMORY_GUIDE.md) | 翻訳モードのメモリ別セットアップ |

### その他のガイド

| ドキュメント | 説明 |
|---|---|
| [GUI ガイド](./guides/GUI_GUIDE.md) | GUI でモード・エンジン・モデルを切り替える方法 |
| [CLI リファレンス](../reference/CLI_REFERENCE.md) | コマンドラインオプション一覧 |

## トラブルシューティング

問題解決のガイドです。

| ドキュメント | 対象者 |
|---|---|
| [BlackHole トラブルシューティング](./troubleshooting/BLACKHOLE_TROUBLESHOOTING.md) | macOS ユーザー |
| [Linux トラブルシューティング](./troubleshooting/LINUX_TROUBLESHOOTING.md) | Linux ユーザー |
| よくある質問（FAQ） | 全ユーザー |

## 技術リファレンス

システムアーキテクチャや技術詳細です。

| ドキュメント | 説明 |
|---|---|
| システムアーキテクチャ | 全体設計・ネットワーク接続図・処理パイプライン |
| コンポーネント一覧 | 使用技術・ライブラリ一覧 |
| CLI リファレンス | コマンドラインオプション完全リファレンス |

## 開発者向けドキュメント

本プロジェクトの内部構造や拡張方法についてです。

詳しくは [internal/](./internal/) フォルダをご覧ください。

- [ビルドガイド](./internal/BUILD.md)
- [インテグレーションガイド](./internal/INTEGRATION_GUIDE.md)
- [セットアップガイド](./internal/setup_guide.md)
- [Agents](./internal/AGENTS.md)

## 過去のドキュメント・アーカイブ

以下のドキュメントは完了した機能や参考資料です。

詳しくは [archive/](./archive/) フォルダをご覧ください。

- 完了した修正・機能追加（done/）
- ノート・下書き・参考資料（note/）
