#!/usr/bin/env python3
"""
Extract one Minecraft 1.21.4+ model JSON and PNG textures from a Blockbench
.bbmodel file.

This script intentionally emits exactly one model JSON per input bbmodel.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PACK_NAME_PATTERN = re.compile(r"[^a-z0-9_.]")
VALID_FACES = ("north", "east", "south", "west", "up", "down")


@dataclass(frozen=True)
class TexturePlan:
    index: int
    file_stem: str
    rel_namespace_path: str
    png_bytes: bytes
    mcmeta_json: dict | None


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def to_pack_name(raw: str) -> str:
    return PACK_NAME_PATTERN.sub("_", raw.lower())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract exactly one 1.21.4+ model JSON and PNG textures from a .bbmodel file."
        )
    )
    parser.add_argument("bbmodel", help="Path to .bbmodel file")
    parser.add_argument(
        "--assets-root",
        default="assets",
        help="Assets root directory containing namespaces (default: assets).",
    )
    parser.add_argument(
        "--namespace",
        default="bloodstone",
        help="Destination namespace (default: bloodstone).",
    )
    parser.add_argument(
        "--asset",
        default=None,
        help="Asset folder name under models/item and textures/item (default: bbmodel stem).",
    )
    parser.add_argument(
        "--variant",
        default="default",
        help="Variant subfolder name (default: default).",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Output model file name without extension (default: bbmodel stem).",
    )
    parser.add_argument(
        "--prefix-textures",
        action="store_true",
        help="Prefix texture file names with model name to reduce collisions.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination files if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without writing files.",
    )
    return parser.parse_args()


def read_bbmodel(path: Path) -> dict:
    if not path.is_file():
        fail(f"bbmodel file does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")


def ensure_list3(value: object, label: str, elem_name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        fail(f"Element '{elem_name}' has invalid {label}; expected 3-number array.")
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        fail(f"Element '{elem_name}' has non-numeric {label}.")
    raise AssertionError("unreachable")


def ensure_list4(value: object, label: str, elem_name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        fail(f"Element '{elem_name}' has invalid {label}; expected 4-number array.")
    try:
        return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]
    except (TypeError, ValueError):
        fail(f"Element '{elem_name}' has non-numeric {label}.")
    raise AssertionError("unreachable")


def read_positive_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if value > 0 else default
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed > 0 else default
    if isinstance(value, str):
        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except ValueError:
            return default
    return default


def decode_texture_source(texture: dict, bbmodel_path: Path, idx: int) -> bytes:
    source = texture.get("source")
    if isinstance(source, str) and source:
        if source.startswith("data:"):
            comma = source.find(",")
            if comma < 0:
                fail(f"Texture {idx} has malformed data URL.")
            payload = source[comma + 1 :]
            try:
                return base64.b64decode(payload, validate=False)
            except (ValueError, binascii.Error):
                fail(f"Texture {idx} has invalid base64 payload.")
        else:
            # Some files may reference external sources.
            external = Path(source)
            if not external.is_absolute():
                external = bbmodel_path.parent / external
            if not external.is_file():
                fail(f"Texture {idx} external source missing: {external}")
            return external.read_bytes()

    path_value = texture.get("path")
    if isinstance(path_value, str) and path_value:
        external = Path(path_value)
        if not external.is_absolute():
            external = bbmodel_path.parent / external
        if not external.is_file():
            fail(f"Texture {idx} external path missing: {external}")
        return external.read_bytes()

    fail(f"Texture {idx} has neither embedded source nor readable external path.")
    raise AssertionError("unreachable")


def build_texture_plans(
    bbmodel: dict,
    bbmodel_path: Path,
    namespace: str,
    asset: str,
    variant: str,
    model_name: str,
    prefix_textures: bool,
) -> list[TexturePlan]:
    raw_textures = bbmodel.get("textures")
    if not isinstance(raw_textures, list):
        fail("bbmodel 'textures' field is missing or not an array.")

    plans: list[TexturePlan] = []
    used_names: set[str] = set()
    for idx, texture in enumerate(raw_textures):
        if not isinstance(texture, dict):
            fail(f"Texture entry {idx} is not an object.")

        raw_name = str(texture.get("name") or f"texture_{idx}")
        stem = Path(raw_name).stem
        stem = to_pack_name(stem if stem else f"texture_{idx}")
        if prefix_textures:
            stem = to_pack_name(f"{model_name}_{stem}")

        if not stem:
            stem = f"texture_{idx}"
        unique_stem = stem
        suffix = 2
        while unique_stem in used_names:
            unique_stem = f"{stem}_{suffix}"
            suffix += 1
        used_names.add(unique_stem)

        data = decode_texture_source(texture, bbmodel_path, idx)
        width = read_positive_int(texture.get("width"), 0)
        height = read_positive_int(texture.get("height"), 0)
        uv_width = read_positive_int(texture.get("uv_width"), 0)
        uv_height = read_positive_int(texture.get("uv_height"), 0)
        frame_time = read_positive_int(texture.get("frame_time"), 1)
        frame_interpolate = bool(texture.get("frame_interpolate"))

        if uv_width > 0 and uv_height > 0:
            width_ratio = (width / uv_width) if width > 0 else 0.0
            height_ratio = (height / uv_height) if height > 0 else 0.0
            is_animated = height_ratio > width_ratio
        else:
            is_animated = width > 0 and height > width

        mcmeta_json: dict | None = None
        if is_animated:
            mcmeta_json = {
                "animation": {
                    "interpolate": frame_interpolate,
                    "frametime": frame_time,
                }
            }

        rel_namespace_path = f"{namespace}:item/{asset}/{variant}/{unique_stem}"
        plans.append(
            TexturePlan(
                index=idx,
                file_stem=unique_stem,
                rel_namespace_path=rel_namespace_path,
                png_bytes=data,
                mcmeta_json=mcmeta_json,
            )
        )
    return plans


def convert_face_uv(
    raw_uv: list[float], model_resolution_width: int, model_resolution_height: int
) -> list[float]:
    scale_width = model_resolution_width / 16.0
    scale_height = model_resolution_height / 16.0
    if scale_width <= 0:
        scale_width = 1.0
    if scale_height <= 0:
        scale_height = 1.0
    return [
        raw_uv[0] / scale_width,
        raw_uv[1] / scale_height,
        raw_uv[2] / scale_width,
        raw_uv[3] / scale_height,
    ]


def resolve_texture_index(raw: object, elem_name: str, face_name: str) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            fail(
                f"Element '{elem_name}' face '{face_name}' uses non-numeric texture ref '{raw}'."
            )
    fail(f"Element '{elem_name}' face '{face_name}' has invalid texture ref.")
    raise AssertionError("unreachable")


def convert_rotation(raw_rotation: object, elem: dict, elem_name: str) -> dict | None:
    if raw_rotation is None:
        return None

    if isinstance(raw_rotation, dict):
        axis = raw_rotation.get("axis")
        angle = raw_rotation.get("angle")
        origin = raw_rotation.get("origin")
        if axis in ("x", "y", "z") and isinstance(angle, (int, float)):
            converted: dict[str, object] = {
                "axis": axis,
                "angle": float(angle),
                "origin": ensure_list3(origin, "rotation.origin", elem_name),
            }
            if raw_rotation.get("rescale") is True:
                converted["rescale"] = True
            return converted
        fail(f"Element '{elem_name}' rotation object is missing axis/angle/origin.")

    # Blockbench cube rotation format: "rotation": [x, y, z], "origin": [x, y, z]
    if isinstance(raw_rotation, list):
        vec = ensure_list3(raw_rotation, "rotation", elem_name)
        non_zero = [(axis, value) for axis, value in zip(("x", "y", "z"), vec) if abs(value) > 1e-7]
        if not non_zero:
            return None
        if len(non_zero) > 1:
            fail(
                f"Element '{elem_name}' has multi-axis rotation {vec}; cannot represent in one vanilla cube rotation."
            )
        axis, angle = non_zero[0]
        return {
            "axis": axis,
            "angle": angle,
            "origin": ensure_list3(elem.get("origin"), "origin", elem_name),
        }

    fail(f"Element '{elem_name}' has unsupported rotation format.")
    raise AssertionError("unreachable")


def build_model_json(
    bbmodel: dict,
    texture_plans: list[TexturePlan],
    model_resolution_width: int,
    model_resolution_height: int,
) -> dict:
    texture_lookup = {plan.index: plan for plan in texture_plans}
    texture_object: dict[str, str] = {
        str(plan.index): plan.rel_namespace_path for plan in texture_plans
    }
    if texture_plans:
        texture_object["particle"] = texture_plans[0].rel_namespace_path

    elements = bbmodel.get("elements")
    if not isinstance(elements, list):
        fail("bbmodel 'elements' field is missing or not an array.")

    converted_elements: list[dict] = []
    for idx, elem in enumerate(elements):
        if not isinstance(elem, dict):
            fail(f"Element entry {idx} is not an object.")

        visible = elem.get("visibility", True)
        if visible is False:
            continue

        elem_name = str(elem.get("name") or f"element_{idx}")
        converted: dict[str, object] = {
            "from": ensure_list3(elem.get("from"), "from", elem_name),
            "to": ensure_list3(elem.get("to"), "to", elem_name),
        }

        rotation = convert_rotation(elem.get("rotation"), elem, elem_name)
        if rotation is not None:
            converted["rotation"] = rotation

        if elem.get("shade") is False:
            converted["shade"] = False

        light_emission = elem.get("light_emission")
        if isinstance(light_emission, int) and light_emission > 0:
            converted["light_emission"] = light_emission

        raw_faces = elem.get("faces")
        if not isinstance(raw_faces, dict):
            fail(f"Element '{elem_name}' is missing valid faces object.")

        faces: dict[str, dict] = {}
        for face_name in VALID_FACES:
            raw_face = raw_faces.get(face_name)
            if not isinstance(raw_face, dict):
                continue

            tex_index = resolve_texture_index(raw_face.get("texture"), elem_name, face_name)
            if tex_index not in texture_lookup:
                fail(
                    f"Element '{elem_name}' face '{face_name}' references missing texture index {tex_index}."
                )
            face_obj: dict[str, object] = {
                "uv": convert_face_uv(
                    ensure_list4(raw_face.get("uv"), "face uv", elem_name),
                    model_resolution_width,
                    model_resolution_height,
                ),
                "texture": f"#{tex_index}",
            }

            face_rotation = raw_face.get("rotation")
            if isinstance(face_rotation, (int, float)) and float(face_rotation) != 0.0:
                face_obj["rotation"] = float(face_rotation)

            tint = raw_face.get("tint")
            if isinstance(tint, int) and tint >= 0:
                face_obj["tintindex"] = tint
            tintindex = raw_face.get("tintindex")
            if isinstance(tintindex, int) and tintindex >= 0:
                face_obj["tintindex"] = tintindex

            faces[face_name] = face_obj

        if not faces:
            continue

        converted["faces"] = faces
        converted_elements.append(converted)

    if not converted_elements:
        fail("No visible textured elements were generated from the bbmodel.")

    out: dict[str, object] = {"textures": texture_object, "elements": converted_elements}

    if bbmodel.get("front_gui_light") is True:
        out["gui_light"] = "front"

    display = bbmodel.get("display")
    if isinstance(display, dict) and display:
        out["display"] = display

    return out


def ensure_writable(paths: list[Path], force: bool) -> None:
    if force:
        return
    collisions = [p for p in paths if p.exists()]
    if collisions:
        preview = "\n".join(f"- {p}" for p in collisions[:10])
        rest = "" if len(collisions) <= 10 else f"\n... and {len(collisions) - 10} more"
        fail(f"Destination files already exist. Use --force to overwrite.\n{preview}{rest}")


def main() -> None:
    args = parse_args()
    bbmodel_path = Path(args.bbmodel).resolve()
    assets_root = Path(args.assets_root).resolve()
    if not assets_root.exists() or not assets_root.is_dir():
        fail(f"Assets root directory does not exist: {assets_root}")

    namespace = to_pack_name(args.namespace)
    if namespace != args.namespace.lower():
        print(f"NOTE: sanitized namespace '{args.namespace}' -> '{namespace}'")

    model_name = to_pack_name(args.model_name or bbmodel_path.stem)
    asset = to_pack_name(args.asset or bbmodel_path.stem)
    variant = to_pack_name(args.variant)
    if not model_name:
        fail("Computed empty model name.")
    if not asset:
        fail("Computed empty asset name.")
    if not variant:
        fail("Computed empty variant name.")

    bbmodel = read_bbmodel(bbmodel_path)
    model_resolution_width = read_positive_int(
        bbmodel.get("resolution", {}).get("width"), 16
    )
    model_resolution_height = read_positive_int(
        bbmodel.get("resolution", {}).get("height"), 16
    )
    texture_plans = build_texture_plans(
        bbmodel=bbmodel,
        bbmodel_path=bbmodel_path,
        namespace=namespace,
        asset=asset,
        variant=variant,
        model_name=model_name,
        prefix_textures=args.prefix_textures,
    )
    model_json = build_model_json(
        bbmodel, texture_plans, model_resolution_width, model_resolution_height
    )

    model_dir = assets_root / namespace / "models" / "item" / asset / variant
    texture_dir = assets_root / namespace / "textures" / "item" / asset / variant
    model_path = model_dir / f"{model_name}.json"
    texture_paths = [texture_dir / f"{t.file_stem}.png" for t in texture_plans]
    mcmeta_paths = [
        texture_dir / f"{t.file_stem}.png.mcmeta"
        for t in texture_plans
        if t.mcmeta_json is not None
    ]

    ensure_writable([model_path, *texture_paths, *mcmeta_paths], args.force)

    print(f"Input bbmodel : {bbmodel_path}")
    print(f"Model output  : {model_path}")
    print(f"Texture output: {texture_dir}")
    print(f"Model JSON files to write: 1")
    print(f"PNG textures to write    : {len(texture_paths)}")
    print(f"MCMETA files to write    : {len(mcmeta_paths)}")

    print(f"{'DRY-RUN ' if args.dry_run else ''}WRITE {model_path}")
    for path in texture_paths:
        print(f"{'DRY-RUN ' if args.dry_run else ''}WRITE {path}")
    for path in mcmeta_paths:
        print(f"{'DRY-RUN ' if args.dry_run else ''}WRITE {path}")

    if args.dry_run:
        print("Done (dry-run).")
        return

    model_dir.mkdir(parents=True, exist_ok=True)
    texture_dir.mkdir(parents=True, exist_ok=True)

    model_path.write_text(json.dumps(model_json, indent=2) + "\n", encoding="utf-8")
    for tex, path in zip(texture_plans, texture_paths):
        path.write_bytes(tex.png_bytes)
    for tex in texture_plans:
        if tex.mcmeta_json is None:
            continue
        mcmeta_path = texture_dir / f"{tex.file_stem}.png.mcmeta"
        mcmeta_path.write_text(json.dumps(tex.mcmeta_json, indent=2) + "\n", encoding="utf-8")

    print("Done.")


if __name__ == "__main__":
    main()
