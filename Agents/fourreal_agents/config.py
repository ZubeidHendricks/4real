"""Runtime configuration for the 4real agent fleet.

Model defaults follow the current Claude API guidance: Opus 4.8 with adaptive
thinking. Override per-environment via the 4REAL_* environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Latest, most capable Claude model. Adaptive thinking is the only on-mode on 4.8.
DEFAULT_MODEL = "claude-opus-4-8"
# A cheaper tier for routing / simple specialists; keep the heavy reasoning on Opus.
ROUTER_MODEL = "claude-opus-4-8"

# effort: low | medium | high | xhigh | max  — high is the sweet spot for agentic work.
DEFAULT_EFFORT = "high"


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    router_model: str = ROUTER_MODEL
    effort: str = DEFAULT_EFFORT
    max_tokens: int = 16000
    # How many tool-call rounds a single specialist may take before we stop it.
    max_iterations: int = 24

    # MCP transport to the 4real / Unreal editor.
    #   transport = "mock"  -> in-process fake tools (works on a Mac with no UE)
    #   transport = "http"  -> streamable-HTTP / SSE MCP endpoint exposed by UE
    #   transport = "stdio" -> spawn an MCP server process via `mcp_command`
    mcp_transport: str = "mock"
    mcp_url: str = "http://127.0.0.1:30010/mcp"
    mcp_command: str = ""  # e.g. "python -m some_mcp_server"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.environ.get("4REAL_MODEL", DEFAULT_MODEL),
            router_model=os.environ.get("4REAL_ROUTER_MODEL", ROUTER_MODEL),
            effort=os.environ.get("4REAL_EFFORT", DEFAULT_EFFORT),
            max_tokens=int(os.environ.get("4REAL_MAX_TOKENS", "16000")),
            max_iterations=int(os.environ.get("4REAL_MAX_ITERS", "24")),
            mcp_transport=os.environ.get("4REAL_MCP_TRANSPORT", "mock"),
            mcp_url=os.environ.get("4REAL_MCP_URL", "http://127.0.0.1:30010/mcp"),
            mcp_command=os.environ.get("4REAL_MCP_COMMAND", ""),
        )
