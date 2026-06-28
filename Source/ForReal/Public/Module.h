// Copyright Buckley Builds LLC 2026 All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FModule : public IModuleInterface
{
public:
	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	/** Called before engine exit to cleanup Python references */
	void OnPreExit();

	/** Register ForReal service toolsets with UE 5.8's ToolsetRegistry (exposes them on Epic's MCP endpoint) */
	void RegisterToolsets();
	/** Unregister ForReal service toolsets */
	void UnregisterToolsets();

	static inline FModule& Get()
	{
		return FModuleManager::LoadModuleChecked<FModule>("ForReal");
	}

	static inline bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded("ForReal");
	}

private:
	// False when running as a commandlet (cook, etc.) — services are skipped to
	// avoid keeping UnrealEditor-Cmd.exe alive after the commandlet finishes.
	bool bServicesInitialized = false;
}; 
