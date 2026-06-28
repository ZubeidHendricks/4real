"""4real Agents — our own AI agent runtime for driving the Unreal Engine editor.

A roster of UE-domain specialist agents (terrain, UI, VFX/audio/anim, profiling, ...)
powered by Claude Opus 4.8, each wired to the 4real MCP tool surface, coordinated by a
lead orchestrator that routes a natural-language goal to the right specialist.

This is "4real's own AI agents": the brains live here, the hands (tools) live in the
4real Unreal plugin and are reached over MCP.
"""

__version__ = "0.1.0"
