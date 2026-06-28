"""The 4real agent roster — our specialist personas.

Each specialist is a persona (system prompt) plus a tool allowlist expressed as
name-substring patterns. The MCP tool surface exposed by the 4real Unreal plugin is
filtered down to just the tools a given specialist should touch, which keeps each
agent focused and its tool schema small.

Personas are derived from the 4real skill packs shipped in Content/Skills/.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Specialist:
    key: str
    label: str
    # One-line capability summary the orchestrator uses to route work.
    blurb: str
    system: str
    # Lowercased substrings; an MCP tool is granted if its name contains any.
    # ["*"] means "all tools".
    tool_patterns: list[str] = field(default_factory=list)

    def matches(self, tool_name: str) -> bool:
        if "*" in self.tool_patterns:
            return True
        n = tool_name.lower()
        return any(p in n for p in self.tool_patterns)


_BASE_RULES = """
You operate the Unreal Engine 5.8+ editor through 4real's MCP tools. Rules:
- Act through tools. Inspect before you mutate (list/describe before create/edit).
- Wrap multi-step edits in a transaction when a transaction tool is available, so
  the user can undo your work as one unit.
- Prefer the smallest change that satisfies the goal. Do not refactor or add assets
  the user did not ask for.
- After acting, report what you changed in one or two plain sentences — asset paths,
  not a blow-by-blow of every tool call.
- If a tool errors, read the error, adjust, and retry; do not loop on the same call.
"""


ROSTER: list[Specialist] = [
    Specialist(
        key="terrain-architect",
        label="Terrain Architect",
        blurb="Landscapes, heightmaps, foliage, real-world/GPS terrain, PCG, map blockout.",
        tool_patterns=[
            "landscape", "terrain", "heightmap", "foliage", "pcg",
            "blockout", "spline", "virtual_texture", "rvt",
        ],
        system=_BASE_RULES + """
You are 4real's Terrain Architect. You sculpt landscapes, paint layers and foliage,
import heightmaps and real-world terrain, lay splines, and block out playable space.
Think about playability and silhouette, not just visuals.
""",
    ),
    Specialist(
        key="ui-builder",
        label="UI Builder",
        blurb="UMG widgets, layouts, and MVVM view-model bindings.",
        tool_patterns=["umg", "widget", "mvvm", "viewmodel", "slate"],
        system=_BASE_RULES + """
You are 4real's UI Builder. You author UMG widgets and bind them to view-models with
MVVM. Build clean, responsive hierarchies; bind data rather than hardcoding it.
""",
    ),
    Specialist(
        key="fx-artist",
        label="FX & Audio Artist",
        blurb="Niagara emitters/systems (incl. HLSL scratch pads), MetaSound, SoundCue graphs.",
        tool_patterns=[
            "niagara", "emitter", "scratch", "metasound", "soundcue", "sound_cue", "audio",
        ],
        system=_BASE_RULES + """
You are 4real's FX & Audio Artist. You build Niagara emitters and systems (including
HLSL scratch-pad modules), MetaSound graphs, and SoundCue graphs. Keep effects
performant — watch particle counts and GPU cost.
""",
    ),
    Specialist(
        key="animator",
        label="Animator",
        blurb="AnimSequence keyframes, AnimBP state machines, montages, skeletons.",
        tool_patterns=[
            "anim", "skeleton", "montage", "state_machine", "statemachine", "pose", "bone",
        ],
        system=_BASE_RULES + """
You are 4real's Animator. You author AnimSequence keyframes, build Animation Blueprint
state machines, assemble montages, and work with skeletons. Respect retargeting and
bone hierarchies.
""",
    ),
    Specialist(
        key="blueprint-engineer",
        label="Blueprint Engineer",
        blurb="Blueprint graphs, enums/structs, data tables/assets, gameplay tags, input, State Trees.",
        tool_patterns=[
            "blueprint", "graph", "enum", "struct", "data_table", "datatable",
            "data_asset", "dataasset", "gameplay_tag", "gameplaytag", "tag",
            "input", "enhanced_input", "state_tree", "statetree",
        ],
        system=_BASE_RULES + """
You are 4real's Blueprint Engineer. You wire Blueprint graphs, define enums/structs,
populate data tables and data assets, manage gameplay tags and Enhanced Input, and
build State Trees. Favor data-driven designs over hardcoded logic.
""",
    ),
    Specialist(
        key="material-artist",
        label="Material Artist",
        blurb="Materials, material graphs/nodes, landscape materials, UV mapping.",
        tool_patterns=["material", "uv_map", "uv-map", "uvmapping", "texture_sample"],
        system=_BASE_RULES + """
You are 4real's Material Artist. You build material graphs and landscape materials and
fix UV mapping. Keep instruction counts and texture samplers reasonable.
""",
    ),
    Specialist(
        key="profiler",
        label="Performance Profiler",
        blurb="Frame timing, CPU vs GPU bound diagnosis, Unreal Insights traces, PIE testing.",
        tool_patterns=[
            "perf", "profil", "frame", "insights", "trace", "stat", "pie", "benchmark",
        ],
        system=_BASE_RULES + """
You are 4real's Performance Profiler. You capture frame timings and Insights traces,
diagnose whether the frame is CPU- or GPU-bound, and run PIE tests. Report findings
with numbers and a concrete next action; you measure and advise, you don't blindly edit.
""",
    ),
    Specialist(
        key="level-builder",
        label="Level Builder",
        blurb="Level actors, transforms, viewport control, asset discovery/management.",
        tool_patterns=[
            "actor", "level", "viewport", "asset", "spawn", "transform", "place",
        ],
        system=_BASE_RULES + """
You are 4real's Level Builder. You place and arrange level actors, drive the viewport,
and discover/manage assets. Keep the scene organized (folders, naming, transforms).
""",
    ),
]


ROSTER_BY_KEY = {s.key: s for s in ROSTER}


def roster_table() -> str:
    """Human-readable listing of the fleet."""
    width = max(len(s.label) for s in ROSTER)
    lines = [f"{s.label.ljust(width)}  {s.blurb}" for s in ROSTER]
    return "\n".join(lines)
