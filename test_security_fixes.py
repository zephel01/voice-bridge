"""
セキュリティレビュー指摘の修正パッチに対する回帰テスト

対象:
  - ai_chat.py: load_dotenv の引用符処理・インラインコメント除去
  - transcriber_qwen3.py: モデル名ホワイトリスト検証
  - live2d_bridge.py: host警告分岐
  - tts_voicevox.py / tts_coeiroink.py: host スキーム検証

注意:
  - 実際のモデルロード・実通信・websocketsの実サーバ起動は一切行わない。
  - 重い依存（torch, qwen_asr, websockets）は環境になくても動くよう、
    必要に応じて sys.modules に MagicMock を注入してからモジュールを import する。
"""

import ast
import importlib
import logging
import os
import sys
import tempfile
import types
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# ai_chat.py: load_dotenv
# ---------------------------------------------------------------------------

class TestAiChatLoadDotenv:
    """簡易 load_dotenv の引用符処理・インラインコメント除去のテスト"""

    def _import_ai_chat_fresh(self):
        """requests をモックして ai_chat をインポート（実通信は行わない）"""
        if "requests" not in sys.modules:
            sys.modules["requests"] = MagicMock()
        # 既にロード済みならリロードして .env の再ロードを避ける
        sys.modules.pop("ai_chat", None)
        import ai_chat  # noqa: E402
        importlib.reload(ai_chat)
        return ai_chat

    def _write_env_and_load(self, tmp_path, content):
        ai_chat = self._import_ai_chat_fresh()
        env_file = tmp_path / ".env"
        env_file.write_text(content, encoding="utf-8")

        # os.environ を汚さないよう、対象キーを退避
        keys_to_clear = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            keys_to_clear.append(key)
        saved = {k: os.environ.pop(k, None) for k in keys_to_clear}

        try:
            ai_chat.load_dotenv(str(env_file))
            result = {k: os.environ.get(k) for k in keys_to_clear}
        finally:
            for k in keys_to_clear:
                os.environ.pop(k, None)
                if saved[k] is not None:
                    os.environ[k] = saved[k]
        return result

    def test_double_quoted_value_strips_quotes(self, tmp_path):
        result = self._write_env_and_load(tmp_path, 'FOO="bar baz"\n')
        assert result["FOO"] == "bar baz"

    def test_single_quoted_value_strips_quotes(self, tmp_path):
        result = self._write_env_and_load(tmp_path, "FOO='bar baz'\n")
        assert result["FOO"] == "bar baz"

    def test_mismatched_quotes_not_stripped(self, tmp_path):
        # 先頭と末尾が異なる引用符 → 剥がさない
        result = self._write_env_and_load(tmp_path, "FOO='bar baz\"\n")
        assert result["FOO"] == "'bar baz\""

    def test_unquoted_value_with_hash_no_space_not_treated_as_comment(self, tmp_path):
        # 引用符なし、# の前にスペースが無い場合はコメット除去しない
        result = self._write_env_and_load(tmp_path, "FOO=bar#baz\n")
        assert result["FOO"] == "bar#baz"

    def test_unquoted_value_inline_comment_stripped(self, tmp_path):
        # 引用符なし、" #" 以降はインラインコメントとして除去
        result = self._write_env_and_load(tmp_path, "FOO=bar #this is a comment\n")
        assert result["FOO"] == "bar"

    def test_quoted_value_hash_not_stripped(self, tmp_path):
        # 引用符で囲まれた値の中の # は除去されない
        result = self._write_env_and_load(tmp_path, 'FOO="bar #not a comment"\n')
        assert result["FOO"] == "bar #not a comment"

    def test_comment_line_skipped(self, tmp_path):
        result = self._write_env_and_load(tmp_path, "# FOO=bar\nBAZ=qux\n")
        assert result.get("BAZ") == "qux"
        assert "FOO" not in result

    def test_existing_env_not_overwritten(self, tmp_path):
        ai_chat = self._import_ai_chat_fresh()
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_KEY=fromfile\n", encoding="utf-8")
        os.environ["EXISTING_KEY"] = "original"
        try:
            ai_chat.load_dotenv(str(env_file))
            assert os.environ["EXISTING_KEY"] == "original"
        finally:
            os.environ.pop("EXISTING_KEY", None)

    def test_line_without_equals_skipped(self, tmp_path):
        result = self._write_env_and_load(tmp_path, "NOEQUALSIGN\nBAZ=1\n")
        assert result.get("BAZ") == "1"

    def test_blank_lines_skipped(self, tmp_path):
        result = self._write_env_and_load(tmp_path, "\n\nBAZ=1\n\n")
        assert result.get("BAZ") == "1"


