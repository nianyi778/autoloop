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

    def __post_init__(self) -> None:
        if not (0.0 <= self.llm_judge_weight <= 1.0):
            raise ValueError(f"llm_judge_weight must be in [0, 1], got {self.llm_judge_weight}")
