# Voice Bridge 最適化提案書

> 作成日: 2026-04-18
> スコープ: Python バックエンド全体（`main.py`, `gui.py`, ASR/TTS/翻訳/LLM/Live2D 関連モジュール）
> 方針: **提案のみ・コードは未変更**。実装は本書の承認後に段階的に行う前提。
> `live2d-ui/`（Electron）と `chrome-extension/` は別タスクとして切り出し、本書では言及のみにとどめる。

---

## 0. 要約（最初に読むべき1ページ）

コードは機能としてはよく動いているが、**`main.py` (1401行) と `gui.py` (581行) に責務が集中**し、3系統の ASR/TTS が統一インタフェースを持たないため、機能追加のたびに同じロジックを各所にコピーする状態になっている。次の3つが最大のレバレッジ。

1. **マルチスレッド安全性のバグ修正**（数時間、効果は大）
   - `_is_playing` フラグがロック無しで複数スレッドから読み書きされている
   - `stop()` が `_streaming_asr.stop()` を必ず呼ぶ保証が無い
2. **ASR / TTS を共通インタフェース化**（1〜2日、効果は大）
   - 3種ずつあるエンジンを Protocol + ファクトリで統合 → `main.py` の分岐が消える
3. **`main.py` のモジュール分割**（1週間程度、効果は中長期）
   - `pipeline/translate.py`, `pipeline/chat.py`, `cli.py`, `runner.py` などへ切り出し
   - 現状は `VoiceBridge` クラスに **パイプライン + ASR/TTS 管理 + 設定変更 + AI + Live2D + CLI** が同居

| 区分 | 件数 | 合計工数 | 効果 |
|:----|:----:|:--------:|:-----|
| 高優先度（バグ・安全性） | 6 | 1〜2日 | 即効性あり |
| 中優先度（重複削除・性能） | 9 | 1週間弱 | 明確 |
| 低優先度（構造・体裁） | 8 | 1〜2週 | 長期 |

---

## 1. 現状サマリ

### 1.1 ファイル規模（Python のみ）

| ファイル | 行数 | 主責務 | 備考 |
|:---|---:|:---|:---|
| `main.py` | 1401 | VoiceBridge クラス + run_cli + run_gui + main | **肥大化の主犯** |
| `gui.py` | 581 | VoiceBridgeGUI 1クラス | build() が269行 |
| `benchmark_asr.py` | 434 | ASR比較ベンチ | 単発スクリプト |
| `transcriber_moonshine.py` | 415 | Moonshine ASR | `SUPPORTED_LANGUAGES` が他と不一致 |
| `ai_chat.py` | 398 | OpenAI互換チャット | 内部で chat_stream / chat_batch |
| `live2d_bridge.py` | 393 | WebSocket + 感情推論 | `infer_emotion` はキーワード式 |
| `analyze_and_update_filters.py` | 387 | ログ分析→フィルタ提案 | `--apply` が未実装 |
| `transcriber_qwen3.py` | 343 | Qwen3 ASR | |
| `translator.py` | 307 | Google翻訳ラッパ | `translator.py.bak` が残存（git 非追跡）|
| `audio_capture.py` / `_win.py` | 295 / 239 | macOS/Linux / Windows | VAD 対応が非対称 |
| `latency_tracker.py` | 220 | 3クラス構成 | 過剰設計気味 |
| `test_mistranslation_fix.py` | 182 | 旧テスト | **import 先が存在しない（下記 4.6）** |

### 1.2 検証した事実（スポットチェック済み）

- `translator.py.bak` は **git に追跡されていない**。`.gitignore` の `*.bak` で捕捉済み。ローカルの掃除だけで済む。
- `test_mistranslation_fix.py` は `from translator_improved import Translator` を import しているが、**`translator_improved.py` はリポジトリに存在しない**。テストは実行不能。
- `filter_suggestions.json` は `{"english_patterns": [], "japanese_patterns": []}` の空殻。
- `.env` に `COEIROINK_HOST` があるが `.env.example` には無い（ドキュメント drift）。
- `logs/` は 142ファイル 1.1MB。`.gitignore` 済み。世代管理なし。
- `_is_playing` はロック無しで `main.py:218, 232`（再生スレッド）と `318, 471, 551`（パイプラインスレッド）から同時アクセス。
- `main.py:129` で `mode=="chat"` のとき `self.translator = None` なので、`change_language_pair()`（993行以降）はチャットモードで呼ぶと `AttributeError` を起こしうる（GUI からの呼ばれ方を要確認）。

