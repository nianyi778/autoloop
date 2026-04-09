from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from core.auth import PROVIDERS, save_key


class LoginScreen(ModalScreen[bool]):
    """Modal provider login screen. Returns True if a key was saved."""

    DEFAULT_CSS = """
    LoginScreen {
        align: center middle;
    }
    #login-dialog {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #login-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #provider-select, #api-key-input {
        margin-bottom: 1;
    }
    #btn-row {
        layout: horizontal;
        height: auto;
        align: right middle;
    }
    Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        provider_options = [(meta["label"], name) for name, meta in PROVIDERS.items()]
        with Vertical(id="login-dialog"):
            yield Static("OpenForge — 添加 LLM 提供商", id="login-title")
            yield Label("选择提供商")
            yield Select(options=provider_options, id="provider-select", prompt="选择提供商...")
            yield Label("API Key")
            yield Input(placeholder="sk-...", id="api-key-input", password=True)
            with Vertical(id="btn-row"):
                yield Button("保存", id="save-btn", variant="primary")
                yield Button("跳过", id="skip-btn", variant="default")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            select = self.query_one("#provider-select", Select)
            key_input = self.query_one("#api-key-input", Input)
            provider = select.value
            key = key_input.value.strip()
            if provider and provider is not Select.BLANK and key:
                save_key(str(provider), key)
                self.dismiss(True)
            else:
                key_input.focus()
        elif event.button.id == "skip-btn":
            self.dismiss(False)
