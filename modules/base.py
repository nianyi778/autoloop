from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from langgraph.config import get_stream_writer

from core.evaluator.rubric import EvaluationRubric
from core.evaluator.diagnosis import Diagnosis
from core.parser.task_spec import TaskSpec


@dataclass(frozen=True)
class RoundContext:
    task_spec: TaskSpec
    round_number: int
    previous_output: str | None
    diagnosis: Diagnosis | None
    history_summary: str | None


@dataclass
class ModuleResult:
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamEvent:
    module_name: str
    round_number: int
    event_type: str    # "token" | "progress" | "error" | "done"
    payload: str


class ModuleExecutionError(Exception):
    def __init__(self, module_name: str, reason: str) -> None:
        self.module_name = module_name
        self.reason = reason
        super().__init__(f"[{module_name}] {reason}")


class BaseModule(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    match_pattern: ClassVar[str]
    evaluation_rubric: ClassVar[EvaluationRubric | None] = None

    @abstractmethod
    async def execute(self, context: RoundContext) -> ModuleResult: ...

    def _emit(self, event_type: str, payload: str, round_number: int) -> None:
        writer = get_stream_writer()
        writer(StreamEvent(
            module_name=self.name,
            round_number=round_number,
            event_type=event_type,
            payload=payload,
        ))

    @classmethod
    def compiled_pattern(cls) -> re.Pattern[str]:
        return re.compile(cls.match_pattern, re.IGNORECASE)
