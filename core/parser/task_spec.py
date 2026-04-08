from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskSpec:
    task_type: str
    requirements: tuple[str, ...]
    raw_input: str
    constraints: tuple[str, ...] = field(default_factory=tuple)
    style: str | None = None
