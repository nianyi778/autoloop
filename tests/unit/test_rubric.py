from core.evaluator.rubric import EvaluationRubric, ChecklistItem


def test_checklist_item():
    item = ChecklistItem(id="kw", description="包含关键词'竞品'", required=True)
    assert item.required is True
    assert item.id == "kw"


def test_evaluation_rubric_defaults():
    rubric = EvaluationRubric()
    assert rubric.checklist == []
    assert rubric.llm_judge_weight == 0.7
    assert "correctness" in rubric.scoring_dimensions
    assert "completeness" in rubric.scoring_dimensions


def test_evaluation_rubric_custom():
    item = ChecklistItem(id="length", description="字数超过 800", required=True)
    rubric = EvaluationRubric(checklist=[item], llm_judge_weight=0.5)
    assert len(rubric.checklist) == 1
    assert rubric.llm_judge_weight == 0.5
