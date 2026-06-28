"""Tool transport between the 4real agents and the Unreal editor.

Agents reach the editor's hands through MCP. Three transports are supported:

  * mock  — an in-process set of fake UE tools so the agent loop is fully runnable on
            a machine with no Unreal install (great for a Mac dev box).
  * http  — a streamable-HTTP / SSE MCP endpoint exposed by Unreal's native MCP server.
  * stdio — spawn a local MCP server process and speak MCP over stdio.

All transports expose the same tiny surface: `list_tools()` and `call_tool()`.
"""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_anthropic(self) -> dict[str, Any]:
        """Render as an Anthropic tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema or {"type": "object", "properties": {}},
        }


class ToolHub:
    """Base interface. Async so real MCP transports can share one implementation."""

    async def __aenter__(self) -> "ToolHub":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def list_tools(self) -> list[ToolSpec]:
        raise NotImplementedError

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        raise NotImplementedError


# --------------------------------------------------------------------------- mock

# A representative slice of the 4real tool surface, enough to exercise every
# specialist's routing and the full tool-use loop without Unreal running.
_MOCK_TOOLS: list[ToolSpec] = [
    ToolSpec(
        "transaction_begin",
        "Open an undo transaction so subsequent edits group into one undo step.",
        {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]},
    ),
    ToolSpec(
        "transaction_end",
        "Commit the open undo transaction.",
        {"type": "object", "properties": {}},
    ),
    ToolSpec(
        "landscape_create",
        "Create a Landscape actor of a given size and section layout.",
        {
            "type": "object",
            "properties": {
                "size_quads": {"type": "integer", "description": "Per-component quad count"},
                "components": {"type": "integer"},
            },
            "required": ["size_quads"],
        },
    ),
    ToolSpec(
        "landscape_sculpt",
        "Apply a sculpt brush (raise/lower/flatten/noise) over a region of the landscape.",
        {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["raise", "lower", "flatten", "noise"]},
                "strength": {"type": "number"},
            },
            "required": ["mode"],
        },
    ),
    ToolSpec(
        "foliage_paint",
        "Paint a foliage type across landscape areas above/below a slope or height.",
        {
            "type": "object",
            "properties": {"foliage_asset": {"type": "string"}, "density": {"type": "number"}},
            "required": ["foliage_asset"],
        },
    ),
    ToolSpec(
        "umg_create_widget",
        "Create a UMG widget blueprint with an initial root panel.",
        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    ),
    ToolSpec(
        "umg_bind_mvvm",
        "Bind a widget property to a view-model field via MVVM.",
        {
            "type": "object",
            "properties": {
                "widget": {"type": "string"},
                "property": {"type": "string"},
                "viewmodel_field": {"type": "string"},
            },
            "required": ["widget", "property", "viewmodel_field"],
        },
    ),
    ToolSpec(
        "niagara_create_system",
        "Create a Niagara system with one emitter from a template.",
        {"type": "object", "properties": {"template": {"type": "string"}}, "required": ["template"]},
    ),
    ToolSpec(
        "perf_capture_frame",
        "Capture frame timing and return CPU vs GPU breakdown in milliseconds.",
        {"type": "object", "properties": {"frames": {"type": "integer"}}},
    ),
    ToolSpec(
        "actor_spawn",
        "Spawn an actor from a class or asset at a world transform.",
        {
            "type": "object",
            "properties": {
                "asset": {"type": "string"},
                "location": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["asset"],
        },
    ),
    ToolSpec(
        "asset_find",
        "Search the content browser for assets matching a query.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    ),
]


class MockToolHub(ToolHub):
    """In-process fake editor. Returns plausible JSON so the loop completes."""

    async def list_tools(self) -> list[ToolSpec]:
        return list(_MOCK_TOOLS)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "perf_capture_frame":
            return json.dumps(
                {"ok": True, "frame_ms": 14.7, "cpu_ms": 9.2, "gpu_ms": 14.1, "bound": "GPU"}
            )
        if name == "asset_find":
            q = arguments.get("query", "")
            return json.dumps({"ok": True, "results": [f"/Game/Demo/{q}_A", f"/Game/Demo/{q}_B"]})
        return json.dumps({"ok": True, "tool": name, "applied": arguments})


# ---------------------------------------------------------------------- real MCP


class MCPToolHub(ToolHub):
    """Speak MCP to Unreal's native server over http or stdio.

    Lazily imports the `mcp` package so the mock path has no hard dependency.
    """

    def __init__(self, transport: str, *, url: str = "", command: str = "") -> None:
        self._transport = transport
        self._url = url
        self._command = command
        self._stack = AsyncExitStack()
        self._session: Any = None

    async def __aenter__(self) -> "MCPToolHub":
        try:
            from mcp import ClientSession  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError(
                "The 'mcp' package is required for http/stdio transports. "
                "Install it with: pip install mcp  (or use --mock)."
            ) from exc

        if self._transport == "http":
            from mcp.client.streamable_http import streamablehttp_client  # type: ignore

            read, write, _ = await self._stack.enter_async_context(
                streamablehttp_client(self._url)
            )
        elif self._transport == "stdio":
            import shlex

            from mcp import StdioServerParameters  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore

            parts = shlex.split(self._command)
            if not parts:
                raise RuntimeError("stdio transport needs FOURREAL_MCP_COMMAND / --mcp-command")
            params = StdioServerParameters(command=parts[0], args=parts[1:])
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:  # pragma: no cover - guarded by caller
            raise ValueError(f"unknown MCP transport: {self._transport}")

        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.aclose()

    async def list_tools(self) -> list[ToolSpec]:
        result = await self._session.list_tools()
        return [
            ToolSpec(t.name, t.description or "", dict(t.inputSchema or {}))
            for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = await self._session.call_tool(name, arguments)
        chunks: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            chunks.append(text if text is not None else str(block))
        out = "\n".join(chunks) if chunks else "(no output)"
        if getattr(result, "isError", False):
            return json.dumps({"ok": False, "error": out})
        return out


def make_tool_hub(settings: "Any") -> ToolHub:
    """Construct the configured transport."""
    if settings.mcp_transport == "mock":
        return MockToolHub()
    return MCPToolHub(
        settings.mcp_transport, url=settings.mcp_url, command=settings.mcp_command
    )
