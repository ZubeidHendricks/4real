"""The specialist agent loop.

A Specialist persona + the filtered MCP tool surface + Claude Opus 4.8 (adaptive
thinking) running a manual tool-use loop until the task is done. We use the manual
loop rather than the SDK tool runner so each tool call routes through our MCP hub and
so we can surface a live trace of what the agent is doing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from .config import Settings
from .mcp_client import ToolHub, ToolSpec
from .roster import Specialist


@dataclass
class RunResult:
    specialist: str
    final_text: str
    tool_calls: list[str] = field(default_factory=list)
    stopped_reason: str = ""


Tracer = Callable[[str], None]


def _default_tracer(line: str) -> None:
    print(line, flush=True)


class SpecialistAgent:
    def __init__(
        self,
        specialist: Specialist,
        hub: ToolHub,
        settings: Settings,
        client: anthropic.AsyncAnthropic | None = None,
        trace: Tracer = _default_tracer,
    ) -> None:
        self.spec = specialist
        self.hub = hub
        self.settings = settings
        self.client = client or anthropic.AsyncAnthropic()
        self.trace = trace

    async def _granted_tools(self) -> list[ToolSpec]:
        all_tools = await self.hub.list_tools()
        granted = [t for t in all_tools if self.spec.matches(t.name)]
        # Always allow transaction tools so agents can group their edits for undo.
        for t in all_tools:
            if "transaction" in t.name.lower() and t not in granted:
                granted.append(t)
        return granted

    async def run(self, task: str) -> RunResult:
        tools = await self._granted_tools()
        tool_defs = [t.to_anthropic() for t in tools]
        self.trace(
            f"  · {self.spec.label}: {len(tool_defs)} tools "
            f"[{', '.join(t['name'] for t in tool_defs) or 'none'}]"
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        result = RunResult(specialist=self.spec.key, final_text="")

        for _ in range(self.settings.max_iterations):
            response = await self.client.messages.create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=self.spec.system,
                thinking={"type": "adaptive"},
                output_config={"effort": self.settings.effort},
                tools=tool_defs or anthropic.NOT_GIVEN,
                messages=messages,
            )

            if response.stop_reason == "refusal":
                result.stopped_reason = "refusal"
                result.final_text = "[request refused by safety classifier]"
                return result

            # Preserve the full content (incl. thinking blocks) for the next turn.
            messages.append({"role": "assistant", "content": response.content})

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            text = "".join(b.text for b in response.content if b.type == "text")
            if text.strip():
                result.final_text = text.strip()

            if not tool_uses:
                result.stopped_reason = response.stop_reason or "end_turn"
                return result

            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                args = tu.input if isinstance(tu.input, dict) else {}
                self.trace(f"    → {tu.name}({json.dumps(args, separators=(',', ':'))})")
                result.tool_calls.append(tu.name)
                try:
                    out = await self.hub.call_tool(tu.name, args)
                    is_error = False
                except Exception as exc:  # surface tool failures back to the model
                    out = json.dumps({"ok": False, "error": str(exc)})
                    is_error = True
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": out,
                        "is_error": is_error,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        result.stopped_reason = "max_iterations"
        result.final_text = result.final_text or "[stopped: hit max tool iterations]"
        return result