---

## 2. 高優先度（バグ・安全性）

> 「今すぐ直せば安定する」項目。合計 1〜2日で片付く。

### 2.1 `_is_playing` フラグのレースコンディション
- 場所: `main.py:184, 218, 232, 267, 318, 471, 551`
- 症状: 別スレッドからロック無しで読み書き。GIL 下でも True↔False 切り替わり直後の判定は不安定。
- 提案: `threading.Event` に置き換える。`event.set() / clear() / is_set()` はアトミックで十分。
  - 追加の効果: ブロッキング待機（`event.wait(timeout=...)`）が使えるので `_on_play_end()` の `time.sleep(0.5)` も削れる可能性あり。
- 優先度: **高** / 工数: S / リスク: 低

### 2.2 `change_language_pair()` のチャットモード時 NPE リスク
- 場所: `main.py:990-1006`
- 症状: `mode == "chat"` だと `self.translator is None`（129行）なので `self.translator.set_language_pair(...)` で AttributeError。
- 提案:
  - チャットモードでは `change_language_pair` が呼ばれないよう GUI 側で disable、または
  - `if self.translator is not None:` で防御
  - **GUI から実際に到達するかを確認してから修正範囲を決める**。
- 優先度: **高** / 工数: S / リスク: 低

### 2.3 `stop()` が常に全スレッドを閉じていない
- 場所: `main.py:871-891`（`stop()`）と `440-441`（`_streaming_asr.stop()` が `_chat_pipeline_loop` 内にだけある）
- 症状: 非 VAD 経路や 翻訳モードでは `_streaming_asr.stop()` が呼ばれない。`chat_text()` 内で立てる daemon スレッドも join されない。
- 提案: `stop()` を次の順序に統一（案）:
  1. `self._running = False`
  2. `self.capture.stop()`
  3. `self._streaming_asr` があれば `.stop()`
  4. `self._pipeline_thread.join(timeout=5.0)`（生きてれば warning ログ）
  5. `self.player.stop()` / `self.tts.cleanup()` / `self.logger.close()` / `self.live2d.stop()`
- 優先度: **高** / 工数: S / リスク: 中（再生順序を変えるので手動動作確認が必要）

### 2.4 シグナルハンドリングの脆弱性（CLI）
- 場所: `main.py:1060-1065` の `signal_handler`
- 症状: `bridge.stop()` 完了前に `sys.exit(0)` が呼ばれうる。TTS 一時ファイルや Live2D コネクションが中途半端になる。
- 提案: `sys.exit` を `signal_handler` の外（`bridge.stop()` 完了後）に移す、または flag を立ててメインループが自力で抜ける方式に変更。
- 優先度: 高 / 工数: S / リスク: 低

### 2.5 `load_model()` 失敗時の扱いが不統一
- 場所: `transcriber.py:67-76`, `transcriber_moonshine.py`, `transcriber_qwen3.py`（いずれも `load_model`）+ `main.py:308` の呼び出し側
- 症状: ロード失敗時に `self._model = None` になるが、呼び出し側は特にハンドリングしないため下流で `AttributeError: 'NoneType' object has no attribute ...` として再発する。
- 提案: 各トランスクライバーで `raise RuntimeError("ASR model load failed: …") from e`。`main.py` 側は `try/except` でユーザに「ASR起動失敗」と通知してから終了。
- 優先度: 高 / 工数: M / リスク: 低

### 2.6 壊れているテストの整理
- 場所: `test_mistranslation_fix.py:10`（`from translator_improved import Translator`。対象モジュールが存在しない）
- 提案: **削除**。もしくは `translator` に書き換えて生き返らせる。`translator.py.bak` の差分は「thank-you 系フィルタの追記」なので、このテストが守りたかった挙動は既に現行 `translator.py` に含まれていると推測できる。
- 優先度: 高 / 工数: S / リスク: 低

