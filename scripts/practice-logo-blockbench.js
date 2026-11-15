(async () => {
  const fs = require('fs');
  const root = 'E:/Codex-work/bloodstone-practice-logo-20261028';
  const output = 'E:/Desktop (E)/исходники блудстоун-атлнатис - 19.03.2026/practicertp/release/2026-10-28';
  const canvas = (width, height) => {
    const result = document.createElement('canvas');
    result.width = width;
    result.height = height;
    return result;
  };
  const load = async path => {
    const image = new Image();
    image.src = 'data:image/png;base64,' + fs.readFileSync(path).toString('base64');
    await image.decode();
    return image;
  };
  const save = (image, path) => fs.writeFileSync(path,
    Buffer.from(image.toDataURL('image/png').split(',')[1], 'base64'));
  const source = canvas(1020, 153);
  for (let i = 0; i < 4; i++) source.getContext('2d').drawImage(
    await load(root + '/assets/logo/textures/bloodstone_big/logo_' + (i + 1) + '.png'), i * 255, 0);
  const logo = canvas(528, 80);
  const lc = logo.getContext('2d');
  lc.imageSmoothingEnabled = true;
  lc.imageSmoothingQuality = 'high';
  lc.drawImage(source, 0, 0, 528, 80);
  const shadow = canvas(528, 80);
  const sc = shadow.getContext('2d');
  sc.drawImage(logo, 0, 0);
  sc.globalCompositeOperation = 'source-in';
  sc.fillStyle = '#101012';
  sc.fillRect(0, 0, 528, 80);
  const composite = canvas(534, 160);
  const cc = composite.getContext('2d');
  for (let x = -3; x <= 3; x++) for (let y = -3; y <= 3; y++) {
    if (x * x + y * y <= 10) cc.drawImage(shadow, 3 + x, 3 + y);
  }
  cc.drawImage(logo, 3, 3);
  fs.mkdirSync(root + '/assets/logo/textures/practice_menus', {recursive: true});
  const providers = [];
  const advances = [];
  for (let i = 0; i < 3; i++) {
    const cell = canvas(255, 160);
    const ctx = cell.getContext('2d');
    ctx.drawImage(composite, i * 178, 0, 178, 160, 0, 0, 178, 160);
    save(cell, root + '/assets/logo/textures/practice_menus/logo_' + (i + 1) + '.png');
    const pixels = ctx.getImageData(0, 0, 255, 160).data;
    let inkWidth = 0;
    for (let y = 0; y < 160; y++) for (let x = 0; x < 255; x++) {
      if (pixels[(y * 255 + x) * 4 + 3]) inkWidth = Math.max(inkWidth, x + 1);
    }
    advances.push(Math.floor(.5 + inkWidth / 4) + 1);
    providers.push({type: 'bitmap', file: 'logo:practice_menus/logo_' + (i + 1) + '.png',
      height: 40, ascent: 36, chars: [String.fromCharCode(0xE9E1 + i)]});
  }
  if (advances[0] !== advances[1]) throw new Error('Unequal interior cell advances');
  const join = 44.5 - advances[0];
  const reset = -(13.25 + advances.reduce((sum, n) => sum + n, 0) + join * 2);
  providers.push({type: 'space', advances: {'\uE9E4': 13.25, '\uE9E5': join, '\uE9E6': reset}});
  fs.writeFileSync(root + '/assets/minecraft/font/practice_branding.json', JSON.stringify({providers}, null, 2) + '\n');
  for (const name of ['default', 'bot_training']) {
    const path = root + '/assets/minecraft/font/' + name + '.json';
    const font = JSON.parse(fs.readFileSync(path, 'utf8'));
    if (!font.providers.some(provider => provider.type === 'reference' && provider.id === 'minecraft:practice_branding'))
      font.providers.push({type: 'reference', id: 'minecraft:practice_branding'});
    fs.writeFileSync(path, JSON.stringify(font, null, 2) + '\n');
  }
  const previews = [
    ['bot_training/home_7', 'logo-bot-final.png', 222],
    ['practice_v4/arenas_ru', 'logo-arenas-final.png', 168],
    ['practice_v4/ppk_home_ru', 'logo-kits-final.png', 222]
  ];
  for (const [name, filename, height] of previews) {
    const preview = canvas(690, 810);
    const ctx = preview.getContext('2d');
    ctx.fillStyle = '#35363b';
    ctx.fillRect(0, 0, 690, 810);
    ctx.imageSmoothingEnabled = false;
    const menu = await load(root + '/assets/minecraft/textures/gui/' + name + '.png');
    ctx.drawImage(menu, 0, 0, 176, height, 81, 114, 528, height * 3);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(composite, 0, 0, 534, 86, 81 + 21.25 * 3, 114 - 23 * 3, 133.5 * 3, 21.5 * 3);
    save(preview, output + '/' + filename);
  }
  return {advances, join, reset, source: [1020, 153], cells: [255, 160], logoGui: [132, 20], previews};
})()
