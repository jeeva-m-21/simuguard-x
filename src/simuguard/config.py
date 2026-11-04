"""Configuration and environment management for SimuGuard-X."""

import os
from pathlib import Path


def load_env_file(env_path: Path | None = None) -> None:
    """Load key-value pairs from .env into os.environ if not already set."""
    if env_path is None:
        # Search current working directory and parent directories
        cur = Path.cwd()
        candidates = [cur / ".env", cur.parent / ".env"]
        for cand in candidates:
            if cand.is_file():
                env_path = cand
                break

    if env_path and env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val


# Automatically load .env on import
load_env_file()

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")

# Default models verified on Fireworks serverless
DEFAULT_MODEL = "accounts/fireworks/models/gpt-oss-120b"
DEFAULT_FLASH_MODEL = "accounts/fireworks/models/deepseek-v4p1-flash"
DEFAULT_REASONING_MODEL = "accounts/fireworks/models/glm-5p3-flash"
