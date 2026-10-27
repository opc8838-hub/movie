import sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
import numpy as np
from PIL import Image
from cmp_glass import ref
def meas(im,thr=45):
    a=np.asarray(im.convert('RGB')).astype(int);g=a.mean(2);c=a[:,:,:].min(2)
    # restrict to central 900x900
    sub=g[90:990,510:1410];ys,xs=np.nonzero(sub>thr);tile=(xs.min(),xs.max(),ys.min(),ys.max())
    import cv2
    w=(a[90:990,510:1410].min(2)>200).astype(np.uint8);w=cv2.morphologyEx(w,cv2.MORPH_OPEN,np.ones((21,21),np.uint8));ys2,xs2=np.nonzero(w);note=(xs2.min(),xs2.max(),ys2.min(),ys2.max())
    return tile,note
def ratios(im):
    t,n=meas(im);tw=t[1]-t[0];th=t[3]-t[2];nw=n[1]-n[0];nh=n[3]-n[2]
    return dict(tile=(tw,th),note=(nw,nh),wr=round(nw/th,3),hr=round(nh/th,3))
if __name__=='__main__':
    d=sys.argv[1] if len(sys.argv)>1 else 'work/v4/frames_raw'
    for t in (7.7,7.8,7.9):
        print(t,'ref ',ratios(ref(t)))
        print(t,'ours',ratios(Image.open(R/d/f'{round(t*30):04}.png')))
