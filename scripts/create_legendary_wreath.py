#!/usr/bin/env python3
"""Create a Java composite wreath from the 29 original legendary weapon models.

Run from the resource-pack root. Does not build or deploy the resource pack.
The editable Generic Model is a visual assembly; runtime parts inherit the original
Java models so that their geometry, UVs, textures and texture animations are preserved.
"""

import base64
import itertools
import json
import math
from pathlib import Path
import re
import uuid

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "integrations/legendary_wreath"
MODEL_ROOT = ROOT / "assets/blooddonate/models/item/hats/legendary_wreath"
MODEL_ID = "blooddonate:item/hats/legendary_wreath"
DEG = math.pi / 180


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def vecmul(a, v):
    return [sum(a[i][j] * v[j] for j in range(3)) for i in range(3)]


def rotation(x=0, y=0, z=0):
    cx, cy, cz = (math.cos(v * DEG) for v in (x, y, z))
    sx, sy, sz = (math.sin(v * DEG) for v in (x, y, z))
    return matmul(matmul([[1, 0, 0], [0, cx, -sx], [0, sx, cx]],
                         [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]),
                  [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])


def euler(m):
    y = math.asin(max(-1, min(1, m[0][2])))
    if abs(m[0][2]) < 0.999999:
        x, z = math.atan2(-m[1][2], m[2][2]), math.atan2(-m[0][1], m[0][0])
    else:
        x, z = math.atan2(m[2][1], m[1][1]), 0
    return [round(v / DEG, 6) for v in (x, y, z)]


def bb_euler(m):
    """Blockbench bone rotations use ZYX, unlike Java item display's XYZ."""
    y = math.asin(max(-1, min(1, -m[2][0])))
    if abs(m[2][0]) < 0.999999:
        x, z = math.atan2(m[2][1], m[2][2]), math.atan2(m[1][0], m[0][0])
    else:
        x, z = 0, math.atan2(-m[0][1], m[1][1])
    return [round(v / DEG, 6) for v in (x, y, z)]


def resource(ref, kind, suffix):
    ns, name = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
    return ROOT / "assets" / ns / kind / (name + suffix)


def resolve(ref, seen=()):
    assert ref not in seen, f"Parent cycle: {ref}"
    d = json.loads(resource(ref, "models", ".json").read_text())
    parent = resolve(d["parent"], (*seen, ref)) if "parent" in d else {}
    return parent | d | {"textures": parent.get("textures", {}) | d.get("textures", {})}


def points(element):
    rot = element.get("rotation", {})
    origin = rot.get("origin", [8, 8, 8])
    axis = rot.get("axis", "y")
    angle = rot.get("angle", 0)
    r = rotation(**{axis: angle})
    for p in itertools.product(*zip(element["from"], element["to"])):
        q = [p[i] - origin[i] for i in range(3)]
        if rot.get("rescale"):
            q = [v / math.cos(angle * DEG) if "xyz"[i] != axis else v for i, v in enumerate(q)]
        q = vecmul(r, q)
        yield [q[i] + origin[i] for i in range(3)]


def bounds(elements):
    pts = [p for e in elements for p in points(e)]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def texture_ref(model, name):
    seen = set()
    while name.startswith("#"):
        assert name not in seen, f"Texture cycle: {name}"
        seen.add(name)
        name = model["textures"][name[1:]]
    return name


def normalize_yaw(model):
    """Fold source railgun's +/-67.5 degree rotations into Java's legal range.

    A quarter turn is baked into the axis-aligned box and its face mapping; the
    residual rotation preserves both the shape and UVs. Original files stay intact.
    """
    changed = False
    for element in model["elements"]:
        rot = element.get("rotation", {})
        angle = rot.get("angle", 0)
        if angle in (-45, -22.5, 0, 22.5, 45):
            continue
        assert rot["axis"] == "y" and abs(angle) == 67.5 and not rot.get("rescale"), rot
        before = sorted(tuple(round(v, 5) for v in p) for p in points(element))
        sign = 1 if angle > 0 else -1
        origin = rot["origin"]
        transformed = []
        for p in itertools.product(*zip(element["from"], element["to"])):
            q = vecmul(rotation(y=sign * 90), [p[i] - origin[i] for i in range(3)])
            transformed.append([q[i] + origin[i] for i in range(3)])
        element["from"] = [round(min(p[i] for p in transformed), 7) for i in range(3)]
        element["to"] = [round(max(p[i] for p in transformed), 7) for i in range(3)]
        faces = element["faces"]
        cycle = ["north", "west", "south", "east"]
        old = dict(faces)
        for i, side in enumerate(cycle):
            faces[cycle[(i + sign) % 4]] = old[side]
        for side, delta in (("up", -sign * 90), ("down", sign * 90)):
            faces[side]["rotation"] = (faces[side].get("rotation", 0) + delta) % 360
        rot["angle"] -= sign * 90
        after = sorted(tuple(round(v, 5) for v in p) for p in points(element))
        assert before == after, "Quarter-turn normalization changed the geometry"
        changed = True
    return changed


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "blooddonate:legendary_wreath/" + name))


