(font, layout, numberFont) => {
  const reference=Texture.all.find(t=>t.name==='PracticeRTP template');
  if(!reference) throw new Error('PracticeRTP template missing');
  const canvas=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
  const crop=(x,y,w,h)=>{const c=canvas(w,h);c.getContext('2d').drawImage(reference.canvas,x,y,w,h,0,0,w,h);return c};
  const outer=crop(0,0,176,166),heading=crop(44,6,88,15),cell=crop(7,83,18,18);
  for(const [c,x,y,w,h] of [[outer,3,3,170,160],[heading,4,3,80,9]]) {
    const ctx=c.getContext('2d');ctx.fillStyle='#c6c6c6';ctx.fillRect(x,y,w,h);
  }
  const frame=(ctx,tile,x,y,w,h)=>{
    const sx=[0,3,tile.width-3,tile.width],sy=[0,3,tile.height-3,tile.height];
    const dx=[x,x+3,x+w-3,x+w],dy=[y,y+3,y+h-3,y+h];
    for(let r=0;r<3;r++)for(let c=0;c<3;c++)ctx.drawImage(tile,sx[c],sy[r],sx[c+1]-sx[c],sy[r+1]-sy[r],dx[c],dy[r],dx[c+1]-dx[c],dy[r+1]-dy[r]);
  };
  const rendered=[];
  for(const spec of layout.panels)for(const lang of ['ru','en']) {
    const c=canvas(256,256),ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;
    frame(ctx,outer,0,0,176,114+18*spec.rows);
    frame(ctx,heading,(176-spec.heading)/2,2,spec.heading,15);
    for(let row=0;row<4;row++)for(let col=0;col<9;col++)ctx.drawImage(cell,7+col*18,30+18*spec.rows+row*18+(row===3?4:0));
    for(const slot of spec.cells||[])ctx.drawImage(cell,7+slot%9*18,17+Math.floor(slot/9)*18);
    for(const box of spec.cards) {
      const {x,y,w,h}=box;
      ctx.fillStyle='#ababab';ctx.fillRect(x+1,y,w-2,h);ctx.fillRect(x,y+1,w,h-2);
      ctx.fillStyle='#d0d0d0';ctx.fillRect(x+1,y+1,w-2,h-2);
    }
    // Fine separators organise kits/utility rows without repeating every tooltip.
    if(spec.id===14) {
      ctx.fillStyle='#ababab';ctx.fillRect(8,100,160,1);
      ctx.fillStyle='#dedede';ctx.fillRect(8,101,160,1);
    }
    for(const label of spec.labels) {
      const value=label[lang];
      const advance=char=>Math.max(...numberFont.glyphs[char].map(row=>row.lastIndexOf('1')))+2;
      const width=[...value].reduce((sum,char)=>sum+advance(char),0)-1;
      let cursor=label.x-Math.floor(width/2);
      ctx.fillStyle=label.shade;
      for(const char of value) {
        numberFont.glyphs[char].forEach((row,y)=>[...row].forEach((p,x)=>{if(p==='1')ctx.fillRect(cursor+x,label.y+y,1,1)}));
        cursor+=advance(char);
      }
    }
    rendered.push({name:'practice_v4_'+spec.name+'_'+lang,canvas:c});
  }
  const atlas=canvas(192,Math.ceil(font.alphabet.length/16)*12),ctx=atlas.getContext('2d');ctx.fillStyle='#ffffff';
  [...font.alphabet].forEach((letter,i)=>font.glyphs[letter].forEach((row,y)=>[...row].forEach((p,x)=>{
    if(p==='1')ctx.fillRect(i%16*12+x,Math.floor(i/16)*12+y,1,1);
  })));
  rendered.push({name:'practice_v4_title_font',canvas:atlas});
  const names=rendered.map(t=>t.name),existing=Texture.all.filter(t=>names.includes(t.name)),changed=[];
  Undo.initEdit({textures:existing,bitmap:true});
  for(const generated of rendered) {
    let texture=Texture.all.find(t=>t.name===generated.name);
    if(texture)texture.edit(c=>{c.width=generated.canvas.width;c.height=generated.canvas.height;c.getContext('2d').drawImage(generated.canvas,0,0)},{no_undo:true});
    else texture=new Texture({name:generated.name}).fromDataURL(generated.canvas.toDataURL('image/png')).add(false);
    changed.push(texture);
  }
  Undo.finishEdit('Practice menus v4.5: slots only beneath controls, original item positions',{textures:changed,bitmap:true});
  changed.find(t=>t.name==='practice_v4_cooldowns_ru').select();
  return {textures:changed.length};
}
