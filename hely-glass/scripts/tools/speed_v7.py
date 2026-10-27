import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
import cv2,numpy as np
from PIL import Image,ImageDraw
def flow(a,b):
    g=lambda x:cv2.cvtColor(cv2.resize(x,(480,270)),cv2.COLOR_RGB2GRAY)
    f=cv2.calcOpticalFlowFarneback(g(a),g(b),None,.5,3,15,3,5,1.2,0);m=np.linalg.norm(f,axis=2)
    mask=np.ones_like(m,bool);mask[60:210,150:330]=False       # exclude glass area
    return float(m[mask].mean())
cap=cv2.VideoCapture(str(R/'ref/reference_screenrec.mp4'))
def refframe(t):
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read();return cv2.cvtColor(f[335:669,:592],cv2.COLOR_BGR2RGB)
cuts=[34,79,124,169];Wd=Image.new('RGB',(1920,4*300),(20,20,20));d=ImageDraw.Draw(Wd)
rs=np.arange(0,1.4,.1)
for k,sid in enumerate((1,2,3,4)):
    d0=cuts[k]/30
    ref=[flow(refframe(d0+r),refframe(d0+r+.1)) for r in rs]
    fr=lambda i:np.asarray(Image.open(R/f'work/v7/raw/shot{sid}/{i:04}.png').convert('RGB'))
    our=[flow(fr(int(round(r*30))),fr(int(round(r*30))+3)) for r in rs]
    mx=max(max(ref),max(our))*1.1
    X=lambda r:20+int(r/1.5*1700)
    for cv,col in ((ref,(255,200,0)),(our,(0,255,0))):
        for i in range(len(rs)-1):d.line((X(rs[i]),k*300+280-int(cv[i]/mx*240),X(rs[i+1]),k*300+280-int(cv[i+1]/mx*240)),fill=col,width=3)
    for r,col in ((.15,(255,80,80)),(.28,(255,150,80)),(.95,(80,200,255)),(1.12,(120,120,255)),(1.5,(255,255,255))):
        d.line((X(r),k*300+20,X(r),k*300+285),fill=col);d.text((X(r)+3,k*300+22),f'r={r}',fill=col)
    d.text((10,k*300+4),f'shot{sid} motion (px/0.1s @480w, glass area masked)  yellow=reference  green=ours',fill=(255,255,255))
Wd.save(R/'out/v7_speed.png')
# interp check 200%
W=Image.new('RGB',(1600,1200));  # 4 shots x 2 frames, each 400x300 region at 200% -> 800x600? use 2x2 grid per row pair
cells=[]
for sid,(cx,cy) in ((1,(900,450)),(2,(1300,700)),(3,(1150,470)),(4,(1100,500))):
    for i in (15,16):
        im=Image.open(R/f'work/v7/raw/shot{sid}/{i:04}.png').convert('RGB').crop((cx-200,cy-150,cx+200,cy+150)).resize((800,600),Image.NEAREST);ImageDraw.Draw(im).text((4,4),f'shot{sid} f{i} (r={i/30:.2f}) 200%',fill=(255,255,0));cells.append(im)
W=Image.new('RGB',(3200,1200))
for k,c in enumerate(cells):W.paste(c,((k%4)*800,(k//4)*600))
W.save(R/'out/v7_interp_check.png')
