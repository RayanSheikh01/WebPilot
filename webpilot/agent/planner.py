"""Anthropic tool-use loop (plan §3.2 + §4.3 event emission).

System prompt and tools are cached via `cache_control: ephemeral` on the last
block of each. The loop accumulates token usage into the BudgetTracker and
stops on `finish`, on a response with no tool_use, or on a budget violation.

Lifecycle events are emitted via the optional sync `emit(kind, payload)`
callback supplied by the runner: `status:running` at loop start, `tool_call`
+ `tool_result` per dispatch, `usage` after each API response, and either
`finish` or `status:done` on exit (or `error` if an exception propagates).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .guardrails import BudgetTracker
from .tools import TOOL_SCHEMAS

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system.md"

_TRUNC = 500


def _truncate_repr(obj) -> str:
    s = repr(obj)
    if len(s) > _TRUNC:
        return s[:_TRUNC] + "...<truncated>"
    return s


@dataclass
class LoopResult:
    notes: list[str]
    sources: list[dict]
    summary: str
    terminated_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    messages: list = field(default_factory=list)


class Planner:
    def __init__(
        self,
        client,
        executor,
        tracker: BudgetTracker,
        model: str = "claude-opus-4-7",
        max_output_tokens: int = 4096,
        emit: Callable[[str, dict], None] | None = None,
    ):
        self.client = client
        self.executor = executor
        self.tracker = tracker
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._emit = emit

    def _emit_event(self, kind: str, payload: dict) -> None:
        if self._emit is None:
            return
        try:
            self._emit(kind, payload)
        except Exception:
            # Telemetry must never break the loop.
            pass

    def _system_blocks(self) -> list[dict]:
        prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        return [
            {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}
        ]

    def _tools_with_cache(self) -> list[dict]:
        tools = [dict(t) for t in TOOL_SCHEMAS]
        tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}
        return tools

    async def run(self, brief: str) -> LoopResult:
        messages: list[dict] = [{"role": "user", "content": brief}]
        system = self._system_blocks()
        tools = self._tools_with_cache()

        terminated = "unknown"

        # Note: runner may also emit status:running first; duplicate is harmless.
        self._emit_event("status:running", {})

        try:
            while True:
                violation = self.tracker.check_before_call()
                if violation is not None:
                    terminated = f"budget:{violation.name}"
                    break

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_output_tokens,
                    system=system,
                    tools=tools,
                    messages=messages,
                )

                usage = getattr(response, "usage", None)
                in_tok = getattr(usage, "input_tokens", 0) or 0 if usage else 0
                out_tok = getattr(usage, "output_tokens", 0) or 0 if usage else 0
                if usage is not None:
                    self.tracker.record_usage(in_tok, out_tok)
                self._emit_event(
                    "usage", {"input_tokens": in_tok, "output_tokens": out_tok}
                )

                content_blocks = list(response.content)
                messages.append({"role": "assistant", "content": content_blocks})

                tool_uses = [
                    b for b in content_blocks if getattr(b, "type", None) == "tool_use"
                ]
                if not tool_uses:
                    terminated = "no_tool_use"
                    break

                tool_results = []
                for block in tool_uses:
                    self._emit_event(
                        "tool_call",
                        {"name": block.name, "input": _truncate_repr(block.input)},
                    )
                    result = await self.executor.run(block.name, block.input or {})
                    self._emit_event(
                        "tool_result",
                        {"name": block.name, "result": _truncate_repr(result)},
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )
                    if self.executor.finished:
                        break

                messages.append({"role": "user", "content": tool_results})

                if self.executor.finished:
                    terminated = "finish"
                    break
        except Exception as e:
            self._emit_event(
                "error", {"type": type(e).__name__, "message": str(e)}
            )
            raise

        if terminated == "finish":
            self._emit_event(
                "finish", {"summary": self.executor.finish_summary or ""}
            )
        else:
            self._emit_event(
                "status:done", {"terminated_reason": terminated}
            )

        return LoopResult(
            notes=list(self.executor.notes),
            sources=list(self.executor.sources),
            summary=self.executor.finish_summary or "",
            terminated_reason=terminated,
            input_tokens=self.tracker.input_tokens,
            output_tokens=self.tracker.output_tokens,
            messages=messages,
        )
