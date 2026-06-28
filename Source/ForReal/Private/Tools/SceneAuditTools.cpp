// Copyright Buckley Builds LLC 2026 All Rights Reserved.
//
// SceneAuditTools.cpp
// MCP tool: scene_audit — read-only diagnostics for the currently open editor level.
// Counts actors by class, totals static-mesh actors / lights / nanite vs non-nanite,
// and flags actors with missing materials. Mutates nothing.

#include "Core/ToolRegistry.h"
#include "Json.h"
#include "JsonUtilities.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LightComponentBase.h"
#include "Engine/StaticMesh.h"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static FString ExtractSceneAuditParam(const TMap<FString, FString>& Params, const FString& FieldName, const FString& Default = FString())
{
	// Direct key
	const FString* Direct = Params.Find(FieldName);
	if (Direct) return *Direct;

	// MCP server sometimes capitalizes first letter
	FString Cap = FieldName;
	if (Cap.Len() > 0) Cap[0] = FChar::ToUpper(Cap[0]);
	Direct = Params.Find(Cap);
	if (Direct) return *Direct;

	// Fallback to ParamsJson
	const FString* ParamsJsonStr = Params.Find(TEXT("ParamsJson"));
	if (ParamsJsonStr)
	{
		TSharedPtr<FJsonObject> JsonObj;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(*ParamsJsonStr);
		if (FJsonSerializer::Deserialize(Reader, JsonObj) && JsonObj.IsValid())
		{
			FString Value;
			if (JsonObj->TryGetStringField(FieldName, Value))
				return Value;
			double NumValue;
			if (JsonObj->TryGetNumberField(FieldName, NumValue))
				return FString::Printf(TEXT("%.10g"), NumValue);
		}
	}

	return Default;
}

static int32 ExtractSceneAuditInt(const TMap<FString, FString>& Params, const FString& Name, int32 Default)
{
	const FString V = ExtractSceneAuditParam(Params, Name);
	return V.IsEmpty() ? Default : FCString::Atoi(*V);
}

static FString BuildSceneAuditError(const FString& Code, const FString& Message)
{
	return FString::Printf(TEXT("{\"success\":false,\"error\":\"%s\",\"message\":\"%s\"}"), *Code, *Message);
}

// ---------------------------------------------------------------------------
// Tool registration
// ---------------------------------------------------------------------------
REGISTER_FORREAL_TOOL(scene_audit,
	"Read-only audit of the currently open level: counts actors by class, totals static-mesh actors / lights / "
	"nanite vs non-nanite, and flags actors with missing materials. Returns JSON. Mutates nothing.",
	"Diagnostics",
	TOOL_PARAMS(
		TOOL_PARAM_DEFAULT("top_n", "How many actor classes to list (most common first). Default 20.", "number", "20")
	),
	{
		const int32 TopN = FMath::Max(0, ExtractSceneAuditInt(Params, TEXT("top_n"), 20));

		// Resolve the editor world (read-only). Guard GEditor — it is null in -game/commandlet contexts.
		if (!GEditor)
			return BuildSceneAuditError(TEXT("NO_EDITOR"), TEXT("GEditor is not available; scene_audit requires the editor."));

		UWorld* World = GEditor->GetEditorWorldContext().World();
		if (!World)
			return BuildSceneAuditError(TEXT("NO_WORLD"), TEXT("No editor world is currently open."));

		int32 TotalActors            = 0;
		int32 StaticMeshActorCount   = 0;  // actors with at least one static-mesh component
		int32 StaticMeshComponents   = 0;
		int32 LightComponents        = 0;
		int32 NaniteMeshes           = 0;  // static-mesh components whose mesh has Nanite enabled
		int32 NonNaniteMeshes        = 0;

		TMap<FString, int32> ClassCounts;
		TArray<FString>      ActorsWithMissingMaterials;

		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AActor* Actor = *It;
			if (!Actor) continue;

			++TotalActors;
			ClassCounts.FindOrAdd(Actor->GetClass()->GetName()) += 1;

			bool bActorHasStaticMesh   = false;
			bool bActorMissingMaterial = false;

			TArray<UStaticMeshComponent*> MeshComps;
			Actor->GetComponents<UStaticMeshComponent>(MeshComps);
			for (const UStaticMeshComponent* MeshComp : MeshComps)
			{
				if (!MeshComp) continue;
				bActorHasStaticMesh = true;
				++StaticMeshComponents;

				if (const UStaticMesh* Mesh = MeshComp->GetStaticMesh())
				{
					if (Mesh->NaniteSettings.bEnabled)
						++NaniteMeshes;
					else
						++NonNaniteMeshes;
				}

				// Flag missing materials: any material slot that resolves to null.
				const int32 NumMats = MeshComp->GetNumMaterials();
				for (int32 MatIdx = 0; MatIdx < NumMats; ++MatIdx)
				{
					if (MeshComp->GetMaterial(MatIdx) == nullptr)
					{
						bActorMissingMaterial = true;
						break;
					}
				}
			}

			if (bActorHasStaticMesh)
				++StaticMeshActorCount;

			if (bActorMissingMaterial)
				ActorsWithMissingMaterials.Add(Actor->GetActorLabel());

			TArray<ULightComponentBase*> LightComps;
			Actor->GetComponents<ULightComponentBase>(LightComps);
			LightComponents += LightComps.Num();
		}

		// Sort the class breakdown by count (descending) and keep the top N.
		ClassCounts.ValueSort([](const int32& A, const int32& B) { return A > B; });

		TArray<TSharedPtr<FJsonValue>> ClassArray;
		int32 Emitted = 0;
		for (const TPair<FString, int32>& Pair : ClassCounts)
		{
			if (TopN > 0 && Emitted >= TopN) break;
			TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
			Entry->SetStringField(TEXT("class"), Pair.Key);
			Entry->SetNumberField(TEXT("count"), Pair.Value);
			ClassArray.Add(MakeShared<FJsonValueObject>(Entry));
			++Emitted;
		}

		TArray<TSharedPtr<FJsonValue>> MissingMatArray;
		for (const FString& Label : ActorsWithMissingMaterials)
			MissingMatArray.Add(MakeShared<FJsonValueString>(Label));

		TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
		Out->SetBoolField  (TEXT("success"),                    true);
		Out->SetStringField(TEXT("world"),                      World->GetMapName());
		Out->SetNumberField(TEXT("total_actors"),               TotalActors);
		Out->SetNumberField(TEXT("unique_actor_classes"),       ClassCounts.Num());
		Out->SetNumberField(TEXT("static_mesh_actors"),         StaticMeshActorCount);
		Out->SetNumberField(TEXT("static_mesh_components"),     StaticMeshComponents);
		Out->SetNumberField(TEXT("light_components"),           LightComponents);
		Out->SetNumberField(TEXT("nanite_meshes"),              NaniteMeshes);
		Out->SetNumberField(TEXT("non_nanite_meshes"),          NonNaniteMeshes);
		Out->SetNumberField(TEXT("actors_with_missing_materials_count"), ActorsWithMissingMaterials.Num());
		Out->SetArrayField (TEXT("actors_with_missing_materials"), MissingMatArray);
		Out->SetArrayField (TEXT("actor_class_counts"),         ClassArray);

		FString OutStr;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutStr);
		FJsonSerializer::Serialize(Out, Writer);
		return OutStr;
	}
);