---

## 3. 中優先度（重複削除・性能）

### 3.1 3系統 ASR の共通インタフェース化
- 対象: `transcriber.py`, `transcriber_moonshine.py`, `transcriber_qwen3.py`, `main.py:111-122`
- 提案:
  - `transcriber_base.py` に `TranscriberProtocol`（`load_model / transcribe / set_language / change_model / SUPPORTED_LANGUAGES`）を定義
  - `create_transcriber(engine, model_size, language, device, **kwargs)` ファクトリ関数
  - `main.py` の if-elif-else 分岐（112-122行）はファクトリ1行に置換
- 副作用: Moonshine が `device` / `compute_type` を受け取っても無視する現状の仕様差も Protocol レベルで明文化できる
- 優先度: 高 / 工数: S / リスク: 低（既存シグネチャは保持可能）

### 3.2 AudioCapture の統一
- 対象: `audio_capture.py` (macOS/Linux), `audio_capture_win.py` (Windows), `main.py:22-36`
- 提案:
  - `audio_capture_base.py` に `AudioCaptureBase(ABC)` を置き、`start/stop/get_chunk/list_devices` を抽象化
  - Windows クラス名を `WindowsAudioCapture` → `AudioCapture` に揃え、`main.py` の `import as` を不要にする
  - Windows で `use_vad=True` を渡されたら現状は警告のみで RMS モード → **明示的に `NotImplementedError` を上げる**（無言で挙動が変わる方が危険）
- 優先度: 高 / 工数: M / リスク: 中（Windows での回帰確認が必要）

### 3.3 TTS 3系統の共通化
- 対象: `tts_engine.py` (Edge), `tts_voicevox.py`, `tts_coeiroink.py`
- 提案:
  - `tts_base.py` に `TTSBackend` Protocol + `TTSHTTPClient`（POST + 指数バックオフリトライ）を置く
  - VOICEVOX / CoeiroInk の重複HTTP処理（`audio_query → synthesis`）を共通化
  - エンジン選択は `main.py:131-147` の分岐を `create_tts(config)` ファクトリ化
- 優先度: 高 / 工数: M / リスク: 低

### 3.4 `_chat_pipeline_vad` と `_chat_pipeline_legacy` の統合
- 場所: `main.py:443-524` と `526-584`
- 提案: 「発話区間検出」を strategy として切り出す:
  ```
  UtteranceDetector (Protocol)
    ├── VadUtteranceDetector
    └── SilenceUtteranceDetector
  ```
  後段の「ASR→AI送信→TTS」は共通ループ。
- 優先度: 高 / 工数: M / リスク: 中

### 3.5 `_chat_ai_streaming` と `_chat_ai_batch` の共通後処理
- 場所: `main.py:600-669`, `730-774`, `chat_text` の中の再実装 `788-822`
- 提案: `_finalize_ai_response(text, user_text, t_start, is_streaming=False)` を抽出し、「ログ記録 / TTS 合成 / dispatch / レイテンシ記録」を一か所に集約。chat_text() 内のストリーミング処理も `_stream_with_tts()` に再利用させる。
- 優先度: 高 / 工数: S / リスク: 低

### 3.6 TTS ダブルバッファリングの非同期化
- 場所: `main.py:671-679`（`_synthesize_and_enqueue` が同期呼び出し）
- 症状: 文 N を喋っている間に 文 N+1 を合成する、という理想が半分しか効いていない。合成がブロックするため合成自体が直列化している。
- 提案: 合成を `ThreadPoolExecutor(max_workers=2)` に投げる。キュー順序は future 保持で担保。
- 優先度: 中 / 工数: M / リスク: 中（順序保証のテストが要る）

