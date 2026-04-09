from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, TypedDict

from core.evaluator.diagnosis import Diagnosis
from core.parser.task_spec import TaskSpec


def _append(existing: list, new: list) -> list:
    """LangGraph reducer: append new items to existing list (never overwrite)."""
    return existing + new


EventType = Literal[
    "task_received",
    "module_started",
    "module_completed",
    "eval_checklist",
    "eval_judge",
    "round_failed",
    "round_passed",
    "output_finalized",
    "task_exhausted",
]


@dataclass(frozen=True)
class LoopEvent:
    event_id: str
    timestamp: str
    event_type: EventType
    payload: dict[str, Any]
    causation_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: EventType,
        payload: dict[str, Any],
        causation_id: str | None = None,
    ) -> LoopEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            payload=payload,
            causation_id=causation_id,
        )


class ForgeState(TypedDict):
    # Event log — the single source of truth (append-only via _append reducer)
    events: Annotated[list[LoopEvent], _append]

    # Input (immutable after parse node)
    task_spec: TaskSpec

    # Routing
    selected_module: str | None
    previous_strategies: list[str]

    # Round management
    current_round: int
    max_rounds: int
    best_output: str | None
    best_score: float

    # Current round state (overwritten each round)
    current_output: str | None
    current_diagnosis: Diagnosis | None
    current_score: float | None
    checklist_passed: bool

    # Anti-bloat: LLM-compressed summary of prior rounds (≤200 tokens/round)
    history_summary: str | None

    # Terminal state
    final_output: str | None
    failure_reason: str | None
