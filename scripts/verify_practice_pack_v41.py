"""Check the built pack against disk and the previous v4 delivery."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive',type=Path)
parser.add_argument('previous',type=Path)
parser.add_argument('--cube-v42',action='store_true',help='Allow only biome/arena art and isolated cube textures')
parser.add_argument('--vanilla-v43',action='store_true',help='Allow only biome, arena and player-kit background PNG changes')
parser.add_argument('--settings-v44',action='store_true',help='Allow only kit/cooldown settings background PNG changes')
parser.add_argument('--controls-v45',action='store_true',help='Allow only biome, arena and three settings background PNG changes')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
with ZipFile(args.archive) as new, ZipFile(args.previous) as old:
    assert new.testzip() is None, 'ZIP CRC error'
    assert len(new.namelist())==len(set(new.namelist())), 'Duplicate archive entries'
    names=set(new.namelist())
    prior=set(old.namelist())
    if args.controls_v45:
        assert names==prior, 'No resource additions or removals allowed'
        allowed=tuple(f'assets/minecraft/textures/gui/practice_v4/{panel}_{lang}.png'
                      for panel in ('biomes','arenas','settings','kit_settings','cooldowns') for lang in ('ru','en'))
    elif args.settings_v44:
        assert names==prior, 'No resource additions or removals allowed'
        allowed=tuple(f'assets/minecraft/textures/gui/practice_v4/{panel}_{lang}.png'
                      for panel in ('kit_settings','cooldowns') for lang in ('ru','en'))
    elif args.vanilla_v43:
        assert names==prior, 'No resource additions or removals allowed'
        allowed=tuple(f'assets/minecraft/textures/gui/practice_v4/{panel}_{lang}.png'
                      for panel in ('biomes','arenas','ppk_home') for lang in ('ru','en'))
    elif args.cube_v42:
        assert not prior-names, 'Existing resource removed'
        assert all(name.startswith('assets/minecraft/textures/item/practice/biomes/') and
                   Path(name).name in ('pixel_top.png','pixel_side.png','pixel_bottom.png') for name in names-prior)
        allowed=('assets/minecraft/textures/gui/practice_v4/biomes_',
                 'assets/minecraft/textures/gui/practice_v4/arenas_',
                 'assets/minecraft/models/item/practice/biomes/',
                 'assets/minecraft/items/practice/biomes/',
                 'assets/minecraft/textures/item/practice/biomes/')
    else:
        assert names==prior, 'Unexpected additions/removals against v4'
        allowed=('assets/minecraft/textures/gui/practice_v4/',
             'assets/minecraft/models/item/practice/biomes/',
             'assets/minecraft/items/practice/biomes/')
    changed=[]
    for name in sorted(names):
        data=new.read(name)
        assert hashlib.sha256(data).digest()==hashlib.sha256((root/name).read_bytes()).digest(), name
        if name.endswith(('.json','.mcmeta')):
            json.loads(data.decode('utf-8-sig'))
        if name not in prior or data!=old.read(name):
            assert name.startswith(allowed), 'Unexpected resource change: '+name
            changed.append(name)
    print(f'OK: {len(names)} files, CRC, source hashes, all JSON; {len(changed)} intended changes against previous v4.')
    for name in changed:print(name)
