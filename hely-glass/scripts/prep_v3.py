"""v3 backgrounds: shot3 re-cut (apex at r=0.30) + person-following glass centre, texture pass for generated
shots 3/4 (light, invisible), radial water ripple displacement for all four shots.
Stages: raw3 -> person -> finish.  Pristine inputs: work/v3/raw/shot{1,2,3,4}; outputs: work/v3/shot{N}."""
import sys, json, shutil, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from common import *
import numpy as np, cv2
from PIL import Image

W3 = ROOT / 'work/v3'
GLASS = 499.2

def imread(p):
    return np.asarray(Image.open(p).convert('RGB'))
def imwrite(p, a):
    Image.fromarray(a).save(p, compress_level=2)

def stage_raw3():
    import prep_v2
    cfg = timeline()
    s = [x for x in cfg['shots'] if x['id'] == 3][0]
    prep_v2.prepare(s)          # writes work/v3/shot3 (+ track.json) from cfg['work']
    raw = W3 / 'raw/shot3'; raw.mkdir(parents=True, exist_ok=True)
    for i in range(45): shutil.copy(W3 / f'shot3/{i:04}.png', raw / f'{i:04}.png')
    for k in (1, 2, 4):
        d = W3 / f'raw/shot{k}'
        if not d.exists():
            d.mkdir(parents=True); [shutil.copy(ROOT / f'work/v2/shot{k}/{i:04}.png', d / f'{i:04}.png') for i in range(45)]
    progress('v3 步骤：镜头③重新取段 入点0.85s、1.2倍速、最高点r=0.30、跳推0.25-0.35', str(raw))

def stage_person():
    from rembg import new_session, remove
    import onnxruntime as ort
    so = ort.SessionOptions(); so.enable_cpu_mem_arena = False; so.enable_mem_pattern = False; so.intra_op_num_threads = 2
    sess = new_session('isnet-general-use', sess_opts=so)
    out = []
    for i in range(45):
        im = Image.open(W3 / f'raw/shot3/{i:04}.png').convert('RGB').resize((960, 540))
        m = np.asarray(remove(im, session=sess, only_mask=True)).astype(np.float32) / 255
        ys, xs = np.nonzero(m > .5)
        if len(xs) < 50: out.append(None); continue
        # torso centre: centroid of the upper 70% of the mask's vertical extent (skip board/feet)
        y0, y1 = ys.min(), ys.max(); sel = ys < y0 + .7 * (y1 - y0)
        out.append([float(xs[sel].mean() * 2), float(ys[sel].mean() * 2), int(len(xs))])
        if i % 9 == 0: print('person', i, out[-1], flush=True)
    (W3 / 'shot3/person.json').write_text(json.dumps(out), encoding='utf-8')
    progress('v3 步骤4.2：镜头③逐帧 rembg(isnet-general-use) 抠人，躯干中心存 person.json', str(W3 / 'shot3/person.json'))

def spring_follow(target, w=18.0, sub=8):
    """critically damped follower, sampled per frame; target interpolated linearly between frames."""
    x = target[0].copy(); v = np.zeros_like(x); out = [x.copy()]
    dt = 1 / 30 / sub
    for i in range(1, len(target)):
        for s_ in range(sub):
            tg = target[i - 1] + (target[i] - target[i - 1]) * (s_ + 1) / sub
            a = -2 * w * v - w * w * (x - tg)
            v = v + a * dt; x = x + v * dt
        out.append(x.copy())
    return np.array(out)

def shot3_centres():
    p = json.loads((W3 / 'shot3/person.json').read_text())
    # fill missing by neighbours
    last = None; arr = []
    for q in p:
        if q is None: q = last
        last = q if q is not None else last; arr.append(q)
    first = next(a for a in arr if a is not None); arr = [a if a is not None else first for a in arr]
    cx = np.array([a[0] for a in arr]); cy = np.array([a[1] for a in arr])
    cy0 = np.median(cy[:3])
    # light median filter against mask glitches
    from scipy.signal import medfilt
    cxf = medfilt(cx, 3); cyf = medfilt(cy, 3)
    tgt = np.stack([np.clip(cxf - .16 * 1920, 300, 1620), 540 + .85 * (cyf - cy0)], 1)
    return spring_follow(tgt)

def texture(img, seed):
    """very light: blur .4, black lift 7/255, shoulder <=248, fine weak grain, 4% neutral bloom. No hue change."""
    x = img.astype(np.float32) / 255
    x = cv2.GaussianBlur(x, (0, 0), 0.4)
    b = 7 / 255
    x = b + (1 - b) * x
    kn, top = 0.85, 248 / 255
    hi = x > kn
    x = np.where(hi, kn + (x - kn) * (top - kn) / (1 - kn), x)
    lum = x.mean(2, keepdims=True)
    mask = np.clip((lum - 220 / 255) / (30 / 255), 0, 1)
    bloom = cv2.GaussianBlur(x * mask, (0, 0), 10)
    x = x + 0.04 * bloom
    rng = np.random.default_rng(1000 + seed)
    g = rng.normal(0, 1, x.shape[:2]).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.7); g /= g.std() + 1e-6
    amp = (2.2 / 255) * (1 - np.abs(lum[..., 0] - .5) * 1.2).clip(.3, 1)
    x = x + (g * amp)[..., None]
    return np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)

def ripple(img, centre, r):
    if not (0.15 <= r <= 0.9): return img
    A = 6 * np.exp(-(r - .15) / .35)
    R0 = .5 * GLASS + 700 * (r - .15)
    H, Wd = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    dx, dy = xx - centre[0], yy - centre[1]
    rho = np.sqrt(dx * dx + dy * dy) + 1e-6
    disp = np.zeros_like(rho)
    for k in (0, 1):
        u = (rho - (R0 + 70 * k)) / 11.0
        disp += u * np.exp(-u * u / 2) * 1.65
    disp *= A
    mx = xx - disp * dx / rho; my = yy - disp * dy / rho
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def stage_finish():
    cfg = timeline()
    c3 = shot3_centres()
    for sid in (1, 2, 3, 4):
        raw = W3 / f'raw/shot{sid}'; dest = W3 / f'shot{sid}'; dest.mkdir(parents=True, exist_ok=True)
        tr_path = dest / 'track.json'
        if sid == 3: tracks = json.loads(tr_path.read_text())
        else: tracks = json.loads((ROOT / f'work/v2/shot{sid}/track.json').read_text())
        for i in range(45):
            im = imread(raw / f'{i:04}.png')
            if sid in (3, 4): im = texture(im, sid * 100 + i)
            tr = tracks[i]
            if sid == 3: tr['center'] = [float(c3[i][0]), float(c3[i][1])]
            else: tr['center'] = [960, 540]
            tr['diameter'] = GLASS
            im = ripple(im, tr['center'], tr['r'])
            imwrite(dest / f'{i:04}.png', im)
        tr_path.write_text(json.dumps(tracks, indent=2), encoding='utf-8')
        print('finish shot', sid, flush=True)
    progress('v3 步骤3+5：镜头①-④径向水波位移(2环、6px)；镜头③④轻质感(blur0.4、黑位7、高光≤248、颗粒、光晕4%)；镜头③中心跟人(弹簧18rad/s)', str(W3))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('stage'); a = ap.parse_args()
    {'raw3': stage_raw3, 'person': stage_person, 'finish': stage_finish}[a.stage]()
