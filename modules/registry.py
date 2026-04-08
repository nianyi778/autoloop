from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.base import BaseModule

ENTRY_POINT_GROUP = "autoloop.modules"

_registry: dict[str, type[BaseModule]] = {}


def register(cls: type[BaseModule]) -> type[BaseModule]:
    if cls.name in _registry:
        raise ValueError(f"Module name collision: '{cls.name}' already registered.")
    _registry[cls.name] = cls
    return cls


def discover_and_load() -> None:
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    for ep in eps:
        ep.load()


def get_registry() -> dict[str, type[BaseModule]]:
    return dict(_registry)