# ---------------------------------------------------------------------------
# transcriber_qwen3.py: モデル名ホワイトリスト検証
# ---------------------------------------------------------------------------

class TestTranscriberQwen3Whitelist:
    """モデル名ホワイトリスト検証のテスト（実際のモデルロードは行わない）"""

    @pytest.fixture(autouse=True)
    def _mock_heavy_deps(self):
        """qwen_asr, torch をモックして transcriber_qwen3 をインポート可能にする"""
        mock_qwen_asr = types.ModuleType("qwen_asr")
        mock_qwen_asr.Qwen3ASRModel = MagicMock()
        sys.modules["qwen_asr"] = mock_qwen_asr

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.bfloat16 = "bfloat16"
        mock_torch.cuda.is_available.return_value = False
        sys.modules["torch"] = mock_torch

        sys.modules.pop("transcriber_qwen3", None)
        import transcriber_qwen3  # noqa: E402
        importlib.reload(transcriber_qwen3)
        self.module = transcriber_qwen3
        yield
        sys.modules.pop("transcriber_qwen3", None)
        sys.modules.pop("qwen_asr", None)
        sys.modules.pop("torch", None)

    def test_valid_model_name_via_init(self):
        t = self.module.Transcriber(model_size="small")
        assert t._model_name in set(self.module.Transcriber.MODEL_SIZE_MAP.values())

    def test_validate_model_name_rejects_disallowed(self):
        t = self.module.Transcriber(model_size="small")
        with pytest.raises(ValueError):
            t._validate_model_name("evil/malicious-model")

    def test_validate_model_name_accepts_allowed(self):
        t = self.module.Transcriber(model_size="small")
        allowed = next(iter(set(self.module.Transcriber.MODEL_SIZE_MAP.values())))
        assert t._validate_model_name(allowed) == allowed

    def test_load_model_rejects_tampered_model_name(self):
        """load_model() 内でも from_pretrained 呼び出し前にホワイトリスト検証が行われる"""
        t = self.module.Transcriber(model_size="small")
        # 内部状態を不正な値に書き換えてロードを試みる（防御が効くか確認）
        t._model_name = "attacker-controlled/model"
        with pytest.raises(ValueError):
            t.load_model()
        # from_pretrained が呼ばれていないことを確認
        self.module.Qwen3ASRModel.from_pretrained.assert_not_called()

    def test_change_model_calls_validation(self):
        """change_model() 経由でもホワイトリスト検証が呼ばれることを確認"""
        t = self.module.Transcriber(model_size="small")

        # インスタンスメソッドの呼び出し回数を数える簡易スパイ
        call_count = {"n": 0}
        original = t._validate_model_name

        def spy_validate(name):
            call_count["n"] += 1
            return original(name)

        t._validate_model_name = spy_validate
        t.change_model("medium")
        assert call_count["n"] >= 1

    def test_change_model_with_valid_size_succeeds(self):
        t = self.module.Transcriber(model_size="small")
        t.change_model("medium")
        assert t._model_name == self.module.Transcriber.MODEL_SIZE_MAP["medium"]


# ---------------------------------------------------------------------------
# live2d_bridge.py: host警告分岐
# ---------------------------------------------------------------------------

