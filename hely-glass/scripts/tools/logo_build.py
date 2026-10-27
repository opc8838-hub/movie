import sys,base64,asyncio,io,json,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import numpy as np,cv2,potrace
from scipy.optimize import least_squares,minimize
from PIL import Image,ImageDraw,ImageFont
from playwright.async_api import async_playwright

def trace(mask):
    bm=potrace.Bitmap(~mask.astype(bool));path=bm.trace(alphamax=.8,opttolerance=.2)
    parts=[]
    for curve in path:
        p=curve.start_point;parts.append(f'M{p.x:.3f},{p.y:.3f}')
        for s in curve:
            if s.is_corner:parts.append(f'L{s.c.x:.3f},{s.c.y:.3f}L{s.end_point.x:.3f},{s.end_point.y:.3f}')
            else:parts.append(f'C{s.c1.x:.3f},{s.c1.y:.3f} {s.c2.x:.3f},{s.c2.y:.3f} {s.end_point.x:.3f},{s.end_point.y:.3f}')
        parts.append('Z')
    return ''.join(parts)

async def main():
    dest=ROOT/'assets/logo';dest.mkdir(parents=True,exist_ok=True)
    a=np.array(Image.open(ROOT/'src/logo_hely.jpg').convert('RGB'));big=cv2.resize(a,None,fx=4,fy=4,interpolation=cv2.INTER_LANCZOS4)
    gray=cv2.cvtColor(big,cv2.COLOR_RGB2GRAY);_,white=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    hsv=cv2.cvtColor(big,cv2.COLOR_RGB2HSV);purple=cv2.inRange(hsv,np.array([115,40,80]),np.array([150,255,255]))
    # Erode before sampling to exclude antialiasing and JPEG edge chroma.
    pp=cv2.erode(purple,np.ones((25,25),np.uint8));pp[:,:360*4]=0;pp[:,420*4:970*4]=0;pp[:,1020*4:]=0
    rgb=np.median(big[pp>0],axis=0).round().astype(int);color='#'+''.join(f'{v:02x}' for v in rgb)
    contours,_=cv2.findContours(white[200*4:570*4,150*4:530*4],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    pts=max(contours,key=cv2.contourArea)[:,0,:]/4+np.array([150,200])
    fit=least_squares(lambda p:np.linalg.norm(pts-p[:2],axis=1)-p[2],[340,386,164]).x;cx,cy,rad=fit
    # Straight stems plus circular arch, measured on threshold source.
    hx,hy,lw,ax,ay,ro,ri,bottom,rightbottom=272.5,287.5,39.4,341,414,68.5,29,484.5,429.5
    hp=f'M{hx} {hy}H{hx+lw}V{ay-(ro**2-(hx+lw-ax)**2)**.5} A{ro} {ro} 0 0 1 {ax+ro} {ay}V{rightbottom}H{ax+ri}V{ay}A{ri} {ri} 0 0 0 {ax-ri} {ay}V{bottom}H{hx}Z'
    # Wordmark: compare open-source geometric typefaces, keep source contours when insufficient.
    font_results={}
    for name in ['outfit','lexend','urbanist','manrope','plusjakartasans']:
        url=f'https://raw.githubusercontent.com/google/fonts/main/ofl/{name}/'+{'outfit':'Outfit[wght].ttf','lexend':'Lexend[wght].ttf','urbanist':'Urbanist[wght].ttf','manrope':'Manrope[wght].ttf','plusjakartasans':'PlusJakartaSans[wght].ttf'}[name]
        fp=dest/f'{name}.ttf'
        try:
            if not fp.exists():urllib.request.urlretrieve(url,fp)
            best=0
            target=(white[300*4:510*4,590*4:1305*4]>0)
            for weight in [600,650,700,750,800]:
                ft=ImageFont.truetype(str(fp),190*4)
                try:ft.set_variation_by_axes([weight])
                except Exception:pass
                im=Image.new('L',(3400,1000));ImageDraw.Draw(im).text((0,0),'hely.fun',font=ft,fill=255,stroke_width=0)
                box=im.getbbox();im=im.crop(box).resize((700*4,193*4),Image.Resampling.LANCZOS)
                cand=np.zeros(target.shape,np.uint8);cand[9*4:202*4,8*4:708*4]=np.array(im)>127
                best=max(best,np.logical_and(cand,target).sum()/np.logical_or(cand,target).sum())
            font_results[name]=float(best)
        except Exception as e:font_results[name]=type(e).__name__
    word=(white[:,560*4:1340*4]>0).astype(np.uint8);word[:280*4]=0;word[520*4:]=0
    # Remove purple from white word mask; purple has its own geometric circle.
    word[:,(970-560)*4:(1020-560)*4]=0
    wp=trace(word)
    dot=f'<circle cx="389.35" cy="468.2" r="22.05" fill="{color}"/>'
    wd=f'<circle cx="996.85" cy="439.4" r="17.3" fill="{color}"/>'
    def mark(light):return f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{("#090909" if light else "#fff")}"/><path d="{hp}" fill="{("#fff" if light else "#090909")}"/>'+dot
    def svg(body,vb):return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{body}</svg>'
    assets={}
    for light in [False,True]:
        mode='light' if light else 'dark';fg='#090909' if light else '#fff'
        assets[f'mark_on_{mode}']=svg(mark(light),f'{cx-rad} {cy-rad} {rad*2} {rad*2}')
        assets[f'lockup_on_{mode}']=svg(mark(light)+f'<path transform="translate(560 0) scale(.25)" d="{wp}" fill="{fg}"/>'+wd,f'{cx-rad} {cy-rad} {1298-(cx-rad)} {rad*2}')
    assets['glyph_h']=svg(f'<path d="{hp}" fill="#fff"/>'+dot,'272.5 287.5 139 204')
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True);page=await browser.new_page()
        for name,s in assets.items():
            (dest/f'{name}.svg').write_text(s,encoding='utf-8')
            data=await page.evaluate('''async s=>{let im=new Image();im.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s);await im.decode();let c=document.createElement('canvas');c.width=4096;c.height=Math.round(4096*im.height/im.width);let x=c.getContext('2d');x.drawImage(im,0,0,c.width,c.height);return c.toDataURL().split(',')[1]}''',s)
            (dest/f'{name}.png').write_bytes(base64.b64decode(data))
        await browser.close()
    # Full original placement for threshold IoU and difference, including separate purple class.
    rebuilt=np.zeros((776,1515,4),np.uint8);lock=Image.open(dest/'lockup_on_dark.png').resize((1122,328),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(1515,776));canvas.alpha_composite(lock,(176,222));rebuilt=np.array(canvas)
    target=(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)>127);target[:200]=0;target[570:]=0;target[:,:150]=0;target[:,1340:]=0
    pred=(rebuilt[:,:,:3].max(2)>127)&(rebuilt[:,:,3]>127)
    iou=np.logical_and(target,pred).sum()/np.logical_or(target,pred).sum()
    diff=np.zeros_like(a);diff[target&pred]=[90,90,90];diff[target&~pred]=[255,80,80];diff[pred&~target]=[40,180,255]
    Image.fromarray(diff).save(ROOT/'out/logo_difference.png')
    sheet=Image.new('RGB',(2400,1900),'#202020');d=ImageDraw.Draw(sheet)
    sheet.paste(Image.fromarray(a).resize((1200,615)),(0,40));sheet.paste(Image.fromarray(diff).resize((1200,615)),(1200,40))
    d.text((20,15),f'Original / vector threshold difference   IoU={iou:.6f}   Purple={color}',fill='white')
    # 400% detail: render clean vector at large size, check across four backgrounds.
    glyph=Image.open(dest/'glyph_h.png').convert('RGBA');glyph.thumbnail((140,210),Image.Resampling.LANCZOS)
    cap=cv2.VideoCapture(str(ROOT/'src/clip1_firedance.mp4'));ok,fr=cap.read();fire=Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)).resize((600,700))
    for j,col in enumerate(['white','#808080','black',None]):
        bg=fire.copy().convert('RGBA') if col is None else Image.new('RGBA',(600,700),col)
        mk=Image.open(dest/('mark_on_light.png' if j==0 else 'mark_on_dark.png')).convert('RGBA');mk=mk.resize((390,390),Image.Resampling.LANCZOS);bg.alpha_composite(mk,(100,60))
        bg.alpha_composite(glyph,(230,470));sheet.paste(bg.convert('RGB'),(j*600,700));d.text((j*600+15,675),['WHITE','GRAY','BLACK','FIRE'][j],fill='white')
    # Explicit 4x edge crops from final 1920-wide lockup size.
    small=Image.open(dest/'lockup_on_dark.png').resize((615,180),Image.Resampling.LANCZOS)
    detail=small.crop((0,0,300,110)).resize((1200,440),Image.Resampling.NEAREST)
    bg=Image.new('RGBA',detail.size,'#808080');bg.alpha_composite(detail);sheet.paste(bg.convert('RGB'),(0,1440))
    d.text((1220,1450),f'4x edge detail\nIoU {iou:.6f}\nCircles fitted geometrically\nStems = straight SVG edges\nWordmark = Potrace Beziers',fill='white')
    sheet.save(ROOT/'out/logo_check.png')
    (dest/'metrics.json').write_text(json.dumps({'purple':color,'outer_circle':fit.tolist(),'iou':float(iou),'font_trials':font_results},indent=2),encoding='utf-8')
    print('IoU',iou,'purple',color,'font trials',font_results)
    if iou<.985:raise RuntimeError('Logo IoU below required 0.985; inspect and refine geometry')
if __name__=='__main__':asyncio.run(main())
