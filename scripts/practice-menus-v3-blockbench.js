(font,layout) => {
  const reference=Texture.all.find(t=>t.name==='PracticeRTP template');
  if(!reference)throw new Error('PracticeRTP template missing');
  const source=reference.canvas;
  const canvas=(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c};
  const crop=(x,y,w,h)=>{const c=canvas(w,h);c.getContext('2d').drawImage(source,x,y,w,h,0,0,w,h);return c};
  const clear=(c,x,y,w,h)=>{const ctx=c.getContext('2d');ctx.fillStyle='#c6c6c6';ctx.fillRect(x,y,w,h);return c};
  const outer=clear(crop(0,0,176,166),3,3,170,160);
  const heading=clear(crop(44,6,88,15),4,3,80,9);
  const button=clear(crop(13,27,71,38),2,2,67,34);
  const cell=crop(7,83,18,18);
  const frame=(ctx,tile,x,y,w,h)=>{
    const sx=[0,3,tile.width-3,tile.width],sy=[0,3,tile.height-3,tile.height];
    const dx=[x,x+3,x+w-3,x+w],dy=[y,y+3,y+h-3,y+h];
    for(let r=0;r<3;r++)for(let c=0;c<3;c++)ctx.drawImage(tile,sx[c],sy[r],sx[c+1]-sx[c],sy[r+1]-sy[r],dx[c],dy[r],dx[c+1]-dx[c],dy[r+1]-dy[r]);
  };
  const advance=c=>c===' '?3:Math.max(...font.glyphs[c].map(r=>r.lastIndexOf('1')))+2;
  const text=(ctx,label,lang)=>{
    const value=label[lang],width=[...value].reduce((n,c)=>n+advance(c),0)-1;
    const x=label.align==='center'?label.x-Math.floor(width/2):label.align==='right'?label.x-width:label.x;
    if(width>label.maxWidth||x<3||x+width>173)throw new Error(label.key+' / '+lang+' overflow '+width+' > '+label.maxWidth);
    ctx.fillStyle=label.shade;
    let cursor=x;
    for(const c of value) {
      if(c!==' ')font.glyphs[c].forEach((row,y)=>[...row].forEach((p,dx)=>{if(p==='1')ctx.fillRect(cursor+dx,label.y+y,1,1)}));
      cursor+=advance(c);
    }
  };
  const rendered=[];
  for(const spec of layout.panels)for(const lang of ['ru','en']) {
    const c=canvas(256,256),ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;
    frame(ctx,outer,0,0,176,114+18*spec.rows);
    frame(ctx,heading,(176-spec.heading)/2,2,spec.heading,15);
    for(let row=0;row<4;row++)for(let col=0;col<9;col++)ctx.drawImage(cell,7+col*18,30+18*spec.rows+row*18+(row===3?4:0));
    for(const box of spec.cards||[]) {
      frame(ctx,button,box.x,box.y,box.w,box.h);
      ctx.fillStyle='#cecece';ctx.fillRect(box.x+2,box.y+2,box.w-4,box.h-4);
    }
    for(const slot of spec.cells||[])ctx.drawImage(cell,7+slot%9*18,17+Math.floor(slot/9)*18);
    for(const label of spec.labels||[])text(ctx,label,lang);
    rendered.push({name:'practice_v3_'+spec.name+'_'+lang,canvas:c});
  }
  const names=rendered.map(t=>t.name),existing=Texture.all.filter(t=>names.includes(t.name)),changed=[];
  Undo.initEdit({textures:existing,bitmap:true});
  for(const generated of rendered) {
    let t=Texture.all.find(t=>t.name===generated.name);
    if(t)t.edit(c=>{c.width=256;c.height=256;c.getContext('2d').drawImage(generated.canvas,0,0)},{no_undo:true});
    else {t=new Texture({name:generated.name,width:256,height:256});t.fromDataURL(generated.canvas.toDataURL('image/png')).add(false)}
    changed.push(t);
  }
  Undo.finishEdit('Design localized Bloodstone practice menus v3',{textures:changed,bitmap:true});
  changed.find(t=>t.name==='practice_v3_settings_ru').select();
  return {created:changed.length,names:changed.map(t=>t.name)};
}
