MCP Expansion + AI Editor Toolset for Unreal Engine 5.8+. Plugs into UE5.8's native MCP server, ToolsetRegistry, and AgentSkill system. 


Module — 4real (Editor type), 105 C++ source files. Platform: Win64. Engine: UE 5.8+.


Prerequisites — enable Unreal's native MCP stack and start the MCP server, then point your MCP agent at the endpoint.


Dependencies — 4real declares and auto-enables every engine plugin it needs: PythonScriptPlugin, EditorScriptingUtilities, EnhancedInput, Niagara, MeshModelingToolset, ModelViewViewModel, StateTree, MetaSound, GameplayTagsEditor, ToolsetRegistry, and ModelContextProtocol.


Setup -  run console command 4real.GenerateAgentConfig [ClaudeCode|Gemini|Codex|Cursor|Copilot|All] to write the agent guide to the matching project file (CLAUDE.md, GEMINI.md, AGENTS.md, .github/copilot-instructions.md). 


A free API  key (4real.dev/login), set in Editor Preferences → Plugins → 4real, unlocks the real-world terrain tools; every other feature works without it.


Docs: https://4real.dev/v5-8