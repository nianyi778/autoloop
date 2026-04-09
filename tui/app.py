from __future__ import annotations

import os
import sys

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Header, Footer, Input, Static, Button

from core.orchestrator.graph import graph
from core.orchestrator.state import ForgeState
from core.parser.task_spec import TaskSpec
from modules.base import StreamEvent
from modules.builtin import content_writer  # trigger @register
from tui.widgets import RoundPanel, EvalPanel


class OpenForgeApp(App):
    CSS = """
    Screen { layout: vertical; }
    #input-area { height: 5; }
    #output-area { height: 1fr; border: solid $primary; }
    RoundPanel { border: solid $accent; margin: 1; padding: 1; height: auto; }
    EvalPanel { border: solid $success; margin: 1; padding: 1; height: auto; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("OpenForge — 自主内容锻造引擎", id="title")
        with Vertical(id="input-area"):
            yield Input(placeholder="输入你的需求...", id="task-input")
            yield Button("开始", id="start-btn", variant="primary")
        with VerticalScroll(id="output-area"):
            yield Static("等待输入需求...", id="status")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            input_widget = self.query_one("#task-input", Input)
            raw_input = input_widget.value.strip()
            if raw_input:
                self.run_worker(self._run_loop(raw_input), exclusive=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw_input = event.value.strip()
        if raw_input:
            self.run_worker(self._run_loop(raw_input), exclusive=True)

    async def _run_loop(self, raw_input: str) -> None:
        output_area = self.query_one("#output-area", VerticalScroll)
        status = self.query_one("#status", Static)
        await output_area.remove_children()
        status.update(f"[bold]任务：[/bold]{raw_input}")

        initial_state: ForgeState = {
            "events": [],
            "task_spec": TaskSpec(
                task_type="content_writing",
                requirements=[raw_input],
                raw_input=raw_input,
            ),
            "selected_module": None,
            "previous_strategies": [],
            "current_round": 0,
            "max_rounds": 5,
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

        current_panel: RoundPanel | None = None
        eval_panel: EvalPanel | None = None

        async for chunk in graph.astream(
            initial_state,
            stream_mode=["updates", "custom"],
        ):
            if isinstance(chunk, StreamEvent):
                if current_panel is None:
                    current_panel = RoundPanel(chunk.round_number, chunk.module_name)
                    await output_area.mount(current_panel)
                if chunk.event_type == "progress":
                    current_panel.set_progress(chunk.payload)
                elif chunk.event_type == "token":
                    current_panel.append_token(chunk.payload)
                # "done" event no longer creates panel (moved to dict branch)
            elif isinstance(chunk, dict):
                # state update
                if "current_score" in chunk:
                    if eval_panel is None:
                        eval_panel = EvalPanel()
                        await output_area.mount(eval_panel)
                    score = chunk.get("current_score")
                    diagnosis = chunk.get("current_diagnosis")
                    checklist = chunk.get("checklist_passed", False)
                    details = diagnosis.details if diagnosis else ""
                    eval_panel.set_result(checklist, score, details)
                if "final_output" in chunk and chunk["final_output"]:
                    status.update("[bold green]✓ 任务完成[/bold green]")
                    current_panel = None
                    eval_panel = None  # reset both for next task
                if "failure_reason" in chunk and chunk["failure_reason"]:
                    status.update(f"[yellow]⚠ {chunk['failure_reason']}[/yellow]")


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    app = OpenForgeApp()
    app.run()


if __name__ == "__main__":
    main()
