from __future__ import annotations

import json
import urllib.request

from automation_hub.logging_utils import get_logger


class OllamaClient:
    def __init__(self, url: str, model: str, timeout_sec: int) -> None:
        self.url = url
        self.model = model
        self.timeout_sec = timeout_sec
        self.logger = get_logger("automation_hub.ollama")

    def summarize(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response") or "").strip()
