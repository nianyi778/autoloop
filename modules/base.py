from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

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
    event_type: Literal["token", "progress", "error", "done"]
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
        try:
            writer = get_stream_writer()
        except RuntimeError:
            return  # outside LangGraph context — silently drop
        writer(StreamEvent(
            module_name=self.name,
            round_number=round_number,
            event_type=event_type,
            payload=payload,
        ))

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Only validate concrete subclasses (those that define all required ClassVars)
        required = ("name", "description", "match_pattern")
        missing = [attr for attr in required if not isinstance(getattr(cls, attr, None), str)]
        if missing:
            raise TypeError(
                f"{cls.__name__} must define ClassVar[str] for: {missing}"
            )

    @classmethod
    def compiled_pattern(cls) -> re.Pattern[str]:
        attr = "_compiled_pattern_cache"
        if not hasattr(cls, attr):
            # Use object.__setattr__ to avoid frozen dataclass issues at class level
            try:
                setattr(cls, attr, re.compile(cls.match_pattern, re.IGNORECASE))
            except AttributeError:
                pass  # class has __slots__ or other restriction; fall through to recompile
        return getattr(cls, attr, re.compile(cls.match_pattern, re.IGNORECASE))
