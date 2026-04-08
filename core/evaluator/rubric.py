from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    description: str
    required: bool = True


@dataclass
class EvaluationRubric:
    checklist: list[ChecklistItem] = field(default_factory=list)
    llm_judge_weight: float = 0.7
    scoring_dimensions: list[str] = field(default_factory=lambda: [
        "correctness", "completeness", "style", "relevance"
    ])
