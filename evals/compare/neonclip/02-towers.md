Read AGENTS.md and PLAN.md first (this is step "towers" of PLAN.md).

Write Scripts/make_towers.py, a Blender Python script (run headless with
`studio blender Scripts/make_towers.py -- --outdir assets/models`) that builds and exports these GLB files into
the directory given after --outdir (Blender units: 1 = 1 m; UE converts to cm on import):

1. SM_Tower_01.glb ... SM_Tower_08.glb: eight different skyscraper shells, each a single mesh object, origin at the
   centre of its base, base at z = 0, height 100 m (they get scaled in Unreal), footprints between 15 x 15 m and
   40 x 30 m. Make the silhouettes distinct: straight slab, stepped setbacks (2-3 tiers), chamfered corners,
   a tower with a crown, twin-slab, cylinder-ish (12+ sides), L-shaped plan, tapered top. Add a little rooftop
   clutter as part of the same mesh (boxes for machinery, one or two thin antennas). Keep each under 2,000 triangles.
   Give every mesh UV coordinates (any sensible unwrap; the facade material uses world-aligned projection).
2. SM_Pyramid.glb: a giant stepped pyramid ("arcology"): base 400 x 400 m, height 150 m, 6-8 terraces, flat top,
   plus 4 thin chimney cylinders (radius 3 m) at exactly (x, y) = (+110, +110), (+110, -110), (-110, +110),
   (-110, -110) m, each rising from the terrace surface at that spot up to a top at exactly z = 120 m (the city script
   puts flame flares at those four tops). Origin at the base centre, base at z = 0.

Start from an empty scene (bpy.ops.wm.read_factory_settings(use_empty=True)), build with bmesh or bpy.ops primitives,
apply transforms before export, export each object separately with
bpy.ops.export_scene.gltf(filepath=..., export_format="GLB", use_selection=True).
Run it until all 9 GLBs exist. Then write and run a small check script with studio blender that re-imports each GLB
and prints its name, bounding box (min z, height, x/y size) and triangle count. Do not commit. Report the table.
