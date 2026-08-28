import json
import os
import urllib.error
import urllib.request


class DeepSeekService:
    """Client for the local OpenAI-compatible DeepSeek bridge."""

    def __init__(self):
        self.base_url = os.getenv(
            "DEEPSEEK_BASE_URL",
            "http://127.0.0.1:8001/v1",
        ).rstrip("/")

        self.model = os.getenv(
            "DEEPSEEK_MODEL",
            "deepseek-chat",
        )

        self.timeout = int(
            os.getenv("DEEPSEEK_TIMEOUT", "120")
        )

    def chat(self, messages, model=None):
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"DeepSeek HTTP {exc.code}: {body}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "DeepSeek local API unavailable at "
                f"{self.base_url}: {exc.reason}"
            ) from exc


deepseek_service = DeepSeekService()
