<div align="center">

# 4real — AI-Powered Unreal Engine Development

### 🧩 MCP Expansion + AI Editor Toolset for Unreal Engine 5.8+

**[zubeidhendricks.github.io/4real](https://zubeidhendricks.github.io/4real/)**

[![Website](https://img.shields.io/badge/Website-4real-ff5e5b)](https://zubeidhendricks.github.io/4real/)
[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-5.8%2B-orange)](https://www.unrealengine.com)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

**4real is the MCP Expansion + AI Editor Toolset for Unreal Engine 5.8+.** Unreal 5.8 added a
built-in MCP server and AI toolsets; 4real is an **MCP Expansion** that plugs straight into them and
adds a deep **AI Editor Toolset** — a library of editor capabilities — Blueprints, materials, landscape, foliage, animation, Niagara, UMG, audio, StateTree,
gameplay tags, input, UVs, **performance/profiling**, and more — registered into the engine's own
`ToolsetRegistry` and `ModelContextProtocol` server, plus rich domain **skills** served through
Unreal's native `AgentSkill` system. Any MCP-capable agent (Claude Code, Cursor, Copilot, …) drives
your editor through Unreal's standard MCP endpoint — **or 4real's own AI agents do** (see below).

> 🤖 **4real ships its own AI agents.** Unlike toolkits that depend on an external IDE agent, 4real
> includes a multi-agent fleet — a roster of Unreal-domain specialists powered by Claude Opus 4.8,
> coordinated by a lead orchestrator — that turns a natural-language goal into editor actions over MCP.
> See [**🤖 4real's own AI agents**](#-4reals-own-ai-agents) below and [`Agents/`](Agents/README.md).

> ⚠️ **4real requires Unreal's native MCP to be set up first** — enable the **Unreal MCP** plugin
> (which auto-enables **Toolset Registry**) and the **Editor Tools** plugin, then start the MCP server.
> Follow Epic's guide: **[Unreal MCP in the Unreal Editor](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)**.
> 4real then expands that endpoint — **no separate server and no in-editor chat.** A free API key
> (set in **Editor Preferences → Plugins → 4real**) unlocks the real-world **terrain** tools; everything
> else works without one.

---

## ✨ What 4real adds

Unreal 5.8 ships its own AI toolsets (Blueprints, materials, actors, assets, meshes, data tables, …).
4real **complements** them — it focuses on the domains and depth the engine doesn't cover:

- **Terrain & world** — Landscape sculpting/heightmaps/splines, landscape auto-materials + RVT,
  Foliage, procedural FPS **Map Blockout**, and **real-world terrain** (heightmaps + water from GPS).
- **Audio** — MetaSound and SoundCue graph authoring.
- **Animation assets** — AnimSequence keyframe editing, AnimMontage authoring, AnimBP state machines,
  Skeleton bone/socket/retarget/blend-profile editing.
- **FX depth** — Niagara emitter color/curve authoring and **Custom-HLSL scratch-pad** modules.
- **UI** — UMG widgets with MVVM bindings, animation authoring, and preview/PIE validation.
- **Higher-order Blueprint authoring** — timelines, event dispatchers, delegates, custom-event pins,
  comment boxes, and a batch `build_graph` builder.
- **Editor safety** — `TransactionService` wraps the editor's transaction buffer (undo / redo /
  checkpoints) so an agent can group and roll back its own edits — the engine's toolsets expose none.
- **⚡ Performance & profiling** — 4real's standout: see the dedicated section below.
- **Scene audit** — a read-only `scene_audit` tool returns actor/class counts, static-mesh & light
  totals, Nanite vs non-Nanite, and missing-material flags as JSON — a cheap, structured snapshot agents
  use to ground themselves without spending context exploring the level.
- **Python-first access** — run any `unreal.*` Python in the editor and introspect the whole API.
- **Web research** — search / fetch / geocode for in-context research and terrain workflows.

It deliberately **does not duplicate** the engine's general tools (basic asset/actor/blueprint/material
CRUD, screenshots, logs, PIE) — agents use Unreal's native toolsets for those.

---

## 🤖 4real's own AI agents

Most MCP editor toolkits are *hands without a brain* — they wait for an external agent (Claude Code,
Cursor, …) to drive them. **4real brings its own brain.** [`Agents/`](Agents/README.md) is a
multi-agent runtime: a roster of Unreal-domain specialists on **Claude Opus 4.8**, each wired to the
slice of the MCP tool surface it needs, coordinated by a lead orchestrator that turns a
natural-language goal into ordered editor actions.

```
  you ──goal──▶ Orchestrator ──plans──▶ [ Specialist ]──tool calls──▶ MCP ──▶ Unreal editor
                (Opus 4.8)              (Opus 4.8 ×N)                  (4real plugin)
```

| Specialist | Does |
|---|---|
| Terrain Architect | Landscapes, heightmaps, foliage, real-world/GPS terrain, PCG, map blockout |
| UI Builder | UMG widgets + MVVM view-model bindings |
| FX & Audio Artist | Niagara (incl. HLSL scratch pads), MetaSound, SoundCue |
| Animator | AnimSequence keyframes, AnimBP state machines, montages, skeletons |
| Blueprint Engineer | Blueprint graphs, enums/structs, data tables/assets, gameplay tags, input, State Trees |
| Material Artist | Materials, material graphs, landscape materials, UV mapping |
| Performance Profiler | Frame timing, CPU/GPU-bound diagnosis, Insights traces, PIE testing |
| Level Builder | Level actors, transforms, viewport, asset discovery/management |

```bash
cd Agents && pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python -m fourreal_agents "Block out a foggy forest arena and add a HUD health bar"
python -m fourreal_agents --agent profiler "Are we CPU- or GPU-bound this frame?"
python -m fourreal_agents --list-agents          # no API key / no Unreal needed
```

Point it at a live editor with `--transport http --url http://127.0.0.1:8000/mcp`; agents discover the
editor's real tools via MCP `list_tools` and filter them per specialist automatically.

**Built to resist context rot.** A long tool-calling loop normally bloats and degrades the model's
working set. The fleet defends with: per-specialist fresh conversations, a persistent markdown
scratchpad (`memory_note`/`memory_recall`) so agents offload state instead of carrying it, compact
step-to-step handoffs (digests, not transcripts), server-side context editing that prunes stale tool
results, tool-result capping, prompt caching of the stable prefix, and an optional fresh-context
verifier (`--verify`) that re-checks each step and retries gaps. Full details in
[`Agents/README.md`](Agents/README.md).

---

## ⚡ Performance & Profiling (flagship)

**Unreal's native AI toolsets have *zero* performance tooling** — they can start PIE/Simulate but can't
measure anything. 4real's `PerformanceService` fills that gap so an agent can actually *diagnose and
fix* frame rate:

- **`frame_timing()`** — Game/Render/GPU/RHI thread split + a **CPU-vs-GPU-bound verdict** and a
  concrete next-step hint. *Run this first* — optimising the GPU does nothing on a CPU-bound frame.
- **Unreal Insights capture** — `start_trace` / `stop_trace` / `get_trace_status`, with `bookmark`
  and `region_start` / `region_end` markers.
- **`analyse()`** — reads the trace **and** log back and returns a perf summary (frame stats, worst
  frames, hitches, notable log lines).
- **Trace-attached `start_standalone`** — profile a representative standalone build, not just the
  editor viewport.

```python
import unreal
print(unreal.PerformanceService.frame_timing())   # CPU vs GPU bound — diagnose FIRST
unreal.PerformanceService.start_trace("cap", "")   # Insights trace
# … reproduce the workload (ideally under PIE / standalone) …
unreal.PerformanceService.stop_trace()
print(unreal.PerformanceService.analyse("both", ""))
```

Pair with the `profiling` and `frame-rate` skills for the full CPU/GPU drill-down.

---

## 🏗️ Architecture

4real plugs into three native UE 5.8+ systems:

1. **Toolsets** (`ToolsetRegistry`) — 4real's services register as `UToolsetDefinition`s, so their
   methods become AICallable tools on the MCP endpoint. They're also `BlueprintCallable`, so the same
   methods are callable from Python as `unreal.<Name>Service.<method>()`.
2. **MCP server** (`ModelContextProtocol`) — a small set of 4real utility tools are registered
   directly on the endpoint: `execute_python_code`, `discover_python_module`/`_class`/`_function`,
   `list_python_subsystems`, `deep_research`, `terrain_data`.
3. **Skills** (`AgentSkillToolset`) — ~34 markdown skill packs register as native `UAgentSkill`s,
   discoverable via `ListSkills` and loaded lazily via `GetSkills`, alongside the engine's own skills.

**Efficient usage (for agents):** `execute_python_code` is the workhorse — it batches a whole
multi-step task into one round-trip and reaches every 4real service plus the full `unreal.*` API. Use
`call_tool` only for skills and the few engine toolsets with no Python path (screenshots, etc.). See
[`Content/samples/AGENTS.md.sample`](Content/samples/AGENTS.md.sample) for the full agent guide.

---

## 🚀 Installation & setup

**Requirements:** Unreal Engine **5.8+** · Git

### Step 1 — Set up Unreal's native MCP (do this FIRST)

4real is an **expansion** of Unreal's built-in MCP support, so enable that first. Full details in
Epic's guide: **[Unreal MCP in the Unreal Editor](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)**.

1. **Edit → Plugins** → enable **Unreal MCP** (this auto-enables **Toolset Registry**) and **Editor
   Tools** (the engine's own AI toolsets, so agents get both). These are Experimental. Restart when prompted.
2. **Edit → Editor Preferences → General → Model Context Protocol** → enable **Auto Start Server**
   (or run the console command `ModelContextProtocol.StartServer`). Default endpoint
   `http://127.0.0.1:8000/mcp` (port/path configurable). Enabling **Tool Search** keeps an agent's
   context small — it sees `list_toolsets` / `describe_toolset` / `call_tool` and loads tools on demand.

### Step 2 — Install 4real

```bash
cd /path/to/YourProject/Plugins
git clone https://github.com/ZubeidHendricks/4real.git ForReal
```
Build with the project script (don't run `Build.bat` directly):
```
Plugins/ForReal/BuildAndLaunchGame.ps1                  # builds + launches the editor
Plugins/ForReal/BuildAndLaunchGame.ps1 -StrictRebuild   # full recompile (warnings-as-errors)
```
Then **Edit → Plugins** → enable **4real** and restart. Its services, tools, and skills now register
onto the same endpoint, alongside the engine's own.

### Step 3 — Connect your agent

Two console commands from the editor (open the console with `` ` ``):

**1. Write the MCP server config** (`.mcp.json` at the project root):
```
ModelContextProtocol.GenerateClientConfig ClaudeCode
```
(supports `ClaudeCode`, `Cursor`, `VSCode`, `Gemini`, `Codex`, or `All`.)

**2. Write 4real's agent guide** so the assistant uses the efficient patterns:
```
4real.GenerateAgentConfig ClaudeCode
```
This writes the guide to the correct file for your agent — `CLAUDE.md` (Claude Code), `GEMINI.md`
(Gemini), `AGENTS.md` (Codex / Cursor), or `.github/copilot-instructions.md` (Copilot) — or pass
`All` to write CLAUDE.md + GEMINI.md + AGENTS.md at once. It resolves the plugin location
automatically, so it works whether 4real was installed from **FAB** or **Git**. The guide goes in a
managed block, so re-run any time to refresh without disturbing your own notes. Pass `import` to link
the guide with a one-line `@import` instead of copying it (Claude Code / Gemini only — other agents
don't resolve imports, so they always get a copy).

> The MCP server is loopback-only with no authentication — same-machine use only (per Epic's docs).

The guide teaches: discover before you call (`discover_python_class`), batch with `execute_python_code`,
load skills via `ListSkills`/`GetSkills`, and when to reach for `deep_research` / `terrain_data`.

---

## 🎯 Skills

Skills are lazy-loaded domain knowledge (workflows, gotchas, property formats) served by Unreal's
native `AgentSkillToolset`:

```
# discover (summaries only — cheap)
call_tool(tool_name="ListSkills", toolset_name="ToolsetRegistry.AgentSkillToolset")

# load the packs you need (full markdown, lazy)
call_tool(tool_name="GetSkills", toolset_name="ToolsetRegistry.AgentSkillToolset",
          arguments={"skillPaths": ["/4real/Python/init_unreal_PY.4real_blueprints"]})
```

`ListSkills` is the **live source of truth** for what's available (it reads each pack's `SKILL.md`).
Skills tell you *what* to do and *why*; use `discover_python_class('unreal.<Name>Service', method_filter='…')`
for exact signatures before writing code.

---

## 🔧 Plugin dependencies

**Native engine prerequisites (enable in Step 1 — Epic's MCP stack):**

| Plugin | Purpose |
|--------|---------|
| **Unreal MCP** (`ModelContextProtocol`) | The native MCP server endpoint |
| **Toolset Registry** (`ToolsetRegistry`) | Native AI toolset + `AgentSkill` registration (auto-enabled by Unreal MCP) |
| **Editor Tools** (`EditorToolset`) | The engine's own AI toolsets — 4real complements these |

**Enabled automatically by 4real:** `PythonScriptPlugin` (the `unreal.*` API),
`EditorScriptingUtilities`, and the domain plugins its services need — `Niagara`, `MetaSound`,
`EnhancedInput`, `ModelViewViewModel`, `StateTree`, `MeshModelingToolset`,
`GameplayTagsEditor`. (4real also depends on
`ToolsetRegistry` + `ModelContextProtocol`, so enabling 4real pulls them in — but you still enable
**Editor Tools** and start the server per Step 1.)

---

## 🛠️ Build & launch script

`BuildAndLaunchGame.ps1` (project root or `Plugins/ForReal/`) stops the running editor, builds, and
relaunches:
- `-StrictRebuild` — full plugin recompile under warnings-as-errors
- `-Clean` — wipe intermediate/binaries first
- `-SkipBuild` — relaunch only

---

## 📚 The live API

4real intentionally keeps **no static method catalog** in this README — the surface evolves with the
engine. The authoritative, always-current references are:
- **`ListSkills`** → which domains exist and when to use them.
- **`discover_python_class('unreal.<Name>Service')`** → exact method signatures.
- **`describe_toolset('4real.<Name>Service')`** → the toolset's tools + JSON schemas (token-heavy;
  prefer skills + discovery).

---

## Credits

4real is a fork of **[VibeUE](https://github.com/kevinpbuckley/VibeUE)** by Kevin Buckley /
Buckley Builds LLC (MIT), extended with its own multi-agent runtime, context-rot hardening, and
additional editor tools. The original copyright is retained in [LICENSE](LICENSE).

## License

MIT — see [LICENSE](LICENSE). Project home: https://zubeidhendricks.github.io/4real/
