# Retro: DontPanicTrailer

11 findings, 255 minutes lost in total. Format and loop: docs/self-improvement-design.md.

## Who caught the problems

| caught by | findings | share |
|---|---|---|
| director review of data/ue_assets.json | 1 | 9% |
| director reading the frame | 1 | 9% |
| director preview | 1 | 9% |
| director run | 1 | 9% |
| timeout | 1 | 9% |
| director review | 1 | 9% |
| director animatic review + probe_still.py | 1 | 9% |
| user | 1 | 9% |
| director contact sheet | 1 | 9% |
| exit code + director test run | 1 | 9% |
| director contact sheet + per-cut consistency check (|f(s)-f(s+1)| vs |f(s+1)-f(s+2)|) | 1 | 9% |

**Escape rate: 9%** (1 of 11 found by the user, no check caught them). Lower is better; compare with the next project.

## Causes

| cause | findings | minutes | by the user | examples |
|---|---|---|---|---|
| tooling | 6 | 120 | 1 | lookdev stills rendered pure black; Water plugin ocean (WaterZone + WaterBodyOcean) renders nothing in headless MRQ renders |
| worker | 4 | 120 | 0 | L2 follow-up: worker changed the import but never ran it (AssetImportTask has no override_pipelines) and stopped after 18 min to ask permission; env vars don't reach UE through the studio broker; H4 (animation import) timed out at 40 min; the script worked but the worker kept writing scratch probe scripts (11 files) instead of finishing |
| spec | 1 | 15 | 0 | UE glTF import split multi-part models into separate meshes (ship-wreck 16 StaticMeshes, KayKit characters 7-9 SkeletalMeshes); Skeleton_Rogue classified static |

## Guards

### In place (11)

- **agents-md**: AGENTS.md working rules: never stop to ask; env vars don't pass the broker (F4)
- **checklist**: skill ticket checklist: split image layout (renderer, then compositor) (F6)
- **checklist**: pass config to Pool workers explicitly or use the fork context (Python 3.14) (F9)
- **checklist**: skill ticket checklist: split audio (arrangement with the director's test, then sync) (F10)
- **helper**: template studio_ue.import_file: one combined mesh per file (tested) (F1)
- **helper**: template studio_ue.post_process: physical camera exposure off (tested); AGENTS.md + skill section 5 (F2)
- **routing**: skill ticket checklist: probed UE names in the ticket, 20 min cap; AGENTS.md: scratch in .studio/scratch (F5)
- **skill**: AGENTS.md Rendering + skill section 5: sea as a shader plane (F3)
- **tool**: bin/studio-assets is_skinned(); template studio_ue.import_file sets used_with_skeletal_mesh (tested) (F7)
- **tool**: bin/studio-assets sync: warns and exits 1 when mirrored models lack thumbnails (F8)
- **tool**: bin/studio-cutcheck (tested on a synthetic ghost); AGENTS.md + skill section 5: chunks start a frame early (F11)


## Lessons (director)

- **Local workers on Unreal work:** 7 worker steps; first-try passes 3 (L1 hex maths, L3 island, plus H4 whose
  script worked though the run timed out); the director finished or rewrote 4 (L2 import, C1 cards, the score
  draft, and the H4 cleanup). Pure Python with exact numbers in the ticket went well; open-ended Unreal API work
  and long layout/audio tickets did not. Routing stays Gemma-first, with the new ticket rules (probed names,
  20 min cap, split tickets).
- **Most lost time was tooling** (120 of 255 min): the asset checker breaking rigged models, the Water plugin,
  physical exposure, chunked-render ghosting. All are now fixed in the tools or the template, so the next Unreal
  project starts without them.
- **The user's eye caught what checks missed** only once (the missing KayKit previews); everything else was caught by
  director renders and contact sheets. Per-cut consistency checks now cover the one class that sheets missed.
