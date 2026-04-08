from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskSpec:
    task_type: str                        # e.g. "content_writing", "code_generation"
    requirements: list[str]               # 逐条需求，评估 Checklist 来源
    raw_input: str                        # 用户原始输入，不变
    constraints: list[str] = field(default_factory=list)
    style: str | None = None