def canonical_shape(model, name):
    """Align the actual silhouette, including diagonally authored blades, before weaving."""
    lo, hi = bounds(model["elements"])
    size = [hi[i] - lo[i] for i in range(3)]
    if name in {"laser", "shrink_ray", "rail_gun", "endurance_glove", "sculk_crossbow", "lite_mace"}:
        basis = rotation(x=90)
    elif size[0] < size[2]:
        basis = rotation(y=90)
    else:
        basis = rotation()
    pts = [p for element in model["elements"] for p in points(element)]
    flat = [vecmul(basis, p) for p in pts]
    mean = [sum(p[i] for p in flat) / len(flat) for i in range(3)]
    xx = sum((p[0] - mean[0]) ** 2 for p in flat)
    yy = sum((p[1] - mean[1]) ** 2 for p in flat)
    xy = sum((p[0] - mean[0]) * (p[1] - mean[1]) for p in flat)
    principal = math.atan2(2 * xy, xx - yy) / 2 / DEG
    if principal < 0:
        principal += 180
    basis = matmul(rotation(z=90 - principal), basis)
    flat = [vecmul(basis, p) for p in pts]
    lo = [min(p[i] for p in flat) for i in range(3)]
    hi = [max(p[i] for p in flat) for i in range(3)]
    inverse = [list(column) for column in zip(*basis)]
    center = vecmul(inverse, [(lo[i] + hi[i]) / 2 for i in range(3)])
    return basis, center, [hi[i] - lo[i] for i in range(3)]


