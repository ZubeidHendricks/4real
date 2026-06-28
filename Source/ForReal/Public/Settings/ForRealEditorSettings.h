// Copyright Buckley Builds LLC 2026 All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "ForRealEditorSettings.generated.h"

// ForReal editor settings.
//
// Surfaced under Editor Preferences > Plugins > ForReal. Stored as a per-machine user setting
// (globaluserconfig) so the key is entered once and shared across all projects, and never
// committed to source control. globaluserconfig also suppresses the panel's Set-as-Default /
// Reset-to-Defaults buttons. Read it from C++ with: GetDefault<UForRealEditorSettings>()->ApiKey
UCLASS(config = EditorSettings, globaluserconfig, meta = (DisplayName = "ForReal"))
class FORREAL_API UForRealEditorSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	/** Free ForReal API key (forreal.com/login). Used by the terrain_data tool. */
	UPROPERTY(config, EditAnywhere, Category = "API", meta = (DisplayName = "API Key", PasswordField = true))
	FString ApiKey;

	//~ Place the settings panel under Editor Preferences > Plugins > ForReal
	virtual FName GetContainerName() const override { return TEXT("Editor"); }
	virtual FName GetCategoryName() const override { return TEXT("Plugins"); }
	virtual FName GetSectionName() const override { return TEXT("ForReal"); }
};
