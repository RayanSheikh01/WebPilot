"""Anthropic tool-use loop (plan §3.2).

System prompt and tools are cached via `cache_control: ephemeral` on the last
block of each. The loop accumulates token usage into the BudgetTracker and
stops on `finish`, on a response with no tool_use, or on a budget violation.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .guardrails import BudgetTracker
from .tools import TOOL_SCHEMAS

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system.md"


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
    ):
        self.client = client
        self.executor = executor
        self.tracker = tracker
        self.model = model
        self.max_output_tokens = max_output_tokens

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
            if usage is not None:
                self.tracker.record_usage(
                    getattr(usage, "input_tokens", 0) or 0,
                    getattr(usage, "output_tokens", 0) or 0,
                )

            content_blocks = list(response.content)
            messages.append({"role": "assistant", "content": content_blocks})

            tool_uses = [b for b in content_blocks if getattr(b, "type", None) == "tool_use"]
            if not tool_uses:
                terminated = "no_tool_use"
                break

            tool_results = []
            for block in tool_uses:
                result = await self.executor.run(block.name, block.input or {})
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

        return LoopResult(
            notes=list(self.executor.notes),
            sources=list(self.executor.sources),
            summary=self.executor.finish_summary or "",
            terminated_reason=terminated,
            input_tokens=self.tracker.input_tokens,
            output_tokens=self.tracker.output_tokens,
            messages=messages,
        )
