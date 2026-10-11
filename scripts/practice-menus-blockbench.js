(font) => {
  const reference = Texture.all.find(t => t.name === 'PracticeRTP template');
  if (!reference) throw new Error('PracticeRTP template is missing');
  const source = reference.canvas;
  const canvas = (w,h) => {const c=document.createElement('canvas');c.width=w;c.height=h;return c};
  const crop = (x,y,w,h) => {const c=canvas(w,h);c.getContext('2d').drawImage(source,x,y,w,h,0,0,w,h);return c};
  const clear = (c,x,y,w,h) => {const ctx=c.getContext('2d');ctx.fillStyle='#c6c6c6';ctx.fillRect(x,y,w,h);return c};
  const outer = clear(crop(0,0,176,166),3,3,170,160);
  const heading = clear(crop(44,6,88,15),4,3,80,9);
  const button = clear(crop(13,27,71,38),2,2,67,34);
  const cell = crop(7,83,18,18);
  const frame = (ctx,tile,x,y,w,h) => {
    const sx=[0,3,tile.width-3,tile.width],sy=[0,3,tile.height-3,tile.height];
    const dx=[x,x+3,x+w-3,x+w],dy=[y,y+3,y+h-3,y+h];
    for(let r=0;r<3;r++) for(let c=0;c<3;c++) ctx.drawImage(tile,sx[c],sy[r],sx[c+1]-sx[c],sy[r+1]-sy[r],dx[c],dy[r],dx[c+1]-dx[c],dy[r+1]-dy[r]);
  };
  const specs = [
    ...Array.from({length:6},(_,i)=>({name:'rows_'+(i+1),rows:i+1,heading:144})),
    {name:'biomes',rows:3,heading:120,slots:[11,12,13,14,15,22]},
    {name:'arenas',rows:3,heading:104,slots:[11,12,14,15]},
    {name:'queue',rows:6,heading:128,slots:[1,3,5,7,11,13,15,19,21,23,25,29,31,33,37,39,41,43,45,49,50,53]},
    {name:'settings',rows:3,heading:104,slots:[11,15,22],cards:true},
    {name:'kit_settings',rows:6,heading:128,slots:[4,18,19,20,21,22,23,24,25,26,28,29,30,32,33,34]},
    {name:'cooldowns',rows:6,heading:128,slots:[4,18,19,20,21,22,23,24,25,26,45,49,53]},
    {name:'presets',rows:3,heading:112,slots:[11,15,22],cards:true},
    {name:'layout',rows:6,heading:144,slots:[0,1,2,3,4,...Array.from({length:36},(_,i)=>i+9),52,53]}
  ];
  const names=[...specs.map(s=>'practice_'+s.name),'practice_title_font'];
  const existing=Texture.all.filter(t=>names.includes(t.name));
  Undo.initEdit({textures:existing,bitmap:true});
  const generated=[];
  const save=(name,c)=>{
    let texture=Texture.all.find(t=>t.name===name);
    if(texture) texture.edit(out=>{out.width=c.width;out.height=c.height;out.getContext('2d').drawImage(c,0,0)},{no_undo:true});
    else {texture=new Texture({name,width:c.width,height:c.height});texture.fromDataURL(c.toDataURL('image/png')).add(false)}
    generated.push(texture);
  };
  for(const spec of specs) {
    const c=canvas(256,256),ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;
    frame(ctx,outer,0,0,176,114+18*spec.rows);
    frame(ctx,heading,(176-spec.heading)/2,2,spec.heading,15);
    for(let row=0;row<4;row++) for(let col=0;col<9;col++) ctx.drawImage(cell,7+col*18,30+18*spec.rows+row*18+(row===3?4:0));
    for(const slot of spec.slots || Array.from({length:spec.rows*9},(_,i)=>i)) {
      const x=7+slot%9*18,y=17+Math.floor(slot/9)*18;
      if(spec.cards && (slot===11||slot===15)) frame(ctx,button,x-16,y-7,50,30);
      else ctx.drawImage(cell,x,y);
    }
    save('practice_'+spec.name,c);
  }
  const atlas=canvas(128,48),ctx=atlas.getContext('2d');ctx.fillStyle='white';
  [...font.alphabet].forEach((letter,index)=>font.glyphs[letter].forEach((row,y)=>[...row].forEach((p,x)=>{
    if(p==='1')ctx.fillRect(index%16*8+x,Math.floor(index/16)*8+y,1,1);
  })));
  save('practice_title_font',atlas);
  Undo.finishEdit('Align practice menus to native slots and Bloodstone frames',{textures:generated,bitmap:true});
  generated.find(t=>t.name==='practice_settings').select();
  return {panels:specs,fontCharacters:font.alphabet.length,textures:generated.map(t=>t.name)};
}
