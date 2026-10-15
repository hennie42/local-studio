extends Node3D
## Recipe: a night/neon look (Forward+): dark sky colour, AgX tonemapping, glow (bloom), thin volumetric fog,
## screen-space reflections for wet floors, emissive "neon" materials and coloured lights. Web exports use the
## Compatibility renderer: no volumetric fog/SDFGI/SSR there.


static func make_environment() -> WorldEnvironment:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.01, 0.012, 0.03)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.05, 0.06, 0.12)
	env.ambient_light_energy = 0.4
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	env.glow_intensity = 1.2
	env.glow_bloom = 0.15
	env.glow_hdr_threshold = 0.9
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.02
	env.volumetric_fog_albedo = Color(0.6, 0.65, 0.8)
	env.ssr_enabled = true
	env.ssr_max_steps = 64
	var we := WorldEnvironment.new()
	we.environment = env
	return we


static func neon_material(color: Color, energy: float = 4.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color * 0.3
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = energy   # > ~2 blooms with glow on
	return m


static func wet_floor_material() -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.02, 0.02, 0.025)
	m.roughness = 0.08   # low roughness + SSR = mirror-like puddles
	m.metallic = 0.2
	return m


static func neon_light(color: Color, energy: float = 3.0, range_m: float = 8.0) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.light_color = color
	l.light_energy = energy
	l.omni_range = range_m
	l.light_volumetric_fog_energy = 2.0   # makes the light visible in the fog
	return l


func run_selftest() -> String:
	var we := make_environment()
	add_child(we)
	var n := neon_material(Color(1, 0.1, 0.8))
	var l := neon_light(Color(0.2, 0.9, 1))
	add_child(l)
	var ok := we.environment.glow_enabled and we.environment.tonemap_mode == Environment.TONE_MAPPER_AGX \
		and n.emission_enabled and l.light_volumetric_fog_energy > 0.0 and wet_floor_material().roughness < 0.1
	return "" if ok else "environment settings not applied"
