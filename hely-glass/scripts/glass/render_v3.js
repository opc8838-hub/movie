/* MIT optical core by Zanwei Guo / CellMotion. Production motion and layout only. */
const output=document.querySelector('#output'),ctx=output.getContext('2d');
const gc=Object.assign(document.createElement('canvas'),{width:1920,height:1080});
const core=GlassRevealCore,renderer=core.createRenderer(gc,{preserve:true});
const smooth=(a,b,x)=>{let t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t)};
const cache={};async function img(url){if(!cache[url]){let im=new Image();im.src=url;await im.decode();cache[url]=im}return cache[url]}
let glyph,mark,textDark,textLight,lockDark,lockLight;
const TEXT_Y=.32,TEXT_TILE=650,TEXT_SCALE=1.03;
// Precompensate the uploaded lockup for the external text-stage aspect ratio.
// The renderer, all optical equations and LOOKS remain the vendor implementation.
async function textLogo(image){
  const c=document.createElement('canvas');c.width=1400;c.height=Math.round(1400*image.height/image.width/TEXT_Y);
  c.getContext('2d').drawImage(image,0,0,c.width,c.height);
  return core.makeLogo('upload',{url:c.toDataURL()});
}
window.ready=(async()=>{
  glyph=await core.makeLogo('upload',{url:'/assets/logo/glyph_h.svg'});
  mark=await core.makeLogo('upload',{url:'/assets/logo/mark_on_dark.svg'});
  lockDark=await img('/assets/logo/lockup_on_dark.png');lockLight=await img('/assets/logo/lockup_on_light.png');
  textDark=await textLogo(lockDark);textLight=await textLogo(lockLight);
})();
function paintCore(logo,P,T,tile,bg=null,cx=960,cy=540,mod=null){
  renderer.setBackground(bg);renderer.setLogo(logo);
  const f=core.frameAt(Math.max(0,T),P);if(window.tune.vivid)f.uVivid=window.tune.vivid;if(mod)mod(f,T,P);
  renderer.render(f,1920,1080,tile,cx,1080-cy);
  ctx.drawImage(gc,0,0);
  if(window.tune.outline){
    const ps=f.uPlateScale||1,a=tile/2*ps,n=Math.max(2,f.uShapeN||4.8);
    const al=Math.max(0,Math.min(1,(f.uPlateAlpha||0)*(f.uOptics||0)*smooth(2.6,4.2,n)*(1-(f.uDrop||0))));
    const path=(h)=>{ctx.beginPath();for(let i=0;i<=240;i++){const t=i/240*Math.PI*2,c=Math.cos(t),s_=Math.sin(t);
      const x=Math.sign(c)*Math.pow(Math.abs(c),2/n)*h,y=Math.sign(s_)*Math.pow(Math.abs(s_),2/n)*h;i?ctx.lineTo(cx+x,cy+y):ctx.moveTo(cx+x,cy+y)}ctx.closePath()};
    if(al>0.01){ctx.save();ctx.globalAlpha=al;
      path(a-1);ctx.lineWidth=2.2;ctx.strokeStyle='rgba(235,244,255,.55)';ctx.stroke();
      path(a-window.tune.outline);ctx.lineWidth=2.4;ctx.strokeStyle='rgba(8,14,28,.38)';ctx.stroke();
      path(a-window.tune.outline-3);ctx.lineWidth=1.4;ctx.strokeStyle='rgba(235,244,255,.22)';ctx.stroke();ctx.restore()}
  }
  window.lastGlass={center:[cx,cy],tile,look:P.background==='#000000'?'dark':'light',T,frame:f};
}
window.tune=window.tune||{shotScale:.7,endScale:.72,endFinal:1};
function shotGlass(r,bg,c){
  const P={...core.LOOKS.light,logo:'upload',originalColors:true,drift:0,response:.22,present:.95,logoScale:window.tune.shotScale,...(window.tune.shotLook||{})};
  // Scheduling only: a faster entry and release, the vendor spring remains untouched.
  paintCore(glyph,P,(r-.15)*1.35,window.tune.shotTile||499.2,bg,c[0],c[1]);
}
function directLockup(light,alpha=1){
  ctx.save();ctx.globalAlpha=alpha;
  const im=light?lockLight:lockDark,w=806.4,h=w*im.height/im.width;
  ctx.drawImage(im,960-w/2,540-h/2,w,h);ctx.restore();
}
function endingGlass(t){
  const r=t-214/30;
  const P={...core.LOOKS.dark,logo:'upload',originalColors:true,drift:0,ripple:1,present:window.tune.endPresent||.68,finalScale:window.tune.endFinal,logoScale:window.tune.endScale,...(window.tune.endLook||{})};
  paintCore(glyph,P,(r-.12),window.tune.endTile||537.6,null,960,540,window.tune.exitFade?((f,T,P)=>{
    const e=smooth(P.present-.12,P.present+.18,T),d=1-e;
    f.uDisp*=d;f.uFaceDisp*=d;f.uFocusSplit*=d;f.uGlow*=d;f.uCornerPull=1+(f.uCornerPull-1)*d;f.uStreak=1+(f.uStreak-1)*d;f.uSlab*=(.15+.85*d);f.uEtaSpread*=d;f.uDepth*=(.15+.85*d);
  }):null);
  // Let the released white h become the original solid brand roundel.
  if(t>=8.38){
    const a=smooth(8.38,8.48,t),w=176*(1-.30*smooth(8.40,8.6,t));
    ctx.save();ctx.globalAlpha=a;ctx.fillStyle='#000';ctx.fillRect(0,0,1920,1080);ctx.restore();
    ctx.save();ctx.globalAlpha=a;ctx.drawImage(cache['/assets/logo/mark_on_dark.png'],960-w/2,540-w/2,w,w);ctx.restore();
  }
}
window.renderFrame=async data=>{
  await window.ready;await img('/assets/logo/mark_on_dark.png');
  const t=data.frame/30;
  ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=1;ctx.fillStyle=data.frame<34?'#e9e9e9':'#000';ctx.fillRect(0,0,1920,1080);
  if(data.shot){let bg=await img(data.bg);shotGlass(data.r,bg,data.center);delete cache[data.bg];}
  else if(data.frame<34){}
  else if(t<8.6)endingGlass(t);
  else if(t<10.2){}
  else directLockup(false);
  if(t>=11.5){ctx.fillStyle=`rgba(0,0,0,${smooth(11.5,12-1/30,t)})`;ctx.fillRect(0,0,1920,1080);}
  return output.toDataURL('image/png').split(',')[1];
};
