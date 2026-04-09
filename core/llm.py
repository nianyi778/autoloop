from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator

import litellm

# Suppress litellm verbose output
litellm.suppress_debug_info = True


@lru_cache(maxsize=1)
def _config() -> dict:
    with open(Path(__file__).parent.parent / "config.toml", "rb") as f:
        return tomllib.load(f)


def resolve_model(*, role: str | None = None, module: str | None = None) -> str:
    """Priority: modules.X > roles.X > default_model"""
    llm = _config()["llm"]
    if module and module in llm.get("modules", {}):
        return llm["modules"][module]
    if role and role in llm.get("roles", {}):
        return llm["roles"][role]
    return llm["default_model"]


class LLMClient:
    def __init__(self, model: str, temperature: float = 0.7) -> None:
        self.model = model
        self.temperature = temperature

    async def complete(self, messages: list[dict], max_tokens: int = 512) -> str:
        resp = await litellm.acompletion(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return resp.choices[0].message.content

    async def stream(self, messages: list[dict], max_tokens: int = 2048) -> AsyncIterator[str]:
        resp = await litellm.acompletion(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            stream=True,
        )
        async for chunk in resp:
            text = chunk.choices[0].delta.content
            if text:
                yield text


def get_llm(*, role: str | None = None, module: str | None = None) -> LLMClient:
    llm_cfg = _config()["llm"]
    return LLMClient(
        model=resolve_model(role=role, module=module),
        temperature=llm_cfg.get("temperature", 0.7),
    )
