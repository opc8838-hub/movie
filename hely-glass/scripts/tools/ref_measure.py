import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import cv2,numpy as np
from PIL import Image,ImageDraw
def main():
    dst=ROOT/'out/ref';dst.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(str(ROOT/'ref/reference_screenrec.mp4'))
    rows=[];frames=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        t=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
        f=f[335:669,:592];frames.append((t,f));(dst/f'{len(frames)-1:04}.png').write_bytes(cv2.imencode('.png',f)[1].tobytes())
        rows.append({'index':len(frames)-1,'pts':round(t,6)})
    (dst/'pts.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    # Every actual source frame; keep original variable timestamps rather than inventing 20fps.
    W,H=296,188;sheet=Image.new('RGB',(W*8,H*((len(frames)+7)//8)), '#202020');d=ImageDraw.Draw(sheet)
    for i,(t,f) in enumerate(frames):
        sheet.paste(Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)).resize((296,167)),((i%8)*W,(i//8)*H+21))
        d.text(((i%8)*W+5,(i//8)*H+4),f'{i:03} / {t:.3f}s',fill='white')
    sheet.save(dst/'all_actual_frames.jpg')
    progress('步骤1：通读方案、拆帧图、CellMotion 分析和完整内核源码','PLAN.md; ref/sheet_*.png; src/*sheet*.png; glass/vendor/')
    print('source frames',len(frames),'last PTS',rows[-1])
if __name__=='__main__':main()
