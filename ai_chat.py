"""
AI チャットモジュール
OpenAI 互換 API を使って会話し、応答テキストを返す

対応:
  - OpenAI (GPT-4o 等)
  - Anthropic Claude (OpenAI 互換ラッパー経由)
  - ローカル LLM (Ollama, LM Studio 等)

設定例:
  # OpenAI
  AiChat(api_key="sk-...", model="gpt-4o")

  # Ollama (ローカル)
  AiChat(base_url="http://localhost:11434/v1", api_key="ollama", model="llama3")

  # LM Studio (ローカル)
  AiChat(base_url="http://localhost:1234/v1", api_key="lm-studio", model="local-model")
"""

import json
import os
import threading
from typing import Optional

try:
    import requests
except ImportError:
    raise ImportError("requests が必要です: pip install requests")


def load_dotenv(env_path: str = ".env"):
    """簡易 .env ローダー（python-dotenv 不要）"""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # 引用符除去: 先頭と末尾が同じ引用符文字で対になっている場合のみ剥がす
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ("'", '"')
            ):
                value = value[1:-1]
            else:
                # 引用符で囲まれていない値のみ、インラインコメント（半角スペース+#以降）を除去
                comment_idx = value.find(" #")
                if comment_idx != -1:
                    value = value[:comment_idx].rstrip()

            if key and key not in os.environ:
                os.environ[key] = value


# .env を自動ロード
load_dotenv()


