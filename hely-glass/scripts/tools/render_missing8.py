import subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];raw=R/'work/v8/frames_raw'
need=[i for i in list(range(34,258)) if not (raw/f'{i:04}.png').exists()]
print(len(need),'missing',flush=True)
chunk=30
for k in range(0,len(need),chunk):
    part=need[k:k+chunk]
    spec=','.join(f'{i}:{i+1}' for i in part)
    for attempt in range(4):
        subprocess.run([sys.executable,'-X','utf8',str(R/'glass/render.py'),'--frames',spec],cwd=R,capture_output=True)
        if all((raw/f'{i:04}.png').exists() for i in part):break
    print(part[0],'ok' if all((raw/f'{i:04}.png').exists() for i in part) else 'FAIL',flush=True)
