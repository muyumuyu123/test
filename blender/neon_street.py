"""Procedural cyberpunk street, rendered with Blender Cycles.

    python3 neon_street.py [out.png] [--preview]

Everything (buildings, signs, lights, wet road) is generated here, so the
render is original artwork you fully own. --preview renders small and fast.
"""
import math
import os
import random
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
OUT = next((a for a in sys.argv[1:] if not a.startswith("--")), os.path.join(HERE, "renders", "neon_street.png"))
PREVIEW = "--preview" in sys.argv
SEED = 7
rnd = random.Random(SEED)

NEON = {
    "pink": (1.0, 0.12, 0.45),
    "cyan": (0.1, 0.85, 1.0),
    "violet": (0.55, 0.25, 1.0),
    "amber": (1.0, 0.55, 0.12),
    "red": (1.0, 0.1, 0.12),
    "green": (0.3, 1.0, 0.45),
    "warm": (1.0, 0.75, 0.45),
}

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def link(obj):
    col.objects.link(obj)
    return obj


# ---------------------------------------------------------------- materials
def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_basic(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def mat_facade(name, base, win_color, lit_bias, win_strength, scale):
    """Dark concrete facade with a grid of randomly lit windows (brick texture trick)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    tc = N.new("ShaderNodeTexCoord")
    mapping = N.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    L.new(tc.outputs["Object"], mapping.inputs["Vector"])
    # windows run along the facade: use (y, z) for walls facing ±x
    sep = N.new("ShaderNodeSeparateXYZ")
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(mapping.outputs[0], sep.inputs[0])
    L.new(sep.outputs["Y"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    brick = N.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.squash = 1.0
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (*win_color, 1)
    brick.inputs["Mortar"].default_value = (0, 0, 0, 1)
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.12
    brick.inputs["Bias"].default_value = lit_bias
    brick.inputs["Brick Width"].default_value = 0.9
    brick.inputs["Row Height"].default_value = 0.5
    L.new(comb.outputs[0], brick.inputs["Vector"])
    L.new(brick.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = win_strength
    # darker frames between windows
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*base, 1)
    mix.inputs["B"].default_value = (base[0] * 0.4, base[1] * 0.4, base[2] * 0.4, 1)
    L.new(brick.outputs["Fac"], mix.inputs["Factor"])
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return m


def mat_road():
    """Wet asphalt: dark, puddles (low roughness) from noise, slight bump."""
    m = bpy.data.materials.new("road")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.22
    noise.inputs["Detail"].default_value = 6
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.38
    ramp.color_ramp.elements[0].color = (0.04, 0.04, 0.04, 1)
    ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[1].color = (0.42, 0.42, 0.42, 1)
    L.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    fine = N.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 60
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    L.new(fine.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_shop(name, color):
    """Lit shop window: uneven interior light instead of a flat panel."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 3
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.05, 0.05, 0.05, 1)
    ramp.color_ramp.elements[1].position = 0.75
    L.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 1.4
    L.new(ramp.outputs["Color"], mul.inputs[0])
    L.new(mul.outputs[0], em.inputs["Strength"])
    L.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_billboard(name, c1, c2, strength=3.0):
    """Big ad screen: diagonal colour gradient with bright horizontal bars."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    tc = N.new("ShaderNodeTexCoord")
    grad = N.new("ShaderNodeTexGradient")
    L.new(tc.outputs["Generated"], grad.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    L.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    wave = N.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3.0
    wr = N.new("ShaderNodeValToRGB")
    wr.color_ramp.elements[0].position = 0.85
    wr.color_ramp.elements[1].position = 0.9
    L.new(tc.outputs["Generated"], wave.inputs["Vector"])
    L.new(wave.outputs["Fac"], wr.inputs["Fac"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    mix.inputs["Factor"].default_value = 0.6
    L.new(ramp.outputs["Color"], mix.inputs["A"])
    L.new(wr.outputs["Color"], mix.inputs["B"])
    L.new(mix.outputs["Result"], em.inputs["Color"])
    L.new(em.outputs[0], out.inputs["Surface"])
    return m


M_ROAD = mat_road()
M_CURB = mat_basic("curb", (0.03, 0.03, 0.035), 0.5)
M_PAVE = mat_basic("pave", (0.02, 0.02, 0.024), 0.35)
M_DARK = mat_basic("dark", (0.01, 0.01, 0.012), 0.5, 0.4)
M_METAL = mat_basic("metal", (0.05, 0.05, 0.06), 0.35, 0.8)
M_CABLE = mat_basic("cable", (0.005, 0.005, 0.005), 0.6)
EMIT = {k: mat_emit(f"neon_{k}", c, 18) for k, c in NEON.items()}
SOFT = {k: mat_shop(f"shop_{k}", c) for k, c in NEON.items()}
BOARDS = [mat_billboard("bb1", NEON["pink"], NEON["violet"]), mat_billboard("bb2", NEON["cyan"], (0.1, 0.2, 1.0)), mat_billboard("bb3", NEON["amber"], NEON["red"])]
FACADES = [
    mat_facade("facade_warm", (0.03, 0.028, 0.034), (1.0, 0.62, 0.32), -0.72, 1.6, 2.2),
    mat_facade("facade_cool", (0.026, 0.03, 0.04), (0.45, 0.75, 1.0), -0.78, 1.4, 2.6),
    mat_facade("facade_mix", (0.034, 0.026, 0.034), (1.0, 0.4, 0.75), -0.8, 1.4, 2.0),
]


# ---------------------------------------------------------------- geometry helpers
def box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return o


def text(body, font_file, size, loc, rot, mat, extrude=0.02, align="CENTER"):
    cu = bpy.data.curves.new(name=f"txt_{body[:8]}", type="FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(os.path.join(FONT_DIR, font_file), check_existing=True)
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    o = bpy.data.objects.new(f"txt_{body[:8]}", cu)
    o.location = loc
    o.rotation_euler = rot
    link(o)
    o.data.materials.append(mat)
    return o


def cable(p0, p1, sag, thick=0.02):
    cu = bpy.data.curves.new("cable", type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = thick
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(1)
    a, b = sp.bezier_points
    a.co, b.co = p0, p1
    mid = [(p0[i] + p1[i]) / 2 for i in range(3)]
    mid[2] -= sag
    a.handle_right = [(p0[i] * 2 + mid[i]) / 3 for i in range(3)]
    b.handle_left = [(p1[i] * 2 + mid[i]) / 3 for i in range(3)]
    a.handle_left, b.handle_right = p0, p1
    o = bpy.data.objects.new("cable", cu)
    link(o)
    o.data.materials.append(M_CABLE)
    return o


# ---------------------------------------------------------------- street layout
# Street runs along +Y. Camera at y=0 looking down the street.
HALF = 7.0          # facade line at x = ±HALF
SIDEWALK = 2.4
LENGTH = 220

# road + sidewalks
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, LENGTH / 2, 0))
road = bpy.context.active_object
road.scale = (HALF * 2 + 2, LENGTH, 1)
road.data.materials.append(M_ROAD)
for s in (-1, 1):
    box("sidewalk", (s * (HALF - SIDEWALK / 2), LENGTH / 2, 0.08), (SIDEWALK, LENGTH, 0.16), M_PAVE)
    box("curb", (s * (HALF - SIDEWALK), LENGTH / 2, 0.08), (0.18, LENGTH, 0.17), M_CURB)

# lane dashes
M_PAINT = mat_emit("paint", (0.9, 0.75, 0.4), 0.25)
for y in range(4, LENGTH, 9):
    box("dash", (0, y, 0.005), (0.14, 3.2, 0.01), M_PAINT)

signs_placed = []


def blade_sign(x_face, side, y, z, word, color, vertical=True):
    """Sign sticking out from the facade towards the street, facing the camera."""
    font = "DelaGothicOne-Regular.ttf" if not word.isascii() else "ChakraPetch-Bold.ttf"
    n = len(word)
    if vertical:
        w, h = 1.1, 0.95 * n + 0.5
    else:
        w, h = 0.62 * n + 0.8, 1.2
    x = x_face - side * (w / 2 + 0.3)
    box("sign_back", (x, y, z), (w, 0.18, h), M_DARK)
    # neon border (4 thin tubes)
    t = 0.06
    for dx, dz, sw, sh in ((0, h / 2 - 0.12, w - 0.2, t), (0, -h / 2 + 0.12, w - 0.2, t), (w / 2 - 0.12, 0, t, h - 0.2), (-w / 2 + 0.12, 0, t, h - 0.2)):
        box("tube", (x + dx, y - 0.1, z + dz), (sw, t, sh), EMIT[color])
    rot = (math.pi / 2, 0, 0)
    if vertical:
        for i, ch in enumerate(word):
            text(ch, font, 0.78, (x, y - 0.11, z + h / 2 - 0.62 - i * 0.95), rot, EMIT[color], 0.01)
    else:
        text(word, font, 0.8, (x, y - 0.11, z), rot, EMIT[color], 0.01)
    signs_placed.append((x, y, z, color))


WORDS = ["酒", "夜市", "ラーメン", "電脳", "ホテル", "営業中", "BAR", "24H", "OPEN", "CLUB", "月"]
COLORS = ["pink", "cyan", "violet", "amber", "red", "green"]

for side in (-1, 1):
    y = 3.0
    while y < LENGTH - 20:
        depth = rnd.uniform(8, 18)
        height = rnd.uniform(14, 46)
        x_face = side * HALF
        cx = x_face + side * 9
        fac = rnd.choice(FACADES)
        b = box("building", (cx, y + depth / 2, height / 2), (18, depth - 0.3, height), fac)
        # crown / setback
        if rnd.random() < 0.5:
            box("crown", (cx + side * 2, y + depth / 2, height + 2), (12, depth * 0.7, 4), fac)
        # shopfront band at street level (emissive glass)
        shop = rnd.choice(list(SOFT.values()))
        bays = max(2, int(depth // 3.2))
        bw = (depth - 1.0) / bays
        for k in range(bays):
            by = y + 0.5 + bw * (k + 0.5)
            if rnd.random() < 0.8:
                box("shop", (x_face - side * 0.02, by, 1.4), (0.05, bw - 0.35, 2.3), shop)
            box("mullion", (x_face - side * 0.06, by + bw / 2, 1.5), (0.14, 0.3, 3.0), M_DARK)
            if rnd.random() < 0.6:
                box("shelf", (x_face - side * 0.12, by + rnd.uniform(-0.6, 0.6), rnd.uniform(0.6, 1.1)), (0.1, rnd.uniform(0.4, 1.2), rnd.uniform(0.6, 1.6)), M_DARK)
        if height > 22 and rnd.random() < 0.45:
            bz = height * rnd.uniform(0.45, 0.65)
            bh = rnd.uniform(4, 7)
            box("billboard_frame", (x_face - side * 0.12, y + depth / 2, bz), (0.2, depth * 0.7 + 0.4, bh + 0.4), M_DARK)
            box("billboard", (x_face - side * 0.24, y + depth / 2, bz), (0.04, depth * 0.7, bh), rnd.choice(BOARDS))
        box("awning", (x_face - side * 0.6, y + depth / 2, 3.1), (1.2, depth - 0.8, 0.12), M_DARK)
        box("awning_neon", (x_face - side * 1.18, y + depth / 2, 3.04), (0.05, depth - 0.8, 0.06), EMIT[rnd.choice(COLORS)])
        # AC units + pipes clutter
        for _ in range(rnd.randint(2, 6)):
            box("ac", (x_face - side * 0.35, y + rnd.uniform(1, depth - 1), rnd.uniform(5, height - 2)), (0.7, 1.0, 0.7), M_METAL)
        if rnd.random() < 0.6:
            box("pipe", (x_face - side * 0.2, y + rnd.uniform(0.5, depth - 0.5), height / 2), (0.18, 0.18, height), M_METAL)
        # blade signs
        for _ in range(rnd.randint(2, 4)):
            word = rnd.choice(WORDS)
            vertical = not word.isascii() or rnd.random() < 0.4
            blade_sign(x_face, side, y + rnd.uniform(1.5, depth - 1.5), rnd.uniform(5.5, min(height - 3, 18)), word, rnd.choice(COLORS), vertical)
        y += depth

# far skyline blocking the end of the street
for i in range(26):
    h = rnd.uniform(40, 140)
    box("far", (rnd.uniform(-60, 60), LENGTH + rnd.uniform(0, 60), h / 2), (rnd.uniform(10, 26), rnd.uniform(10, 26), h), rnd.choice(FACADES))

# ---------------------------------------------------------------- hero signage
# Big overhead banner across the street: STARTING SOON
BY, BZ = 26, 11.5
box("banner_back", (0, BY, BZ), (11.4, 0.25, 3.3), M_DARK)
for dz in (1.45, -1.45):
    box("banner_tube", (0, BY - 0.14, BZ + dz), (11.0, 0.07, 0.08), EMIT["pink"])
for dx in (5.55, -5.55):
    box("banner_tube", (dx, BY - 0.14, BZ), (0.08, 0.07, 2.9), EMIT["pink"])
text("STARTING SOON", "BarlowCondensed-Bold.ttf", 2.1, (0, BY - 0.16, BZ + 0.25), (math.pi / 2, 0, 0), EMIT["pink"], 0.02)
text("配信開始", "DelaGothicOne-Regular.ttf", 0.62, (0, BY - 0.16, BZ - 0.95), (math.pi / 2, 0, 0), EMIT["cyan"], 0.01)
for dx in (-5.2, 5.2):
    cable((dx, BY, BZ + 1.6), (dx * 1.35, BY, BZ + 7), 0, 0.03)

# Tall vertical name sign on the right: NOVA
blade_sign(HALF, 1, 14, 9.5, "NOVA", "cyan", True)

# power cables crossing the street
for i in range(10):
    y = rnd.uniform(8, 120)
    z = rnd.uniform(9, 16)
    cable((-HALF, y, z), (HALF, y + rnd.uniform(-4, 4), z + rnd.uniform(-1.5, 1.5)), rnd.uniform(0.6, 1.6))

# vending machines on the sidewalks (one close to camera on the left)
M_VEND = mat_emit("vend", (0.55, 0.8, 1.0), 0.7)
for (vx, vy, rot) in [(-HALF + 0.6, 2.5, 0), (-HALF + 0.6, 3.6, 0), (HALF - 0.6, 18, 0), (-HALF + 0.6, 44, 0)]:
    box("vend_body", (vx, vy, 0.95), (0.8, 1.0, 1.9), M_METAL)
    s_ = 1 if vx < 0 else -1
    box("vend_front", (vx + s_ * 0.41, vy, 1.05), (0.02, 0.85, 1.4), M_VEND)
    bpy.ops.object.light_add(type="POINT", location=(vx + s_ * 1.0, vy, 1.2))
    Lv = bpy.context.active_object
    Lv.data.energy = 60
    Lv.data.color = (0.75, 0.9, 1.0)

# street lamps
M_LAMP = mat_emit("lamp", NEON["warm"], 30)
for side in (-1, 1):
    for y in range(8, 140, 16):
        x = side * (HALF - SIDEWALK + 0.4)
        box("pole", (x, y, 3.2), (0.12, 0.12, 6.4), M_METAL)
        box("arm", (x - side * 0.8, y, 6.35), (1.6, 0.1, 0.1), M_METAL)
        box("lamp", (x - side * 1.5, y, 6.25), (0.5, 0.25, 0.08), M_LAMP)
        bpy.ops.object.light_add(type="POINT", location=(x - side * 1.5, y, 6.0))
        L = bpy.context.active_object
        L.data.energy = 600
        L.data.color = NEON["warm"]
        L.data.shadow_soft_size = 0.3

# colored fill lights near the biggest signs so their colour spills on the road
for (x, y, z, c) in signs_placed[:: max(1, len(signs_placed) // 18)]:
    bpy.ops.object.light_add(type="POINT", location=(x, y - 0.8, z))
    L = bpy.context.active_object
    L.data.energy = 250
    L.data.color = NEON[c]
bpy.ops.object.light_add(type="AREA", location=(0, BY - 1.5, BZ - 1.8), rotation=(math.radians(60), 0, 0))
L = bpy.context.active_object
L.data.energy = 3500
L.data.size = 10
L.data.color = NEON["pink"]

# ---------------------------------------------------------------- world + fog
world = bpy.data.worlds.new("night")
scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
bg.inputs["Color"].default_value = (0.012, 0.01, 0.03, 1)
bg.inputs["Strength"].default_value = 1.0
vol = wn.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (0.55, 0.45, 0.8, 1)
vol.inputs["Density"].default_value = 0.012
vol.inputs["Anisotropy"].default_value = 0.3
wn.links.new(vol.outputs[0], wn.nodes["World Output"].inputs["Volume"])

# ---------------------------------------------------------------- camera
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 28
cam_data.dof.use_dof = True
cam_data.dof.focus_distance = 26
cam_data.dof.aperture_fstop = 4.0
cam = bpy.data.objects.new("cam", cam_data)
cam.location = (-3.4, -4, 1.6)
cam.rotation_euler = (math.radians(95), 0, math.radians(-7))
link(cam)
scene.camera = cam

# ---------------------------------------------------------------- render settings
r = scene.render
r.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24 if PREVIEW else 48
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.volume_bounces = 0
scene.cycles.volume_step_rate = 4.0 if PREVIEW else 2.0
r.resolution_x = 1920
r.resolution_y = 1080
r.resolution_percentage = 40 if PREVIEW else 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = -0.6
r.image_settings.file_format = "PNG"
r.filepath = OUT
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
