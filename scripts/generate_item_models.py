import math
import os
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "assets" / "models"


COLORS = {
    "white": (0.95, 0.9, 0.78, 1),
    "cream": (0.86, 0.74, 0.56, 1),
    "red": (0.88, 0.1, 0.07, 1),
    "orange": (1.0, 0.42, 0.06, 1),
    "yellow": (1.0, 0.78, 0.08, 1),
    "green": (0.28, 0.62, 0.18, 1),
    "blue": (0.1, 0.45, 0.92, 1),
    "light_blue": (0.34, 0.78, 0.96, 1),
    "purple": (0.55, 0.28, 0.85, 1),
    "brown": (0.56, 0.28, 0.12, 1),
    "black": (0.02, 0.02, 0.02, 1),
    "pink": (0.95, 0.55, 0.58, 1),
    "gold": (0.95, 0.67, 0.18, 1),
    "metal": (0.72, 0.66, 0.48, 1),
    "glass": (0.28, 0.9, 0.95, 0.45),
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def mat(name, color, roughness=0.65, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if color[3] < 1:
        bsdf.inputs["Alpha"].default_value = color[3]
        material.blend_method = "BLEND"
    return material


def assign(obj, material):
    obj.data.materials.append(material)
    return obj


def ico(name, loc, scale, material, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, material)
    return obj


def sphere(name, loc, scale, material, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, material)
    return obj


def cyl(name, loc, radius, depth, material, vertices=16, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return obj


def cone(name, loc, r1, r2, depth, material, vertices=16, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return obj


def cube(name, loc, scale, material, rotation=(0, 0, 0), bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, material)
    if bevel:
        modifier = obj.modifiers.new("small bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
        obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def torus(name, loc, major, minor, material, rotation=(0, 0, 0), segments=16):
    bpy.ops.mesh.primitive_torus_add(major_segments=segments, minor_segments=6, location=loc, major_radius=major, minor_radius=minor, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return obj


def make_materials():
    return {name: mat(name, color, metallic=0.25 if name in {"gold", "metal"} else 0.0) for name, color in COLORS.items()}


def add_leaf(mats, loc=(0, 0, 0), scale=(0.12, 0.04, 0.28), rot=(0, 0, 0)):
    return cube("leaf", loc, scale, mats["green"], rot, 0.02)


def add_eye(mats, x, y, z):
    return ico("eye", (x, y, z), (0.035, 0.035, 0.035), mats["black"], 1)


def build_goose(m):
    ico("body", (0, 0, 0.22), (0.42, 0.28, 0.24), m["white"])
    ico("neck", (0.23, 0, 0.52), (0.14, 0.12, 0.35), m["white"])
    ico("head", (0.32, 0, 0.82), (0.17, 0.14, 0.14), m["white"])
    cone("beak", (0.52, 0, 0.82), 0.08, 0.02, 0.22, m["orange"], rotation=(0, math.pi / 2, 0))
    add_eye(m, 0.37, -0.09, 0.88)
    add_eye(m, 0.37, 0.09, 0.88)
    cube("left foot", (0.16, -0.16, -0.03), (0.18, 0.09, 0.03), m["orange"])
    cube("right foot", (0.16, 0.16, -0.03), (0.18, 0.09, 0.03), m["orange"])


def build_egg(m):
    ico("egg", (0, 0, 0.32), (0.32, 0.32, 0.45), m["cream"], 2)


def build_apple(m):
    ico("apple", (0, 0, 0.33), (0.38, 0.38, 0.34), m["red"])
    cyl("stem", (0, 0, 0.72), 0.04, 0.24, m["brown"], vertices=8)
    add_leaf(m, (0.13, 0, 0.78), (0.16, 0.04, 0.08), (0, 0.4, 0.35))


def build_carrot(m):
    cone("root", (0, 0, 0.28), 0.18, 0.04, 0.82, m["orange"], rotation=(0, math.pi / 2, 0))
    for y in (-0.12, 0, 0.12):
        add_leaf(m, (-0.43, y, 0.45), (0.2, 0.035, 0.06), (0.25, 0.1, y * 2))


def build_corn(m):
    cyl("cob", (0, 0, 0.3), 0.18, 0.78, m["yellow"], vertices=14, rotation=(0, math.pi / 2, 0))
    for i in range(5):
        x = -0.25 + i * 0.13
        for y in (-0.11, 0, 0.11):
            ico("kernel", (x, y, 0.48), (0.04, 0.035, 0.035), m["gold"], 1)
    cube("left husk", (0, -0.22, 0.28), (0.36, 0.05, 0.12), m["green"], (0, 0.25, 0.25))
    cube("right husk", (0, 0.22, 0.28), (0.36, 0.05, 0.12), m["green"], (0, 0.25, -0.25))


def build_pumpkin(m):
    for x in (-0.22, 0, 0.22):
        ico("pumpkin lobe", (x, 0, 0.32), (0.25, 0.38, 0.3), m["orange"])
    cyl("stem", (0, 0, 0.68), 0.07, 0.26, m["green"], vertices=8)


def build_mushroom(m):
    cyl("stem", (0, 0, 0.2), 0.15, 0.38, m["cream"], vertices=10)
    ico("cap", (0, 0, 0.52), (0.42, 0.42, 0.18), m["red"])
    for x, y in [(-0.15, -0.08), (0.12, 0.12), (0.05, -0.18)]:
        ico("spot", (x, y, 0.68), (0.07, 0.07, 0.02), m["white"], 1)


def build_bread(m):
    ico("loaf", (0, 0, 0.25), (0.48, 0.28, 0.22), m["brown"])
    for x in (-0.22, 0, 0.22):
        cube("score", (x, -0.01, 0.46), (0.07, 0.31, 0.015), m["cream"], (0, 0, 0.55), 0.01)


def build_milk_bottle(m):
    cyl("bottle", (0, 0, 0.34), 0.22, 0.64, m["white"], vertices=12)
    cyl("neck", (0, 0, 0.76), 0.14, 0.24, m["white"], vertices=12)
    cyl("cap", (0, 0, 0.93), 0.17, 0.1, m["blue"], vertices=12)


def build_fish(m):
    ico("body", (0, 0, 0.28), (0.44, 0.25, 0.22), m["blue"])
    cone("nose", (0.42, 0, 0.28), 0.16, 0.02, 0.2, m["light_blue"], rotation=(0, math.pi / 2, 0))
    cone("tail", (-0.48, 0, 0.28), 0.22, 0.03, 0.25, m["blue"], rotation=(0, -math.pi / 2, 0))
    cube("fin", (0.02, -0.22, 0.32), (0.16, 0.035, 0.08), m["light_blue"], (0.2, 0, 0.2))
    add_eye(m, 0.25, -0.18, 0.39)


def build_crab(m):
    ico("body", (0, 0, 0.26), (0.36, 0.28, 0.18), m["red"])
    for side in (-1, 1):
        cone("claw", (0.38 * side, 0.22, 0.32), 0.13, 0.03, 0.28, m["red"], rotation=(0.3, side * 1.2, 0))
        for i in range(3):
            cube("leg", (side * (0.18 + i * 0.1), -0.22, 0.16), (0.13, 0.035, 0.035), m["red"], (0, 0, side * 0.3))
    add_eye(m, -0.1, 0.18, 0.44)
    add_eye(m, 0.1, 0.18, 0.44)


def build_shell(m):
    for i in range(7):
        angle = -0.7 + i * 0.23
        cube("rib", (math.sin(angle) * 0.16, 0.02, 0.28 + math.cos(angle) * 0.08), (0.05, 0.3, 0.18), m["cream"], (0, 0, angle), 0.02)
    ico("shell back", (0, 0, 0.22), (0.42, 0.16, 0.16), m["pink"])


def build_starfish(m):
    for i in range(5):
        angle = i * math.tau / 5
        cube("arm", (math.cos(angle) * 0.16, math.sin(angle) * 0.16, 0.25), (0.12, 0.34, 0.08), m["orange"], (0, 0, angle), 0.07)
    ico("center", (0, 0, 0.28), (0.18, 0.18, 0.1), m["orange"], 1)


def build_shrimp(m):
    for i in range(5):
        ico("segment", (-0.28 + i * 0.13, math.sin(i * 0.6) * 0.08, 0.28), (0.14, 0.11, 0.09), m["orange"], 1)
    cone("tail", (-0.44, -0.1, 0.25), 0.12, 0.03, 0.18, m["red"], rotation=(0.3, -1.0, 0))
    add_eye(m, 0.28, 0.08, 0.38)


def build_octopus(m):
    ico("head", (0, 0, 0.45), (0.32, 0.3, 0.28), m["purple"])
    for i in range(8):
        angle = i * math.tau / 8
        cube("tentacle", (math.cos(angle) * 0.28, math.sin(angle) * 0.28, 0.18), (0.08, 0.25, 0.06), m["purple"], (0, 0, angle), 0.06)
    add_eye(m, -0.08, -0.2, 0.52)
    add_eye(m, 0.08, -0.2, 0.52)


def build_seaweed(m):
    cyl("base", (0, 0, 0.05), 0.25, 0.1, m["cream"], vertices=12)
    for i, x in enumerate([-0.22, -0.08, 0.08, 0.22]):
        cube("blade", (x, 0, 0.36), (0.055, 0.05, 0.38), m["green"], (0.15 * i, 0.25 - i * 0.12, 0.2 * i), 0.03)


def build_pearl_clam(m):
    ico("bottom shell", (0, 0, 0.16), (0.44, 0.26, 0.1), m["pink"])
    ico("top shell", (0, 0.1, 0.44), (0.44, 0.16, 0.1), m["cream"])
    ico("pearl", (0, -0.04, 0.34), (0.16, 0.16, 0.16), m["white"])


def build_message_bottle(m):
    cyl("bottle", (0, 0, 0.28), 0.18, 0.72, m["glass"], vertices=12, rotation=(0, math.pi / 2, 0))
    cyl("cork", (0.42, 0, 0.28), 0.11, 0.18, m["brown"], vertices=10, rotation=(0, math.pi / 2, 0))
    cube("scroll", (-0.02, 0, 0.29), (0.23, 0.04, 0.08), m["cream"], (0, 0, 0.15), 0.01)


def build_building_block(m):
    cube("block", (0, 0, 0.28), (0.42, 0.42, 0.28), m["blue"], bevel=0.06)
    for x in (-0.16, 0.16):
        for y in (-0.16, 0.16):
            cyl("stud", (x, y, 0.6), 0.09, 0.08, m["red"], vertices=12)


def build_toy_car(m):
    cube("body", (0, 0, 0.22), (0.5, 0.26, 0.14), m["blue"], bevel=0.06)
    cube("cab", (0.08, 0, 0.42), (0.26, 0.22, 0.16), m["blue"], bevel=0.04)
    for x in (-0.28, 0.28):
        for y in (-0.18, 0.18):
            cyl("wheel", (x, y, 0.12), 0.09, 0.05, m["black"], vertices=12, rotation=(math.pi / 2, 0, 0))


def build_rubber_ball(m):
    ico("ball", (0, 0, 0.34), (0.36, 0.36, 0.36), m["red"])
    for angle, material in [(0, m["blue"]), (math.pi / 2, m["yellow"]), (math.pi / 4, m["purple"])]:
        cube("stripe", (0, 0, 0.37), (0.04, 0.39, 0.39), material, (0, 0, angle), 0.01)


def build_key(m):
    torus("ring", (0.26, 0, 0.25), 0.16, 0.035, m["gold"], segments=18)
    cube("shaft", (-0.08, 0, 0.25), (0.34, 0.055, 0.035), m["gold"], bevel=0.02)
    cube("tooth one", (-0.32, -0.05, 0.2), (0.07, 0.05, 0.05), m["gold"], bevel=0.01)
    cube("tooth two", (-0.22, -0.05, 0.2), (0.05, 0.05, 0.05), m["gold"], bevel=0.01)


def build_alarm_clock(m):
    cyl("face", (0, 0, 0.32), 0.34, 0.14, m["red"], vertices=16, rotation=(math.pi / 2, 0, 0))
    cyl("dial", (0, -0.08, 0.32), 0.25, 0.04, m["white"], vertices=16, rotation=(math.pi / 2, 0, 0))
    cube("hand one", (0.06, -0.12, 0.36), (0.02, 0.02, 0.16), m["black"], (0.8, 0, 0), 0.01)
    cube("hand two", (-0.05, -0.12, 0.31), (0.02, 0.02, 0.12), m["black"], (0, 0, 0.6), 0.01)
    ico("bell left", (-0.22, 0, 0.66), (0.13, 0.11, 0.08), m["yellow"], 1)
    ico("bell right", (0.22, 0, 0.66), (0.13, 0.11, 0.08), m["yellow"], 1)


def build_pencil(m):
    cyl("barrel", (0, 0, 0.28), 0.12, 0.78, m["yellow"], vertices=6, rotation=(0, math.pi / 2, 0))
    cone("tip", (0.47, 0, 0.28), 0.12, 0.02, 0.2, m["cream"], vertices=6, rotation=(0, math.pi / 2, 0))
    cone("lead", (0.58, 0, 0.28), 0.045, 0.01, 0.08, m["black"], vertices=6, rotation=(0, math.pi / 2, 0))
    cyl("eraser", (-0.48, 0, 0.28), 0.12, 0.16, m["pink"], vertices=12, rotation=(0, math.pi / 2, 0))


def build_gift_box(m):
    cube("box", (0, 0, 0.28), (0.38, 0.38, 0.28), m["purple"], bevel=0.05)
    cube("ribbon x", (0, 0, 0.58), (0.42, 0.06, 0.035), m["green"], bevel=0.015)
    cube("ribbon y", (0, 0, 0.58), (0.06, 0.42, 0.035), m["green"], bevel=0.015)
    torus("bow left", (-0.12, 0, 0.68), 0.08, 0.025, m["green"], (0.6, 0, 0))
    torus("bow right", (0.12, 0, 0.68), 0.08, 0.025, m["green"], (0.6, 0, 0))


def build_rubber_duck(m):
    ico("body", (0, 0, 0.25), (0.4, 0.28, 0.2), m["yellow"])
    ico("head", (0.26, -0.05, 0.48), (0.18, 0.16, 0.16), m["yellow"])
    cone("beak", (0.45, -0.05, 0.46), 0.08, 0.02, 0.18, m["orange"], rotation=(0, math.pi / 2, 0))
    add_eye(m, 0.3, -0.18, 0.54)


def build_button(m):
    cyl("button", (0, 0, 0.12), 0.36, 0.16, m["blue"], vertices=20)
    cyl("rim", (0, 0, 0.23), 0.29, 0.04, m["light_blue"], vertices=20)
    for x in (-0.1, 0.1):
        for y in (-0.1, 0.1):
            cyl("hole", (x, y, 0.31), 0.035, 0.025, m["black"], vertices=10)


BUILDERS = {
    "farm-kitchen": [
        ("goose", build_goose),
        ("egg", build_egg),
        ("apple", build_apple),
        ("carrot", build_carrot),
        ("corn", build_corn),
        ("pumpkin", build_pumpkin),
        ("mushroom", build_mushroom),
        ("bread", build_bread),
        ("milk-bottle", build_milk_bottle),
    ],
    "seaside-catch": [
        ("fish", build_fish),
        ("crab", build_crab),
        ("shell", build_shell),
        ("starfish", build_starfish),
        ("shrimp", build_shrimp),
        ("octopus", build_octopus),
        ("seaweed", build_seaweed),
        ("pearl-clam", build_pearl_clam),
        ("message-bottle", build_message_bottle),
    ],
    "toy-clutter": [
        ("building-block", build_building_block),
        ("toy-car", build_toy_car),
        ("rubber-ball", build_rubber_ball),
        ("key", build_key),
        ("alarm-clock", build_alarm_clock),
        ("pencil", build_pencil),
        ("gift-box", build_gift_box),
        ("rubber-duck", build_rubber_duck),
        ("button", build_button),
    ],
}


def add_world_setup():
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 5))
    light = bpy.context.object
    light.name = "softbox"
    light.data.energy = 350
    light.data.size = 5


def export_item(theme, slug, builder):
    clear_scene()
    mats = make_materials()
    builder(mats)
    add_world_setup()
    out_dir = MODEL_ROOT / theme
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{slug}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
        export_yup=True,
    )
    print(f"exported {filepath.relative_to(ROOT)}")


def main():
    for theme, items in BUILDERS.items():
        for slug, builder in items:
            export_item(theme, slug, builder)


if __name__ == "__main__":
    main()
