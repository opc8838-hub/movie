"""Original 80 BPM sound design; no reference audio is used."""
from common import *
import numpy as np,wave
SR=48000;DURATION=timeline()['frames']/timeline()['fps'];WORK=ROOT/timeline().get('work','work');N=int(DURATION*SR);rng=np.random.default_rng(8721);audio=np.zeros((N,2),np.float64);events=[]
def put(signal,start,kind,pan=0):
    signal=np.asarray(signal);i=round(start*SR);k=min(len(signal),N-i)
    if k<=0:return
    audio[i:i+k,0]+=signal[:k]*np.sqrt((1-pan)/2);audio[i:i+k,1]+=signal[:k]*np.sqrt((1+pan)/2)
    events.append({'type':kind,'time':start,'sample':i,'frame':start*30})
def kick(t,level=.7):
    x=np.arange(int(.43*SR))/SR;freq=46+110*np.exp(-x*38);phase=np.cumsum(freq)*2*np.pi/SR
    y=np.sin(phase)*np.exp(-x*12)*(1-np.exp(-x*450));y+=rng.normal(0,.035,len(x))*np.exp(-x*140)
    put(y*level,t,'cut kick')
def bell(t,pan=0):
    x=np.arange(int(.65*SR))/SR;y=sum(np.sin(2*np.pi*f*x)*np.exp(-x*d)*a for f,d,a in [(1760,17,.13),(2816,22,.06),(4360,28,.025)])
    y*=1-np.exp(-x*900);put(y,t,'glass chime',pan)
    for delay,gain in [(.061,.23),(.107,.12),(.169,.07)]:put(y*gain,t+delay,'chime reverb',-pan)
def chord(t,dur,freqs,level):
    x=np.arange(int(dur*SR))/SR;y=np.zeros_like(x)
    for f in freqs:y+=(np.sin(2*np.pi*f*x)+.17*np.sin(2*np.pi*(f*2+.17)*x))/len(freqs)
    env=(1-np.exp(-x*10))*np.minimum(1,(dur-x)/.6)*np.exp(-x*.24)
    put(y*env*level,t,'soft chord')
def main():
    cfg=timeline();cuts=[f/30 for f in cfg['cuts']]
    for t in cuts:kick(t)
    # Subtle 80BPM pulse supplies continuity, cut kicks remain foreground.
    for k in range(8):
        t=cuts[0]+.75*k+.375;x=np.arange(int(.13*SR))/SR;y=rng.normal(0,1,len(x));y=np.r_[0,np.diff(y)];put(y*np.exp(-x*60)*.018,t,'half beat tick',(-1)**k*.35)
    for k,t in enumerate(cuts):bell(t+.15,(-1)**k*.2)
    chord(.05,1.0,[220,329.63,440],.08)
    chord(1.15,2.9,[110,164.81,220],.09);chord(4.15,2.9,[130.81,196,261.63],.085)
    chord(cfg['lockup']['settled'],DURATION-cfg['lockup']['settled'],[220,329.63,440,554.37],.20)
    # Head push: a short rising texture lands at the exact animation trigger.
    peak=79/30+.375;x=np.arange(int(.3*SR))/SR;noise=rng.normal(0,1,len(x));noise=np.convolve(noise,np.ones(19)/19,'same');y=noise*np.linspace(0,1,len(x))**2*.20
    put(y,peak-.3,'hair riser');kick(peak,.40)
    if cfg.get('version',1)>=2:
        # Moving camera whoosh: energy travels left to right with the pan.
        x=np.arange(int(.52*SR))/SR;y=rng.normal(0,1,len(x));y=np.convolve(y,np.ones(21)/21,'same')*np.sin(np.pi*x/.52)**1.6*.38
        for j in range(8):
            a=int(j*len(x)/8);b=int((j+1)*len(x)/8)
            if cfg.get('version',1)<6:put(y[a:b],34/30+a/SR,'fire pan whoosh',-.8+j*1.6/7)
        if cfg.get('version',1)>=6:
            if cfg.get('version',1)>=8:
                kick(34/30+.15,.30);kick(34/30+.95,.32)
                xh=np.arange(int(.30*SR))/SR;yh=rng.normal(0,1,len(xh));yh=np.convolve(yh,np.ones(15)/15,'same')*np.sin(np.pi*np.clip(xh/.30,0,1)**1.4)**2*.30
                put(yh,34/30+.97,'fire accel whoosh',0.0)
            else:
                kick(34/30+(.20 if cfg.get('version',1)>=7 else .15),.30);kick(34/30+(.45 if cfg.get('version',1)>=7 else .75),.30)
        apex=124/30+(.40 if cfg.get('version',1)>=7 else .30 if cfg.get('version',1)>=3 else .75);kick(apex,.40);bell(apex,.15)
    # Passing vehicle, with stereo movement matching the right-to-left generated car.
    t=169/30+1.00;x=np.arange(int(.46*SR))/SR;y=rng.normal(0,1,len(x));y=np.convolve(y,np.ones(34)/34,'same')*np.sin(np.pi*x/.46)**2*.75
    put(y,t,'car whoosh',.35)
    audio[:240]*=np.linspace(0,1,240)[:,None];audio[-int(.5*SR):]*=np.linspace(1,0,int(.5*SR))[:,None]
    peakval=abs(audio).max();audio[:]*=(10**(-3/20))/peakval
    dest=WORK/'music.wav';dest.parent.mkdir(exist_ok=True)
    with wave.open(str(dest),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
    (WORK/'audio_events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    progress('v3/v4 步骤：声音重生成，滑板顶点重音前移到4.433s；其余同v2',str(dest))
    print('Original sound generated, dry peak -3dBFS; final loudness normalized in compose.py')
if __name__=='__main__':main()
