import pytest
from core.evaluator.diagnosis import Diagnosis


def test_diagnosis_valid_category():
    d = Diagnosis(
        category="requirement_mismatch",
        details="输出未提及价格对比",
        suggested_strategy="重点围绕需求列表逐条展开",
    )
    assert d.category == "requirement_mismatch"


def test_all_valid_categories():
    categories = [
        "requirement_mismatch", "quality_insufficient",
        "execution_failed", "scope_exceeded", "info_insufficient"
    ]
    for cat in categories:
        d = Diagnosis(category=cat, details="x", suggested_strategy="y")
        assert d.category == cat


def test_diagnosis_invalid_category():
    with pytest.raises(ValueError, match="Invalid category"):
        Diagnosis(category="unknown_category", details="x", suggested_strategy="y")
