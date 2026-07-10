#!/usr/bin/env python3
"""Generate compact 2d_doll totems from current Mojang player skins.

For every nickname this script:
  - resolves the licensed Minecraft profile through Mojang APIs;
  - downloads the current 64x64 skin;
  - copies only UV regions used by My Totem Doll's 2d_doll into a 32x16 atlas;
  - creates a child model that reuses the shared 2d_doll geometry;
  - assigns or preserves a custom_model_data threshold in totem_of_undying.json.

Examples:
  python3 scripts/generate_player_totems.py Notch jeb_
  python3 scripts/generate_player_totems.py Trard --force
  python3 scripts/generate_player_totems.py Notch --cmd 1023
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,16}$")
USER_AGENT = "BloodStone-player-totem-generator/1.0"

ATLAS_WIDTH = 32
ATLAS_HEIGHT = 16


@dataclass(frozen=True)
class AtlasRegion:
    source: tuple[int, int, int, int]
    destination: tuple[int, int]


# These are the exact source-skin areas referenced by My Totem Doll's 2d_doll.bbmodel.
# The layout fits them into 32x16 while preserving all base and outer-layer pixels.
ATLAS_REGIONS = (
    AtlasRegion((0, 0, 24, 8), (0, 0)),
    AtlasRegion((8, 8, 16, 16), (24, 0)),
    AtlasRegion((40, 8, 48, 16), (0, 8)),
    AtlasRegion((20, 20, 28, 27), (8, 8)),
    AtlasRegion((20, 36, 28, 43), (16, 8)),
    AtlasRegion((44, 20, 47, 21), (24, 8)),
    AtlasRegion((44, 29, 47, 30), (27, 8)),
    AtlasRegion((44, 31, 46, 32), (30, 8)),
    AtlasRegion((44, 36, 47, 37), (24, 9)),
    AtlasRegion((44, 45, 47, 46), (27, 9)),
    AtlasRegion((44, 47, 46, 48), (30, 9)),
    AtlasRegion((37, 52, 40, 53), (24, 10)),
    AtlasRegion((37, 61, 40, 62), (27, 10)),
    AtlasRegion((37, 63, 39, 64), (30, 10)),
    AtlasRegion((53, 52, 56, 53), (24, 11)),
    AtlasRegion((53, 61, 56, 62), (27, 11)),
    AtlasRegion((53, 63, 55, 64), (30, 11)),
)


class GeneratorError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlayerSkin:
    requested_name: str
    canonical_name: str
    uuid: str
    slim: bool
    source_url: str
    source_width: int
    source_height: int
    original_png: bytes
    compact_png: bytes

    @property
    def asset_name(self) -> str:
        return self.canonical_name.lower()


@dataclass(frozen=True)
class TotemPlan:
    skin: PlayerSkin
    custom_model_data: int
    model_ref: str
    model_path: Path
    texture_path: Path
    existing_entry: bool


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Generate compact My Totem Doll-style totems from Mojang player names.")
    parser.add_argument("nicknames", nargs="+", help="One or more licensed Minecraft player names.")
    parser.add_argument("--root", default=str(default_root), help=f"Resource-pack root (default: {default_root}).")
    parser.add_argument("--start-cmd", type=int, default=1000, help="First automatic CMD value (default: 1000).")
    parser.add_argument("--end-cmd", type=int, default=4999, help="Last automatic CMD value (default: 4999).")
    parser.add_argument("--cmd", type=int, default=None, help="Explicit CMD value; only valid with one nickname.")
    parser.add_argument("--force", action="store_true", help="Refresh an existing nickname while preserving its CMD.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve and validate skins, but do not write files.")
    return parser.parse_args()


def request_bytes(url: str, label: str, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,image/png,*/*"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read()
                if response.status == 204 or not data:
                    raise GeneratorError(f"{label}: empty response (HTTP {response.status}).")
                return data
        except GeneratorError:
            raise
        except urllib.error.HTTPError as exc:
            if exc.code in (204, 400, 404):
                raise GeneratorError(f"{label}: not found or invalid request (HTTP {exc.code}).") from exc
            last_error = exc
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == attempts:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                break
        time.sleep(float(attempt))
    raise GeneratorError(f"{label}: request failed after {attempts} attempts: {last_error}")


def request_json(url: str, label: str) -> dict:
    raw = request_bytes(url, label)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeneratorError(f"{label}: response is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise GeneratorError(f"{label}: expected a JSON object.")
    return value


def resolve_skin(nickname: str) -> PlayerSkin:
    if not USERNAME_PATTERN.fullmatch(nickname):
        raise GeneratorError(f"Invalid Minecraft nickname: {nickname!r}")

    encoded_name = urllib.parse.quote(nickname, safe="")
    profile = request_json(f"https://api.mojang.com/users/profiles/minecraft/{encoded_name}", f"Profile {nickname}")
    uuid = profile.get("id")
    canonical_name = profile.get("name")
    if not isinstance(uuid, str) or len(uuid) != 32 or not isinstance(canonical_name, str):
        raise GeneratorError(f"Profile {nickname}: Mojang response does not contain a valid UUID and name.")

    session = request_json(
        f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}?unsigned=false",
        f"Skin metadata {canonical_name}",
    )
    properties = session.get("properties")
    if not isinstance(properties, list):
        raise GeneratorError(f"Skin metadata {canonical_name}: missing properties list.")

    encoded_textures: str | None = None
    for prop in properties:
        if isinstance(prop, dict) and prop.get("name") == "textures" and isinstance(prop.get("value"), str):
            encoded_textures = prop["value"]
            break
    if encoded_textures is None:
        raise GeneratorError(f"Skin metadata {canonical_name}: missing textures property.")

    try:
        padding = "=" * (-len(encoded_textures) % 4)
        texture_payload = base64.b64decode(encoded_textures + padding).decode("utf-8")
        texture_data = json.loads(texture_payload)
        skin_data = texture_data["textures"]["SKIN"]
        skin_url = skin_data["url"]
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GeneratorError(f"Skin metadata {canonical_name}: malformed textures property.") from exc
    if not isinstance(skin_url, str):
        raise GeneratorError(f"Skin metadata {canonical_name}: invalid skin URL.")

    parsed_url = urllib.parse.urlparse(skin_url)
    if parsed_url.hostname != "textures.minecraft.net":
        raise GeneratorError(f"Skin metadata {canonical_name}: unexpected texture host {parsed_url.hostname!r}.")
    secure_url = urllib.parse.urlunparse(parsed_url._replace(scheme="https"))
    original_png = request_bytes(secure_url, f"Skin texture {canonical_name}")
    width, height, rgba = decode_png(original_png, canonical_name)
    if (width, height) == (64, 32):
        normalized_rgba = remap_legacy_skin(rgba)
    elif (width, height) == (64, 64):
        normalized_rgba = rgba
    else:
        raise GeneratorError(f"Skin texture {canonical_name}: expected 64x64 or legacy 64x32 PNG, got {width}x{height}.")

    metadata = skin_data.get("metadata")
    slim = isinstance(metadata, dict) and metadata.get("model") == "slim"
    compact_png = encode_png_rgba(ATLAS_WIDTH, ATLAS_HEIGHT, build_compact_atlas(normalized_rgba, 64, 64))
    return PlayerSkin(nickname, canonical_name, uuid, slim, secure_url, width, height, original_png, compact_png)


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def decode_png(data: bytes, label: str) -> tuple[int, int, bytes]:
    if not data.startswith(PNG_SIGNATURE):
        raise GeneratorError(f"Skin texture {label}: response is not a PNG file.")

    position = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    palette: bytes | None = None
    transparency: bytes | None = None
    compressed = bytearray()
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        chunk_data = data[position + 8 : position + 8 + length]
        expected_crc = struct.unpack(">I", data[position + 8 + length : position + 12 + length])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise GeneratorError(f"Skin texture {label}: invalid PNG checksum in {chunk_type!r} chunk.")
        position += 12 + length

        if chunk_type == b"IHDR":
            if len(chunk_data) != 13:
                raise GeneratorError(f"Skin texture {label}: invalid IHDR chunk.")
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", chunk_data)
            if compression != 0 or filter_method != 0:
                raise GeneratorError(f"Skin texture {label}: unsupported PNG compression or filtering method.")
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"tRNS":
            transparency = chunk_data
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if None in (width, height, bit_depth, color_type, interlace):
        raise GeneratorError(f"Skin texture {label}: missing PNG header.")
    if bit_depth != 8 or interlace != 0:
        raise GeneratorError(f"Skin texture {label}: only non-interlaced 8-bit PNG skins are supported.")

    channel_counts = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channel_counts.get(color_type)
    if channels is None:
        raise GeneratorError(f"Skin texture {label}: unsupported PNG color type {color_type}.")
    try:
        filtered = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        raise GeneratorError(f"Skin texture {label}: invalid compressed PNG data.") from exc

    stride = width * channels
    expected_size = height * (stride + 1)
    if len(filtered) != expected_size:
        raise GeneratorError(f"Skin texture {label}: unexpected decoded PNG data size.")

    rows: list[bytes] = []
    offset = 0
    previous = bytes(stride)
    for _ in range(height):
        filter_type = filtered[offset]
        source = filtered[offset + 1 : offset + 1 + stride]
        offset += stride + 1
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = value + left
            elif filter_type == 2:
                decoded = value + above
            elif filter_type == 3:
                decoded = value + ((left + above) // 2)
            elif filter_type == 4:
                decoded = value + paeth_predictor(left, above, upper_left)
            else:
                raise GeneratorError(f"Skin texture {label}: unsupported PNG row filter {filter_type}.")
            row[index] = decoded & 0xFF
        decoded_row = bytes(row)
        rows.append(decoded_row)
        previous = decoded_row

    rgba = bytearray(width * height * 4)
    target = 0
    for row in rows:
        for x in range(width):
            source = x * channels
            if color_type == 6:
                red, green, blue, alpha = row[source : source + 4]
            elif color_type == 2:
                red, green, blue = row[source : source + 3]
                alpha = 255
            elif color_type == 4:
                gray, alpha = row[source : source + 2]
                red = green = blue = gray
            elif color_type == 0:
                gray = row[source]
                red = green = blue = gray
                alpha = 255
            else:
                palette_index = row[source]
                if palette is None or palette_index * 3 + 2 >= len(palette):
                    raise GeneratorError(f"Skin texture {label}: invalid indexed PNG palette.")
                red, green, blue = palette[palette_index * 3 : palette_index * 3 + 3]
                alpha = transparency[palette_index] if transparency is not None and palette_index < len(transparency) else 255
            rgba[target : target + 4] = bytes((red, green, blue, alpha))
            target += 4
    return width, height, bytes(rgba)


def copy_rgba_rect(
    image: bytearray,
    image_width: int,
    source_x: int,
    source_y: int,
    translate_x: int,
    translate_y: int,
    width: int,
    height: int,
    mirror_x: bool,
) -> None:
    copied = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            read_x = width - 1 - x if mirror_x else x
            source_offset = ((source_y + y) * image_width + source_x + read_x) * 4
            copied[(y * width + x) * 4 : (y * width + x + 1) * 4] = image[source_offset : source_offset + 4]
    destination_x = source_x + translate_x
    destination_y = source_y + translate_y
    for y in range(height):
        target_offset = ((destination_y + y) * image_width + destination_x) * 4
        copied_offset = y * width * 4
        image[target_offset : target_offset + width * 4] = copied[copied_offset : copied_offset + width * 4]


def remap_legacy_skin(rgba: bytes) -> bytes:
    if len(rgba) != 64 * 32 * 4:
        raise GeneratorError("Internal error: legacy skin buffer is not 64x32 RGBA.")
    remapped = bytearray(64 * 64 * 4)
    remapped[: len(rgba)] = rgba

    # Same mirror/copy layout used by Minecraft's legacy skin remapper.
    for source_x, source_y, translate_x, translate_y, width, height in (
        (4, 16, 16, 32, 4, 4),
        (8, 16, 16, 32, 4, 4),
        (0, 20, 24, 32, 4, 12),
        (4, 20, 16, 32, 4, 12),
        (8, 20, 8, 32, 4, 12),
        (12, 20, 16, 32, 4, 12),
        (44, 16, -8, 32, 4, 4),
        (48, 16, -8, 32, 4, 4),
        (40, 20, 0, 32, 4, 12),
        (44, 20, -8, 32, 4, 12),
        (48, 20, -16, 32, 4, 12),
        (52, 20, -8, 32, 4, 12),
    ):
        copy_rgba_rect(remapped, 64, source_x, source_y, translate_x, translate_y, width, height, True)
    return bytes(remapped)


def build_compact_atlas(rgba: bytes, width: int, height: int) -> bytes:
    atlas = bytearray(ATLAS_WIDTH * ATLAS_HEIGHT * 4)
    for region in ATLAS_REGIONS:
        source_x1, source_y1, source_x2, source_y2 = region.source
        destination_x, destination_y = region.destination
        if source_x2 > width or source_y2 > height:
            raise GeneratorError(f"Atlas source region {region.source} exceeds the downloaded skin size.")
        region_width = source_x2 - source_x1
        region_height = source_y2 - source_y1
        if destination_x + region_width > ATLAS_WIDTH or destination_y + region_height > ATLAS_HEIGHT:
            raise GeneratorError(f"Atlas destination for region {region.source} exceeds {ATLAS_WIDTH}x{ATLAS_HEIGHT}.")
        for row in range(region_height):
            source_offset = ((source_y1 + row) * width + source_x1) * 4
            target_offset = ((destination_y + row) * ATLAS_WIDTH + destination_x) * 4
            atlas[target_offset : target_offset + region_width * 4] = rgba[source_offset : source_offset + region_width * 4]
    return bytes(atlas)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def filter_png_row(row: bytes, previous: bytes, filter_type: int, bytes_per_pixel: int = 4) -> bytes:
    result = bytearray(len(row))
    for index, value in enumerate(row):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        else:
            predictor = paeth_predictor(left, above, upper_left)
        result[index] = (value - predictor) & 0xFF
    return bytes(result)


def encode_png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise GeneratorError("Internal error: RGBA buffer size does not match compact atlas dimensions.")
    filtered_rows = bytearray()
    previous = bytes(width * 4)
    for y in range(height):
        row = rgba[y * width * 4 : (y + 1) * width * 4]
        candidates = [(filter_type, filter_png_row(row, previous, filter_type)) for filter_type in range(5)]
        filter_type, filtered = min(candidates, key=lambda candidate: sum(min(value, 256 - value) for value in candidate[1]))
        filtered_rows.append(filter_type)
        filtered_rows.extend(filtered)
        previous = row
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(filtered_rows), level=9)
    return PNG_SIGNATURE + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", compressed) + png_chunk(b"IEND", b"")


def load_item_definition(path: Path) -> tuple[dict, list[dict], str, bool]:
    if not path.is_file():
        raise GeneratorError(f"Missing totem item definition: {path}")
    raw_text = path.read_bytes().decode("utf-8")
    try:
        root = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GeneratorError(f"Invalid JSON in {path}: {exc}") from exc
    model = root.get("model") if isinstance(root, dict) else None
    if not isinstance(model, dict) or model.get("type") not in ("range_dispatch", "minecraft:range_dispatch"):
        raise GeneratorError(f"Expected range_dispatch model in {path}.")
    entries = model.get("entries")
    if not isinstance(entries, list):
        raise GeneratorError(f"Expected entries array in {path}.")
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    ends_with_newline = raw_text.endswith(("\n", "\r"))
    return root, entries, newline, ends_with_newline


def entry_threshold(entry: object) -> int | None:
    if not isinstance(entry, dict):
        return None
    threshold = entry.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not float(threshold).is_integer():
        return None
    return int(threshold)


def entry_model_ref(entry: object) -> str | None:
    if not isinstance(entry, dict) or not isinstance(entry.get("model"), dict):
        return None
    value = entry["model"].get("model")
    return value if isinstance(value, str) else None


def make_plans(args: argparse.Namespace, skins: list[PlayerSkin], root: Path, entries: list[dict]) -> list[TotemPlan]:
    if args.start_cmd > args.end_cmd:
        raise GeneratorError("--start-cmd cannot be greater than --end-cmd.")
    if args.cmd is not None and len(skins) != 1:
        raise GeneratorError("--cmd can only be used with one nickname.")

    used_thresholds = {value for entry in entries if (value := entry_threshold(entry)) is not None}
    existing_by_ref: dict[str, int] = {}
    for entry in entries:
        threshold = entry_threshold(entry)
        model_ref = entry_model_ref(entry)
        if threshold is not None and model_ref is not None:
            if model_ref in existing_by_ref:
                raise GeneratorError(f"Duplicate model reference in totem item definition: {model_ref}")
            existing_by_ref[model_ref] = threshold

    reserved_values = [value for value in used_thresholds if args.start_cmd <= value <= args.end_cmd]
    next_automatic = max(reserved_values, default=args.start_cmd - 1) + 1
    plans: list[TotemPlan] = []
    for skin in skins:
        model_ref = f"minecraft:item/totems/{skin.asset_name}"
        model_path = root / "assets" / "minecraft" / "models" / "item" / "totems" / f"{skin.asset_name}.json"
        texture_path = root / "assets" / "minecraft" / "textures" / "item" / "totems" / f"{skin.asset_name}.png"
        existing_cmd = existing_by_ref.get(model_ref)
        if existing_cmd is not None:
            if args.cmd is not None and args.cmd != existing_cmd:
                raise GeneratorError(f"{skin.canonical_name} already uses CMD {existing_cmd}; refusing to change it to {args.cmd}.")
            custom_model_data = existing_cmd
        elif args.cmd is not None:
            if args.cmd in used_thresholds:
                raise GeneratorError(f"CMD {args.cmd} is already used by another model.")
            custom_model_data = args.cmd
        else:
            while next_automatic in used_thresholds:
                next_automatic += 1
            if next_automatic > args.end_cmd:
                raise GeneratorError(f"No free CMD values remain in {args.start_cmd}..{args.end_cmd}.")
            custom_model_data = next_automatic
            next_automatic += 1

        collisions = [path for path in (model_path, texture_path) if path.exists()]
        if collisions and not args.force:
            collision_list = "\n".join(f"- {path}" for path in collisions)
            raise GeneratorError(f"Assets for {skin.canonical_name} already exist. Use --force to refresh them.\n{collision_list}")
        if existing_cmd is None:
            used_thresholds.add(custom_model_data)
        plans.append(TotemPlan(skin, custom_model_data, model_ref, model_path, texture_path, existing_cmd is not None))
    return plans


def child_model_json(skin: PlayerSkin) -> dict:
    return {
        "parent": "minecraft:item/totems/player_doll/2d_doll",
        "textures": {"skin": f"minecraft:item/totems/{skin.asset_name}"},
    }


def write_plans(
    args: argparse.Namespace,
    item_definition: dict,
    entries: list[dict],
    item_path: Path,
    item_newline: str,
    item_ends_with_newline: bool,
    plans: list[TotemPlan],
) -> None:
    for plan in plans:
        action = "UPDATE" if plan.existing_entry else "CREATE"
        skin_type = "slim" if plan.skin.slim else "wide"
        print(
            f"{action} {plan.skin.canonical_name}: CMD {plan.custom_model_data}, {skin_type}, "
            f"{plan.skin.source_width}x{plan.skin.source_height}/{len(plan.skin.original_png)} B -> "
            f"{ATLAS_WIDTH}x{ATLAS_HEIGHT}/{len(plan.skin.compact_png)} B"
        )
        print(f"  model   {plan.model_path}")
        print(f"  texture {plan.texture_path}")

    if args.dry_run:
        print("Done (dry-run; no files written).")
        return

    for plan in plans:
        plan.model_path.parent.mkdir(parents=True, exist_ok=True)
        plan.texture_path.parent.mkdir(parents=True, exist_ok=True)
        plan.model_path.write_text(json.dumps(child_model_json(plan.skin), indent=2) + "\n", encoding="utf-8")
        plan.texture_path.write_bytes(plan.skin.compact_png)
        if not plan.existing_entry:
            entries.append(
                {
                    "threshold": plan.custom_model_data,
                    "model": {"type": "model", "model": plan.model_ref},
                }
            )

    entries.sort(key=lambda entry: (entry_threshold(entry) is None, entry_threshold(entry) or 0))
    item_text = json.dumps(item_definition, indent=4)
    if item_newline != "\n":
        item_text = item_text.replace("\n", item_newline)
    if item_ends_with_newline:
        item_text += item_newline
    item_path.write_text(item_text, encoding="utf-8")
    print(f"UPDATE {item_path}")
    for plan in plans:
        print(
            f'/give @s minecraft:totem_of_undying[minecraft:custom_model_data={{floats:[{plan.custom_model_data}.0f]}}]'
        )


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: Resource-pack root does not exist: {root}", file=sys.stderr)
        return 1

    base_model = root / "assets" / "minecraft" / "models" / "item" / "totems" / "player_doll" / "2d_doll.json"
    if not base_model.is_file():
        print(f"ERROR: Missing shared 2d_doll model: {base_model}", file=sys.stderr)
        return 1

    item_path = root / "assets" / "minecraft" / "items" / "totem_of_undying.json"
    try:
        item_definition, entries, item_newline, item_ends_with_newline = load_item_definition(item_path)
        skins: list[PlayerSkin] = []
        seen_assets: set[str] = set()
        for nickname in args.nicknames:
            print(f"Resolving {nickname}...", file=sys.stderr)
            skin = resolve_skin(nickname)
            if skin.asset_name in seen_assets:
                raise GeneratorError(f"Duplicate resolved player in arguments: {skin.canonical_name}")
            seen_assets.add(skin.asset_name)
            skins.append(skin)
        plans = make_plans(args, skins, root, entries)
        write_plans(args, item_definition, entries, item_path, item_newline, item_ends_with_newline, plans)
    except GeneratorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
