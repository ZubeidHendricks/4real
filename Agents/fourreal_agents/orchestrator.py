"""The lead orchestrator — 4real's director.

Turns a high-level goal into ordered (specialist, task) steps, dispatches each to its
specialist, and synthesizes a final report.

Anti-context-rot architecture:
  * Each specialist runs in its OWN fresh conversation — the orchestrator never grows
    one giant shared transcript.
  * Continuity between steps is carried by a COMPACT handoff digest pulled from the
    shared memory scratchpad, not by replaying prior transcripts.
  * Long-lived state lives in the memory file; agents recall it on demand.
  * Optional fresh-context verification after each step, with one gap-driven retry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anthropic

from .agent import SpecialistAgent
from .config import Settings
from .mcp_client import ToolHub
from .memory import RunMemory, memory_tools
from .roster import ROSTER, ROSTER_BY_KEY
from .verifier import verify_step


_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "specialist": {"type": "string", "enum": [s.key for s in ROSTER]},
                    "task": {
                        "type": "string",
                        "description": "Self-contained instruction for that specialist.",
                    },
                },
                "required": ["specialist", "task"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["steps"],
    "additionalProperties": False,
}


@dataclass
class PlanStep:
    specialist: str
    task: str


def _slug(text: str, n: int = 40) -> str:
    out = "".join(c if c.isalnum() or c in " -_" else "" for c in text).strip()
    return ("-".join(out.lower().split()))[:n] or "run"


class Orchestrator:
    def __init__(
        self,
        hub: ToolHub,
        settings: Settings,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.hub = hub
        self.settings = settings
        self.client = client or anthropic.AsyncAnthropic()

    def _roster_blurbs(self) -> str:
        return "\n".join(f"- {s.key}: {s.blurb}" for s in ROSTER)

    async def plan(self, goal: str) -> list[PlanStep]:
        system = (
            "You are 4real's lead director for Unreal Engine editor automation. "
            "Break the user's goal into an ordered list of steps, each assigned to one "
            "specialist. Editor state is shared and serial, so order matters: build "
            "dependencies before dependents (e.g. terrain before foliage, widgets "
            "before bindings). Use the fewest steps that achieve the goal. Only use "
            "specialists from this roster:\n" + self._roster_blurbs()
        )
        response = await self.client.messages.create(
            model=self.settings.router_model,
            max_tokens=2000,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": _PLAN_SCHEMA}},
            messages=[{"role": "user", "content": goal}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "{}")
        data = json.loads(text)
        return [PlanStep(s["specialist"], s["task"]) for s in data.get("steps", [])]

    async def run(self, goal: str) -> str:
        print(f"\n4real ▸ planning: {goal}\n")
        memory = RunMemory(namespace=_slug(goal))
        memory.note("goal", goal, author="director")

        steps = await self.plan(goal)
        if not steps:
            return "No actionable steps were produced for that goal."

        for i, step in enumerate(steps, 1):
            label = ROSTER_BY_KEY[step.specialist].label
            print(f"[{i}/{len(steps)}] {label}: {step.task}")

        transcripts: list[str] = []
        for i, step in enumerate(steps, 1):
            spec = ROSTER_BY_KEY[step.specialist]
            print(f"\n── step {i}: {spec.label} ──")
            res = await self._run_step(spec, step.task, memory)
            transcripts.append(f"### {spec.label}\n{res}")

        return await self._synthesize(goal, transcripts, memory)

    async def _run_step(self, spec: Any, task: str, memory: RunMemory) -> str:
        # Compact handoff: prior decisions, not prior transcripts.
        digest = memory.digest()
        framed = task
        if digest:
            framed = (
                f"{task}\n\n--- context so far (from the shared memory; "
                f"recall more with memory_recall) ---\n{digest}"
            )

        agent = SpecialistAgent(
            spec,
            self.hub,
            self.settings,
            self.client,
            local_tools=memory_tools(memory, author=spec.key),
        )
        res = await agent.run(framed)
        if res.cleared_tokens:
            print(f"  (context editing pruned {res.cleared_tokens} stale tokens)")
        memory.note(f"{spec.key}/done", res.final_text[:280], author=spec.key)

        if not self.settings.verify:
            return res.final_text

        print(f"  ✓ verifying {spec.label}…")
        verdict = await verify_step(task, res.final_text, self.hub, self.settings, self.client)
        if verdict.satisfied:
            print(f"  ✓ verified: {verdict.summary}")
            return res.final_text

        gaps = "; ".join(verdict.gaps) or verdict.summary
        print(f"  ✗ gaps: {gaps} — retrying once")
        memory.note(f"{spec.key}/gaps", gaps, author="verifier")
        retry = await agent.run(
            f"Your previous attempt left gaps. Original task:\n{task}\n\n"
            f"Gaps to fix now:\n{gaps}"
        )
        return f"{res.final_text}\n(after fixing: {retry.final_text})"

    async def _synthesize(self, goal: str, transcripts: list[str], memory: RunMemory) -> str:
        joined = "\n\n".join(transcripts)
        response = await self.client.messages.create(
            model=self.settings.router_model,
            max_tokens=1500,
            system=(
                "Summarize for the user what the 4real fleet accomplished toward their "
                "goal. Be concrete: name assets/paths changed and call out anything that "
                "needs their attention. A few sentences; no per-tool play-by-play."
            ),
            thinking={"type": "adaptive"},
            messages=[
                {"role": "user", "content": f"Goal: {goal}\n\nSpecialist reports:\n{joined}"}
            ],
        )
        report = "".join(b.text for b in response.content if b.type == "text").strip()
        return f"{report}\n\nMemory: {memory.path}"
