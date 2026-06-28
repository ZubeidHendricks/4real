// Copyright Buckley Builds LLC 2026 All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * Bridges ForReal's dynamic FToolRegistry tools (registered via REGISTER_FORREAL_TOOL) onto
 * UE 5.8's native ModelContextProtocol server, so they appear as ordinary MCP tools on Epic's
 * endpoint. ForReal no longer runs its own MCP server — Epic's is the single endpoint.
 */
namespace ForRealMCPToolBridge
{
	/** Wrap every non-internal ForReal tool as an IModelContextProtocolTool and AddTool() it to Epic's MCP module. */
	FORREAL_API void RegisterAll();

	/** Remove the tools registered by RegisterAll(). */
	FORREAL_API void UnregisterAll();
}
