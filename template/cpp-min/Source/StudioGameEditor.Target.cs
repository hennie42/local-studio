using UnrealBuildTool;

public class StudioGameEditorTarget : TargetRules
{
	public StudioGameEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("StudioGame");
	}
}
