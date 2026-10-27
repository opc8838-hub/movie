"""v3 frame assembly: wordmark lens frames (opening 0-33, ending 258-305), black-field ripples (214-257).
raw WebGL renders live in work/v8/frames_raw; final frames go to work/v8/frames."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np, cv2
from PIL import Image
import wordmark_lens as wl
from wordmark_lens import sm, to8

RAW = ROOT / 'work/v8/frames_raw'; OUT = ROOT / 'work/v8/frames'
_mark = None
def mark(w):
    global _mark
    if _mark is None: _mark = Image.open(ROOT / 'assets/logo/mark_on_dark.png').convert('RGBA')
    return _mark.resize((int(round(w)), int(round(w))), Image.LANCZOS)

def black_ripple(a, i):
    rr = (i - 214) / 30
    if not (0.15 <= rr <= 1.0): return a
    amp = 8 / 255 * np.exp(-(rr - .15) / .6)
    half = 585 / 2.0; n = 4.8
    yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float32); X = xx - 960; Y = yy - 540
    d = (np.abs(X / half) ** n + np.abs(Y / half) ** n) ** (1 / n) * half - half
    rip = np.zeros_like(d)
    for k in (0, 1, 2):
        dk = 820 * (rr - .15) - 110 * k
        if dk < 0: continue
        u = (d - dk) / 16.0
        rip += np.clip(-u * np.exp(-u * u / 2) * 1.65 * .5 + np.exp(-u * u / 2) * .5, 0, None) * (1 - .22 * k)
    x = a.astype(np.float32) / 255 + (rip * amp * 1.4)[..., None] * np.array([.80, .90, 1.0], np.float32)
    return to8(x)


import json
GI = ROOT / 'work/v8/glassinfo'
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
ECHO = dict(amp=12.0, gap=0.052, drift=0.045, hi=0.85, dk=0.45, decay=(1.0, 0.68, 0.45), nk=3)
def echo_sides(a, i):
    """v8: left/right 'echo edges' (thin glass verticals) copied outward from the plate sides; replaces the v6/v7 rounded-square displacement ring."""
    dark = i >= 214
    r = (i - 214) / 30 if dark else ((i - 34) % 45) / 30
    gi = json.loads((GI / f'{i:04}.json').read_text())
    tile = gi['tile']; ps = gi.get('ps') or 1; n = max(2.0, gi.get('n') or 4.8)
    al = float(np.clip((gi.get('pa') or 0) * (gi.get('op') or 0) * sstep(2.6, 4.2, n) * (1 - (gi.get('dr') or 0)), 0, 1))
    env = float(sstep(0.30, 0.42, r)) * al
    if env < 0.01: return a
    A = tile / 2 * ps
    cx, cy = 960, 540
    R = int(A * 1.0 + 2 * 0 + tile * 0.30)
    x0, x1, y0, y1 = max(0, int(cx - A - tile * 0.32)), min(1920, int(cx + A + tile * 0.32)), int(cy - A * 1.02), int(cy + A * 1.02)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32); X = xx - cx; Y = yy - cy
    def sd(ax, ay):
        u = np.abs(X) / ax + 1e-6; v = np.abs(Y) / ay + 1e-6
        g = (u ** n + v ** n) ** (1 / n)
        gx = u ** (n - 1) / g ** (n - 1) / ax; gy = v ** (n - 1) / g ** (n - 1) / ay
        return (g - 1) / (np.sqrt(gx ** 2 + gy ** 2) + 1e-6)
    dT = sd(A, A)
    outside = sstep(1.0, 7.0, dT)
    sidew = sstep(0.55, 0.90, np.abs(X) / A) * (1 - sstep(0.62, 0.90, np.abs(Y) / A))
    base = a[y0:y1, x0:x1].astype(np.float32) / 255
    disp = np.zeros_like(X); hi = np.zeros_like(X); dk = np.zeros_like(X); cyan = np.zeros_like(X); org = np.zeros_like(X)
    for k in range(1, ECHO['nk'] + 1):
        off = tile * ECHO['gap'] * k + tile * ECHO['drift'] * sstep(0.35, 0.95, r) + tile * 0.007 * np.sin(2 * np.pi * (1.5 * r) + 1.3 * k)
        ax = A + off; ay = 0.88 * A + 0.25 * off
        d = sd(ax, ay); w = ECHO['decay'][k - 1] * outside * sidew
        vmod = 0.75 + 0.25 * np.cos(Y / A * 2.2 + k)
        bump = np.exp(-((d + 4.0) / 7.0) ** 2) * (d < 5)
        disp += np.sign(X) * ECHO['amp'] * w * bump * (0.5 + 0.5 * np.cos(Y / A * 1.6 + 2.0 * k))
        hi += np.exp(-0.5 * (d / 1.7) ** 2) * w * vmod
        dk += np.exp(-0.5 * ((d + 2.6) / 1.1) ** 2) * w
        cyan += np.exp(-0.5 * ((d - 2.2) / 1.2) ** 2) * w
        org += np.exp(-0.5 * ((d + 5.0) / 1.5) ** 2) * w
    mx = (xx - x0 - disp * env).astype(np.float32)
    out = cv2.remap(base, mx, (yy - y0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if dark:
        col = np.array([0.72, 0.86, 1.0], np.float32)
        out = out + (hi * ECHO['hi'] * 0.6 * env)[..., None] * col * (1 - out) + (cyan * 0.10 * env)[..., None] * np.array([.3, .6, 1.], np.float32)
    else:
        out = out * (1 - (hi * ECHO['hi'] * env)[..., None]) + (hi * ECHO['hi'] * env)[..., None]
        out = out * (1 - (dk * ECHO['dk'] * env)[..., None] * 0.9) + 0.03 * (dk * ECHO['dk'] * env)[..., None]
        out = out + (cyan * 0.16 * env)[..., None] * np.array([-.10, .06, .22], np.float32) + (org * 0.12 * env)[..., None] * np.array([.20, .06, -.14], np.float32)
    res = a.copy(); res[y0:y1, x0:x1] = to8(np.clip(out, 0, 1))
    return res

def frame(i):
    if i < 34: return wl.frame_opening(i)
    if 258 <= i < 306:
        t = i / 30; tau = (t - 8.6) / 1.25
        gr = 0.52 + 0.48 * sm(0, 0.12, tau)
        img = wl.render(tau, True, grow=gr, end_clean=sm(1.10, 1.26, tau))
        al = 1 - sm(0, 0.06, tau)
        if al > 0:
            m = mark(123.2); a = np.asarray(m).astype(np.float32) / 255
            x0 = int(round(960 - m.width / 2)); y0 = int(round(540 - m.height / 2))
            roi = img[y0:y0 + m.height, x0:x0 + m.width]
            roi[:] = roi * (1 - a[..., 3:] * al) + a[..., :3] * a[..., 3:] * al
        return to8(img)
    a = np.asarray(Image.open(RAW / f'{i:04}.png').convert('RGB'))
    return echo_sides(a, i) if i < 258 else a

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    rng = sys.argv[1] if len(sys.argv) > 1 else '0:360'
    a, b = map(int, rng.split(':'))
    for i in range(a, b):
        Image.fromarray(frame(i)).save(OUT / f'{i:04}.png', compress_level=2)
