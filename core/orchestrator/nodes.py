from __future__ import annotations

import json
import tomllib
from pathlib import Path

from core.evaluator.checklist import ChecklistEvaluator
from core.evaluator.llm_judge import EvaluatorInput, LLMJudge
from core.evaluator.diagnosis import Diagnosis
from core.llm import get_llm, LLMClient
from core.orchestrator.state import ForgeState, LoopEvent
from core.parser.task_spec import TaskSpec
from modules.registry import get_registry
from modules.router import MatchRouter
from modules.base import RoundContext


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


_config = _load_config()
_parser_llm = get_llm(role="parser")
_judge_llm  = get_llm(role="evaluator")
_router = MatchRouter()
_checklist_evaluator = ChecklistEvaluator()
_llm_judge = LLMJudge(
    client=_judge_llm,
    model=_judge_llm.model,
    pass_threshold=_config["loop"]["pass_threshold"],
)


async def parse_node(state: ForgeState) -> dict:
    """Parse raw input into structured TaskSpec via LLM."""
    raw = state["task_spec"].raw_input
    text = await _parser_llm.complete(messages=[{"role": "user", "content": f"""将以下需求解析为结构化任务单，严格 JSON 格式：

需求：{raw}

返回格式：
{{
  "task_type": "content_writing",
  "requirements": ["需求1", "需求2"],
  "constraints": [],
  "style": null
}}

task_type 只能是：content_writing / code_generation / analysis"""}], max_tokens=512)
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        parsed = TaskSpec(
            task_type=data.get("task_type", "content_writing"),
            requirements=tuple(data.get("requirements", [raw])),
            raw_input=raw,
            constraints=tuple(data.get("constraints", [])),
            style=data.get("style"),
        )
    except (ValueError, json.JSONDecodeError):
        parsed = TaskSpec(
            task_type="content_writing",
            requirements=(raw,),
            raw_input=raw,
        )

    event = LoopEvent.create("task_received", {"raw_input": raw})
    return {
        "task_spec": parsed,
        "events": [event],
        "current_round": 0,
        "max_rounds": _config["loop"]["max_rounds"],
        "selected_module": None,
        "previous_strategies": [],
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


async def route_node(state: ForgeState) -> dict:
    """Route task_spec to the appropriate module via MatchRouter."""
    cls = await _router.route(state["task_spec"])
    return {"selected_module": cls.name}


async def execute_node(state: ForgeState) -> dict:
    """Instantiate selected module and call execute(). Handle errors gracefully."""
    registry = get_registry()
    cls = registry[state["selected_module"]]
    module = cls()

    context = RoundContext(
        task_spec=state["task_spec"],
        round_number=state["current_round"],
        previous_output=state["current_output"],
        diagnosis=state["current_diagnosis"],
        history_summary=state["history_summary"],
    )

    event_start = LoopEvent.create("module_started", {
        "module": state["selected_module"],
        "round": state["current_round"],
    })

    try:
        result = await module.execute(context)
    except Exception as e:
        diagnosis = Diagnosis(
            category="execution_failed",
            details=str(e)[:500],
            suggested_strategy="检查错误信息并重新尝试",
        )
        event_fail = LoopEvent.create("module_completed", {
            "module": state["selected_module"],
            "round": state["current_round"],
            "success": False,
            "error": str(e)[:200],
        }, causation_id=event_start.event_id)
        return {
            "current_output": None,
            "current_diagnosis": diagnosis,
            "checklist_passed": False,
            "events": [event_start, event_fail],
        }

    event_done = LoopEvent.create("module_completed", {
        "module": state["selected_module"],
        "round": state["current_round"],
        "success": True,
        "output_len": len(result.output),
    }, causation_id=event_start.event_id)

    return {
        "current_output": result.output,
        "events": [event_start, event_done],
    }


async def evaluate_node(state: ForgeState) -> dict:
    """Two-stage evaluation: Checklist then LLM Judge. Evaluator sees only requirements + output."""
    if state["current_output"] is None:
        # Execution failed — pass through the diagnosis already set by execute_node
        return {"checklist_passed": False}

    # Extract rubric from module class (orchestrator extracts, evaluator never imports modules)
    registry = get_registry()
    module_cls = registry.get(state["selected_module"])
    rubric = module_cls.evaluation_rubric if module_cls else None

    # Stage 1: Checklist (parallel, fast)
    checklist_passed, failures = await _checklist_evaluator.evaluate(
        output=state["current_output"],
        task_spec=state["task_spec"],
        rubric=rubric,
    )
    event_checklist = LoopEvent.create("eval_checklist", {
        "passed": checklist_passed,
        "failures": failures,
        "round": state["current_round"],
    })

    if not checklist_passed:
        diagnosis = Diagnosis(
            category="requirement_mismatch",
            details=f"Checklist 失败：{'; '.join(failures)}",
            suggested_strategy="逐条满足需求列表中的每一项",
        )
        return {
            "checklist_passed": False,
            "current_diagnosis": diagnosis,
            "events": [event_checklist],
        }

    # Stage 2: LLM Judge (only if checklist passed)
    requirements_text = "\n".join(f"- {r}" for r in state["task_spec"].requirements)
    eval_input = EvaluatorInput(
        original_requirements=requirements_text,
        output=state["current_output"],
        rubric=rubric,
    )
    score, diagnosis = await _llm_judge.evaluate(eval_input)

    event_judge = LoopEvent.create("eval_judge", {
        "score": score,
        "diagnosis_category": diagnosis.category,
        "round": state["current_round"],
    }, causation_id=event_checklist.event_id)

    updates: dict = {
        "checklist_passed": True,
        "current_score": score,
        "current_diagnosis": diagnosis,
        "events": [event_checklist, event_judge],
    }
    if score > state["best_score"]:
        updates["best_output"] = state["current_output"]
        updates["best_score"] = score

    return updates


async def finalize_node(state: ForgeState) -> dict:
    """Task completed successfully — write final_output."""
    event = LoopEvent.create("output_finalized", {
        "score": state["current_score"],
        "round": state["current_round"],
    })
    return {
        "final_output": state["current_output"],
        "events": [event],
    }


async def exhaust_node(state: ForgeState) -> dict:
    """Max rounds exhausted — degrade to best_output (never return empty-handed)."""
    event = LoopEvent.create("task_exhausted", {
        "rounds_used": state["current_round"],
        "best_score": state["best_score"],
    })
    return {
        "final_output": state["best_output"],
        "failure_reason": (
            f"达到最大轮次 {state['max_rounds']}，"
            f"输出历史最优版本（得分 {state['best_score']:.2f}）"
        ),
        "events": [event],
    }


async def increment_round_node(state: ForgeState) -> dict:
    """Increment round counter and record the strategy used in this round."""
    used = list(state["previous_strategies"])
    if state["current_diagnosis"]:
        used.append(state["current_diagnosis"].suggested_strategy)
    return {
        "current_round": state["current_round"] + 1,
        "previous_strategies": used,
    }


def should_retry(state: ForgeState) -> str:
    """
    Conditional edge function — pure function, no state mutation.
    Returns: "finalize" | "exhaust" | "retry"
    """
    score = state.get("current_score") or 0.0
    passed = state.get("checklist_passed", False)
    threshold = _config["loop"]["pass_threshold"]

    if passed and score >= threshold:
        return "finalize"
    if state["current_round"] >= state["max_rounds"] - 1:
        return "exhaust"
    return "retry"
