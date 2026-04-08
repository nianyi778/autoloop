"""
集成测试：mock Anthropic API，验证图的流转逻辑正确。
不测试 LLM 输出质量，只测试状态流转。
"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.orchestrator.graph import build_graph
from core.parser.task_spec import TaskSpec
from core.orchestrator.state import AutoLoopState


def make_initial_state(raw_input: str = "写一篇测试文章") -> AutoLoopState:
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


async def _async_gen(items):
    for item in items:
        yield item


def _make_mock_client(parse_response_text: str, judge_response_text: str):
    """
    Build a mock AsyncAnthropic client that handles both parse and judge calls.

    Since nodes.py uses _client for parse + judge, and content_writer creates
    its own client via anthropic.AsyncAnthropic(), we patch both the module-level
    singleton and the class constructor.
    """
    mock_parse_msg = MagicMock()
    mock_parse_msg.content = [MagicMock(text=parse_response_text)]

    mock_judge_msg = MagicMock()
    mock_judge_msg.content = [MagicMock(text=judge_response_text)]

    call_count = [0]

    async def mock_create(**kwargs):
        # First call is parse_node (解析为结构化任务单), subsequent calls are LLM Judge
        call_count[0] += 1
        messages = kwargs.get("messages", [])
        content = messages[0].get("content", "") if messages else ""
        if "解析为结构化任务单" in content:
            return mock_parse_msg
        return mock_judge_msg

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_stream_ctx.text_stream = _async_gen(["这是", "测试", "内容"])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=mock_create)
    mock_client.messages.stream = MagicMock(return_value=mock_stream_ctx)

    return mock_client


@pytest.mark.asyncio
async def test_graph_reaches_final_output_on_high_score():
    """当 LLM Judge 打高分时，图应该在第一轮就走到 finalize。"""
    from modules.builtin import content_writer  # trigger registration

    parse_text = '{"task_type": "content_writing", "requirements": ["写测试文章"], "constraints": [], "style": null}'
    judge_text = '{"scores": {"correctness": 0.9}, "overall": 0.9, "diagnosis_category": "quality_insufficient", "diagnosis_details": "良好", "suggested_strategy": "保持"}'

    mock_client = _make_mock_client(parse_text, judge_text)

    with (
        patch("core.orchestrator.nodes._client", mock_client),
        patch("core.orchestrator.nodes._llm_judge._client", mock_client),
        patch("anthropic.AsyncAnthropic", return_value=mock_client),
    ):
        graph = build_graph()
        result = await graph.ainvoke(make_initial_state())

    assert result["final_output"] is not None
    assert result["failure_reason"] is None


@pytest.mark.asyncio
async def test_graph_exhausts_after_max_rounds():
    """当评分始终不达标时，图应该在 max_rounds 后走到 exhaust，返回最优版本。"""
    from modules.builtin import content_writer  # trigger registration

    parse_text = '{"task_type": "content_writing", "requirements": ["写测试"], "constraints": [], "style": null}'
    judge_text = '{"scores": {}, "overall": 0.3, "diagnosis_category": "quality_insufficient", "diagnosis_details": "质量不足", "suggested_strategy": "改进"}'

    # Each round generates new stream context, so we need a factory
    def make_stream_ctx():
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.text_stream = _async_gen(["低质量内容"])
        return ctx

    mock_parse_msg = MagicMock()
    mock_parse_msg.content = [MagicMock(text=parse_text)]

    mock_judge_msg = MagicMock()
    mock_judge_msg.content = [MagicMock(text=judge_text)]

    async def mock_create(**kwargs):
        messages = kwargs.get("messages", [])
        content = messages[0].get("content", "") if messages else ""
        if "解析为结构化任务单" in content:
            return mock_parse_msg
        return mock_judge_msg

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=mock_create)
    mock_client.messages.stream = MagicMock(side_effect=lambda **kw: make_stream_ctx())

    with (
        patch("core.orchestrator.nodes._client", mock_client),
        patch("core.orchestrator.nodes._llm_judge._client", mock_client),
        patch("anthropic.AsyncAnthropic", return_value=mock_client),
    ):
        graph = build_graph()
        result = await graph.ainvoke(make_initial_state())

    assert result["failure_reason"] is not None
    assert "最大轮次" in result["failure_reason"]
    # 降级输出：best_output 非空（有历史最优版本）
    assert result["final_output"] is not None
