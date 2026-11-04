"""Fireworks AI serverless client with reasoning token handling and token accounting."""

import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from simuguard.config import FIREWORKS_API_KEY, DEFAULT_FLASH_MODEL


# Live rates per 1M tokens on Fireworks serverless (USD)
MODEL_RATES = {
    "accounts/fireworks/models/deepseek-v4p1-flash": {"prompt": 0.30, "completion": 1.20},
    "accounts/fireworks/models/deepseek-v4p1-flash-1017": {"prompt": 0.30, "completion": 1.20},
    "accounts/fireworks/models/glm-5p3-flash": {"prompt": 0.20, "completion": 0.80},
    "accounts/fireworks/models/glm-5p3": {"prompt": 0.90, "completion": 1.80},
    "accounts/fireworks/models/gpt-oss-120b": {"prompt": 0.90, "completion": 0.90},
    "accounts/fireworks/models/kimi-k3": {"prompt": 1.00, "completion": 2.00},
    "accounts/fireworks/models/minimax-m3p1-flash": {"prompt": 0.20, "completion": 0.80},
    "default": {"prompt": 0.90, "completion": 0.90},
}


class FireworksClient:
    """Client for Fireworks AI Serverless Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.fireworks.ai/inference/v1",
        default_model: str = DEFAULT_FLASH_MODEL,
        timeout: int = 60,
    ):
        self.api_key = api_key or FIREWORKS_API_KEY or os.environ.get("FIREWORKS_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Fireworks API key not found. Please set FIREWORKS_API_KEY in .env or pass it explicitly."
            )
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate USD cost from exact token counts."""
        rates = MODEL_RATES.get(model, MODEL_RATES["default"])
        cost = (prompt_tokens / 1_000_000.0) * rates["prompt"] + (
            completion_tokens / 1_000_000.0
        ) * rates["completion"]
        return cost

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        json_mode: bool = False,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Send a chat completion request to Fireworks AI serverless endpoint."""
        model_name = model or self.default_model
        url = f"{self.base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SimuGuard-X/1.0",
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        last_error = None

        for attempt in range(1, retries + 1):
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            try:
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    latency = time.time() - t0
                    res_json = json.loads(resp.read().decode("utf-8"))

                choice = res_json.get("choices", [{}])[0]
                message = choice.get("message", {})
                raw_content = message.get("content", "") or ""
                reasoning_content = message.get("reasoning_content", "") or ""

                usage = res_json.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                cost_usd = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

                return {
                    "model": model_name,
                    "content": raw_content.strip(),
                    "reasoning": reasoning_content.strip(),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost_usd,
                    "latency_sec": latency,
                }

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {e.code}: {err_body}"
                if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError(f"Fireworks API call failed: {last_error}") from e

            except urllib.error.URLError as e:
                last_error = str(e.reason)
                if attempt < retries:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError(f"Fireworks connection error: {last_error}") from e

        raise RuntimeError(f"Fireworks call failed after {retries} retries: {last_error}")
