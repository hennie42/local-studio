# Asset library (`studio-assets`)

The studio's local library of **CC0** assets: 3D models, PBR materials and textures, HDRIs, 2D sprites/tilesets/UI
and sound effects. After a brief is approved, the director (Claude) proposes sets that fit it, you say yes or no on
a local review page, and approved assets are copied into the project, checked and ready. Local workers then place
assets instead of modelling them (they are good at the first and bad at the second). The design and its reasons:
[assets-design.md](assets-design.md).

## Sources

| source | what | how | licence check |
|---|---|---|---|
| Kenney | ~220 packs: low-poly 3D kits (GLB), 2D, UI, audio, textures | packs mirrored (only GLB/PNG/OGG kept, ~1 GB), every file indexed | each pack's `License.txt` must say CC0 |
| KayKit | low-poly 3D kits (free tier) | **you download the free zips once** into `inbox/kaykit/` (see below); sync mirrors and indexes them | pack page must say CC0 |
| Poly Haven | ~520 photoreal models, ~870 textures, ~1,000 HDRIs | API index; files downloaded when first approved, cached | all CC0 |
| ambientCG | ~2,000 PBR materials, ~430 HDRIs | API index; zips downloaded when first approved, cached | all CC0 |

Not used: Quaternius (licence changed in 2026), Fab/Megascans, Sonniss, mixed-licence OpenGameArt/itch packs.
Later: Freesound (CC0 filter, needs OAuth2), Sketchfab/Poly Pizza (CC0 filter).

**KayKit by hand:** itch.io's robots.txt forbids automated downloads, so the studio does not script them. For each
pack, open its page (sync prints the missing ones), click *Download Now*, choose *No thanks, just take me to the
downloads*, download the **Free** zip into `$STUDIO_ASSET_HOME/inbox/kaykit/`, then run `studio-assets sync kaykit`.
A newer zip in the inbox replaces the mirrored version.

## Commands

```sh
studio-assets sync [kenney kaykit polyhaven ambientcg] [--no-thumbs]   # weekly via studio-assets-sync.timer
studio-assets search tree pine --kind model [--source kenney] [--style "low-poly"] [-n 40] [--json]
studio-assets show <id>                 # licence, size, page, files; for a pack id: all its files
studio-assets stats
studio-assets taste                     # recent yes/no decisions; the director reads them before proposing
studio-assets style <project> [--lock "Kenney low-poly" | --unlock] [--allow "KayKit low-poly"] [--res 1k|2k|4k]
studio-assets propose <project> proposal.json
studio-assets review <project>          # opens http://127.0.0.1:<port>/ and waits for your decisions
studio-assets fetch <project> [--res 2k]
studio-assets check <project> [--fix]
```

Ids: `kenney:<pack>/<path in pack>`, `kaykit:<pack>/<path>`, `polyhaven:<key>`, `ambientcg:<AssetId>`; packs are
`kenney:<pack>`. Kinds: model, material, texture, hdri, sprite, tileset, ui, sound, pack.

## The asset pass (director)

1. `studio-assets taste` and `studio-assets style <project>` (style lock, resolution).
2. Per need, search and look at thumbnails, then write a proposal:

```json
{"brief": "one line from BRIEF.md",
 "needs": [
  {"id": "street-props", "why": "the street needs clutter",
   "sets": [
    {"id": "A", "why": "Kenney road kit, matches the low-poly brief", "items": [
       {"id": "kenney:city-kit-roads/Models/GLB format/construction-cone.glb", "height_m": [0.6, 0.8]},
       "kenney:city-kit-roads/Models/GLB format/construction-barrier.glb",
       {"id": "kenney:city-kit-roads/Models/GLB format/dumpster.glb", "decorative": true}]},
    {"id": "B", "why": "photoreal alternative", "items": ["polyhaven:Barrel_01"]}],
   "gaps": ["no hover-car in any CC0 source: propose a TRELLIS.2 generation from a concept image"]}],
 "gaps": []}
```

   Rules the validator enforces: every id exists and is CC0; at most a main set and one alternative per need;
   the alternative should be another style; once a project has a **style lock**, visual sets must match it unless
   the proposal says `"lift_lock": true` (only when you asked for it). Item options: `height_m` [min, max] (scale
   check), `origin` (`bottom-centre` default, or `keep`), `decorative` (no collision), `collision` (`box`/`convex`).
3. `studio-assets propose`, then `studio-assets review` (runs until you save). On the page: one card per need,
   thumbnails, measured size and triangles of 3D models, play buttons for sounds, a veto per item, a set or
   *none* per need, and a reason (remembered in `taste.json`). The first approved visual set sets the style lock;
   you can lift or change it there.
4. `studio-assets fetch`, then `studio-assets check --fix`.

## What lands in the project

```
assets/<source>/<pack>/...        the files (git LFS: .gitattributes is written, `git lfs install --local` run)
assets/ASSETS.json                per asset: source, page URL, licence as checked + date, need, sha256 per file, fixes
assets/proposals/*.json           proposals with their decisions
assets/style.json                 style lock, default resolution (2k; 1k suits low-poly, 4k only for close-ups)
assets/collision.json             Godot: res:// path -> box | convex | none
addons/studio_assets/collision_import.gd   Godot post-import script (adds StaticBody3D + shape per mesh)
CREDITS.md                        generated (credit is a courtesy for CC0; Poly Haven asks for it)
```

`check` measures every model (size in metres, origin, triangles) in Blender. Out-of-range sizes (against
`height_m`) and off-centre origins are fixed by a generated Blender step on the project's copy (the scale is baked
into the mesh), recorded under `fixes` in ASSETS.json; never by hand in a worker step. **Kenney kits are in kit
units, not metres** (a traffic cone is 0.09 tall): give `height_m` whenever real size matters. In Godot projects
`check` also writes each model's `.import` with the post-import script, so collisions are generated on import:
convex by default, a box on request, none for decorative items. Reimport with `godot --headless --path <project> --import`.
Godot projects are then imported and every model is measured again in Godot, instanced as the game loads it
(`lib/godot/studio_measure.gd`, stored as `measured_godot`). Models that are never fixed (`origin: keep`, rigged or
animated files) get a WARNING when their origin lies outside the mesh: placed as is, they float beside their spot
(the Don't Panic Island alien sat 2 m off its UFO). Offset the instance in the engine, or approve them with
`bottom-centre`.

## Library layout (`STUDIO_ASSET_HOME`, default ~/StudioProjects/assets)

`index.db` (SQLite + FTS5), `mirror/<source>/<pack>/`, `cache/<source>/<id>/<res>/`, `thumbs/`, `inbox/kaykit/`,
`taste.json`, `sync.log`. Downloaded assets never go into the studio repo. Workers see only their project's
`assets/`; they never search the library or the network.

## Notes

- Sync is polite: one request per second to kenney.nl, slower to itch.io, a unique User-Agent everywhere. It
  removes index rows a source no longer offers (withdrawn assets, licence changes). Projects keep what they
  fetched, with the licence recorded at fetch time.
- Heavy work (Blender thumbnail batches) runs under the timer's `MemoryMax=12G`; run big manual syncs in a scope
  too: `systemd-run --user --scope -p MemoryMax=12G studio-assets sync`.
- AI 3D generation (TRELLIS.2, evals/scorecard-gen3d.md) is the gap filler for missing props; generated
  assets go through the same review.
