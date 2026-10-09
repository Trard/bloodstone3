"""Layout proof using exported Blockbench panels and vanilla icons; NOT an in-game screenshot."""
import argparse
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-jar', type=Path, required=True)
    args = parser.parse_args()
    data=json.loads((ROOT/'sources/practice-menus/title-glyphs.json').read_text('utf-8'))
    atlas=Image.open(ROOT/'assets/minecraft/textures/gui/practice/title_font.png').convert('RGBA')
    advances={c:max(row.rfind('1') for row in data['glyphs'][c])+2 for c in data['alphabet']}
    advances[' ']=3

    def small_text(image,value,x=None,y=6):
        value=value.upper()
        width=sum(advances.get(c,5) for c in value)-1
        if x is None:x=(176-width)//2
        for c in value:
            if c!=' ':
                i=data['alphabet'].index(c)
                tile=atlas.crop((i%16*8,i//16*8,i%16*8+8,i//16*8+8))
                black=Image.new('RGBA',tile.size,(40,40,40,255))
                black.putalpha(tile.getchannel('A'))
                image.alpha_composite(black,(x,y))
            x+=advances.get(c,5)

    with ZipFile(args.client_jar) as jar:
        def texture(path):
            return Image.open(BytesIO(jar.read('assets/minecraft/textures/'+path+'.png'))).convert('RGBA')

        def cube(tile):
            # Thumbnail projection of vanilla block faces, not a replacement item texture.
            out=Image.new('RGBA',(16,16))
            for box,coeffs,shade in [
                ((1,1),(.8,1.6,-6.4,-.8,1.6,0),1.0),
                ((1,4),(1.6,0,0,-.8,1.6,0),.75),
                ((8,4),(1.6,0,0,.8,1.6,-5.6),.55)]:
                if box==(1,1):
                    face=tile.resize((8,8),Image.Resampling.NEAREST).transform((14,7),Image.Transform.AFFINE,(.57,1.14,-3.43,-.57,1.14,4.0),Image.Resampling.NEAREST)
                else:
                    face=tile.resize((7,10),Image.Resampling.NEAREST).transform((7,13),Image.Transform.AFFINE,(1,0,0,(-.5 if box[0]==1 else .5),1,(0 if box[0]==1 else -3)),Image.Resampling.NEAREST)
                rgb=face.convert('RGB').point(lambda p:int(p*shade)).convert('RGBA')
                rgb.putalpha(face.getchannel('A'));out.alpha_composite(rgb,box)
            return out

        def icon(image,name,slot):
            x,y=8+slot%9*18,18+slot//9*18
            if name=='shulker_box':
                tile=texture('entity/shulker/shulker').crop((16,0,32,16))
                tile=cube(tile)
            elif name=='redstone_block':
                tile=cube(texture('block/redstone_block'))
            elif name=='cobweb':tile=texture('block/cobweb')
            else:tile=texture('item/'+name).crop((0,0,16,16))
            image.alpha_composite(tile,(x,y))

        sheet=Image.new('RGBA',(388,458),(31,34,39,255))
        for name,title,origin in [
            ('settings','Настройки',(12,18)),('settings','Settings',(200,18)),
            ('cooldowns','Настройки КД',(12,200)),('cooldowns','Cooldown Settings',(200,200))]:
            panel=Image.open(ROOT/f'assets/minecraft/textures/gui/practice/{name}.png').convert('RGBA')
            small_text(panel,title)
            if name=='settings':
                for slot,item in [(11,'diamond_sword'),(15,'shulker_box'),(22,'oak_door')]:icon(panel,item,slot)
            else:
                for slot,item in [(4,'arrow'),(18,'diamond_sword'),(19,'tnt_minecart'),(20,'ender_pearl'),(21,'trident'),
                                  (23,'wind_charge'),(24,'elytra'),(25,'cobweb'),(26,'lime_dye'),
                                  (45,'barrier'),(49,'clock_00'),(53,'redstone_block')]:icon(panel,item,slot)
            height=168 if name=='settings' else 222
            sheet.alpha_composite(panel.crop((0,0,176,height)),origin)
        ImageDraw.Draw(sheet).text((12,437),'LAYOUT PROOF / NOT AN IN-GAME CAPTURE',fill=(218,224,232,255))
        target=ROOT/'sources/practice-menus/layout-preview-v2.png'
        sheet.resize((1164,1374),Image.Resampling.NEAREST).save(target)
        print(target)


if __name__=='__main__':main()
