"""Fresh-context verifier.

After a specialist finishes a step, a separate agent with a clean context checks the
work against the task — using only read-only tools — and returns a verdict. A fresh
context catches gaps that self-critique (which shares the doer's biased, rotted context)
misses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anthropic

from .config import Settings
from .mcp_client import ToolHub

# Tool names that only read editor state — safe for a verifier to call.
_READONLY_HINTS = (
    "find", "list", "describe", "get", "query", "audit", "inspect",
    "perf", "stat", "capture", "read", "info", "report",
)

_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "satisfied": {"type": "boolean"},
        "summary": {"type": "string"},
        "gaps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["satisfied", "summary", "gaps"],
    "additionalProperties": False,
}


@dataclass
class Verdict:
    satisfied: bool
    summary: str
    gaps: list[str]


async def verify_step(
    task: str,
    report: str,
    hub: ToolHub,
    settings: Settings,
    client: anthropic.AsyncAnthropic,
) -> Verdict:
    all_tools = await hub.list_tools()
    ro_tools = [
        t.to_anthropic()
        for t in all_tools
        if any(h in t.name.lower() for h in _READONLY_HINTS)
    ]

    system = (
        "You are 4real's independent verifier. Given a task and the doer's report, "
        "decide whether the task was actually accomplished in the editor. Use ONLY the "
        "provided read-only tools to check — never assume the report is true. Be strict "
        "but fair; list concrete gaps if any remain."
    )
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Task:\n{task}\n\nDoer's report:\n{report}"}
    ]

    # Let the verifier do a few read-only checks before judging.
    for _ in range(6):
        resp = await client.messages.create(
            model=settings.router_model,
            max_tokens=2000,
            system=system,
            thinking={"type": "adaptive"},
            tools=ro_tools or anthropic.NOT_GIVEN,
            messages=messages,
        )
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for tu in tool_uses:
            try:
                out = await hub.call_tool(tu.name, tu.input if isinstance(tu.input, dict) else {})
            except Exception as exc:
                out = json.dumps({"ok": False, "error": str(exc)})
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
        messages.append({"role": "user", "content": results})

    # Final structured judgment.
    messages.append(
        {"role": "user", "content": "Give your final verdict using the required schema."}
    )
    final = await client.messages.create(
        model=settings.router_model,
        max_tokens=1000,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": _VERDICT_SCHEMA}},
        messages=messages,
    )
    text = next((b.text for b in final.content if b.type == "text"), "{}")
    data = json.loads(text)
    return Verdict(
        satisfied=bool(data.get("satisfied", False)),
        summary=str(data.get("summary", "")),
        gaps=list(data.get("gaps", [])),
    )
