"""Command-line entry point for the 4real agent fleet.

Examples:
  # See the roster (no API key, no UE needed)
  python -m fourreal_agents --list-agents

  # See the tool surface the agents can reach (mock works offline)
  python -m fourreal_agents --list-tools

  # Run the fleet against a goal in mock mode (needs ANTHROPIC_API_KEY)
  python -m fourreal_agents "Block out a foggy forest arena with a HUD health bar"

  # Drive a single specialist directly
  python -m fourreal_agents --agent profiler "Why are we GPU-bound this frame?"

  # Talk to a real Unreal editor over MCP
  python -m fourreal_agents --transport http --url http://127.0.0.1:30010/mcp "..."
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import sys

from .config import Settings
from .mcp_client import make_tool_hub
from .roster import ROSTER, ROSTER_BY_KEY, roster_table


def _build_settings(args: argparse.Namespace) -> Settings:
    base = Settings.from_env()
    overrides = {}
    if args.transport:
        overrides["mcp_transport"] = args.transport
    if args.mock:
        overrides["mcp_transport"] = "mock"
    if args.url:
        overrides["mcp_url"] = args.url
    if args.mcp_command:
        overrides["mcp_command"] = args.mcp_command
    if args.effort:
        overrides["effort"] = args.effort
    return dataclasses.replace(base, **overrides)


async def _list_tools(settings: Settings) -> int:
    async with make_tool_hub(settings) as hub:
        tools = await hub.list_tools()
        print(f"4real tool surface ({settings.mcp_transport}): {len(tools)} tools\n")
        width = max((len(t.name) for t in tools), default=0)
        for t in tools:
            print(f"  {t.name.ljust(width)}  {t.description}")
    return 0


async def _run_agent(settings: Settings, key: str, task: str) -> int:
    import anthropic  # imported here so --list-* works without the SDK installed

    from .agent import SpecialistAgent

    spec = ROSTER_BY_KEY.get(key)
    if spec is None:
        print(f"Unknown agent '{key}'. Try --list-agents.", file=sys.stderr)
        return 2
    client = anthropic.AsyncAnthropic()
    async with make_tool_hub(settings) as hub:
        agent = SpecialistAgent(spec, hub, settings, client)
        res = await agent.run(task)
        print(f"\n{spec.label} ▸ {res.final_text}")
    return 0


async def _run_fleet(settings: Settings, goal: str) -> int:
    import anthropic

    from .orchestrator import Orchestrator

    client = anthropic.AsyncAnthropic()
    async with make_tool_hub(settings) as hub:
        orch = Orchestrator(hub, settings, client)
        report = await orch.run(goal)
        print(f"\n══ 4real report ══\n{report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="4real", description="4real AI agent fleet for Unreal Engine")
    parser.add_argument("goal", nargs="*", help="Natural-language goal for the fleet")
    parser.add_argument("--agent", help="Run a single specialist by key (see --list-agents)")
    parser.add_argument("--list-agents", action="store_true", help="List the specialist roster and exit")
    parser.add_argument("--list-tools", action="store_true", help="List the reachable MCP tools and exit")
    parser.add_argument("--transport", choices=["mock", "http", "stdio"], help="MCP transport")
    parser.add_argument("--mock", action="store_true", help="Use the in-process mock editor")
    parser.add_argument("--url", help="MCP endpoint URL (http transport)")
    parser.add_argument("--mcp-command", dest="mcp_command", help="MCP server command (stdio transport)")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], help="Reasoning effort")
    args = parser.parse_args(argv)

    if args.list_agents:
        print("4real specialist roster:\n")
        print(roster_table())
        print(f"\n{len(ROSTER)} specialists. Run one with: --agent <key> \"task\"")
        print("keys: " + ", ".join(s.key for s in ROSTER))
        return 0

    settings = _build_settings(args)

    if args.list_tools:
        return asyncio.run(_list_tools(settings))

    goal = " ".join(args.goal).strip()
    if args.agent:
        if not goal:
            parser.error("--agent needs a task, e.g. --agent profiler \"diagnose this frame\"")
        return asyncio.run(_run_agent(settings, args.agent, goal))

    if not goal:
        parser.error("provide a goal, or use --list-agents / --list-tools")
    return asyncio.run(_run_fleet(settings, goal))


if __name__ == "__main__":
    raise SystemExit(main())
