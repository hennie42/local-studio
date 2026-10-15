Read AGENTS.md and PLAN.md first (this is step "import" of PLAN.md). Use Scripts/studio_ue.py (import it as `su`;
read its docstring and function signatures first).

Write Scripts/import_assets.py (Unreal Python, re-runnable) and run it with
`studio ue-python {NAME}.uproject Scripts/import_assets.py` until it succeeds. It must:
1. Import every PNG in assets/tex into /Game/City/Textures and every GLB in assets/models into /Game/City/Meshes
   (su.import_dir; the project root is the parent directory of Scripts/). Imported GLB meshes land in subfolders;
   use su.find_assets("/Game/City/Meshes", "StaticMesh") to list them.
2. Create materials in /Game/City/Materials with su.texture_material / su.color_material:
   - M_Win_A, M_Win_B, M_Win_C from T_Windows_A/B/C: world_aligned_cm=400, emissive=6.0, roughness=0.15,
     base_dark=0.03, tint (1,1,1).
   - M_Ad_01 ... M_Ad_08 from T_Ad_01..08: emissive=25.0, base_dark=0.02, roughness=0.4; give M_Ad_02, M_Ad_05 and
     M_Ad_07 a flicker (flicker_hz 2.5, 4.0 and 6.0).
   - M_Pyramid from T_Windows_A: world_aligned_cm=800, emissive=4.0, tint (1.0, 0.55, 0.25), roughness=0.2.
   - M_Wet: color_material, rgb (0.012, 0.012, 0.016), roughness 0.05, metallic 0.0 (mirror-like wet asphalt).
   - M_Flare: color_material rgb (1.0, 0.45, 0.1), emissive 80.
   - M_Light_White: color_material rgb (0.9, 0.95, 1.0), emissive 60.  M_Light_Red: rgb (1, 0.05, 0.03), emissive 60.
   - M_Hull: color_material rgb (0.03, 0.03, 0.035), roughness 0.25, metallic 0.8.
3. Finish with su.save() and print (su.log) the full list of meshes, textures and materials it produced.
Do not commit. Report the printed asset list.
