"""UE C++: add a gameplay actor class that compiles."""
import re
import _ue

AREA = "ue"
TITLE = "UE C++: AHoverActor (sine bob + spin) that compiles"
KIND = "agent"
TIMEOUT = 2400

PROMPT = """This is an Unreal Engine 5.8 C++ project (StudioGame.uproject, module StudioGame in
Source/StudioGame). Read AGENTS.md first. Add a new actor class AHoverActor
(Source/StudioGame/HoverActor.h and HoverActor.cpp) that:
- has a UStaticMeshComponent named Mesh as the root component (created in the constructor);
- has UPROPERTY(EditAnywhere, BlueprintReadWrite) floats Amplitude (cm, default 50),
  Frequency (Hz, default 0.5) and SpinDegreesPerSecond (default 45);
- remembers its start location in BeginPlay;
- in Tick sets its Z to StartZ + Amplitude * sin(2*pi*Frequency*time since BeginPlay) and spins
  around the vertical axis at SpinDegreesPerSecond.
Ticking must be enabled. Build with `studio ue-build StudioGame.uproject` and fix all compile errors
until the build succeeds. Do not modify SpinActor."""


def setup(ws):
    _ue.setup_project(ws, cpp=True)


def grade(ws):
    up = ws / "StudioGame.uproject"
    h, cpp = ws / "Source/StudioGame/HoverActor.h", ws / "Source/StudioGame/HoverActor.cpp"
    if not (h.exists() and cpp.exists()):
        return {"score": 0.0, "passed": False, "notes": "HoverActor.h/.cpp missing"}
    built, errors = _ue.build_cpp(ws, up)
    src_h, src_c = h.read_text(), cpp.read_text()
    both = src_h + src_c
    checks = {
        "uclass": bool(re.search(r"UCLASS\s*\(", src_h)) and "AHoverActor" in src_h and "HoverActor.generated.h" in src_h,
        "props": all(re.search(rf"UPROPERTY\([^)]*EditAnywhere[^)]*\)\s*float\s+{p}\b", src_h) for p in ("Amplitude", "Frequency", "SpinDegreesPerSecond")),
        "defaults": bool(re.search(r"Amplitude\s*(=|\{)\s*50", both)) and bool(re.search(r"Frequency\s*(=|\{)\s*0?\.5", both)) and bool(re.search(r"SpinDegreesPerSecond\s*(=|\{)\s*45", both)),
        "mesh_root": "UStaticMeshComponent" in src_h and re.search(r"RootComponent\s*=\s*Mesh|SetRootComponent\(\s*Mesh", src_c) is not None,
        "tick_enabled": "bCanEverTick = true" in src_c,
        "beginplay": "BeginPlay" in src_c and "Super::BeginPlay" in src_c,
        "sine": re.search(r"FMath::Sin|sinf?\s*\(|FMath::Sin\(", src_c) is not None and ("PI" in src_c or "3.14" in src_c or "TWO_PI" in src_c),
        "spin": re.search(r"AddActorLocalRotation|AddActorWorldRotation|SetActorRotation", src_c) is not None,
        "spin_actor_untouched": "DegreesPerSecond = 90.f" in (ws / "Source/StudioGame/SpinActor.h").read_text(),
    }
    static = sum(checks.values()) / len(checks)
    score = 0.6 * built + 0.4 * static
    failed = [k for k, v in checks.items() if not v]
    return {"score": round(score, 3), "passed": built and not failed,
            "notes": f"build {'OK' if built else 'FAILED ' + ' | '.join(e[:100] for e in errors[:2])}"
                     + (f"; missing: {', '.join(failed)}" if failed else "")}
