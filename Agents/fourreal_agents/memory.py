"""Durable scratchpad for the fleet — the primary defense against context rot.

Instead of carrying everything in a single ever-growing conversation, agents write
findings and decisions to a small markdown memory file and recall them on demand. The
orchestrator also reads the latest notes to build a *compact* handoff between steps, so
specialist N gets a short summary of what came before — not the full transcripts.

One fact per note; the file stays human-readable so you can inspect what the fleet
"knows" about a project.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .local_tools import LocalTool
from .mcp_client import ToolSpec

DEFAULT_MEMORY_DIR = Path(
    os.environ.get("FOURREAL_MEMORY_DIR", str(Path.cwd() / ".4real_memory"))
)


class RunMemory:
    """A markdown-backed note store, namespaced per project/run."""

    def __init__(self, namespace: str = "default", directory: Path | None = None) -> None:
        self.dir = directory or DEFAULT_MEMORY_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in namespace) or "default"
        self.path = self.dir / f"{safe}.md"
        if not self.path.exists():
            self.path.write_text(f"# 4real memory — {namespace}\n\n", encoding="utf-8")

    def note(self, topic: str, note: str, author: str = "") -> None:
        stamp = time.strftime("%Y-%m-%d %H:%M")
        who = f" ({author})" if author else ""
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(f"- **{topic}**{who} — {note.strip()}  <!-- {stamp} -->\n")

    def recall(self, query: str = "") -> list[str]:
        lines = [
            ln.rstrip()
            for ln in self.path.read_text(encoding="utf-8").splitlines()
            if ln.startswith("- ")
        ]
        if query:
            q = query.lower()
            lines = [ln for ln in lines if q in ln.lower()]
        return lines

    def digest(self, limit: int = 12) -> str:
        """A compact recap for handoffs between steps."""
        notes = self.recall()
        if not notes:
            return ""
        recent = notes[-limit:]
        return "\n".join(recent)


def memory_tools(mem: RunMemory, author: str = "") -> list[LocalTool]:
    """Expose the scratchpad as two client-side tools."""

    async def _note(args: dict[str, Any]) -> str:
        topic = str(args.get("topic", "note"))
        body = str(args.get("note", "")).strip()
        if not body:
            return json.dumps({"ok": False, "error": "note is empty"})
        mem.note(topic, body, author=author)
        return json.dumps({"ok": True, "saved": topic})

    async def _recall(args: dict[str, Any]) -> str:
        hits = mem.recall(str(args.get("query", "")))
        return json.dumps({"ok": True, "notes": hits[-20:]})

    return [
        LocalTool(
            ToolSpec(
                "memory_note",
                "Record a durable fact, decision, or finding so you (and other 4real "
                "agents) don't have to re-derive it. Use this instead of keeping detail "
                "in your head across many tool calls. One fact per call.",
                {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Short key, e.g. 'forest/terrain'"},
                        "note": {"type": "string", "description": "The fact to remember."},
                    },
                    "required": ["topic", "note"],
                },
            ),
            _note,
        ),
        LocalTool(
            ToolSpec(
                "memory_recall",
                "Recall previously recorded facts. Optionally filter by a substring query. "
                "Check this before re-investigating something that may already be known.",
                {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
            _recall,
        ),
    ]
