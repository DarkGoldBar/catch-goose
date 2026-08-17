import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "assets" / "models" / "lowpoly-fruit"

FRUIT_ORDER = [
    "whole-watermelon",
    "watermelon-wedge",
    "durian",
    "half-pomegranate",
    "orange",
    "apple",
    "pineapple",
    "banana-bunch",
    "grape-cluster",
]


COLORS = {
    "watermelon_dark": (0.06, 0.28, 0.07, 1),
    "watermelon_mid": (0.16, 0.50, 0.12, 1),
    "watermelon_light": (0.62, 0.84, 0.22, 1),
    "watermelon_flesh": (0.92, 0.08, 0.07, 1),
    "rind_white": (0.88, 0.86, 0.66, 1),
    "durian": (0.62, 0.58, 0.10, 1),
    "durian_shadow": (0.43, 0.43, 0.08, 1),
    "pomegranate_shell": (0.64, 0.06, 0.08, 1),
    "pomegranate_seed": (0.78, 0.02, 0.05, 1),
    "membrane": (0.88, 0.76, 0.54, 1),
    "orange": (1.0, 0.42, 0.02, 1),
    "apple": (0.86, 0.04, 0.05, 1),
    "pineapple": (0.95, 0.58, 0.04, 1),
    "pineapple_groove": (0.63, 0.35, 0.04, 1),
    "banana": (1.0, 0.82, 0.04, 1),
    "banana_shadow": (0.82, 0.58, 0.02, 1),
    "grape": (0.38, 0.12, 0.72, 1),
    "grape_light": (0.55, 0.25, 0.88, 1),
    "leaf": (0.16, 0.50, 0.10, 1),
    "leaf_light": (0.28, 0.62, 0.16, 1),
    "stem": (0.43, 0.21, 0.08, 1),
    "black": (0.02, 0.018, 0.014, 1),
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def mat(name, color, roughness=0.72):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    material.diffuse_color = color
    return material


def make_materials():
    return {name: mat(name, color, 0.55 if "seed" in name or "grape" in name else 0.74) for name, color in COLORS.items()}


def assign(obj, material):
    obj.data.materials.append(material)
    return obj


def flat(obj):
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = False
    return obj


def ico(name, loc, scale, material, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, material)
    return flat(obj)


def cyl(name, loc, radius, depth, material, vertices=12, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return flat(obj)


def cone(name, loc, r1, r2, depth, material, vertices=8, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    return flat(obj)


def cube(name, loc, scale, material, rotation=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, material)
    if bevel:
        modifier = obj.modifiers.new("low bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
    return flat(obj)


def mesh_obj(name, verts, faces, materials, face_materials=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        obj.data.materials.append(material)
    if face_materials:
        for index, material_index in enumerate(face_materials):
            obj.data.polygons[index].material_index = material_index
    return flat(obj)


def ellipsoid_mesh(name, scale, materials, material_for_lon, lat_steps=10, lon_steps=24, loc=(0, 0, 0)):
    verts = []
    faces = []
    face_mats = []
    for i in range(lat_steps + 1):
        theta = math.pi * i / lat_steps
        for j in range(lon_steps):
            phi = 2 * math.pi * j / lon_steps
            verts.append((
                loc[0] + scale[0] * math.sin(theta) * math.cos(phi),
                loc[1] + scale[1] * math.sin(theta) * math.sin(phi),
                loc[2] + scale[2] * math.cos(theta),
            ))
    for i in range(lat_steps):
        for j in range(lon_steps):
            a = i * lon_steps + j
            b = i * lon_steps + (j + 1) % lon_steps
            c = (i + 1) * lon_steps + (j + 1) % lon_steps
            d = (i + 1) * lon_steps + j
            faces.append((a, b, c, d))
            face_mats.append(material_for_lon(j, i))
    return mesh_obj(name, verts, faces, materials, face_mats)


def leaf(name, loc, length, width, material, rotation=(0, 0, 0)):
    verts = [
        (0, 0, 0),
        (width * 0.55, 0, length * 0.38),
        (0, 0, length),
        (-width * 0.55, 0, length * 0.38),
        (0, 0.035, length * 0.42),
    ]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 3, 2, 1)]
    obj = mesh_obj(name, verts, faces, [material])
    obj.location = loc
    obj.rotation_euler = rotation
    return obj


def seed(loc, rot, m, scale=(0.035, 0.018, 0.07)):
    obj = ico("black watermelon seed", loc, scale, m["black"], 1)
    obj.rotation_euler = rot
    return obj


def build_whole_watermelon(m):
    materials = [m["watermelon_light"], m["watermelon_dark"]]
    ellipsoid_mesh(
        "striped whole watermelon",
        (0.58, 0.58, 0.50),
        materials,
        lambda j, _i: 0 if j % 4 in (0, 1) else 1,
        8,
        24,
        (0, 0, 0.50),
    )
    cyl("short curled watermelon stem", (0, 0, 1.03), 0.035, 0.20, m["stem"], 7, (0.35, 0, 0))
    cone("stem hook", (0.04, 0, 1.15), 0.045, 0.012, 0.15, m["leaf"], 7, (0, 1.15, 0))


def build_watermelon_wedge(m):
    angle = math.radians(54)
    r = 0.72
    thickness = 0.18
    z0, z1 = 0.22, 0.86
    verts = [
        (0, -thickness, z1), (-r * math.sin(angle), -thickness, z0), (r * math.sin(angle), -thickness, z0),
        (0, thickness, z1), (-r * math.sin(angle), thickness, z0), (r * math.sin(angle), thickness, z0),
    ]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (0, 2, 5, 3), (1, 4, 5, 2)]
    mesh_obj("red triangular watermelon flesh", verts, faces, [m["watermelon_flesh"]])
    cube("white rind band", (0, 0, z0 - 0.015), (0.72, 0.205, 0.055), m["rind_white"], bevel=0.01)
    cube("green outer rind band", (0, 0, z0 - 0.085), (0.76, 0.215, 0.065), m["watermelon_dark"], bevel=0.01)
    for x, z in [(-0.22, 0.56), (0.0, 0.62), (0.22, 0.56), (-0.12, 0.74), (0.14, 0.75), (0.0, 0.42)]:
        seed((x, -0.205, z), (math.radians(90), 0, 0), m)


def build_durian(m):
    ico("durian oval core", (0, 0, 0.55), (0.43, 0.40, 0.55), m["durian"], 2)
    for zi in range(8):
        z = 0.08 + zi * 0.135
        ring_radius = 0.39 * math.sin((zi + 1) / 9 * math.pi)
        count = max(9, int(18 * ring_radius / 0.39))
        for j in range(count):
            a = 2 * math.pi * (j / count + (zi % 2) * 0.04)
            x, y = ring_radius * math.cos(a), ring_radius * math.sin(a)
            spike = cone("durian spike", (x, y, z), 0.070, 0.0, 0.24, m["durian_shadow"], 5)
            direction = Vector((x, y, z - 0.55)).normalized()
            spike.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    cyl("durian stem", (0, 0, 1.17), 0.055, 0.33, m["stem"], 7)


def build_half_pomegranate(m):
    ico("red half pomegranate shell", (0, 0.10, 0.50), (0.52, 0.26, 0.48), m["pomegranate_shell"], 2)
    cube("flat cut membrane base", (0, -0.18, 0.50), (0.46, 0.032, 0.41), m["membrane"], bevel=0.015)
    for a in (0, math.radians(120), math.radians(240)):
        cube("cream membrane partition", (0, -0.225, 0.50), (0.028, 0.035, 0.34), m["membrane"], (0, a, 0), 0.008)
    for row, z in enumerate([0.34, 0.46, 0.58, 0.70]):
        count = 4 if row in (0, 3) else 6
        for i in range(count):
            x = (i - (count - 1) / 2) * 0.105 + (0.025 if row % 2 else 0)
            if abs(x) + abs(z - 0.52) * 0.55 < 0.42:
                ico("ruby pomegranate seed", (x, -0.255, z), (0.042, 0.034, 0.042), m["pomegranate_seed"], 1)
    for a in range(6):
        cone("pomegranate crown", (0.0, -0.02, 1.00), 0.035, 0.005, 0.19, m["stem"], 4, (0.6, 0, a * math.pi / 3))


def build_orange(m):
    ellipsoid_mesh("faceted orange", (0.48, 0.48, 0.44), [m["orange"]], lambda _j, _i: 0, 8, 18, (0, 0, 0.47))
    cyl("orange top nub", (0, 0, 0.92), 0.035, 0.08, m["leaf"], 7)
    for a in range(6):
        leaf("orange calyx point", (0, 0, 0.91), 0.14, 0.06, m["leaf"], (math.radians(78), 0, a * math.pi / 3))
    leaf("orange leaf", (0.02, 0, 0.93), 0.36, 0.18, m["leaf_light"], (math.radians(78), 0, math.radians(86)))


def build_apple(m):
    ellipsoid_mesh("squat faceted apple", (0.50, 0.46, 0.36), [m["apple"]], lambda _j, _i: 0, 8, 18, (0, 0, 0.45))
    ico("top apple dimple shadow", (0, 0, 0.80), (0.20, 0.18, 0.07), m["pomegranate_shell"], 1)
    cyl("apple stem", (0, 0, 0.93), 0.035, 0.22, m["stem"], 7, (0.15, 0.2, 0))
    leaf("apple leaf", (0.03, 0.01, 0.91), 0.38, 0.19, m["leaf_light"], (math.radians(76), 0, math.radians(78)))


def build_pineapple(m):
    ellipsoid_mesh("pineapple oval body", (0.42, 0.40, 0.62), [m["pineapple"]], lambda _j, _i: 0, 9, 18, (0, 0, 0.54))
    for zi in range(7):
        z = 0.12 + zi * 0.13
        z_norm = max(-0.95, min(0.95, (z - 0.54) / 0.62))
        ring = math.sqrt(1 - z_norm * z_norm)
        for j in range(12):
            a = 2 * math.pi * (j / 12 + zi * 0.055)
            x = (0.42 * ring + 0.010) * math.cos(a)
            y = (0.40 * ring + 0.010) * math.sin(a)
            patch = cube("raised pineapple diamond", (x, y, z), (0.070, 0.018, 0.050), m["pineapple_groove"], (0.55, 0, a + math.pi / 4), 0.004)
            patch.rotation_euler.rotate_axis("X", math.radians(18))
    for level in range(3):
        count = 7 - level
        for j in range(count):
            a = 2 * math.pi * (j / count + level * 0.08)
            leaf("pineapple crown leaf", (0, 0, 1.05 + level * 0.07), 0.42 - level * 0.06, 0.12, m["leaf"], (math.radians(45 - level * 8), 0, a))


def banana_curve(name, offset, angle, m):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = 0.055
    curve.bevel_resolution = 0
    curve.resolution_v = 4
    spline = curve.splines.new("POLY")
    spline.points.add(8)
    for i, point in enumerate(spline.points):
        t = i / 8
        x = -0.42 + t * 0.84
        z = 0.34 + math.sin(t * math.pi) * 0.30
        y = offset + (t - 0.5) * 0.11
        point.co = (x, y, z, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (0, angle, 0)
    obj.data.materials.append(m["banana"])
    cube("banana dark tip", (-0.44, offset - 0.055, 0.33), (0.045, 0.045, 0.045), m["stem"], bevel=0.008)
    cube("banana dark tip", (0.44, offset + 0.055, 0.33), (0.045, 0.045, 0.045), m["stem"], bevel=0.008)
    return obj


def build_banana_bunch(m):
    for index, off in enumerate([-0.18, -0.09, 0, 0.09, 0.18]):
        banana_curve("curved low poly banana", off, math.radians((index - 2) * 5), m)
    ico("brown banana crown", (0, -0.02, 0.76), (0.18, 0.14, 0.11), m["stem"], 1)


def build_grape_cluster(m):
    rows = [(0.0, 4), (0.13, 5), (0.26, 4), (0.39, 3), (0.52, 2), (0.65, 1)]
    for row, (zoff, count) in enumerate(rows):
        for i in range(count):
            x = (i - (count - 1) / 2) * 0.16 + (row % 2) * 0.025
            y = -0.02 * row
            material = m["grape_light"] if (i + row) % 3 == 0 else m["grape"]
            ico("faceted purple grape", (x, y, 0.78 - zoff), (0.095, 0.095, 0.095), material, 1)
    cyl("curved grape stem", (0, 0, 0.95), 0.035, 0.34, m["stem"], 7, (0.45, 0.0, -0.25))
    for a in [-0.9, -0.25, 0.45, 1.1]:
        leaf("grape leaf", (0, 0, 0.86), 0.32, 0.16, m["leaf_light"], (math.radians(68), 0, a))


BUILDERS = {
    "whole-watermelon": build_whole_watermelon,
    "watermelon-wedge": build_watermelon_wedge,
    "durian": build_durian,
    "half-pomegranate": build_half_pomegranate,
    "orange": build_orange,
    "apple": build_apple,
    "pineapple": build_pineapple,
    "banana-bunch": build_banana_bunch,
    "grape-cluster": build_grape_cluster,
}


def normalize_to_ground():
    bpy.context.view_layer.update()
    curves = [obj for obj in bpy.context.scene.objects if obj.type == "CURVE"]
    if curves:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in curves:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = curves[0]
        bpy.ops.object.convert(target="MESH")
        bpy.context.view_layer.update()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (low + high) / 2
    size = max((high - low).x, (high - low).y, (high - low).z)
    root = bpy.data.objects.new("fruit_model_root", None)
    bpy.context.collection.objects.link(root)
    for obj in meshes:
        obj.parent = root
    Matrix.Translation((-center.x, -center.y, -low.z))
    for obj in meshes:
        obj.location.x -= center.x
        obj.location.y -= center.y
        obj.location.z -= low.z
    root.scale = (1.2 / size, 1.2 / size, 1.2 / size)
    bpy.context.view_layer.update()
    return root


def build_item(slug):
    clear_scene()
    materials = make_materials()
    BUILDERS[slug](materials)
    return normalize_to_ground()


def export_item(slug):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    output = MODEL_DIR / f"{slug}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=False,
        export_apply=True,
    )
    print(f"exported {output}")


def main():
    parser = argparse.ArgumentParser(description="Build low-poly fruit models. Defaults to no export.")
    parser.add_argument("--item", choices=FRUIT_ORDER + ["all"], required=True)
    parser.add_argument("--export", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)

    items = FRUIT_ORDER if args.item == "all" else [args.item]
    for item in items:
        build_item(item)
        if args.export:
            export_item(item)


if __name__ == "__main__":
    main()
