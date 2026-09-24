"""
DeepSeek / Ollama client.

Two models are configured:

  - DEEPSEEK_CHAT_MODEL  → general chat (default: qwen2.5:3b)
  - DEEPSEEK_CODE_MODEL  → code assistance (default: deepseek-coder:1.3b)

Both run locally via Ollama on an OpenAI-compatible endpoint.
"""
import json
import os
import urllib.error
import urllib.request


class DeepSeekService:
    """Client for a local OpenAI-compatible model endpoint (Ollama)."""

    def __init__(self):
        self.base_url = os.getenv(
            "DEEPSEEK_BASE_URL",
            "http://127.0.0.1:11434/v1",
        ).rstrip("/")

        self.chat_model = os.getenv(
            "DEEPSEEK_CHAT_MODEL",
            os.getenv("DEEPSEEK_MODEL", "qwen2.5:3b"),
        )

        self.code_model = os.getenv(
            "DEEPSEEK_CODE_MODEL",
            "deepseek-coder:1.3b",
        )

        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "180"))

    def model_for(self, mode: str) -> str:
        if mode == "code":
            return self.code_model
        return self.chat_model

    def chat(self, messages, model=None, mode="chat"):
        chosen = model or self.model_for(mode)

        payload = {
            "model": chosen,
            "messages": messages,
            "stream": False,
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"AI endpoint HTTP {exc.code}: {body}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Local AI API unavailable at "
                f"{self.base_url}: {exc.reason}"
            ) from exc


deepseek_service = DeepSeekService()