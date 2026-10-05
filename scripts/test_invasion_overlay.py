#!/usr/bin/env python3
"""GPU regression check using the target client's includes (Pillow, numpy, moderngl)."""
import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class Renderer:
    def __init__(self, client, baseline=False):
        self.ctx = moderngl.create_standalone_context(require=330)
        with zipfile.ZipFile(client) as archive:
            def expand(source):
                return re.sub(r"#moj_import <minecraft:([^>]+)>", lambda m: expand(archive.read(
                    "assets/minecraft/shaders/include/" + m[1]).decode()).replace("#version 330", ""), source)
            shader = ROOT / "1.21.11/assets/minecraft/shaders/core"
            def source(name):
                path = shader / name
                return subprocess.check_output(["git","show","5298eeb:"+path.relative_to(ROOT).as_posix()],cwd=ROOT,text=True) if baseline else path.read_text()
            self.program = self.ctx.program(vertex_shader=expand(source("rendertype_text.vsh")),
                                            fragment_shader=expand(source("rendertype_text.fsh")))
        self.buffers = {}
        for index, name in enumerate(("DynamicTransforms", "Fog", "Projection")):
            self.program[name].binding = index
            self.buffers[name] = self.ctx.buffer(reserve=self.program[name].size)
            self.buffers[name].bind_to_uniform_block(index)
        dynamic = np.zeros(40, dtype="f4")
        dynamic[:16] = np.eye(4, dtype="f4").flatten()
        dynamic[16:20] = 1
        dynamic[24:] = np.eye(4, dtype="f4").flatten()
        self.buffers["DynamicTransforms"].write(dynamic.tobytes())
        fog = np.zeros(12, dtype="f4")
        fog[4:10] = 1e7
        self.buffers["Fog"].write(fog.tobytes())
        self.light = self.ctx.texture((1, 1), 4, bytes([255] * 4))
        self.light.use(2)
        self.program["Sampler0"] = 0
        self.program["Sampler2"] = 2
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.fonts = {}
        self.textures = {}

    def font(self, name):
        if name in self.fonts:
            return self.fonts[name]
        namespace, path = name.split(":")
        result = {}
        for provider in json.loads((ROOT / f"assets/{namespace}/font/{path}.json").read_text(encoding="utf-8"))["providers"]:
            if provider["type"] == "space":
                result.update({char: (advance, None, 0, 0, 0) for char, advance in provider["advances"].items()})
                continue
            assert provider["type"] == "bitmap"
            ns, texture = provider["file"].split(":")
            sheet = Image.open(ROOT / f"assets/{ns}/textures/{texture}").convert("RGBA")
            rows = provider["chars"]
            w, h = sheet.width // len(rows[0]), sheet.height // len(rows)
            scale = provider["height"] / h
            for row, chars in enumerate(rows):
                for col, char in enumerate(chars):
                    if char == "\0":
                        continue
                    tile = sheet.crop((col*w, row*h, (col+1)*w, (row+1)*h))
                    bounds = tile.getchannel("A").getbbox()
                    advance = int((bounds[2] if bounds else 0) * scale + .5) + 1
                    result.setdefault(char, (advance, tile, w*scale, h*scale, 7-provider["ascent"]))
        self.fonts[name] = result
        return result

    def glyph(self, tile, x, y, width, height, color):
        key = (tile.size, tile.tobytes())
        texture = self.textures.get(key)
        if texture is None:
            texture = self.ctx.texture(tile.size, 4, tile.tobytes())
            texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
            self.textures[key] = texture
        texture.use(0)
        data = np.array([[x,y,0,*color,0,0], [x,y+height,0,*color,0,1],
                         [x+width,y+height,0,*color,1,1], [x+width,y,0,*color,1,0]], dtype="f4")
        vb = self.ctx.buffer(data.tobytes())
        lights = self.ctx.buffer(np.zeros((4,2),dtype="i4").tobytes())
        indices = self.ctx.buffer(np.array([0,1,2,0,2,3], dtype="i4").tobytes())
        vao = self.ctx.vertex_array(self.program, [(vb,"3f 4f 2f","Position","Color","UV0"),
                                                  (lights,"2i","UV2")],indices)
        vao.render(moderngl.TRIANGLES)
        vao.release(); vb.release(); lights.release(); indices.release()

    def render(self, component, size, actionbar, scale=1, offset_y=0):
        width, height = size
        pixels = (width*scale,height*scale)
        target = self.ctx.simple_framebuffer(pixels, components=4)
        target.use(); target.clear(0,0,0,0)
        projection = np.array([[2/width,0,0,-1],[0,-2/height,0,1],[0,0,-1,0],[0,0,0,1]],dtype="f4")
        self.buffers["Projection"].write(projection.T.tobytes())
        runs = []
        def walk(node, style):
            if isinstance(node, str): node = {"text":node}
            if isinstance(node, list):
                for child in node: walk(child,style)
                return
            style = style | {k:node[k] for k in ("font","color","shadow_color") if k in node}
            for char in node.get("text", ""):
                runs.append((self.font(style["font"])[char],style))
            for child in node.get("extra",[]): walk(child,style)
        walk(component,{"font":"minecraft:invasion_hud_top","color":"#ffffff","shadow_color":0})
        advance = sum(glyph[0] for glyph,style in runs)
        x, y = width//2-int(advance/2), (height-72 if actionbar else 3) + offset_y
        named = {"white":"ffffff", "gray":"aaaaaa", "gold":"ffaa00"}
        for (step,tile,w,h,up), style in runs:
            if tile:
                value = named.get(style["color"],style["color"].lstrip("#"))
                color = tuple(int(value[i:i+2],16)/255 for i in (0,2,4)) + (1,)
                shadow = style["shadow_color"] & 0xffffffff
                if shadow >> 24:
                    c = tuple(((shadow >> n)&255)/255 for n in (16,8,0,24))
                    self.glyph(tile,x+1,y+up+1,w,h,c)
                self.glyph(tile,x,y+up,w,h,color)
            x += step
        image = Image.frombytes("RGBA",pixels,target.read(components=4)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        target.release()
        return image


def relocate(component):
    if isinstance(component,str): return component
    if isinstance(component,list): return list(map(relocate,component))
    result = dict(component)
    font = result.get("font","")
    if font.startswith("minecraft:invasion_"):
        result["font"] = "bloodinvasion:overlay/" + font.split(":")[1]
    if "extra" in result: result["extra"] = list(map(relocate,result["extra"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client",type=Path,required=True)
    parser.add_argument("--samples",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    renderer = Renderer(args.client)
    args.output.mkdir(parents=True,exist_ok=True)
    files = sorted(args.samples.glob("4-always-*.json"))
    files += sorted(args.samples.glob("4-neutralizing-*.json"))
    assert files
    checked = 0
    for size in ((427,240),(640,360),(960,540),(1920,1080),(3840,2160)):
        for path in files:
            source = json.loads(path.read_text(encoding="utf-8"))
            expected = renderer.render(source,size,False,offset_y=0)
            actual = renderer.render(relocate(source),size,True)
            assert expected.tobytes() == actual.tobytes(), (size,path.name)
            assert actual.getbbox() is not None
            checked += 1
    sample = json.loads((args.samples / "overlay-respawn.json").read_text(encoding="utf-8"))
    result = renderer.render(sample,(640,360),True)
    assert result.crop((0,0,640,60)).getbbox() is not None
    assert result.crop((0,280,640,315)).getbbox() is not None
    renderer.render(sample,(640,360),True,2).save(args.output / "overlay-respawn.png")
    for char in "ABCD0123456789Йй":
        font = {"font":"minecraft:invasion_hud_top","text":char}
        result = renderer.render(font,(640,360),True)
        bounds = result.getbbox()
        assert bounds and bounds[1] >= 280, (char,bounds)
        checked += 1
    branding = {"font":"minecraft:invasion_branding", "text":"\ue700"}
    for size in ((320,240),(427,240),(640,360),(1920,1080)):
        branded = renderer.render(branding,size,True)
        bounds = branded.getbbox()
        left = (size[0]-85)/2
        assert bounds and abs(bounds[0]-left) <= 1 and abs(bounds[2]-(left+85)) <= 1
        assert 4 <= bounds[1] <= 5 and bounds[3] <= 17
        assert branded.crop((0,17,*size)).getbbox() is None
        assert renderer.font("minecraft:invasion_branding")["\ue700"][0] == 86
        checked += 1
    unchanged = ["#ffffff","#f6c644","#fd7e01","#fb5a00","#fb5a01","#fb5a02","#fb5b12","#fc6363","#fc6464","#fc6767"]
    def ordinary(color):
        return {"font":"minecraft:invasion_hud_top","text":"Bloodstone Йй", "color":color}
    current = {color:renderer.render(ordinary(color),(640,360),True).tobytes() for color in unchanged}
    device = renderer.ctx.info['GL_RENDERER']
    baseline = Renderer(args.client,baseline=True)
    for color in unchanged:
        assert baseline.render(ordinary(color),(640,360),True).tobytes() == current[color], color
        checked += 1
    print(f"{checked} GPU checks passed; shader compiled on {device}; existing BSE effects unchanged")


if __name__ == "__main__":
    main()
