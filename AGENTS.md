# AGENTS.md instructions

## Skills
A skill is a set of local instructions in a `SKILL.md` file.

### Available skills
- bloodstone-resourcepack-tools: Use local scripts to add bitmap font suffixes, import `.bbmodel` files, extract model/textures, create item files, rename texture paths, and transfer item namespaces. (file: `skills/bloodstone-resourcepack-tools/SKILL.md`)
- bloodstone-self-refinement: Save reusable lessons from a completed task into `AGENTS.md` or local skills, and create/update a skill when the workflow is worth keeping. (file: `skills/bloodstone-self-refinement/SKILL.md`)

### How to use skills
- Trigger this skill for requests about:
  - adding or updating suffix PNGs in `assets/minecraft/font/suffixes.json`
  - importing models from `new/*.bbmodel`
  - extracting textures/model JSON from Blockbench files
  - creating item definitions in `assets/<namespace>/items/...`
  - moving or copying asset families between namespaces
  - fixing texture naming/path references in generated model JSON
- Trigger `bloodstone-self-refinement` for requests about:
  - saving what was learned from a task
  - updating `AGENTS.md` after a discovery or mistake
  - adding workflow notes to an existing skill
  - creating a new local skill from a repeated workflow
- Read `skills/bloodstone-resourcepack-tools/SKILL.md` and follow the workflow directly.

## Persistent Preferences
- When the user asks to add or import something, assume the source files are in `new/` unless they specify a different location.
- When the user asks to add a new icon, default to the `minecraft` namespace and write under `assets/minecraft/...` unless they explicitly ask for a different namespace.
- When the user asks to add a new icon and the source file has a non-English name, translate it to clear English for the final asset name to keep naming/style consistent. If the filename is opaque or not understandable (for example `image_8589128391.png`), ask the user for the intended English name before creating files.
- When the user asks to add a new symbol to the font, always return both the symbol code and the rendered symbol character so it can be copied directly.
- When Minecraft resource-pack behavior or file format rules are unclear, use Minecraft Wiki as the default external reference and then confirm version-sensitive details against the target version's vanilla assets from the game jar.
