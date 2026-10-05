#!/usr/bin/env python3
"""Simple 16px SMP crate: <=24 cubes, two 16x16 textures, 1 texel/unit, opaque Java item.
Copper palette follows civilization's copper golem mask; gold/turquoise follows its Midas sword.
"""
from pathlib import Path
import base64
import io
import json
import uuid
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'integrations/blooddonate/mechanism/mechanism_crate.bbmodel'


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'blooddonate:mechanism/simple/' + name))


def textures():
    copper = Image.new('RGBA', (16, 16), (178, 98, 71, 255))
    d = ImageDraw.Draw(copper)
    d.rectangle((0, 0, 15, 3), fill=(194, 107, 76))
    d.line((0, 0, 15, 0), fill=(214, 123, 91))
    d.line((0, 1, 0, 14), fill=(194, 107, 76))
    d.line((1, 15, 15, 15), fill=(120, 57, 37))
    d.line((15, 1, 15, 14), fill=(154, 80, 56))
    # Sparse broad pixel clusters, without noise, rivets, grooves or scratches.
    d.rectangle((3, 5, 6, 6), fill=(194, 107, 76))
    d.rectangle((9, 10, 12, 12), fill=(167, 90, 64))
    d.rectangle((2, 12, 3, 13), fill=(154, 80, 56))
    metal = Image.new('RGBA', (16, 16), (228, 161, 78, 255))
    d = ImageDraw.Draw(metal)
    d.rectangle((0, 0, 15, 1), fill=(240, 212, 87))
    d.rectangle((0, 2, 15, 4), fill=(235, 188, 83))
    d.rectangle((0, 10, 15, 11), fill=(217, 127, 73))
    d.rectangle((0, 12, 15, 13), fill=(120, 57, 37))
    d.rectangle((0, 14, 15, 15), fill=(154, 80, 56))
    d.rectangle((12, 12, 13, 13), fill=(54, 182, 165))
    d.point((12, 12), fill=(83, 201, 169))
    out = []
    for name, img in [('mechanism_copper', copper), ('mechanism_metal', metal)]:
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        out.append({'name': name + '.png', 'id': str(len(out)), 'uuid': uid(name), 'mode': 'bitmap',
                    'width': 16, 'height': 16, 'uv_width': 16, 'uv_height': 16,
                    'source': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()})
    return out


def make():
    # Retain the eight transforms already reviewed in Blockbench.
    display = {'gui': {'rotation': [25, 225, 0], 'translation': [0, -0.2, 0], 'scale': [0.66, 0.66, 0.66]},
     'ground': {'rotation': [0, 0, 0], 'translation': [0, 3.5, 0], 'scale': [0.38, 0.38, 0.38]},
     'fixed': {'rotation': [0, 0, 0], 'translation': [0, -0.2, -1], 'scale': [0.8, 0.8, 0.8]},
     'head': {'rotation': [0, 0, 0], 'translation': [0, 10, 0], 'scale': [0.7, 0.7, 0.7]},
     'thirdperson_righthand': {'rotation': [75, 45, 0], 'translation': [0, 2.3, 1], 'scale': [0.36, 0.36, 0.36]},
     'thirdperson_lefthand': {'rotation': [75, 315, 0], 'translation': [0, 2.3, 1], 'scale': [0.36, 0.36, 0.36]},
     'firstperson_righthand': {'rotation': [0, 180, 0], 'translation': [-1, 5.5, -1], 'scale': [0.38, 0.38, 0.38]},
     'firstperson_lefthand': {'rotation': [0, 180, 0], 'translation': [-1, 5.5, -1], 'scale': [0.38, 0.38, 0.38]}}
    elements, groups = [], {}

    def cube(name, a, b, texture=0, group='Copper shell', omit=(), solid_uv=None, front_uv=None):
        x, y, z = [b[i] - a[i] for i in range(3)]
        dims = {'north': (x, y), 'south': (x, y), 'east': (z, y), 'west': (z, y), 'up': (x, z), 'down': (x, z)}
        faces = {}
        for f, (w, h) in dims.items():
            if f in omit:
                faces[f] = {'uv': [0, 0, 0, 0], 'texture': None}
                continue
            uv = front_uv if front_uv and f == 'north' else solid_uv or [0, 0, w, h]
            faces[f] = {'uv': uv, 'texture': texture}
        elements.append({'name': name, 'type': 'cube', 'uuid': uid(name), 'from': a, 'to': b,
                         'origin': [8, 8, 8], 'box_uv': False, 'autouv': 0, 'faces': faces})
        groups.setdefault(group, []).append(uid(name))

    cube('Copper body', [1, 1, 1], [15, 11.5, 15], omit=('up',))
    cube('Copper base', [1, .5, 1], [15, 1, 15], texture=1, solid_uv=[0, 14, 1, 15], omit=('up',))
    cube('Lid seam', [1, 11.5, 1], [15, 12, 15], texture=1, solid_uv=[0, 12, 1, 13], omit=('up', 'down'))
    cube('Copper lid', [1, 12, 1], [15, 15, 15], group='Lid', omit=('down',))
    # Ten-pixel cog, with connected teeth and one-pixel notches.
    pattern = ['....##....', '.##.##.##.', '.########.', '..######..', '##########',
               '##########', '..######..', '.########.', '.##.##.##.', '....##....']
    mask = [[pixel == '#' for pixel in row] for row in pattern]
    active, runs = {}, []
    for y, row in enumerate(mask + [[False] * 10]):
        row_runs, x = [], 0
        while x < 10:
            if not row[x]:
                x += 1
                continue
            start = x
            while x < 10 and row[x]:
                x += 1
            row_runs.append((start, x))
        for interval in list(active):
            if interval not in row_runs:
                runs.append((*interval, active.pop(interval), y))
        for interval in row_runs:
            active.setdefault(interval, y)
    for i, (x0, x1, y0, y1) in enumerate(runs):
        cube(f'Winding gear {i + 1}', [3 + x0, 11.5 - y1, .25], [3 + x1, 11.5 - y0, 1], texture=1,
             group='Winding lock', omit=('south',), front_uv=[x0, y0, x1, y1])
    cube('Square spindle', [7, 5.5, 0], [9, 7.5, .25], texture=1, group='Winding lock', solid_uv=[0, 12, 2, 14], omit=('south',))
    cube('Turquoise pin', [7.5, 6, -.125], [8.5, 7, 0], texture=1, group='Winding lock', solid_uv=[12, 12, 13, 13], omit=('south',))
    bb = {'meta': {'format_version': '4.10', 'model_format': 'java_block', 'box_uv': False},
          'name': 'SMP Mechanism Copper Crate', 'resolution': {'width': 16, 'height': 16}, 'elements': elements,
          'outliner': [{'name': name, 'uuid': uid('group/' + name), 'origin': [8, 8, 8], 'children': children}
                       for name, children in groups.items()], 'textures': textures(), 'display': display}
    assert len(elements) <= 24
    SOURCE.write_text(json.dumps(bb, ensure_ascii=False, indent=2) + '\n')
    faces = sum(f['texture'] is not None for e in elements for f in e['faces'].values())
    print(json.dumps({'cubes': len(elements), 'faces': faces, 'triangles': faces * 2, 'textures': '2 x 16x16',
                      'gear_mask': [''.join('#' if p else '.' for p in row) for row in mask]}))


if __name__ == '__main__':
    make()
