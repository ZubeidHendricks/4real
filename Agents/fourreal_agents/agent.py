"""The specialist agent loop — built to resist context rot.

A Specialist persona + the filtered MCP tool surface (+ optional client-side tools)
running a manual tool-use loop on Claude Opus 4.8 until the task is done.

Context-rot defenses (a long tool-calling loop otherwise bloats and degrades):
  1. Server-side context editing (`clear_tool_uses_20250919`) clears stale tool
     results from the model's working set once the run gets long.
  2. Each stored tool result is capped, so one chatty tool can't flood the transcript.
  3. The stable system+tools prefix is prompt-cached, so loop iterations don't re-pay
     for it and the cache stays warm even as old tool results are cleared.
  4. The orchestrator gives each specialist a fresh conversation plus a *compact*
     handoff digest — long-horizon state lives in the memory scratchpad, not the chat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from .config import Settings
from .local_tools import LocalTool
from .mcp_client import ToolHub, ToolSpec
from .roster import Specialist

_CONTEXT_EDIT_BETA = "context-management-2025-06-27"


@dataclass
class RunResult:
    specialist: str
    final_text: str
    tool_calls: list[str] = field(default_factory=list)
    stopped_reason: str = ""
    cleared_tokens: int = 0


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
        local_tools: list[LocalTool] | None = None,
    ) -> None:
        self.spec = specialist
        self.hub = hub
        self.settings = settings
        self.client = client or anthropic.AsyncAnthropic()
        self.trace = trace
        self.local_tools = {lt.name: lt for lt in (local_tools or [])}

    async def _granted_tools(self) -> list[ToolSpec]:
        all_tools = await self.hub.list_tools()
        granted = [t for t in all_tools if self.spec.matches(t.name)]
        # Always grant transaction tools so edits group into one undo step.
        for t in all_tools:
            if "transaction" in t.name.lower() and t not in granted:
                granted.append(t)
        # Append client-side tools (e.g. the memory scratchpad) for every specialist.
        granted.extend(lt.spec for lt in self.local_tools.values())
        return granted

    def _system_blocks(self) -> Any:
        """System prompt, cached as a stable prefix when caching is enabled."""
        if not self.settings.prompt_caching:
            return self.spec.system
        return [
            {
                "type": "text",
                "text": self.spec.system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def _create(self, **kwargs: Any) -> Any:
        """Route through the beta endpoint when context editing is on."""
        if self.settings.context_editing:
            return await self.client.beta.messages.create(
                betas=[_CONTEXT_EDIT_BETA],
                context_management={
                    "edits": [{"type": "clear_tool_uses_20250919"}]
                },
                **kwargs,
            )
        return await self.client.messages.create(**kwargs)

    async def _dispatch(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Call a client-side tool if we own it, else the editor over MCP."""
        try:
            if name in self.local_tools:
                out = await self.local_tools[name].handler(args)
            else:
                out = await self.hub.call_tool(name, args)
        except Exception as exc:  # surface failures back to the model
            return json.dumps({"ok": False, "error": str(exc)}), True
        cap = self.settings.tool_result_char_cap
        if cap and len(out) > cap:
            out = out[:cap] + f"\n…[truncated {len(out) - cap} chars]"
        return out, False

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
            response = await self._create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=self._system_blocks(),
                thinking={"type": "adaptive"},
                output_config={"effort": self.settings.effort},
                tools=tool_defs or anthropic.NOT_GIVEN,
                messages=messages,
            )

            # Surface how much stale context the server pruned this turn.
            cm = getattr(response, "context_management", None)
            for edit in getattr(cm, "applied_edits", []) or []:
                cleared = getattr(edit, "cleared_input_tokens", 0) or 0
                if cleared:
                    result.cleared_tokens += cleared
                    self.trace(f"    ✂ cleared {cleared} stale tool-result tokens")

            if response.stop_reason == "refusal":
                result.stopped_reason = "refusal"
                result.final_text = "[request refused by safety classifier]"
                return result

            # Preserve full content (incl. thinking blocks) for the next turn.
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
                out, is_error = await self._dispatch(tu.name, args)
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
