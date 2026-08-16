import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
THEME_ORDERS = {
    "toy-clutter": [
        "building-block",
        "toy-car",
        "rubber-ball",
        "key",
        "alarm-clock",
        "pencil",
        "gift-box",
        "rubber-duck",
        "button",
    ],
    "seaside-catch": [
        "fish",
        "crab",
        "shell",
        "starfish",
        "shrimp",
        "octopus",
        "seaweed",
        "pearl-clam",
        "message-bottle",
    ],
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def bounds(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH":
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def import_item(path, loc):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.join()

    joined = bpy.context.object
    joined.name = path.stem
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    low, high = bounds([joined])
    center = (low + high) / 2
    size = max((high - low).x, (high - low).y, (high - low).z)
    joined.data.transform(Matrix.Translation(-center))
    joined.location = Vector(loc)
    joined.scale = (0.9 / size, 0.9 / size, 0.9 / size)
    joined.rotation_euler = (0, 0, math.radians(-22))
    return joined


def add_scene():
    bpy.ops.object.light_add(type="AREA", location=(0, -5, 6))
    light = bpy.context.object
    light.data.energy = 650
    light.data.size = 5

    bpy.ops.mesh.primitive_plane_add(size=7, location=(0, 0, -0.03))
    plane = bpy.context.object
    plane.name = "matte review plane"
    material = bpy.data.materials.new("warm white")
    material.diffuse_color = (0.92, 0.89, 0.82, 1)
    plane.data.materials.append(material)

    bpy.ops.object.camera_add(location=(0, -6.2, 4.4))
    camera = bpy.context.object
    look_at(camera, (0, 0, 0.45))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.5
    bpy.context.scene.camera = camera


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="toy-clutter", choices=sorted(THEME_ORDERS))
    parser.add_argument("--output")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)
    output = args.output or str(ROOT / "assets" / "models" / f"{args.theme}-review.png")

    clear_scene()
    add_scene()
    spacing = 1.55
    for index, slug in enumerate(THEME_ORDERS[args.theme]):
        row, col = divmod(index, 3)
        loc = ((col - 1) * spacing, (1 - row) * spacing, 0.45)
        import_item(ROOT / "assets" / "models" / args.theme / f"{slug}.glb", loc)

    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 1200
    bpy.context.scene.render.resolution_y = 1200
    bpy.context.scene.render.filepath = output
    bpy.context.scene.eevee.taa_render_samples = 64
    bpy.ops.render.render(write_still=True)
    bpy.data.images["Render Result"].save_render(filepath=output)
    print(f"rendered {output}")


if __name__ == "__main__":
    main()
