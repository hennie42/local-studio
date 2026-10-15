using UnrealBuildTool;

public class StudioGameTarget : TargetRules
{
	public StudioGameTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("StudioGame");
	}
}
