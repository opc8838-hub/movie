"""Prepare native-colored 1080p backgrounds with beat-driven speed, zoom and LK tracking."""
from common import *
import argparse,cv2,numpy as np
def smooth(x):return np.clip(x,0,1)**2*(3-2*np.clip(x,0,1))
def curve(points,t,expo=False):
    for (a,v),(b,w) in zip(points,points[1:]):
        if t<=b:
            u=float(np.clip((t-a)/(b-a),0,1));u=(1-2**(-10*u))/(1-2**-10) if expo and w>v else smooth(u)
            return v+(w-v)*u
    return points[-1][1]
def source_time(s,r):
    xx=np.linspace(0,r,max(2,int(r*600)+1));return s['in']+np.trapezoid([curve(s['speed'],x) for x in xx],xx)
def read_video(path):
    cap=cv2.VideoCapture(str(path));fs=cap.get(cv2.CAP_PROP_FPS);frames=[];ts=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        frames.append(f);ts.append(cap.get(cv2.CAP_PROP_POS_MSEC)/1000)
    cap.release();return frames,np.array(ts),fs
def prepare(s):
    path=ROOT/s['source'];dest=ROOT/f'work/shot{s["id"]}';dest.mkdir(parents=True,exist_ok=True)
    if not path.exists():raise FileNotFoundError(path)
    if s.get('interpolate'):
        ip=ROOT/'work/live72.mp4'
        if not ip.exists():run([FFMPEG,'-hide_banner','-loglevel','warning','-y','-i',path,'-vf','minterpolate=fps=72:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1','-an','-c:v','libx264','-crf','12','-pix_fmt','yuv420p',ip])
        path=ip
    frames,times,fs=read_video(path);h,w=frames[0].shape[:2]
    # LK feature patch follows the subject; the offset point can sit beside the head.
    pivot=np.array(s['anchor'])*[w,h];point=np.array(s['track'])*[w,h]
    first=int(np.argmin(abs(times-s['in'])));gray=cv2.cvtColor(frames[first],cv2.COLOR_BGR2GRAY)
    mask=np.zeros_like(gray);px,py=pivot.astype(int);cv2.rectangle(mask,(px-80,py-80),(px+80,py+80),255,-1)
    features=cv2.goodFeaturesToTrack(gray,maxCorners=60,qualityLevel=.03,minDistance=6,mask=mask)
    offsets=np.zeros((len(frames),2));acc=np.zeros(2)
    for j in range(first+1,len(frames)):
        nxt=cv2.cvtColor(frames[j],cv2.COLOR_BGR2GRAY)
        if features is not None and len(features)>4:
            q,st,err=cv2.calcOpticalFlowPyrLK(gray,nxt,features,None,winSize=(25,25),maxLevel=3)
            valid=st[:,0]>0;delta=q[valid,0]-features[valid,0]
            if len(delta)>3:acc+=np.clip(np.median(delta,axis=0),-12,12)
            features=q[valid]
        offsets[j]=acc;gray=nxt
    from scipy.ndimage import gaussian_filter1d
    offsets=gaussian_filter1d(offsets,2,axis=0)
    tracks=[]
    for i in range(s['end']-s['start']):
        r=i/30;st=source_time(s,r);idx=int(np.argmin(abs(times-st)));f=frames[idx]
        z=curve(s['zoom'],r,s.get('zoom_ease')=='expo');base=max(1920/w,1080/h)
        # Center crop first; scale about fixed subject anchor, no pan/reframe jumps.
        dx=(1920-w*base)/2;dy=(1080-h*base)/2;anchor=pivot*base+[dx,dy]
        M=np.array([[base*z,0,dx*z+(1-z)*anchor[0]],[0,base*z,dy*z+(1-z)*anchor[1]]],np.float32)
        out=cv2.warpAffine(f,M,(1920,1080),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_REFLECT_101)
        if s.get('sharpen'):out=cv2.addWeighted(out,1.4,cv2.GaussianBlur(out,(0,0),1),-.4,0)
        if s.get('car_wipe'):
            a,b=s['car_wipe'];u=smooth((r-a)/(b-a));xx=np.arange(1920)[None,:,None]/1920
            if s.get('car_direction')=='right_to_left':xx=1-xx
            # Directional occlusion follows the generated left-to-right car, never a global dissolve.
            dark=smooth((u*1.4-xx)/.16);out=np.clip(out.astype(float)*(1-dark),0,255).astype('uint8')
        center=M[:,:2]@(point+offsets[idx])+M[:,2]
        (dest/f'{i:04}.png').write_bytes(cv2.imencode('.png',out,[cv2.IMWRITE_PNG_COMPRESSION,2])[1].tobytes())
        tracks.append({'frame':i,'global':s['start']+i,'r':r,'source_time':float(st),'source_frame':idx,'zoom':float(z),'center':center.tolist(),'diameter':1920*timeline()['glass']['diameter']*z})
    (dest/'track.json').write_text(json.dumps(tracks,indent=2),encoding='utf-8')
    print('prepared shot',s['id'],flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--shot',type=int);a=ap.parse_args()
    for s in timeline()['shots']:
        if a.shot is None or s['id']==a.shot:prepare(s)
