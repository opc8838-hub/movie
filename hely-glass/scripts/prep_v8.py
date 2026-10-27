"""v8 backgrounds. shot1: new dolly (zoom 1->1.10->1.02->1.20) + speed 1.2x -> 0.30x -> 2.0x with 3-subframe blur on the push.
shots 2-4: v7 raw reused, NO square ripple (echo edges are added in build_v8). Output work/v8/shotN."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from common import *
from prep import read_video
import numpy as np, cv2
from PIL import Image
import prep_v3 as p3
W8 = ROOT / 'work/v8'
OFF = 0.85   # interp/shot1.mp4 starts at source 0.85 s
def sm(x): x = float(np.clip(x, 0, 1)); return x * x * (3 - 2 * x)
def speed(r):
    if r < 0.13: return 1.2
    if r < 0.20: return 1.2 + (0.30 - 1.2) * sm((r - 0.13) / 0.07)
    if r < 0.90: return 0.30
    if r < 1.05: return 0.30 + (2.0 - 0.30) * sm((r - 0.90) / 0.15)
    return 2.0
def zoom(r):
    if r < 0.15: u = r / 0.15; return 1.0 + 0.10 * (1 - (1 - u) ** 3)
    if r < 0.90: return 1.10 + (1.02 - 1.10) * sm((r - 0.15) / 0.75)
    u = min((r - 0.90) / 0.60, 1); return 1.02 + 0.18 * u ** 3
def S(r, n=3000):
    xx = np.linspace(0, r, max(2, int(r * n) + 1)); return float(np.trapezoid([speed(x) for x in xx], xx))
def v7S(r):
    # v7 shot1 speed: 1.0 to .15, smooth to .45 at .28, .45 to .95, smooth to 1.6 at 1.12, 1.6 after
    from prep import source_time
    s = [s for s in timeline_v7()['shots'] if s['id'] == 1][0]; return source_time(s, r) - s['in']
def timeline_v7(): return json.loads((ROOT / 'timeline_v7.json').read_text(encoding='utf-8'))
ANCHOR = 0.17
IN = 1.06 + v7S(ANCHOR) - S(ANCHOR)   # keep the knife/gong action start at r~0.17 as in v7
PIVOT = (960.0, 480.0)
def sampled(frames, times, t):
    j = int(np.clip(np.searchsorted(times, t) - 1, 0, len(times) - 2)); u = float(np.clip((t - times[j]) / (times[j + 1] - times[j]), 0, 1))
    return cv2.addWeighted(frames[j], 1 - u, frames[j + 1], u, 0)
def stage_raw1():
    frames, times, fs = read_video(W8 / '../v7/interp/shot1.mp4' if False else ROOT / 'work/v7/interp/shot1.mp4')
    h, w = frames[0].shape[:2]; base = 1920 / w; top = 0.12 * (h * base - 1080)
    dest = W8 / 'raw/shot1'; dest.mkdir(parents=True, exist_ok=True)
    print('in', IN, 'end source', IN + S(1.5), 'interp end', times[-1] + OFF, flush=True)
    tracks = json.loads((W8 / 'shot1/track.json').read_text())
    for i in range(45):
        r = i / 30
        shut = 0.0125 * float(np.clip((r - 0.85) / 0.10, 0, 1))
        rs = [r - shut, r, r + shut] if shut > 0 else [r]
        acc = np.zeros((1080, 1920, 3), np.float32)
        for rr in rs:
            z = zoom(rr); st = IN + S(rr) - OFF
            im = sampled(frames, times, st)
            M = np.array([[base * z, 0, PIVOT[0] * (1 - z)], [0, base * z, -top * z + PIVOT[1] * (1 - z)]], np.float32)
            acc += cv2.warpAffine(im, M, (1920, 1080), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        out = np.clip(acc / len(rs), 0, 255).astype(np.uint8)
        Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).save(dest / f'{i:04}.png', compress_level=2)
        tracks[i].update(source_time=IN + S(r), zoom=zoom(r), speed=speed(r))
        p3.imwrite(W8 / f'shot1/{i:04}.png', np.asarray(Image.open(dest / f'{i:04}.png').convert('RGB')))
    (W8 / 'shot1/track.json').write_text(json.dumps(tracks, indent=2), encoding='utf-8')
def stage_finish():
    for sid in (2, 3, 4):
        raw = ROOT / f'work/v7/raw/shot{sid}'; dest = W8 / f'shot{sid}'
        for i in range(45):
            im = p3.imread(raw / f'{i:04}.png')
            if sid in (3, 4): im = p3.texture(im, sid * 100 + i)
            p3.imwrite(dest / f'{i:04}.png', im)
        print('finish', sid, flush=True)
if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'raw1': stage_raw1()
    else: stage_finish()
