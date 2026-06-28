// Copyright Buckley Builds LLC 2026 All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * Utility class for resolving ForReal plugin paths.
 * Works whether plugin is installed in Project/Plugins, Engine/Plugins/Marketplace, or elsewhere.
 */
class FORREAL_API FForRealPaths
{
public:
	/**
	 * Get the base directory of the ForReal plugin.
	 * Uses IPluginManager to find the actual plugin location regardless of install type.
	 * 
	 * @return Absolute path to the ForReal plugin directory, or empty string if not found
	 */
	static FString GetPluginDir();

	/**
	 * Get the Content directory of the ForReal plugin.
	 * 
	 * @return Absolute path to ForReal/Content, or empty string if not found
	 */
	static FString GetPluginContentDir();

	/**
	 * Get the Help content directory.
	 * 
	 * @return Absolute path to ForReal/Content/Help, or empty string if not found
	 */
	static FString GetHelpDir();

	/**
	 * Get the instructions content directory.
	 * 
	 * @return Absolute path to ForReal/Content/instructions, or empty string if not found
	 */
	static FString GetInstructionsDir();

	/**
	 * Get the Config directory of the ForReal plugin.
	 * 
	 * @return Absolute path to ForReal/Config, or empty string if not found
	 */
	static FString GetConfigDir();

	/**
	 * Get the ForReal Screenshots directory under Project/Saved.
	 * Creates the directory if it doesn't exist.
	 * 
	 * @return Absolute path to Project/Saved/ForReal/Screenshots
	 */
	static FString GetScreenshotsDir();

	/**
	 * Get the ForReal plugin version name (e.g. "3.0").
	 * Reads from the plugin descriptor via IPluginManager.
	 *
	 * @return Version string, or "unknown" if not found
	 */
	static FString GetPluginVersionName();

	/**
	 * Clear all files in the ForReal Screenshots directory.
	 * Called on plugin startup to save disk space.
	 */
	static void ClearScreenshotsDir();

private:
	/** Cached plugin directory path */
	static FString CachedPluginDir;
	
	/** Whether cache has been initialized */
	static bool bCacheInitialized;
};