class TestLive2DBridgeHostWarning:
    """host が非ローカルの場合に logger.warning が呼ばれることを確認"""

    @pytest.fixture(autouse=True)
    def _mock_websockets(self):
        mock_websockets = MagicMock()
        mock_websockets_server = MagicMock()
        mock_websockets_server.WebSocketServerProtocol = MagicMock
        sys.modules["websockets"] = mock_websockets
        sys.modules["websockets.server"] = mock_websockets_server

        sys.modules.pop("live2d_bridge", None)
        import live2d_bridge  # noqa: E402
        importlib.reload(live2d_bridge)
        self.module = live2d_bridge
        yield
        sys.modules.pop("live2d_bridge", None)
        sys.modules.pop("websockets", None)
        sys.modules.pop("websockets.server", None)

    def _make_bridge_without_real_thread(self, host):
        bridge = self.module.Live2DBridge(host=host, port=8765)
        # 実際のスレッド起動を避けるため _run_server をダミーに差し替え、
        # サーバ起動待ちを即座に成功させる
        bridge._run_server = MagicMock()
        bridge._server_ready.set()
        return bridge

    def test_warning_logged_for_non_local_host(self, caplog):
        bridge = self._make_bridge_without_real_thread("0.0.0.0")
        with caplog.at_level(logging.WARNING, logger="voice_bridge.live2d"):
            bridge.start()
        try:
            assert any(
                "LAN" in record.message or "露出" in record.message
                for record in caplog.records
            )
        finally:
            bridge._stop_flag.set()
            if bridge._server_thread:
                bridge._server_thread.join(timeout=2.0)

    def test_no_warning_for_localhost(self, caplog):
        bridge = self._make_bridge_without_real_thread("127.0.0.1")
        with caplog.at_level(logging.WARNING, logger="voice_bridge.live2d"):
            bridge.start()
        try:
            assert not any(
                "LAN" in record.message or "露出" in record.message
                for record in caplog.records
            )
        finally:
            bridge._stop_flag.set()
            if bridge._server_thread:
                bridge._server_thread.join(timeout=2.0)

    def test_no_warning_for_literal_localhost_string(self, caplog):
        bridge = self._make_bridge_without_real_thread("localhost")
        with caplog.at_level(logging.WARNING, logger="voice_bridge.live2d"):
            bridge.start()
        try:
            assert not any(
                "LAN" in record.message or "露出" in record.message
                for record in caplog.records
            )
        finally:
            bridge._stop_flag.set()
            if bridge._server_thread:
                bridge._server_thread.join(timeout=2.0)

    def test_max_size_reduced_to_1mb(self):
        import inspect
        source = inspect.getsource(self.module.Live2DBridge._run_server)
        assert "1 * 1024 * 1024" in source
        assert "8 * 1024 * 1024" not in source


# ---------------------------------------------------------------------------
# tts_voicevox.py / tts_coeiroink.py: host スキーム検証
# ---------------------------------------------------------------------------

class TestTtsHostSchemeValidation:
    """host の URL スキーム検証（http/https 以外は ValueError）。実通信は行わない。"""

    @pytest.fixture(autouse=True)
    def _mock_requests(self):
        if "requests" not in sys.modules or not isinstance(sys.modules["requests"], MagicMock):
            sys.modules["requests"] = MagicMock()
        sys.modules.pop("tts_voicevox", None)
        sys.modules.pop("tts_coeiroink", None)
        import tts_voicevox  # noqa: E402
        import tts_coeiroink  # noqa: E402
        importlib.reload(tts_voicevox)
        importlib.reload(tts_coeiroink)
        self.tts_voicevox = tts_voicevox
        self.tts_coeiroink = tts_coeiroink
        yield
        sys.modules.pop("tts_voicevox", None)
        sys.modules.pop("tts_coeiroink", None)

    @pytest.mark.parametrize("bad_host", [
        "ftp://localhost:50021",
        "file:///etc/passwd",
        "ws://localhost:50021",
        "not-a-url",
    ])
    def test_voicevox_rejects_non_http_scheme(self, bad_host):
        with pytest.raises(ValueError):
            self.tts_voicevox.VoicevoxTTS(host=bad_host)

    def test_voicevox_accepts_http(self):
        tts = self.tts_voicevox.VoicevoxTTS(host="http://localhost:50021")
        assert tts.host == "http://localhost:50021"
        tts.cleanup()

    def test_voicevox_accepts_https(self):
        tts = self.tts_voicevox.VoicevoxTTS(host="https://example.com:50021")
        assert tts.host == "https://example.com:50021"
        tts.cleanup()

    def test_voicevox_uses_session(self):
        tts = self.tts_voicevox.VoicevoxTTS(host="http://localhost:50021")
        assert hasattr(tts, "session")
        tts.cleanup()

    @pytest.mark.parametrize("bad_host", [
        "ftp://localhost:50031",
        "file:///etc/passwd",
        "ws://localhost:50031",
        "not-a-url",
    ])
    def test_coeiroink_rejects_non_http_scheme(self, bad_host):
        with pytest.raises(ValueError):
            self.tts_coeiroink.CoeiroinkTTS(host=bad_host)

    def test_coeiroink_accepts_http(self):
        tts = self.tts_coeiroink.CoeiroinkTTS(host="http://localhost:50031")
        assert tts.host == "http://localhost:50031"
        tts.cleanup()

    def test_coeiroink_uses_session(self):
        tts = self.tts_coeiroink.CoeiroinkTTS(host="http://localhost:50031")
        assert hasattr(tts, "session")
        tts.cleanup()


