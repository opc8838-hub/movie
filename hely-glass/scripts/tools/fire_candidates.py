import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
import cv2,numpy as np
from PIL import Image,ImageDraw
cap=cv2.VideoCapture(str(R/'src/clip1_firedance.mp4'));fr=[]
while True:
    ok,f=cap.read()
    if not ok:break
    fr.append(f)
g=[cv2.cvtColor(cv2.resize(f,(272,180)),cv2.COLOR_BGR2GRAY) for f in fr]
mot=[0];cen=[0]
for a,b in zip(g,g[1:]):
    fl=cv2.calcOpticalFlowFarneback(a,b,None,.5,3,15,3,5,1.2,0);m=np.linalg.norm(fl,axis=2);mot.append(float(m.mean()));cen.append(float(m[30:150,70:200].mean()))
mot=np.array(mot);cen=np.array(cen);np.save(R/'work/v6/fire_mot.npy',np.stack([mot,cen]))
def sm(x,k=3):return np.convolve(x,np.ones(k)/k,'same')
M=sm(cen)
dM=np.gradient(M)
print('n',len(mot),'mean',mot.mean())
# score windows: onset (positive derivative peak) near r=.15,.75 and strong motion at 1.0
best=[]
for s in range(0,len(fr)-46):
    sc=0
    for r,w in ((.15,1),(.75,1)):
        i=s+int(round(r*30));sc+=w*max(dM[max(0,i-3):i+4])
    sc+=.5*M[s+30]
    best.append((sc,s))
best.sort(reverse=True);sel=[];
for sc,s in best:
    if all(abs(s-t)>12 for _,t in sel):sel.append((sc,s))
    if len(sel)==3:break
print(sel)
W=Image.new('RGB',(1920,3*420),(20,20,20));d=ImageDraw.Draw(W)
for k,(sc,s) in enumerate(sel):
    for j,r in enumerate((0,.15,.5,.75,1.0,1.5)):
        i=min(len(fr)-1,s+int(round(r*30)));im=Image.fromarray(cv2.cvtColor(fr[i],cv2.COLOR_BGR2RGB)).resize((300,200));W.paste(im,(j*310,k*420+10));d.text((j*310+4,k*420+12),f'r={r} f{i}',fill=(255,255,0))
    # curve
    cv=M[s:s+46];mx=M.max()
    for i in range(45):d.line((i*40+10,k*420+420-10-int(cv[i]/mx*170),(i+1)*40+10,k*420+420-10-int(cv[i+1]/mx*170)),fill=(0,255,0),width=2)
    for r in (.15,.75,1.0,1.5):d.line((int(r*30)*40+10,k*420+220,int(r*30)*40+10,k*420+410),fill=(255,60,60))
    d.text((1500,k*420+14),f'cand{k+1} start={s} t={s/30:.2f}s score={sc:.2f}',fill=(255,255,255))
W.save(R/'out/v6_fire_candidates.png')
json.dump([s for _,s in sel],open(R/'work/v6/fire_cands.json','w'))
