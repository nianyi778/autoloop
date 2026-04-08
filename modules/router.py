from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from modules.registry import get_registry

if TYPE_CHECKING:
    from modules.base import BaseModule
    from core.parser.task_spec import TaskSpec


class NoModuleFound(Exception):
    pass


class AmbiguousModuleMatch(Exception):
    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        super().__init__(f"Multiple modules matched: {candidates}")


class MatchRouter:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    async def route(self, task_spec: TaskSpec) -> type[BaseModule]:
        cache_key = self._cache_key(task_spec)
        if cache_key in self._cache:
            name = self._cache[cache_key]
            return get_registry()[name]

        registry = get_registry()
        candidates = [
            cls for cls in registry.values()
            if cls.compiled_pattern().search(task_spec.task_type)
        ]

        if len(candidates) == 0:
            raise NoModuleFound(
                f"No module matched task_type='{task_spec.task_type}'. "
                f"Registered: {list(registry.keys())}"
            )

        if len(candidates) > 1:
            raise AmbiguousModuleMatch([c.name for c in candidates])

        chosen = candidates[0]
        self._cache[cache_key] = chosen.name
        return chosen

    @staticmethod
    def _cache_key(task_spec: TaskSpec) -> str:
        payload = json.dumps({"task_type": task_spec.task_type}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