# ---------------------------------------------------------------------------
# analyze_and_update_filters.py: 構文検証・冪等性・バックアップ・ロールバック
# ---------------------------------------------------------------------------

class TestAnalyzeAndUpdateFiltersSyntax:
    def test_module_is_valid_python(self):
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "analyze_and_update_filters.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)  # SyntaxError なら失敗

    def test_idempotency_skips_existing_pattern(self, tmp_path):
        """既にファイルに含まれるパターンは重複追加されないことを確認"""
        sys.modules.pop("analyze_and_update_filters", None)
        import analyze_and_update_filters as m
        importlib.reload(m)

        translator_content = (
            "WHISPER_MISTRANSLATIONS = {\n"
            '        r"thank\\s+you": True,\n'
            "}\n\n"
            "MISTRANSLATION_PATTERNS = {\n"
            "}\n"
        )
        translator_file = tmp_path / "translator.py"
        translator_file.write_text(translator_content, encoding="utf-8")

        updater = m.FilterUpdater(translator_path=str(translator_file))
        # 既存パターンと全く同じものを再度追加しようとする → スキップされるはず
        updater._apply_filters_to_file(
            english_patterns=['r"thank\\s+you"'],
            japanese_patterns=[],
        )

        result = translator_file.read_text(encoding="utf-8")
        # 重複して2回追加されていないことを確認
        assert result.count('r"thank\\s+you"') == 1

    def test_backup_file_created(self, tmp_path):
        sys.modules.pop("analyze_and_update_filters", None)
        import analyze_and_update_filters as m
        importlib.reload(m)

        translator_content = (
            "WHISPER_MISTRANSLATIONS = {\n"
            "}\n\n"
            "MISTRANSLATION_PATTERNS = {\n"
            "}\n"
        )
        translator_file = tmp_path / "translator.py"
        translator_file.write_text(translator_content, encoding="utf-8")

        updater = m.FilterUpdater(translator_path=str(translator_file))
        updater._apply_filters_to_file(
            english_patterns=['r"new\\s+pattern"'],
            japanese_patterns=[],
        )

        backup_file = tmp_path / "translator.py.bak"
        assert backup_file.exists()

    def test_rollback_on_syntax_error(self, tmp_path, monkeypatch):
        """ast.parse が失敗した場合にバックアップからロールバックされることを確認"""
        sys.modules.pop("analyze_and_update_filters", None)
        import analyze_and_update_filters as m
        importlib.reload(m)

        translator_content = (
            "WHISPER_MISTRANSLATIONS = {\n"
            "}\n\n"
            "MISTRANSLATION_PATTERNS = {\n"
            "}\n"
        )
        translator_file = tmp_path / "translator.py"
        translator_file.write_text(translator_content, encoding="utf-8")

        updater = m.FilterUpdater(translator_path=str(translator_file))

        original_parse = m.ast.parse

        def fake_parse(*args, **kwargs):
            raise SyntaxError("forced failure for test")

        monkeypatch.setattr(m.ast, "parse", fake_parse)
        try:
            updater._apply_filters_to_file(
                english_patterns=['r"broken\\s+pattern"'],
                japanese_patterns=[],
            )
        finally:
            monkeypatch.setattr(m.ast, "parse", original_parse)

        result = translator_file.read_text(encoding="utf-8")
        # ロールバックされ、元の内容に戻っていることを確認
        assert result == translator_content


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
