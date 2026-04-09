from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.base import BaseModule

ENTRY_POINT_GROUP = "openforge.modules"

_registry: dict[str, type[BaseModule]] = {}
_registry_version: int = 0


def register(cls: type[BaseModule]) -> type[BaseModule]:
    global _registry_version
    if cls.name in _registry:
        raise ValueError(f"Module name collision: '{cls.name}' already registered.")
    _registry[cls.name] = cls
    _registry_version += 1
    return cls


def discover_and_load() -> None:
    # Entry-point group is empty in Phase 1; @register handles builtin modules at import time
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    for ep in eps:
        ep.load()


def get_registry() -> dict[str, type[BaseModule]]:
    return dict(_registry)


def get_registry_version() -> int:
    return _registry_version
