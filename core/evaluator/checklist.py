from __future__ import annotations

import asyncio
import re

from core.evaluator.rubric import EvaluationRubric, ChecklistItem
from core.parser.task_spec import TaskSpec


class ChecklistEvaluator:
    """
    Phase 1: keyword-based checklist verification (fast, no LLM calls).
    Phase 2 upgrade: replace _check_item with LLM verification per item.

    Returns (passed: bool, failures: list[str]) where failures contains
    descriptions of required items that did not pass.
    """

    async def evaluate(
        self,
        output: str,
        task_spec: TaskSpec,
        rubric: EvaluationRubric | None,
    ) -> tuple[bool, list[str]]:
        # No rubric = no checklist to run; go straight to LLM Judge
        if rubric is None or not rubric.checklist:
            return True, []

        results = await asyncio.gather(*[
            self._check_item(output, item)
            for item in rubric.checklist
        ])

        failures = [
            item.description
            for item, passed in zip(rubric.checklist, results)
            if item.required and not passed
        ]
        return len(failures) == 0, failures

    async def _check_item(self, output: str, item: ChecklistItem) -> bool:
        """
        Extract meaningful keywords from item.description and check if any
        appear in the output. Strips common stop words and punctuation.
        """
        stop = {
            "包含", "字数", "超过", "不少于", "的", "了", "是", "有", "和",
            "要", "需", "应", "该", "一", "个", "在", "中", "上", "下",
        }

        # Extract all Chinese characters and ASCII words
        keywords = re.findall(r'[\w\u4e00-\u9fff]+', item.description)

        # Also extract individual Chinese characters for more flexible matching
        chars = re.findall(r'[\u4e00-\u9fff]', item.description)
        chars = [k for k in chars if k not in stop]

        # Filter multi-char tokens
        keywords = [k for k in keywords if k not in stop and len(k) > 1]

        # If no multi-char keywords found, use individual characters
        if not keywords:
            keywords = chars if chars else ['']
        else:
            keywords.extend(chars)

        return any(kw in output for kw in keywords)
