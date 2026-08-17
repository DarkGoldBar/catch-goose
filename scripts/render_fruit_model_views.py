import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_fruit_models


ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "scripts" / "fruit-renders"


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_lighting():
    bpy.ops.object.light_add(type="AREA", location=(0, -3.5, 4.5))
    key = bpy.context.object
    key.name = "large softbox"
    key.data.energy = 550
    key.data.size = 4.0
    bpy.ops.object.light_add(type="POINT", location=(-3, 2, 3))
    fill = bpy.context.object
    fill.name = "small fill"
    fill.data.energy = 60


def add_camera(view):
    if view == "front":
        loc = (0, -4.2, 0.65)
    elif view == "side":
        loc = (4.2, 0, 0.65)
    elif view == "top":
        loc = (0, 0, 4.5)
    else:
        loc = (3.3, -4.0, 2.5)
    bpy.ops.object.camera_add(location=loc)
    camera = bpy.context.object
    look_at(camera, (0, 0, 0.58))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.65 if view != "beauty" else 1.85
    bpy.context.scene.camera = camera
    return camera


def setup_render(path):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    scene.world.color = (0.96, 0.95, 0.92)
    scene.render.filepath = str(path)


def render_view(item, view):
    generate_fruit_models.build_item(item)
    add_lighting()
    add_camera(view)
    output = RENDER_DIR / item / f"{view}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    setup_render(output)
    bpy.ops.render.render(write_still=True)
    print(f"rendered {output}")
    return output


def make_sheet(item):
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        print(f"cannot make sheet without Pillow: {exc}")
        return
    paths = [RENDER_DIR / item / f"{view}.png" for view in ["front", "side", "top", "beauty"]]
    images = [Image.open(path).convert("RGB") for path in paths]
    w, h = images[0].size
    sheet = Image.new("RGB", (w * 2, h * 2), (245, 243, 238))
    for index, image in enumerate(images):
        x = (index % 2) * w
        y = (index // 2) * h
        sheet.paste(image, (x, y))
    draw = ImageDraw.Draw(sheet)
    draw.line((w, 0, w, h * 2), fill=(210, 210, 205), width=3)
    draw.line((0, h, w * 2, h), fill=(210, 210, 205), width=3)
    output = RENDER_DIR / item / f"{item}-sheet.png"
    sheet.save(output)
    print(f"sheet {output}")


def main():
    parser = argparse.ArgumentParser(description="Render fruit model review views without exporting GLB.")
    parser.add_argument("--item", choices=generate_fruit_models.FRUIT_ORDER + ["all"], required=True)
    parser.add_argument("--view", choices=["front", "side", "top", "beauty", "all"], default="all")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)

    items = generate_fruit_models.FRUIT_ORDER if args.item == "all" else [args.item]
    views = ["front", "side", "top", "beauty"] if args.view == "all" else [args.view]
    for item in items:
        for view in views:
            render_view(item, view)
        if set(views) == {"front", "side", "top", "beauty"}:
            make_sheet(item)


if __name__ == "__main__":
    main()
