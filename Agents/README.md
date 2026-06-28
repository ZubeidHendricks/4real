# 4real Agents

**Our own AI agents** for driving the Unreal Engine editor.

VibeUE (and most MCP editor toolkits) rely on an *external* agent — Claude Code, Cursor,
Copilot — to be the brain. **4real ships its own.** This package is a multi-agent
runtime: a roster of Unreal-domain specialists powered by **Claude Opus 4.8**, each
wired to the 4real MCP tool surface, coordinated by a lead orchestrator that turns a
natural-language goal into editor actions.

```
  you ──goal──▶ Orchestrator ──plans──▶ [ Specialist ]──tool calls──▶ MCP ──▶ Unreal editor
                (Opus 4.8)              (Opus 4.8 ×N)                  (4real plugin)
```

## The fleet

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

Each specialist only sees the slice of the tool surface relevant to its domain, which
keeps it focused. Personas are derived from the 4real skill packs in `../Content/Skills/`.

## Quick start

```bash
cd Agents
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Inspect the fleet — no API key, no Unreal needed
python -m fourreal_agents --list-agents
python -m fourreal_agents --list-tools        # uses the mock editor

# 2) Run the fleet end-to-end in mock mode (needs an Anthropic API key)
export ANTHROPIC_API_KEY=sk-ant-...
python -m fourreal_agents "Block out a foggy forest arena and add a HUD health bar"

# 3) Drive one specialist directly
python -m fourreal_agents --agent profiler "Are we CPU- or GPU-bound this frame?"
```

`--mock` is the default transport: an in-process fake editor so you can develop the
agent loop on any machine (e.g. a Mac with no Unreal install).

## Connecting to a real Unreal editor

Once the 4real plugin is built into a UE 5.8+ project and Unreal's native MCP server is
running, point the fleet at it:

```bash
# streamable-HTTP / SSE endpoint exposed by Unreal's MCP server
python -m fourreal_agents --transport http --url http://127.0.0.1:30010/mcp "..."

# or spawn a local stdio MCP server
python -m fourreal_agents --transport stdio --mcp-command "python -m your_mcp_server" "..."
```

The agents discover the editor's real tools via MCP `list_tools` and filter them per
specialist automatically — no per-tool wiring needed when the plugin adds new tools.

## Configuration

Environment variables (all optional):

| Var | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required to actually run agents |
| `4REAL_MODEL` | `claude-opus-4-8` | Model for specialists |
| `4REAL_EFFORT` | `high` | Reasoning effort (`low`…`max`) |
| `4REAL_MCP_TRANSPORT` | `mock` | `mock` \| `http` \| `stdio` |
| `4REAL_MCP_URL` | `http://127.0.0.1:30010/mcp` | http endpoint |
| `4REAL_MCP_COMMAND` | — | stdio server command |

## Design notes

- **Opus 4.8 + adaptive thinking** throughout; the manual tool-use loop preserves
  thinking blocks across turns and feeds tool results back as the conversation grows.
- **Transactions**: every specialist is always granted the editor's transaction tools so
  its edits group into a single undo step.
- **Planner uses structured output** (`output_config.format`) so the orchestrator's plan
  is a validated list of `(specialist, task)` steps, run in dependency order.
