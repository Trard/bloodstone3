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
            if name.endswith('shulker_box'):
                color=name.removesuffix('_shulker_box') if name!='shulker_box' else None
                tile=cube(texture('entity/shulker/shulker'+('_'+color if color else '')).crop((16,0,32,16)))
            elif name in ('skeleton_skull','wither_skeleton_skull'):
                kind='wither_skeleton' if name.startswith('wither') else 'skeleton'
                tile=cube(texture('entity/skeleton/'+kind).crop((8,8,16,16)))
            elif name=='ender_chest':
                tile=cube(texture('entity/chest/ender').crop((14,33,28,47)))
            elif name=='bell':
                tile=cube(texture('entity/bell/bell_body').crop((6,6,12,13)))
            elif name in ('grass_block','sand','red_sand','red_mushroom_block','snow','bedrock','carved_pumpkin','bookshelf'):
                base='grass_block_top' if name=='grass_block' else name
                tile=texture('block/'+base)
                if name=='grass_block':
                    gray=tile.convert('L');tile=Image.merge('RGBA',(gray.point(lambda p:p//2),gray,gray.point(lambda p:p//3),tile.getchannel('A')))
                tile=cube(tile)
            elif name=='redstone_block':
                tile=cube(texture('block/redstone_block'))
            elif name=='cobweb':tile=texture('block/cobweb')
            else:tile=texture('item/'+name).crop((0,0,16,16))
            image.alpha_composite(tile,(x,y))

        vanilla_glyphs={}
        default=json.loads(jar.read('assets/minecraft/font/include/default.json'))
        for provider in default['providers']:
            if provider['type']!='bitmap':continue
            glyph_atlas=texture(provider['file'].split(':')[-1][:-4])
            rows=provider['chars'];cw=glyph_atlas.width//len(rows[0]);ch=glyph_atlas.height//len(rows)
            for row,line in enumerate(rows):
                for col,char in enumerate(line):
                    if char=='\0' or char in vanilla_glyphs:continue
                    tile=glyph_atlas.crop((col*cw,row*ch,(col+1)*cw,(row+1)*ch))
                    bbox=tile.getbbox()
                    vanilla_glyphs[char]=(tile,(bbox[2]+1 if bbox else 4),7-provider['ascent'])

        def inventory_label(image,lang,rows):
            x,y=8,20+18*rows
            for c in 'Инвентарь' if lang=='ru' else 'Inventory':
                tile,advance,dy=vanilla_glyphs[c]
                colored=Image.new('RGBA',tile.size,(64,64,64,255))
                colored.putalpha(tile.getchannel('A'));image.alpha_composite(colored,(x,y+dy));x+=advance

        mappings={
            'settings':[(11,'diamond_sword'),(15,'shulker_box'),(40,'oak_door')],
            'cooldowns':[(8,'arrow'),(10,'diamond_sword'),(12,'tnt_minecart'),(14,'ender_pearl'),(16,'trident'),
                         (28,'wind_charge'),(30,'elytra'),(32,'cobweb'),(34,'lime_dye'),
                         (45,'barrier'),(49,'clock_00'),(53,'redstone_block')],
            'kit_settings':[(8,'arrow'),(9,'skeleton_skull'),(11,'diamond_sword'),(13,'golden_apple'),(15,'milk_bucket'),
                            (17,'splash_potion'),(27,'totem_of_undying'),(29,'glistering_melon_slice'),(31,'clock_00'),
                            (33,'recovery_compass_00'),(35,'wither_skeleton_skull'),(45,'ender_pearl'),(47,'lime_shulker_box'),
                            (49,'spyglass'),(51,'paper'),(53,'bell')],
            'ppk_home':[(i,'red_shulker_box' if i%3 else 'light_gray_shulker_box') for i in range(9,18)]+
                       [(i,'ender_chest') for i in range(27,36)]+[(45,'carved_pumpkin'),(46,'barrier'),(47,'compass_16'),
                       (48,'experience_bottle'),(50,'nether_star'),(51,'skeleton_skull'),(52,'bookshelf'),(53,'netherite_upgrade_smithing_template')],
            'biomes':[(10,'grass_block'),(13,'sand'),(16,'red_sand'),(28,'red_mushroom_block'),(31,'snow'),(34,'bedrock')],
            'arenas':[(10,'tnt_minecart'),(12,'diamond_sword'),(14,'netherite_chestplate'),(16,'mace')]
        }
        titles={
            'settings':('Настройки','Settings'),'cooldowns':('Настройки КД','Cooldown Settings'),
            'kit_settings':('Настройки китов','Kit Settings'),'ppk_home':('Киты игрока Player',"Player's Kits"),
            'biomes':('Выбор биома','Select Biome'),'arenas':('Арены','Arenas')}
        definitions=json.loads((ROOT/'sources/practice-menus/v3-layouts.json').read_text('utf-8'))
        specs={p['name']:p for p in definitions['panels']}
        def proof(name,lang):
            panel=Image.open(ROOT/f'assets/minecraft/textures/gui/practice_v3/{name}_{lang}.png').convert('RGBA')
            small_text(panel,titles[name][0 if lang=='ru' else 1])
            for slot,item in mappings[name]:icon(panel,item,slot)
            inventory_label(panel,lang,specs[name]['rows'])
            return panel.crop((0,0,176,114+18*specs[name]['rows']))

        for lang in ('ru','en'):
            sheet=Image.new('RGBA',(388,262),(31,34,39,255))
            sheet.alpha_composite(proof('settings',lang),(12,14))
            sheet.alpha_composite(proof('cooldowns',lang),(200,14))
            ImageDraw.Draw(sheet).text((12,245),'LAYOUT PROOF / NOT IN-GAME',fill=(218,224,232,255))
            path=ROOT/f'sources/practice-menus/quality-preview-v3-{lang}.png'
            sheet.resize((1164,786),Image.Resampling.NEAREST).save(path)
            print(path)
        sheet=Image.new('RGBA',(576,500),(31,34,39,255))
        for i,name in enumerate(mappings):
            sheet.alpha_composite(proof(name,'ru'),(12+i%3*188,12+i//3*238))
        ImageDraw.Draw(sheet).text((12,485),'LAYOUT PROOF / APPROXIMATE BLOCK THUMBNAILS / NOT IN-GAME',fill=(218,224,232,255))
        target=ROOT/'sources/practice-menus/all-menus-v3.png'
        sheet.resize((1152,1000),Image.Resampling.NEAREST).save(target)
        print(target)


if __name__=='__main__':main()