### 3.7 マジックナンバーを `config/constants.py` へ
- 場所: `main.py:225, 485, 534, 929, 1.0 timeout` 等
- 提案: `AUTO_LANG_MIN_PROB`, `AUTO_LANG_SWITCH_COUNT`, `SILENCE_THRESHOLD`, `STREAMING_ASR_WAIT`, `AUDIO_CAPTURE_TIMEOUT`, `PIPELINE_THREAD_JOIN_TIMEOUT` などを集約。
- 優先度: 中 / 工数: S / リスク: 低

### 3.8 `_auto_lang_history` の遅延初期化を廃止
- 場所: `main.py:949` 付近 `if not hasattr(self, "_auto_lang_history"):`
- 提案: `__init__` で `self._auto_lang_history = []`。判定は `threading.Lock` で包む。
- 優先度: 中 / 工数: S / リスク: 低

### 3.9 AudioCapture のバッファ管理（メモリコピー削減）
- 場所: `audio_capture.py:137-156` のバッファ蓄積 → `np.concatenate` 後にキュー投入
- 提案: 事前割り当て配列に直接書き込むか、`collections.deque` / リングバッファに置き換え
- 効果: 連続稼働時の CPU -5〜10% 程度（VAD モードでは特に効きやすい）
- 優先度: 中 / 工数: M / リスク: 中
- 備考: プロファイリングで実測してから着手する方が安全。

---

## 4. 低優先度（構造・体裁）

### 4.1 `main.py` のモジュール分割
- 提案構成（案）:
  ```
  voice_bridge/
    core.py          # VoiceBridge クラス（調整役だけに痩せる）
    pipeline/
      translate.py   # _translate_pipeline_loop 系
      chat.py        # _chat_pipeline_* 系（3.4 と合流）
    audio/           # audio_capture* の共通化（3.2 と合流）
    asr/             # transcriber 系（3.1 と合流）
    tts/             # tts 系（3.3 と合流）
    runner/
      cli.py         # run_cli / signal
      gui_adapter.py # run_gui + create_bridge
    config/
      constants.py   # 3.7
      voices.py      # ハードコードされた speaker_id 等
  ```
- 優先度: 低 / 工数: L / リスク: 中〜高（段階 PR 化が必須）
- **実施順の注意**: 3.1〜3.5 を先に入れて重複が減ってから移動するほうが diff が見やすい。

### 4.2 `gui.py` の `build()` と コールバック dataclass 化
- 場所: `gui.py:39, 72, 342-447, 485`
- 提案:
  - `GUICallbacks` dataclass（11引数 → 1引数）
  - `GUIConfig` dataclass（11引数 → 1引数）
  - `build()` 269行を `_build_header / _build_settings / _build_buttons / _build_monitor / _build_text / _build_chat / _build_style` に分解
  - `_on_*_changed` ハンドラはファクトリで共通化
- 優先度: 中 / 工数: M / リスク: 低

### 4.3 `translation_logger.py` → 標準 `logging` 移行
- 場所: `translation_logger.py` 全体
- 提案: `TranslationLogger` は 71行のラッパ。標準 `logging.FileHandler` + フォーマッタで置換可能。
  - 併せて、main.py 内の `print("[Pipeline] ...")` などの混在 prefix を `logging` に統一するのは別PR。
- 優先度: 低 / 工数: S / リスク: 低

### 4.4 `latency_tracker.py` の簡潔化
- 場所: `latency_tracker.py` 全体（3クラス）
- 提案: `StageStats + CycleRecord + LatencyTracker` → `LatencyRecord + LatencyTracker` の2本立てに縮小（~140行 → ~60行）。シリアライズが必要な箇所は無さそう。
- 優先度: 中 / 工数: S / リスク: 低

### 4.5 `analyze_and_update_filters.py` の整理
- 場所: ファイル全体 + `filter_suggestions.json`
- 症状: `--apply` 実装が未完で、`filter_suggestions.json` は空のまま。
- 提案:
  - 責務を分離: `analyze_filters.py`（分析→JSON 出力）と `apply_filters.py`（JSON→translator.py 更新）
  - `apply_filters.py` は行マッチではなく AST ベース（行マッチだとコメント中のパターンを誤爆する）
  - ドライラン → `--apply` の2段階UXに
- 優先度: 低 / 工数: M / リスク: 中（translator.py を書き換える機能なので危険）

