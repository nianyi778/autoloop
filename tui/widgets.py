from __future__ import annotations
from textual.widgets import Static


class RoundPanel(Static):
    """单轮执行面板，实时追加 token"""

    def __init__(self, round_number: int, module_name: str) -> None:
        super().__init__()
        self.round_number = round_number
        self.module_name = module_name
        self._tokens: list[str] = []
        self.border_title = f"Round {round_number + 1} · {module_name}"

    def append_token(self, token: str) -> None:
        self._tokens.append(token)
        self.update("".join(self._tokens))

    def set_progress(self, message: str) -> None:
        if not self._tokens:
            self.update(f"[dim]{message}[/dim]")
        # if tokens are already streaming, don't overwrite them


class EvalPanel(Static):
    """评估结果面板"""

    def set_result(self, checklist_passed: bool, score: float | None, diagnosis_details: str) -> None:
        lines = []
        lines.append(f"Checklist: {'✓' if checklist_passed else '✗'}")
        if score is not None:
            lines.append(f"LLM Judge: {score:.2f}/1.00")
        if diagnosis_details:
            lines.append(f"诊断: [yellow]{diagnosis_details[:80]}[/yellow]")
        self.update("\n".join(lines))
