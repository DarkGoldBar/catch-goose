import argparse
import math
import os
import sys
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


def rounded_cube(name, loc, scale, material, rotation=(0, 0, 0), bevel=0.04, segments=2):
    obj = cube(name, loc, scale, material, rotation, bevel=0)
    if bevel:
        modifier = obj.modifiers.new("rounded bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.affect = "EDGES"
        obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def torus(name, loc, major, minor, material, rotation=(0, 0, 0), segments=16):
    bpy.ops.mesh.primitive_torus_add(major_segments=segments, minor_segments=6, location=loc, major_radius=major, minor_radius=minor, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return obj


def bevelled_cylinder(name, loc, radius, depth, material, vertices=32, rotation=(0, 0, 0), bevel=0.015):
    obj = cyl(name, loc, radius, depth, material, vertices=vertices, rotation=rotation)
    if bevel:
        modifier = obj.modifiers.new("edge bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def mesh_obj(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign(obj, material)
    return obj


def spherical_patch(name, loc, radius, phi0, phi1, material, lat_steps=9, lon_steps=3):
    verts = []
    faces = []
    for i in range(lat_steps + 1):
        theta = math.pi * i / lat_steps
        for j in range(lon_steps + 1):
            phi = phi0 + (phi1 - phi0) * j / lon_steps
            verts.append(
                (
                    loc[0] + radius * math.sin(theta) * math.cos(phi),
                    loc[1] + radius * math.sin(theta) * math.sin(phi),
                    loc[2] + radius * math.cos(theta),
                )
            )
    row = lon_steps + 1
    for i in range(lat_steps):
        for j in range(lon_steps):
            a = i * row + j
            faces.append((a, a + 1, a + row + 1, a + row))
    obj = mesh_obj(name, verts, faces, material)
    obj.modifiers.new("segment normals", "WEIGHTED_NORMAL")
    return obj


def clock_tick(mats, angle, radius=0.235, length=0.045, width=0.01):
    x = math.sin(angle) * radius
    z = 0.32 + math.cos(angle) * radius
    return cube("clock tick", (x, -0.151, z), (width, 0.012, length), mats["red"], (0, angle, 0), 0.004)


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
    rounded_cube("blue block body", (0, 0, 0.28), (0.82, 0.82, 0.56), m["blue"], bevel=0.045, segments=3)
    rounded_cube("yellow side panel", (-0.43, 0, 0.28), (0.04, 0.79, 0.51), m["yellow"], bevel=0.018, segments=2)
    rounded_cube("red top plate", (0, 0, 0.595), (0.79, 0.79, 0.07), m["red"], bevel=0.025, segments=2)
    for x in (-0.16, 0.16):
        for y in (-0.16, 0.16):
            bevelled_cylinder("round stud", (x, y, 0.67), 0.09, 0.08, m["red"], vertices=32, bevel=0.012)


def build_toy_car(m):
    rounded_cube("lower chassis", (0, 0, 0.18), (0.86, 0.35, 0.22), m["blue"], bevel=0.045, segments=3)
    rounded_cube("front hood", (0.23, 0, 0.34), (0.42, 0.32, 0.18), m["blue"], bevel=0.035, segments=2)
    rounded_cube("rear body", (-0.24, 0, 0.34), (0.32, 0.32, 0.18), m["blue"], bevel=0.035, segments=2)
    rounded_cube("tall cabin", (-0.06, 0, 0.55), (0.36, 0.30, 0.26), m["blue"], bevel=0.04, segments=2)
    rounded_cube("front windshield", (0.12, -0.161, 0.55), (0.15, 0.012, 0.11), m["light_blue"], (0.18, 0, 0), 0.012, 2)
    rounded_cube("side window left", (-0.08, -0.165, 0.56), (0.12, 0.012, 0.095), m["light_blue"], bevel=0.012, segments=2)
    rounded_cube("side window right", (-0.08, 0.165, 0.56), (0.12, 0.012, 0.095), m["light_blue"], bevel=0.012, segments=2)
    rounded_cube("front bumper", (0.45, 0, 0.19), (0.035, 0.37, 0.05), m["metal"], bevel=0.015, segments=2)
    for y in (-0.105, 0.105):
        bevelled_cylinder("headlight", (0.47, y, 0.30), 0.035, 0.018, m["white"], vertices=20, rotation=(0, math.pi / 2, 0), bevel=0.006)
    for x in (-0.29, 0.29):
        for y in (-0.19, 0.19):
            bevelled_cylinder("black tire", (x, y, 0.11), 0.095, 0.055, m["black"], vertices=28, rotation=(math.pi / 2, 0, 0), bevel=0.012)
            bevelled_cylinder("silver hub", (x, y * 1.01, 0.11), 0.052, 0.062, m["white"], vertices=24, rotation=(math.pi / 2, 0, 0), bevel=0.006)


def build_rubber_ball(m):
    colors = [m["red"], m["yellow"], m["green"], m["blue"], m["blue"], m["purple"]]
    for i, material in enumerate(colors):
        phi0 = i * math.tau / len(colors)
        phi1 = (i + 1) * math.tau / len(colors)
        spherical_patch("colored beach ball panel", (0, 0, 0.38), 0.36, phi0, phi1, material)
    bevelled_cylinder("white top cap", (0, 0, 0.74), 0.095, 0.035, m["white"], vertices=32, bevel=0.008)


def build_key(m):
    bevelled_cylinder("round key head", (0.23, 0, 0.25), 0.21, 0.07, m["gold"], vertices=48, bevel=0.012)
    bevelled_cylinder("dark key hole", (0.23, 0, 0.295), 0.092, 0.076, m["black"], vertices=36, bevel=0.006)
    rounded_cube("long key shaft", (-0.15, 0, 0.25), (0.52, 0.07, 0.05), m["gold"], bevel=0.018, segments=2)
    rounded_cube("raised shaft ridge", (-0.14, 0.043, 0.295), (0.42, 0.014, 0.014), m["metal"], bevel=0.004, segments=1)
    rounded_cube("big tooth", (-0.43, -0.065, 0.205), (0.08, 0.055, 0.045), m["gold"], bevel=0.01, segments=1)
    rounded_cube("middle tooth", (-0.34, -0.065, 0.205), (0.07, 0.05, 0.045), m["gold"], bevel=0.01, segments=1)
    rounded_cube("small tooth", (-0.25, -0.055, 0.21), (0.055, 0.04, 0.04), m["gold"], bevel=0.008, segments=1)


def build_alarm_clock(m):
    bevelled_cylinder("red outer case", (0, 0, 0.32), 0.35, 0.16, m["red"], vertices=48, rotation=(math.pi / 2, 0, 0), bevel=0.018)
    bevelled_cylinder("cream clock face", (0, -0.095, 0.32), 0.27, 0.035, m["white"], vertices=48, rotation=(math.pi / 2, 0, 0), bevel=0.006)
    for i in range(12):
        clock_tick(m, i * math.tau / 12, length=0.042 if i % 3 else 0.055, width=0.007 if i % 3 else 0.011)
    cube("minute hand", (0.0, -0.145, 0.405), (0.012, 0.01, 0.13), m["black"], (0, 0.05, 0), 0.005)
    cube("hour hand", (0.075, -0.148, 0.275), (0.014, 0.01, 0.105), m["black"], (0, -0.9, 0), 0.005)
    bevelled_cylinder("center pin", (0, -0.157, 0.32), 0.035, 0.018, m["black"], vertices=20, rotation=(math.pi / 2, 0, 0), bevel=0.004)
    ico("left yellow bell", (-0.22, 0, 0.68), (0.15, 0.12, 0.085), m["yellow"], 2)
    ico("right yellow bell", (0.22, 0, 0.68), (0.15, 0.12, 0.085), m["yellow"], 2)
    rounded_cube("top hammer", (0, 0, 0.79), (0.045, 0.045, 0.05), m["gold"], bevel=0.012, segments=2)
    rounded_cube("left foot", (-0.18, -0.01, -0.02), (0.055, 0.065, 0.12), m["black"], (0.45, 0, -0.35), 0.015, 2)
    rounded_cube("right foot", (0.18, -0.01, -0.02), (0.055, 0.065, 0.12), m["black"], (0.45, 0, 0.35), 0.015, 2)


def build_pencil(m):
    cyl("hex yellow barrel", (0, 0, 0.28), 0.13, 0.72, m["yellow"], vertices=6, rotation=(0, math.pi / 2, 0))
    for y in (-0.075, 0.075):
        cube("barrel facet highlight", (0, y, 0.382), (0.34, 0.008, 0.012), m["gold"], (0, 0, 0), 0.002)
    cone("wooden sharpened tip", (0.46, 0, 0.28), 0.13, 0.035, 0.2, m["cream"], vertices=6, rotation=(0, math.pi / 2, 0))
    cone("black graphite point", (0.59, 0, 0.28), 0.048, 0.01, 0.09, m["black"], vertices=6, rotation=(0, math.pi / 2, 0))
    for x in (-0.42, -0.37):
        bevelled_cylinder("silver ferrule band", (x, 0, 0.28), 0.132, 0.045, m["metal"], vertices=18, rotation=(0, math.pi / 2, 0), bevel=0.006)
    bevelled_cylinder("pink eraser", (-0.5, 0, 0.28), 0.13, 0.16, m["pink"], vertices=18, rotation=(0, math.pi / 2, 0), bevel=0.012)


def build_gift_box(m):
    rounded_cube("purple lower box", (0, 0, 0.25), (0.76, 0.76, 0.5), m["purple"], bevel=0.045, segments=3)
    rounded_cube("purple lid", (0, 0, 0.54), (0.84, 0.84, 0.16), m["purple"], bevel=0.04, segments=3)
    rounded_cube("vertical ribbon front", (0, -0.39, 0.31), (0.09, 0.025, 0.56), m["green"], bevel=0.012, segments=2)
    rounded_cube("vertical ribbon back", (0, 0.39, 0.31), (0.09, 0.025, 0.56), m["green"], bevel=0.012, segments=2)
    rounded_cube("vertical ribbon left", (-0.39, 0, 0.31), (0.025, 0.09, 0.56), m["green"], bevel=0.012, segments=2)
    rounded_cube("vertical ribbon right", (0.39, 0, 0.31), (0.025, 0.09, 0.56), m["green"], bevel=0.012, segments=2)
    rounded_cube("top ribbon x", (0, 0, 0.64), (0.88, 0.09, 0.04), m["green"], bevel=0.014, segments=2)
    rounded_cube("top ribbon y", (0, 0, 0.642), (0.09, 0.88, 0.04), m["green"], bevel=0.014, segments=2)
    torus("left bow loop", (-0.115, 0, 0.72), 0.08, 0.026, m["green"], (0.55, 0.4, 0), segments=24)
    torus("right bow loop", (0.115, 0, 0.72), 0.08, 0.026, m["green"], (0.55, -0.4, 0), segments=24)
    rounded_cube("bow knot", (0, 0, 0.705), (0.065, 0.065, 0.045), m["green"], bevel=0.014, segments=2)


def build_rubber_duck(m):
    ico("duck rounded body", (-0.05, 0, 0.25), (0.42, 0.29, 0.19), m["yellow"], 2)
    ico("duck upright head", (0.18, -0.02, 0.52), (0.2, 0.17, 0.17), m["yellow"], 2)
    ico("tail lift", (-0.42, 0, 0.35), (0.13, 0.18, 0.13), m["yellow"], 1)
    ico("side wing left", (-0.08, -0.245, 0.28), (0.18, 0.045, 0.13), m["gold"], 1)
    ico("side wing right", (-0.08, 0.245, 0.28), (0.18, 0.045, 0.13), m["gold"], 1)
    ico("upper orange bill", (0.37, -0.02, 0.49), (0.15, 0.09, 0.045), m["orange"], 1)
    ico("lower orange bill", (0.36, -0.02, 0.455), (0.13, 0.075, 0.032), m["orange"], 1)
    add_eye(m, 0.26, -0.155, 0.57)
    add_eye(m, 0.26, 0.115, 0.57)


def build_button(m):
    bevelled_cylinder("thick blue button", (0, 0, 0.14), 0.36, 0.18, m["blue"], vertices=48, bevel=0.025)
    bevelled_cylinder("raised outer rim", (0, 0, 0.25), 0.305, 0.04, m["light_blue"], vertices=48, bevel=0.012)
    bevelled_cylinder("recessed inner dish", (0, 0, 0.278), 0.235, 0.018, m["blue"], vertices=48, bevel=0.008)
    for x in (-0.1, 0.1):
        for y in (-0.1, 0.1):
            bevelled_cylinder("dark button hole", (x, y, 0.302), 0.043, 0.026, m["black"], vertices=20, bevel=0.004)


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
    parser = argparse.ArgumentParser(description="Generate catch-goose GLB item models.")
    parser.add_argument("--theme", choices=sorted(BUILDERS), help="Generate one theme instead of every model.")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)

    selected = {args.theme: BUILDERS[args.theme]} if args.theme else BUILDERS
    for theme, items in selected.items():
        for slug, builder in items:
            export_item(theme, slug, builder)


if __name__ == "__main__":
    main()