### 4.6 `live2d_bridge.py` の `infer_emotion` 改善
- 場所: `live2d_bridge.py:342-349, 352-371`
- 現状: キーワード辞書による簡易推論
- 提案:
  - `EmotionAnalyzer` として切り出し、`use_llm=True` のときだけ `ai_chat` を再利用して推論
  - キーワード辞書は `config/voices.py` または YAML へ
- 優先度: 低 / 工数: M / リスク: 低

### 4.7 `player.py` のクリーンアップ
- 場所: `player.py`（`_init_mixer`, `stop`, `_play_loop`）
- 提案:
  - `stop()` で `pygame.mixer.quit()` を呼ぶ（再起動で hang する可能性を減らす）
  - 再生エラー時のコールバック呼び出しを `finally` で保証
  - `frequency=24000` のハードコードは TTS 種別から動的に決める（Edge TTS の mp3 は実際は 24kHz だが、将来に備えて config 化）
- 優先度: 中 / 工数: S / リスク: 低

### 4.8 requirements / テスト整備
- 提案:
  - `requirements.txt` にバージョン下限（`>=`）を追記。完全ピンは `requirements-lock.txt` 別持ち
  - `psutil`（`benchmark_asr.py` で使用）を明記
  - `torch` は ASR エンジン次第なので `requirements-asr-whisper.txt` など optional 化を検討
  - `test_*.py` は `pytest` 化（`if __name__ == "__main__"` を外す）
  - `test_mistranslation_fix.py` の対応は 2.6 参照
  - `logs/` のローテーション（30日超を自動削除）を `scripts/cleanup_logs.py` として用意
- 優先度: 低 / 工数: S〜M / リスク: 低

---

## 5. 実施ロードマップ（推奨順）

```
Week 1  ───── 高優先度バグ修正（2章）
              2.1 _is_playing を Event 化
              2.3 stop() 順序整理
              2.4 CLI シグナル
              2.5 load_model 例外統一
              2.6 壊れたテスト除去
              2.2 change_language_pair NPE ガード（GUI 経路確認後）

Week 2  ───── 共通インタフェース化（3.1〜3.3）
              ASR Protocol + factory
              AudioCapture 抽象基底
              TTS Protocol + HTTP client 共通化

Week 3  ───── パイプライン重複削除（3.4〜3.5）
              UtteranceDetector 抽出
              _finalize_ai_response 抽出

Week 4+ ───── main.py 分割 (4.1) / gui.py リファクタ (4.2) / 性能最適化 (3.6, 3.9)
              ここからは独立PR単位で
```

各フェーズ終了時に以下を推奨:
- 手動動作確認（翻訳モード / チャットモード VAD / 非VAD / Live2D接続あり・なし）
- `pytest` スモークテストの追加
- Live2D 絡みはモック WebSocket で疎通確認

---

## 6. 手を付けない方がよいもの（今回）

- `live2d-ui/`（Electron + Vue + pixi-live2d-display）: 独立したフロント。触るなら別タスク。
- `chrome-extension/`: Python 側と疎結合。今回の最適化対象外。
- ASR モデル自体の変更（Whisper→他）: これは「最適化」ではなく仕様変更。

---

## 7. 検討したが採用しなかった案

- **`gui.py` を PyQt / PySide に移植**: 単純に規模が 10倍になる。Tkinter のままで十分。
- **完全 async/await 化**: 現状は threading + queue で素直に動いている。async に寄せると pygame / sounddevice 周りで別の罠を踏む。3.6 の合成スレッドプール化程度で足りる。
- **logging を最初の PR で全面導入**: 変更量が大きすぎるので 4.3 として後回し。先にバグ修正と構造分割を優先。

---

## 8. 次のアクション（確認お願いします）

1. 本書のフェーズ分けで OK か、それとも別の優先順位で進めたいか
2. 実装時のブランチ戦略（`optimization/week1-bugs` のように週単位 PR でよいか）
3. 実装に入る前に「まずは 2章（高優先度）だけやる」など、刻んで進めたいか

以上を決めていただければ、具体的なパッチ作成に着手できます。
