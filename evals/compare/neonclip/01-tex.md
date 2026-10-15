Read AGENTS.md and PLAN.md first (this is step "tex" of PLAN.md).

Write Scripts/make_textures.py (python3 + Pillow + numpy; run it with python3) that generates, deterministically
(fixed random seed), these PNGs in assets/tex/:

1. T_Windows_A.png, T_Windows_B.png, T_Windows_C.png: 512x512 window-grid atlases for skyscraper facades.
   One texture repeat = one 4 m x 4 m patch of facade: a grid of 4 x 4 windows (cells of 128 px) with thin dark
   mullions; background (wall) near-black (about 8,8,12). Each window is either dark (~55%) or lit; lit windows vary
   in brightness and colour: A = warm (amber/sodium 255,190,110 and dim yellow), B = cold (cyan/blue-white 170,215,255),
   C = mixed with a few magenta/red neon-tinted ones. Some lit windows have a darker lower half (blinds).
2. T_Ad_01.png ... T_Ad_06.png: 1024x2048 (portrait) giant commercials, T_Ad_07.png and T_Ad_08.png: 2048x1024
   (landscape). Neon-advertising look on a near-black background: bold Japanese/Chinese text drawn with the font
   /usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc (if missing, find a CJK font with `fc-list :lang=ja file`),
   fictional brand names in Latin capitals (e.g. "OKAMI", "SHIROI", "NEXUS DRINK", "KAZE AIR" - invent your own),
   simple glowing shapes (circles, stripes, a stylised face or bottle silhouette), saturated reds, magentas, cyans,
   electric blue, warm orange. Make each ad clearly different. Add a soft glow (blur of the bright parts added back).
3. T_Puddles.png: 1024x1024 grayscale tileable noise map (blurred blobs; white = puddle, black = wet asphalt) with
   about 30% puddle coverage.

Then run it and verify with python3 that all 12 files exist with the right pixel sizes; print a short summary.
Do not commit. Report the file list and sizes.