def main():
    weapons = json.loads((SOURCE / "weapons.json").read_text())
    assert len(weapons) == 29 and len({w["name"] for w in weapons}) == 29
    # Fourteen crossed links make two continuous strands; Excalibur closes the front seam.
    # Broad silhouettes alternate with narrow ones instead of competing with the blades.
    pairs = [(4, 20), (24, 7), (6, 0), (10, 27), (22, 12), (8, 9), (23, 17),
             (26, 25), (13, 18), (15, 2), (16, 28), (1, 21), (14, 5), (11, 19)]
    order = [weapon for pair in pairs for weapon in pair] + [3]
    assert sorted(order) == list(range(len(weapons)))
    slots = {
        "head": {"rotation": [0, 0, 0], "translation": [0, 5.5, 0], "scale": [1.61] * 3},
        "gui": {"rotation": [28, 135, 0], "translation": [0, 1, 0], "scale": [0.8] * 3},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 5, 0], "scale": [0.65] * 3},
        "fixed": {"rotation": [-90, 0, 0], "translation": [0, 0, -8], "scale": [1.0] * 3},
        "thirdperson_righthand": {"rotation": [55, 0, 0], "translation": [0, 3, 1], "scale": [0.6] * 3},
        "thirdperson_lefthand": {"rotation": [55, 0, 0], "translation": [0, 3, 1], "scale": [0.6] * 3},
        "firstperson_righthand": {"rotation": [0, 0, 0], "translation": [0.5, 3.5, 0], "scale": [0.5] * 3},
        "firstperson_lefthand": {"rotation": [0, 0, 0], "translation": [0.5, 3.5, 0], "scale": [0.5] * 3},
    }
    bb = {"meta": {"format_version": "4.10", "model_format": "free", "box_uv": False},
          "name": "Legendary Wreath — 29 weapons", "resolution": {"width": 16, "height": 16},
          "elements": [], "outliner": [], "textures": []}
    texture_indices = {}
    components, report = [], []
    for index, weapon_index in enumerate(order):
        w = weapons[weapon_index]
        model = resolve(w["model"])
        parent = w["model"]
        if normalize_yaw(model):
            parent = MODEL_ID + "/sources/" + w["name"]
            save(MODEL_ROOT / "sources" / (w["name"] + ".json"), {
                "textures": model["textures"], "elements": model["elements"],
                "credit": "Original weapon geometry; quarter-turn normalization for Java item compatibility",
            })
        basis, center, size = canonical_shape(model, w["name"])
        link, strand = divmod(index, 2)
        angle = (link + 0.5) * 360 / len(pairs)
        # Long axes follow the tangent. Opposing shallow diagonals cross at every link;
        # radial separation swaps which strand lies over the other at each next crossing.
        lean = -72 if strand == 0 else 72
        over = 1 if (link + strand) % 2 == 0 else -1
        scale = min(4.15 / size[1], 1.3 / size[0], 0.8 / size[2])
        radius = 5.8 + over * 0.24
        height = 7.9 + (0.08 if strand == 0 else -0.08)
        if index == 28:
            angle, lean, radius, height = 0, 0, 6.2, 8.0
            scale = min(2.3 / size[1], 1.15 / size[0])
        orient = matmul(rotation(y=-angle), matmul(rotation(z=lean), basis))
        destination = [8 + radius * math.sin(angle * DEG), height,
                       8 - radius * math.cos(angle * DEG)]
        offset = vecmul(orient, [scale * (v - 8) for v in center])
        delta = [destination[i] - 8 - offset[i] for i in range(3)]
        displays = {}
        for key, slot in slots.items():
            sr = rotation(*slot["rotation"])
            ss = slot["scale"][0]
            dt = vecmul(sr, delta)
            displays[key] = {
                "rotation": euler(matmul(sr, orient)),
                "translation": [round(slot["translation"][i] + ss * dt[i], 6) for i in range(3)],
                "scale": [round(ss * scale, 8)] * 3,
            }
        part = {"parent": parent, "display": displays}
        save(MODEL_ROOT / (w["name"] + ".json"), part)
        components.append({"type": "minecraft:model", "model": MODEL_ID + "/" + w["name"]})
        group = {"name": w["name"], "uuid": uid(w["name"]), "origin": destination,
                 "rotation": bb_euler(orient), "children": []}
        for j, element in enumerate(model["elements"]):
            eid = uid(w["name"] + f"/{j}")
            rot = element.get("rotation", {})
            er = [0, 0, 0]
            er["xyz".index(rot.get("axis", "y"))] = rot.get("angle", 0)
            element_origin = rot.get("origin", [8, 8, 8])
            transform = lambda v: [round((v[i] - center[i]) * scale + destination[i], 7) for i in range(3)]
            cube = {"name": w["name"] + f"_{j:03}", "uuid": eid, "type": "cube", "box_uv": False,
                    "from": transform(element["from"]), "to": transform(element["to"]),
                    "origin": transform(element_origin), "rotation": er,
                    "rescale": rot.get("rescale", False), "shade": element.get("shade", True), "faces": {}}
            for side in ("north", "south", "east", "west", "up", "down"):
                face = element.get("faces", {}).get(side)
                if not face:
                    cube["faces"][side] = {"uv": [0, 0, 0, 0], "texture": None}
                    continue
                ref = texture_ref(model, face["texture"])
                if ref not in texture_indices:
                    tp = resource(ref, "textures", ".png")
                    image = Image.open(tp)
                    ti = len(bb["textures"])
                    texture_indices[ref] = ti
                    bb["textures"].append({"name": ref.split(":")[-1].replace("/", "_") + ".png", "id": str(ti),
                                           "uuid": uid(ref), "source": "data:image/png;base64," + base64.b64encode(tp.read_bytes()).decode(),
                                           "mode": "bitmap", "width": image.width, "height": image.height,
                                           "uv_width": 16, "uv_height": 16, "particle": ti == 0})
                cube["faces"][side] = {"uv": face["uv"], "texture": texture_indices[ref], "rotation": face.get("rotation", 0)}
            bb["elements"].append(cube)
            group["children"].append(eid)
        bb["outliner"].append(group)
        report.append(w | {"elements": len(model["elements"]), "center": center, "scale": scale,
                           "rotation": euler(orient), "destination": destination})
    item = {"model": {"type": "minecraft:composite", "models": components}}
    save(ROOT / "assets/blooddonate/items/hats/legendary_wreath.json", item)
    # Keep the existing BloodDonate CMD route identical without reformatting unrelated entries.
    registry = ROOT / "assets/minecraft/items/carved_pumpkin.json"
    raw = registry.read_bytes().decode()
    marker = re.search(r'"threshold"\s*:\s*6020\b', raw)
    if marker:
        member = re.search(r'"model"\s*:\s*', raw[marker.end():])
        assert member is not None
        start = marker.end() + member.end()
        previous, length = json.JSONDecoder().raw_decode(raw[start:])
        assert previous["type"] == "minecraft:composite"
        indent = " " * (len(raw[:start].split("\n")[-1]) - len('"model": '))
        replacement = json.dumps(item["model"], indent=4).replace("\n", "\n" + indent)
        registry.write_bytes((raw[:start] + replacement + raw[start + length:]).encode())
    save(SOURCE / "legendary_wreath.bbmodel", bb)
    save(SOURCE / "assembly.json", {
        "name": "Legendary Wreath", "item_model": "blooddonate:hats/legendary_wreath", "custom_model_data": 6020,
        "target": "Minecraft Java 1.21.4+ composite item; opaque/cutout albedo; no shaders or animation required",
        "design": "Two tangential strands with 14 crossed links, alternating over/under depth, Excalibur front clasp; 29 original weapons",
        "budget": "All 29 original weapons, no extra decorative geometry; 837 cubes before parent updates",
        "texture_density": "Uniform scaling per weapon preserves UV proportions; original weapon atlases deliberately retained",
        "display": slots, "elements": len(bb["elements"]), "textures": len(bb["textures"]), "weapons": report,
    })
    print(f"Created {len(components)} weapon parts, {len(bb['elements'])} cubes, {len(bb['textures'])} original textures")


if __name__ == "__main__":
    main()
