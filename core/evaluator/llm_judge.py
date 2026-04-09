from __future__ import annotations

import json
from dataclasses import dataclass

from core.evaluator.diagnosis import Diagnosis
from core.evaluator.rubric import EvaluationRubric


@dataclass(frozen=True)
class EvaluatorInput:
    """
    Strict context isolation: Judge sees ONLY original requirements + final output.
    Deliberately excludes: module_name, round_number, history, diagnosis.
    This prevents sunk-cost bias inflating scores on later rounds.
    """
    original_requirements: str
    output: str
    rubric: EvaluationRubric | None = None


class LLMJudge:
    def __init__(self, client, model: str, pass_threshold: float = 0.8) -> None:
        self._client = client
        self._model = model
        self._pass_threshold = pass_threshold

    async def evaluate(self, input_: EvaluatorInput) -> tuple[float, Diagnosis]:
        dimensions = (
            input_.rubric.scoring_dimensions
            if input_.rubric
            else ["correctness", "completeness", "style", "relevance"]
        )
        prompt = self._build_prompt(input_, dimensions)
        text = await self._client.complete(messages=[{"role": "user", "content": prompt}], max_tokens=512)
        return self._parse_response(text)

    def _build_prompt(self, input_: EvaluatorInput, dimensions: list[str]) -> str:
        dims_str = "\n".join(f"- {d}: 0.0~1.0" for d in dimensions)
        dim_defaults = ", ".join(f'"{d}": 0.0' for d in dimensions)
        return f"""你是严格的内容质量评审专家。根据【原始需求】评审【输出内容】。

【原始需求】
{input_.original_requirements}

【输出内容】
{input_.output}

【评分维度】（每项 0.0~1.0）
{dims_str}

请严格按以下 JSON 格式回复，不要输出其他内容：
{{
  "scores": {{{dim_defaults}}},
  "overall": 0.0,
  "diagnosis_category": "quality_insufficient",
  "diagnosis_details": "具体说明哪里不足",
  "suggested_strategy": "下一轮改进建议"
}}

diagnosis_category 必须是以下之一：
requirement_mismatch / quality_insufficient / execution_failed / scope_exceeded / info_insufficient

如果 overall >= {self._pass_threshold}，diagnosis_category 填 "quality_insufficient" 即可（不会被使用）。"""

    def _parse_response(self, text: str) -> tuple[float, Diagnosis]:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            data = json.loads(text[start:end])
            score = float(data.get("overall", 0.0))
            score = max(0.0, min(1.0, score))  # clamp to [0, 1]
            diagnosis = Diagnosis(
                category=data.get("diagnosis_category", "quality_insufficient"),
                details=data.get("diagnosis_details", ""),
                suggested_strategy=data.get("suggested_strategy", ""),
            )
            return score, diagnosis
        except (ValueError, KeyError, json.JSONDecodeError):
            return 0.0, Diagnosis(
                category="quality_insufficient",
                details=f"评估响应解析失败，原始响应：{text[:200]}",
                suggested_strategy="重新尝试生成",
            )
