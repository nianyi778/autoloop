from __future__ import annotations
import pytest
from core.evaluator.checklist import ChecklistEvaluator
from core.evaluator.rubric import EvaluationRubric, ChecklistItem
from core.parser.task_spec import TaskSpec


def make_spec(requirements: tuple[str, ...] = ()) -> TaskSpec:
    return TaskSpec(task_type="content_writing", requirements=requirements, raw_input="test")


@pytest.mark.asyncio
async def test_no_rubric_returns_pass():
    evaluator = ChecklistEvaluator()
    passed, failures = await evaluator.evaluate(output="anything", task_spec=make_spec(), rubric=None)
    assert passed is True
    assert failures == []


@pytest.mark.asyncio
async def test_empty_checklist_returns_pass():
    evaluator = ChecklistEvaluator()
    rubric = EvaluationRubric(checklist=[])
    passed, failures = await evaluator.evaluate(output="anything", task_spec=make_spec(), rubric=rubric)
    assert passed is True
    assert failures == []


@pytest.mark.asyncio
async def test_keyword_found_passes():
    evaluator = ChecklistEvaluator()
    rubric = EvaluationRubric(checklist=[
        ChecklistItem(id="kw", description="包含关键词竞品", required=True),
    ])
    output = "这是一篇关于竞品分析的报告"
    passed, failures = await evaluator.evaluate(output=output, task_spec=make_spec(), rubric=rubric)
    assert passed is True
    assert failures == []


@pytest.mark.asyncio
async def test_keyword_not_found_fails():
    evaluator = ChecklistEvaluator()
    rubric = EvaluationRubric(checklist=[
        ChecklistItem(id="data", description="包含数据图表", required=True),
    ])
    output = "这篇文章完全没有统计信息"
    passed, failures = await evaluator.evaluate(output=output, task_spec=make_spec(), rubric=rubric)
    assert passed is False
    assert len(failures) == 1
    assert "数据" in failures[0] or "图表" in failures[0]


@pytest.mark.asyncio
async def test_non_required_failure_does_not_block():
    evaluator = ChecklistEvaluator()
    rubric = EvaluationRubric(checklist=[
        ChecklistItem(id="optional", description="建议包含截图", required=False),
    ])
    output = "这篇文章没有截图"
    passed, failures = await evaluator.evaluate(output=output, task_spec=make_spec(), rubric=rubric)
    # Non-required items do not contribute to failures
    assert passed is True
    assert failures == []


@pytest.mark.asyncio
async def test_multiple_items_parallel():
    evaluator = ChecklistEvaluator()
    rubric = EvaluationRubric(checklist=[
        ChecklistItem(id="a", description="包含数据支撑", required=True),
        ChecklistItem(id="b", description="包含竞品对比", required=True),
    ])
    output = "本报告包含详细数据支撑和竞品对比分析"
    passed, failures = await evaluator.evaluate(output=output, task_spec=make_spec(), rubric=rubric)
    assert passed is True
    assert failures == []
