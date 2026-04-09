# AutoLoop

An autonomous content generation engine that takes a requirement as input and iteratively generates, evaluates, and refines output until it meets quality standards — or exhausts its retry budget and returns the best result so far.

## How It Works

```
Input → Parse → Route → Execute → Evaluate → [Pass] → Output
                            ↑         |
                            └─[Retry]─┘
```

1. **Parse** — Extracts structured requirements from raw input via LLM
2. **Route** — Matches task type to a module via regex
3. **Execute** — Module generates content (streaming)
4. **Evaluate** — Two-stage: keyword Checklist → LLM Judge (0–1 score)
5. **Retry** — If score < threshold, diagnosis feeds next round with a different strategy
6. **Exhaust** — After `max_rounds`, returns the historically best output

The evaluator only sees the original requirements and the output — no round history, no module name. This isolation prevents the judge from being lenient on context it wasn't asked about.

## Features

- **Pluggable modules** — Register a module with `@register` and a regex pattern; the router picks it automatically
- **Strategy diversification** — Each retry tracks `previous_strategies` so the module never repeats the same fix
- **Event sourcing** — Every state transition is recorded as an append-only `LoopEvent` (UUID + UTC timestamp)
- **Degraded output** — Never returns empty. On exhaustion, returns the highest-scoring output from any round
- **Streaming TUI** — Textual-based terminal UI with real-time token rendering per round

## Quickstart

```bash
# Install
git clone https://github.com/nianyi778/autoloop
cd autoloop
uv sync

# Configure
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# Run
uv run autoloop
```

Requires Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and an [Anthropic API key](https://console.anthropic.com/).

## Configuration

`config.toml`:

```toml
[loop]
max_rounds = 5          # maximum retry attempts
pass_threshold = 0.8    # LLM Judge score to accept output

[llm]
model = "claude-sonnet-4-6"
temperature = 0.7

[evaluator]
checklist_parallel = true
```

## Project Structure

```
autoloop/
├── core/
│   ├── parser/         # TaskSpec — structured requirement extraction
│   ├── evaluator/      # Checklist + LLM Judge (context-isolated)
│   └── orchestrator/   # LangGraph StateGraph, nodes, event log
├── modules/
│   ├── base.py         # BaseModule, RoundContext, StreamEvent
│   ├── registry.py     # @register decorator
│   ├── router.py       # regex-based MatchRouter
│   └── builtin/
│       └── content_writer.py
└── tui/                # Textual app
```

## Adding a Module

```python
from modules.base import BaseModule, ModuleResult, RoundContext
from modules.registry import register

@register
class MyModule(BaseModule):
    name = "my_module"
    description = "Does something specific"
    match_pattern = r"keyword|另一个关键词"

    async def execute(self, context: RoundContext) -> ModuleResult:
        self._emit("progress", "Working...", context.round_number)
        # ... generate content ...
        return ModuleResult(output=result)
```

The router picks `MyModule` when `task_type` matches `match_pattern`. Diagnosis from the previous round is available at `context.diagnosis`.

## Tech Stack

- [LangGraph](https://github.com/langchain-ai/langgraph) — stateful agent loop with conditional edges
- [Anthropic](https://docs.anthropic.com/) — Claude for generation and evaluation
- [Textual](https://textual.textualize.io/) — async terminal UI
- [uv](https://docs.astral.sh/uv/) — dependency management

## Roadmap

- **Phase 2** — Planner layer, Clarifier (human-in-loop via LangGraph `interrupt()`), web search tool
- **Phase 3** — Code agent with Docker sandbox execution

## License

MIT
