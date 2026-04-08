from __future__ import annotations
import typing
from dataclasses import dataclass
from typing import Literal

DiagnosisCategory = Literal[
    "requirement_mismatch",
    "quality_insufficient",
    "execution_failed",
    "scope_exceeded",
    "info_insufficient",
]

VALID_CATEGORIES: frozenset[str] = frozenset(typing.get_args(DiagnosisCategory))


@dataclass(frozen=True)
class Diagnosis:
    category: DiagnosisCategory
    details: str
    suggested_strategy: str

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {self.category!r}. Must be one of {VALID_CATEGORIES}")