class AiChat:
    """OpenAI 互換 API でチャット会話を管理するクラス"""

    DEFAULT_SYSTEM_PROMPT = (
        "あなたは親切なアシスタントです。"
        "ユーザーの質問に簡潔に日本語で回答してください。"
        "回答は音声で読み上げられるため、箇条書きや記号は避け、"
        "自然な話し言葉で2〜3文程度にまとめてください。"
    )

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = None,
        model: str = "gpt-4o-mini",
        system_prompt: str = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 30.0,
        response_language: str = "ja",
    ):
        """
        Args:
            base_url: API ベース URL（末尾の /v1 まで）
            api_key: API キー（環境変数 OPENAI_API_KEY からも取得可）
            model: モデル名
            system_prompt: システムプロンプト
            max_tokens: 最大トークン数（音声読み上げ用に短めがおすすめ）
            temperature: 生成の多様性（0.0〜2.0）
            timeout: API タイムアウト（秒）
            response_language: 応答言語 (ja/en/zh 等)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = (
            api_key
            or os.environ.get("AI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.response_language = response_language

        # システムプロンプト
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._build_system_prompt(response_language)

        # 会話履歴
        self._history = []
        self._lock = threading.Lock()

        print(f"[AiChat] base_url={self.base_url}")
        print(f"[AiChat] model={self.model}")
        print(f"[AiChat] response_language={self.response_language}")

    @staticmethod
    def fetch_models(base_url: str = None, api_key: str = None, timeout: float = 3.0) -> list[str]:
        """ローカル LLM サーバーから利用可能なモデル一覧を取得

        OpenAI 互換 /v1/models エンドポイントを使用。
        取得失敗時は空リストを返す。
        """
        if base_url is None:
            base_url = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
        base_url = base_url.rstrip("/")
        if api_key is None:
            api_key = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

        url = f"{base_url}/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])]
            models.sort()
            return models
        except Exception as e:
            print(f"[AiChat] モデル一覧取得失敗: {e}")
            return []

    def _build_system_prompt(self, lang: str) -> str:
        """応答言語に応じたシステムプロンプトを生成"""
        lang_instructions = {
            "ja": (
                "あなたは親切なアシスタントです。"
                "ユーザーの質問に簡潔に日本語で回答してください。"
                "回答は音声で読み上げられるため、箇条書きや記号は避け、"
                "自然な話し言葉で2〜3文程度にまとめてください。"
            ),
            "en": (
                "You are a helpful assistant. "
                "Answer the user's questions concisely in English. "
                "Keep responses to 2-3 sentences in natural spoken language, "
                "as they will be read aloud by text-to-speech."
            ),
        }
        return lang_instructions.get(lang, lang_instructions["ja"])

    def chat(self, user_message: str) -> str:
        """
        ユーザーメッセージを送信して AI の応答を返す

        Args:
            user_message: ユーザーの入力テキスト

        Returns:
            AI の応答テキスト
        """
        if not user_message.strip():
            return ""

        with self._lock:
            # 会話履歴に追加
            self._history.append({"role": "user", "content": user_message})

            # メッセージ構築
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self._history,
            ]

            # API 呼び出し
            try:
                response = self._call_api(messages)
            except Exception as e:
                print(f"[AiChat] API エラー: {e}")
                # エラー時は履歴から最後のメッセージを削除
                self._history.pop()
                return f"エラーが発生しました: {e}"

            # 応答を履歴に追加
            self._history.append({"role": "assistant", "content": response})

            # 履歴が長くなりすぎたら古いものを削除（直近20往復を保持）
            if len(self._history) > 40:
                self._history = self._history[-40:]

            return response

    def chat_stream(self, user_message: str):
        """
        ストリーミングで AI の応答を返すジェネレーター

        LLM からトークン単位で応答を受信し、逐次 yield する。
        呼び出し側で文単位に区切って TTS に渡すことで、
        最初の音声が出るまでの待ち時間を大幅に短縮できる。

        Args:
            user_message: ユーザーの入力テキスト

        Yields:
            str: 応答テキストの断片（delta）
        """
        if not user_message.strip():
            return

        with self._lock:
            self._history.append({"role": "user", "content": user_message})

            messages = [
                {"role": "system", "content": self.system_prompt},
                *self._history,
            ]

            full_response = ""
            try:
                for delta in self._call_api_stream(messages):
                    full_response += delta
                    yield delta
            except Exception as e:
                print(f"[AiChat] ストリーミングエラー: {e}")
                self._history.pop()
                yield f"エラーが発生しました: {e}"
                return

            # 応答を履歴に追加
            if full_response.strip():
                self._history.append({"role": "assistant", "content": full_response})
            else:
                # 空応答 → user メッセージも取り消す
                self._history.pop()

            if len(self._history) > 40:
                self._history = self._history[-40:]

    def _call_api(self, messages: list) -> str:
        """OpenAI 互換 API を呼び出す"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        print(f"[AiChat] リクエスト送信中... ({self.model})")
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        data = resp.json()

        # デバッグ: レスポンス構造を表示
        print(f"[AiChat] ステータス: {resp.status_code}")
        if "choices" not in data:
            print(f"[AiChat] 想定外のレスポンス: {json.dumps(data, ensure_ascii=False)[:500]}")
            # Z.AI 等で output / result キーの場合
            for key in ("output", "result", "response", "data"):
                if key in data:
                    print(f"[AiChat] '{key}' キーを検出")
                    val = data[key]
                    if isinstance(val, str):
                        return val.strip()
                    if isinstance(val, dict) and "content" in val:
                        return val["content"].strip()
            return ""

        choice = data["choices"][0]
        # finish_reason の確認
        finish_reason = choice.get("finish_reason", "unknown")
        message = choice.get("message") or choice.get("delta") or {}
        content = (message.get("content") or "").strip()

        # reasoning_content は内部推論なのでログのみ（応答としては使わない）
        if message.get("reasoning_content"):
            print(f"[AiChat] reasoning_content あり ({len(message['reasoning_content'])}文字, ログのみ)")

        print(f"[AiChat] 応答受信 ({len(content)}文字, finish_reason={finish_reason})")
        if not content and finish_reason == "length":
            print(f"[AiChat] ⚠ トークン上限で応答が切れています。max_tokens を増やしてください")
        if not content:
            print(f"[AiChat] 空応答の詳細: {json.dumps(choice, ensure_ascii=False)[:500]}")
        return content

    def _call_api_stream(self, messages: list):
        """OpenAI 互換 API をストリーミングで呼び出す（SSE）"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        print(f"[AiChat] ストリーミング開始... ({self.model})")
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
            stream=True,
        )
        resp.raise_for_status()

        # Ollama 等は Content-Type に charset を返さないことがあるため
        # 明示的に UTF-8 を指定（日本語の文字化け防止）
        resp.encoding = "utf-8"

        token_count = 0
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data_str = line[6:]  # "data: " を除去
            if data_str.strip() == "[DONE]":
                break

            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    token_count += 1
                    yield content
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

        print(f"[AiChat] ストリーミング完了 ({token_count} tokens)")

    def clear_history(self):
        """会話履歴をクリア"""
        with self._lock:
            self._history.clear()
            print("[AiChat] 会話履歴をクリアしました")

    def set_system_prompt(self, prompt: str):
        """システムプロンプトを変更"""
        self.system_prompt = prompt
        print(f"[AiChat] システムプロンプトを変更しました")

    def set_model(self, model: str):
        """モデルを変更"""
        self.model = model
        print(f"[AiChat] モデルを {model} に変更しました")


if __name__ == "__main__":
    # テスト: API キーが設定されていれば動作確認
    import sys

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY が設定されていません")
        print("テスト例:")
        print("  export OPENAI_API_KEY=sk-...")
        print("  python ai_chat.py")
        sys.exit(1)

    chat = AiChat(api_key=api_key)
    print("=== AI Chat テスト（quit で終了）===")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("quit", "exit", "q"):
            break
        response = chat.chat(user_input)
        print(f"AI: {response}")
