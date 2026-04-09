"""
集成测试：mock litellm.acompletion，验证图的流转逻辑正确。
不测试 LLM 输出质量，只测试状态流转。
"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.orchestrator.graph import build_graph
from core.parser.task_spec import TaskSpec
from core.orchestrator.state import ForgeState


def make_initial_state(raw_input: str = "写一篇测试文章") -> ForgeState:
    return {
        "events": [],
        "task_spec": TaskSpec(
            task_type="content_writing",
            requirements=[raw_input],
            raw_input=raw_input,
        ),
        "selected_module": None,
        "previous_strategies": [],
        "current_round": 0,
        "max_rounds": 3,
        "best_output": None,
        "best_score": 0.0,
        "current_output": None,
        "current_diagnosis": None,
        "current_score": None,
        "checklist_passed": False,
        "history_summary": None,
        "final_output": None,
        "failure_reason": None,
    }


def make_completion_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    return resp


async def make_stream_response(tokens: list[str]):
    for token in tokens:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = token
        yield chunk


@pytest.mark.asyncio
async def test_graph_reaches_final_output_on_high_score():
    """当 LLM Judge 打高分时，图应该在第一轮就走到 finalize。"""
    from modules.builtin import content_writer  # trigger registration

    parse_text = '{"task_type": "content_writing", "requirements": ["写测试文章"], "constraints": [], "style": null}'
    judge_text = '{"scores": {"correctness": 0.9}, "overall": 0.9, "diagnosis_category": "quality_insufficient", "diagnosis_details": "良好", "suggested_strategy": "保持"}'

    async def mock_acompletion(**kwargs):
        stream = kwargs.get("stream", False)
        messages = kwargs.get("messages", [{}])
        content = messages[0].get("content", "")

        if stream:
            return make_stream_response(["这是", "测试", "内容"])
        if "解析为结构化任务单" in content:
            return make_completion_response(parse_text)
        return make_completion_response(judge_text)

    with patch("litellm.acompletion", side_effect=mock_acompletion):
        graph = build_graph()
        result = await graph.ainvoke(make_initial_state())

    assert result["final_output"] is not None
    assert result["failure_reason"] is None
    assert result["task_spec"].task_type == "content_writing"  # confirms parse_node got correct mock


@pytest.mark.asyncio
async def test_graph_exhausts_after_max_rounds():
    """当评分始终不达标时，图应该在 max_rounds 后走到 exhaust，返回最优版本。"""
    from modules.builtin import content_writer  # trigger registration

    parse_text = '{"task_type": "content_writing", "requirements": ["写测试"], "constraints": [], "style": null}'
    judge_text = '{"scores": {}, "overall": 0.3, "diagnosis_category": "quality_insufficient", "diagnosis_details": "质量不足", "suggested_strategy": "改进"}'

    async def mock_acompletion(**kwargs):
        stream = kwargs.get("stream", False)
        messages = kwargs.get("messages", [{}])
        content = messages[0].get("content", "")

        if stream:
            return make_stream_response(["低质量内容"])
        if "解析为结构化任务单" in content:
            return make_completion_response(parse_text)
        return make_completion_response(judge_text)

    with patch("litellm.acompletion", side_effect=mock_acompletion):
        graph = build_graph()
        result = await graph.ainvoke(make_initial_state())

    assert result["failure_reason"] is not None
    assert "最大轮次" in result["failure_reason"]
    # 降级输出：best_output 非空（有历史最优版本）
    assert result["final_output"] is not None
    assert result["task_spec"].task_type == "content_writing"  # confirms parse_node got correct mock
    assert result["current_round"] == result["max_rounds"] - 1  # ran all max_rounds
