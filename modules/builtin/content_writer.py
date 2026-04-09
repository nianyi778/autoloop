from __future__ import annotations

from core.llm import get_llm
from modules.base import BaseModule, ModuleResult, RoundContext
from modules.registry import register


@register
class ContentWriterModule(BaseModule):
    name = "content_writer"
    description = "生成文案、报告、运营方案、分析文章等内容"
    match_pattern = r"content_writing|文案|报告|方案|分析|运营|写作"
    evaluation_rubric = None  # Uses generic LLM Judge scoring

    def __init__(self) -> None:
        self._llm = get_llm(module="content_writer")

    async def execute(self, context: RoundContext) -> ModuleResult:
        self._emit("progress", "开始生成内容...", context.round_number)

        prompt = self._build_prompt(context)
        output_parts: list[str] = []

        async for text in self._llm.stream(messages=[{"role": "user", "content": prompt}], max_tokens=2048):
            output_parts.append(text)
            self._emit("token", text, context.round_number)

        output = "".join(output_parts)
        self._emit("done", output, context.round_number)
        return ModuleResult(output=output)

    def _build_prompt(self, context: RoundContext) -> str:
        spec = context.task_spec
        requirements_str = "\n".join(f"- {r}" for r in spec.requirements)
        constraints_str = (
            "\n".join(f"- {c}" for c in spec.constraints)
            if spec.constraints
            else "无"
        )

        base = f"""你是专业内容创作专家。请根据以下要求创作内容。

【任务】{spec.raw_input}

【需求（必须全部满足）】
{requirements_str}

【约束】
{constraints_str}
"""
        if spec.style:
            base += f"\n【风格要求】{spec.style}\n"

        if context.round_number > 0 and context.diagnosis:
            base += f"""
【上轮反馈（第 {context.round_number} 轮，请针对性改进）】
问题类型：{context.diagnosis.category}
具体问题：{context.diagnosis.details}
改进建议：{context.diagnosis.suggested_strategy}
"""
            if context.previous_output:
                # Only show first 500 chars to avoid bloat
                preview = context.previous_output[:500]
                base += f"\n【上轮输出摘要（改进参考，不要复读）】\n{preview}...\n"

        if context.history_summary:
            base += f"\n【历史摘要】{context.history_summary}\n"

        base += "\n请直接输出内容，不要输出任何解释或前言。"
        return base
