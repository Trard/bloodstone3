# Logo Asset Standards and Conventions

This document outlines the requirements and conventions for logos stored in the `assets/logo/textures/` directory.

## Standard Logo Dimensions

To maintain a consistent pixel resolution and uniform visual appearance across all server gamemodes, all logo textures must adhere to the following dimension guidelines:

| Logo Type | Standard Width | Standard Height | Description |
| :--- | :--- | :--- | :--- |
| **Horizontal Logos** | **255 px** (range: 254-256 px) | Scaled proportionally | Used for most gamemode/server titles (e.g. `ffa_kb.png`, `bloodstone.png`). |
| **Square Logos / Icons** | **255 px** | **255 px** | Used for round or square badges (e.g. `discord.png`). |

### Scaling New Logos
When importing a new logo, do **not** use the raw high-resolution output (e.g., 1024px or higher). Instead, resize the image so that its **width is exactly 255 pixels**, letting the height scale proportionally:
- **Example 1**: An image with a 4:1 aspect ratio (`1024 x 256`) must be scaled to `255 x 64`.
- **Example 2**: An image with a 3.94:1 aspect ratio (`1024 x 260`) must be scaled to `255 x 65`.

You can do this on Linux/WSL using ImageMagick:
```bash
convert new_logo.png -resize 255x assets/logo/textures/new_logo.png
```

---

## Font Configuration (`assets/minecraft/font/logos.json`)

Logos are registered as `bitmap` providers in the custom Minecraft font:

```json
{
    "type": "bitmap",
    "file": "logo:logo_name.png",
    "ascent": 0,
    "height": 40,
    "chars": [
        "\uF807"
    ]
}
```

### Config Properties:
- **`file`**: The texture path relative to `assets/logo/textures/` (using the `logo:` namespace prefix).
- **`height`**: The height in-game (in pixels). Main gamemodes typically use **`40`** or **`36`**. Sub-logos use **`26`** or **`28`**.
- **`ascent`**: The vertical offset from the baseline. Usually set to **`0`**, or slightly positive/negative to align with adjacent text.
- **`chars`**: A unique Unicode character (usually in the Private Use Area range, e.g. `\uF800` - `\uF8FF`).
