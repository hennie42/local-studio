# Unreal Engine

Unreal Engine 5 (tested: 5.8 on Linux) is for photoreal cinematics (Movie Render Queue, hardware ray tracing,
volumetrics) and C++ games where the look matters most. It is heavy: shader compiles, C++ builds and renders take
minutes, and renders need the worker GPU.

## Setup
Install Unreal yourself (Epic's Linux build), then set `STUDIO_UE_ROOT` (the folder containing `Engine/`) and
`STUDIO_UE_ADAPTER` (render GPU) in `~/.config/studio/studio.env`. `ue5` opens the editor interactively.

## Worker tools (broker actions)
`studio ue-python X.uproject Scripts/x.py` (headless Python: levels, sequences, materials), `ue-render` (Movie Render
Queue), `ue-build` (C++ editor target), `ue-package` (Shipping build), `ue-play ... -autopilot` (run the game),
`run-packaged` (run the packaged build). Workers use the tested helpers in `template/ue-base/Scripts/studio_ue.py`
(levels, meshes, cameras, wall panels facing a direction, sequences, camera cuts, render configs) and
`studio_audio.py` (procedural music and sound effects).

## Gotchas we handled (Linux, UE 5.8)
- Wayland: run with `SDL_VIDEODRIVER=wayland`; under some Xwayland setups Vulkan presentation only works from the GPU
  driving the display. `-sm6` enables hardware ray tracing, which also needs `r.SkinCache.CompileShaders=True`.
- `-ExecutePythonScript` quits the editor when the script returns: renders start from a startup hook
  (`Content/Python/init_unreal.py`).
- Animating a camera's focal length through a property track crashes renders: keep it fixed.
- Render asset paths must be object paths (`/Game/X.X`).
- UE forks `UnrealTraceServer`, which keeps inherited pipes open: run UE with output to files.
- C++ that compiles can still crash or do nothing: `NewObject` in constructors, timers cleared in `BeginDestroy`,
  `CastChecked` on input components, an unset `HUDClass`, actors that never tick, overlap flags on one side only,
  string-loaded assets missing from the cook. All are in the worker guide (`template/AGENTS.md`); the autopilot test
  of the packaged build is what finds the rest.
- Shipping builds compile `UE_LOG` out: test markers go through `GameEvent.h` (prints to stdout in Shipping).
