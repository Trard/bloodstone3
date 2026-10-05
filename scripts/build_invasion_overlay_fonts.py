#!/usr/bin/env python3
"""Give only Invasion's action-bar HUD a reserved vertical position for its shader."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFSET = 16384
FONTS = ("invasion_objectives", "invasion_hud_top", "invasion_objective_labels", "invasion_faction_hud")


def main():
    destination = ROOT / "assets/bloodinvasion/font/overlay"
    destination.mkdir(parents=True, exist_ok=True)
    for font in FONTS:
        data = json.loads((ROOT / f"assets/minecraft/font/{font}.json").read_text(encoding="utf-8"))
        for provider in data["providers"]:
            if provider["type"] == "bitmap":
                provider["ascent"] -= OFFSET
        (destination / f"{font}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
