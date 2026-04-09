from __future__ import annotations

import json
import os
import stat
from pathlib import Path

AUTH_FILE = Path.home() / ".local" / "share" / "openforge" / "auth.json"

PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "label": "OpenAI",
        "env_var": "OPENAI_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env_var": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "label": "通义千问 (Qwen)",
        "env_var": "DASHSCOPE_API_KEY",
    },
    "custom": {
        "label": "自定义 OpenAI 兼容接口",
        "env_var": "OPENAI_API_KEY",
    },
}


def get_api_key(provider: str) -> str | None:
    """Priority: env var > auth.json"""
    meta = PROVIDERS.get(provider, {})
    env_var = meta.get("env_var", f"{provider.upper()}_API_KEY")
    if val := os.environ.get(env_var):
        return val
    return _load_auth().get(provider, {}).get("key")


def save_key(provider: str, key: str) -> None:
    creds = _load_auth()
    creds[provider] = {"type": "api_key", "key": key}
    _save_auth(creds)


def remove_key(provider: str) -> None:
    creds = _load_auth()
    creds.pop(provider, None)
    _save_auth(creds)


def list_providers() -> list[dict]:
    creds = _load_auth()
    result = []
    for name, meta in PROVIDERS.items():
        env_key = os.environ.get(meta.get("env_var", ""))
        stored = creds.get(name, {}).get("key")
        result.append({
            "name": name,
            "label": meta["label"],
            "configured": bool(env_key or stored),
            "source": "env" if env_key else ("file" if stored else None),
        })
    return result


def has_any_provider() -> bool:
    return any(p["configured"] for p in list_providers())


def load_into_env() -> None:
    """Load stored keys into env vars so LiteLLM picks them up automatically."""
    creds = _load_auth()
    for provider, data in creds.items():
        meta = PROVIDERS.get(provider, {})
        env_var = meta.get("env_var", f"{provider.upper()}_API_KEY")
        if "key" in data and not os.environ.get(env_var):
            os.environ[env_var] = data["key"]


def _load_auth() -> dict:
    if not AUTH_FILE.exists():
        return {}
    try:
        with open(AUTH_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_auth(creds: dict) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    AUTH_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
