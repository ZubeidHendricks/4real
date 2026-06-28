"""The lead orchestrator — 4real's director.

Takes a high-level natural-language goal, plans which specialists should do what (in
order — editor state is shared and serial), then dispatches each step to its
specialist agent and synthesizes a final report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anthropic

from .agent import SpecialistAgent
from .config import Settings
from .mcp_client import ToolHub
from .roster import ROSTER, ROSTER_BY_KEY


_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "specialist": {
                        "type": "string",
                        "enum": [s.key for s in ROSTER],
                    },
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
            agent = SpecialistAgent(spec, self.hub, self.settings, self.client)
            res = await agent.run(step.task)
            transcripts.append(f"### {spec.label}\n{res.final_text}")

        return await self._synthesize(goal, transcripts)

    async def _synthesize(self, goal: str, transcripts: list[str]) -> str:
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
                {
                    "role": "user",
                    "content": f"Goal: {goal}\n\nSpecialist reports:\n{joined}",
                }
            ],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()
