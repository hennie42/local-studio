# Asset library: design

**Status: v1 built** (user guide: [assets.md](assets.md)). Decided in a `/grill-me` interview.
Deviations from the design below: KayKit zips are downloaded by hand into an inbox (itch.io's
robots.txt forbids automated downloads); Kenney + KayKit measured ~1 GB, so both are mirrored per file.

**Goal:** after a brief is approved, the director proposes free assets that fit it; the user says yes or no per set;
approved assets land in the project, checked and ready, so workers place assets instead of modelling them. Local
workers are good at placing things and bad at modelling them (see [models](models.md): the spaceship that failed).

## Decisions

| topic | decision |
|---|---|
| Licenses | **CC0 only.** CC-BY with a generated `CREDITS.md` can become a per-project switch later. Each asset's license is checked at download time and recorded per asset: licenses change (Quaternius moved from CC0 to a no-redistribution license in 2026; packs downloaded before keep their old terms). |
| Asset types | 3D models, PBR textures/materials, HDRIs, 2D sprites/tilesets/UI, sound effects. Not music (procedural, brief-specific) or fonts (mostly OFL: decide separately). |
| Sources, v1 | **Kenney** (~220 packs: 3D as GLB, 2D, UI, audio), **KayKit** free tier (low-poly kits), **Poly Haven** (photoreal models, textures, HDRIs; public API), **ambientCG** (PBR materials, HDRIs; public API). |
| Sources, later | **Freesound** filtered to CC0 (downloading originals needs an OAuth2 login); Sketchfab and Poly Pizza filtered to CC0 as gap fillers. |
| Excluded | Quaternius (new license), Fab/Megascans (Fab license, not CC0), Sonniss GDC bundles (royalty-free but no redistribution), OpenGameArt and itch.io packs with mixed or custom licenses. |
| Library | One shared local library in `STUDIO_ASSET_HOME` (on the data disk). An index of every asset (name, tags, category, dimensions, license, thumbnail) syncs weekly. Kenney and KayKit have no API: their 3D/2D/UI packs are mirrored and indexed per file with a rendered thumbnail per model, if the total stays under ~20 GB (measured first; otherwise pack-level index only). API sources download an asset when it is first approved, then reuse it. |
| When | An **asset pass** after the brief is approved and before the task graph, plus small ad-hoc passes when a ticket needs something new. Tickets then name approved assets by path. |
| Who picks | The director (Claude), by searching the index and looking at the thumbnails. A local pre-filter only if the index gets huge. |
| Proposals | Per need ("trees for the forest"), one main **set** plus at most one alternative in a different style. Yes accepts the set; single items can be vetoed. After the first approvals the project gets a **style lock** (e.g. "Kenney low-poly, flat colours"): later proposals must match it unless the user lifts it. |
| Memory | Every yes/no, with an optional one-line reason, goes into a library-wide `taste.json`, read before every proposal. |
| Review | A local page: `studio-assets review <project>`. One card per set: why it fits the brief, thumbnails, yes/no, a veto per item, play buttons for sounds, the measured size of 3D models. Choices are saved into the project. |
| Into the project | Copied to `assets/<source>/<pack>/`, committed with git LFS. `assets/ASSETS.json` records source, URL, license as checked, date and hash per file; `CREDITS.md` is generated from it (courtesy for CC0, and Poly Haven's API asks to credit them). |
| Resolution | Textures and HDRIs at 2K by default, 1K for low-poly games, 4K only when the brief needs close-ups. |
| 3D checks | Every approved model is measured (size in metres, origin, triangles). Wrong scale or origin is fixed by a generated Blender script, never by hand in a worker step. |
| Collisions (Godot) | Generated on import: a box or convex hull, none for items marked decorative. |
| Workers | See only the approved assets in their project; never the library or the network. A ticket that needs something new is escalated to the director for an ad-hoc pass. |
| Gaps | Never filled silently: the director flags the gap and proposes an alternative (a procedural Blender model, AI 3D generation if the bake-off pays off, or changing the brief). |
| Engines | Godot first. Unreal after the Godot version has run on a real project: same library, review and manifest, only the import differs. |

## Shape (built)

- `bin/studio-assets` with `sync`, `search`, `propose`, `review`, `fetch`, `check`; one small adapter per source in
  `lib/`; `STUDIO_ASSET_HOME` in `studio.env`; the installer offers the first sync as an optional step; a weekly
  user timer like the Godot updater.
- An asset-pass section in the `/studio` skill, and a `docs/assets.md` user guide once it is built.
- Downloaded assets never go into the studio repo itself.

## Facts the design rests on (checked in 2026)

| source | access | license | notes |
|---|---|---|---|
| Poly Haven | `api.polyhaven.com`, no key, a unique User-Agent required | CC0 | thumbnails, tags, real-world dimensions; ~520 models, 870 textures, 1,000 HDRIs; the live API asks products to credit Poly Haven |
| ambientCG | `ambientcg.com/api/v2/full_json` (v3 live), no key | CC0 | preview images 64-2048 px, dimensions, zips 1K-8K; ~2,900 assets |
| Kenney | one zip per pack, no API | CC0 | preview per pack; 3D kits ship GLB, FBX, OBJ |
| KayKit | itch.io downloads, free tier | CC0 (free tier) | glTF, FBX, OBJ; ~18 packs |
| Freesound | APIv2; search works with a token, original files need OAuth2 | per sound (filter CC0) | the API terms forbid copying the database |
