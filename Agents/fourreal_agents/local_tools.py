"""Client-side tools the agents can call that are NOT part of the editor's MCP surface.

These run inside the 4real runtime (e.g. the memory scratchpad) and are merged into a
specialist's tool list alongside the editor tools. Keeping them as first-class tools —
rather than stuffing context into the prompt — is what lets agents offload state instead
of carrying it in a growing conversation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .mcp_client import ToolSpec

Handler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(frozen=True)
class LocalTool:
    spec: ToolSpec
    handler: Handler

    @property
    def name(self) -> str:
        return self.spec.name
