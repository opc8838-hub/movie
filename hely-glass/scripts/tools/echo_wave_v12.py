"""v12 side waves: wave packets launched from the tile's left/right edges that travel outward,
slow down and fade (deep -> light), like the reference. Each packet is a thin glass sheet:
two close bright arcs with a refracting body between them. Look (thickness/glow) from v11."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np, cv2
from PIL import Image
import build_v8 as B
sstep, to8 = B.sstep, B.to8
W = dict(
    packets=[dict(r0=0.50, s=1.0), dict(r0=0.70, s=0.55)],  # launch time (shot r) and strength
    travel=0.36,   # distance travelled, in tile widths
    dur=0.50,      # seconds of shot-time to travel it
    gap=0.022,     # spacing of the packet's two arcs, tile widths
    amp=20.0, hi=0.95, glow=0.30, body=0.12, dk=0.45, sig=2.6,
)
def wave(a, i, W=W):
    dark = i >= 214
    r = (i - 214) / 30 if dark else ((i - 34) % 45) / 30
    gi = json.loads((B.GI / f'{i:04}.json').read_text())
    tile = gi['tile']; ps = gi.get('ps') or 1; n = max(2.0, gi.get('n') or 4.8)
    al = float(np.clip((gi.get('pa') or 0) * (gi.get('op') or 0) * sstep(2.6, 4.2, n) * (1 - (gi.get('dr') or 0)), 0, 1))
    live = []
    for P in W['packets']:
        p = (r - P['r0']) / W['dur']
        if 0 < p < 1:
            ease = 1 - (1 - p) ** 2.4                    # fast out of the edge, then slows down
            fade = sstep(0, 0.08, p) * (1 - p) ** 1.6    # deep -> light
            live.append((tile * W['travel'] * ease, P['s'] * fade * max(al, 0.6 * sstep(0, 0.3, p))))
    if not live: return a
    A = tile / 2 * ps; cx, cy = 960, 540
    reach = tile * (W['travel'] + W['gap'] + 0.06)
    x0, x1, y0, y1 = max(0, int(cx - A - reach)), min(1920, int(cx + A + reach)), int(cy - A * 1.05), int(cy + A * 1.05)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32); X = xx - cx; Y = yy - cy
    def sd(ax, ay):
        u = np.abs(X) / ax + 1e-6; v = np.abs(Y) / ay + 1e-6
        g = (u ** n + v ** n) ** (1 / n)
        gx = u ** (n - 1) / g ** (n - 1) / ax; gy = v ** (n - 1) / g ** (n - 1) / ay
        return (g - 1) / (np.sqrt(gx ** 2 + gy ** 2) + 1e-6)
    outside = sstep(1.0, 7.0, sd(A, A))
    sidew = sstep(0.50, 0.88, np.abs(X) / A) * (1 - sstep(0.60, 0.92, np.abs(Y) / A))
    base = a[y0:y1, x0:x1].astype(np.float32) / 255
    disp, hi, glow, body, dk, cyan, org = (np.zeros_like(X) for _ in range(7))
    s = W['sig']
    for off, strength in live:
        for j, sub in enumerate((1.0, 0.6)):         # the sheet's outer and inner edge
            o = off - j * tile * W['gap']
            if o < 2: continue
            d = sd(A + o, 0.86 * A + 0.35 * o)        # the arc bows out more as it travels
            w = strength * sub * outside * sidew
            vmod = 0.80 + 0.20 * np.cos(Y / A * 2.0 + j)
            hi += np.exp(-0.5 * (d / s) ** 2) * w * vmod
            glow += np.exp(-0.5 * (d / (s * 3.0)) ** 2) * w
            dk += np.exp(-0.5 * ((d + 4.0) / 1.6) ** 2) * w
            cyan += np.exp(-0.5 * ((d - 3.2) / 1.6) ** 2) * w
            org += np.exp(-0.5 * ((d + 7.0) / 2.2) ** 2) * w
        # refracting body between the two arcs
        d_out = sd(A + off, 0.86 * A + 0.35 * off)
        slab = sstep(-tile * W['gap'] - 2, -tile * W['gap'] + 3, d_out) * (1 - sstep(-3, 0, d_out))
        disp += np.sign(X) * W['amp'] * strength * slab * outside * sidew
        body += slab * strength * outside * sidew
    mx = (xx - x0 - disp).astype(np.float32)
    out = cv2.remap(base, mx, (yy - y0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    bw = np.clip(body, 0, 1)[..., None]
    out = cv2.GaussianBlur(out, (0, 0), 1.0) * bw + out * (1 - bw)
    if dark:
        col = np.array([0.72, 0.86, 1.0], np.float32)
        out = out + (hi * W['hi'] * .7 + glow * W['glow'] * .6)[..., None] * col * (1 - out) + (cyan * 0.14)[..., None] * np.array([.3, .6, 1.], np.float32)
    else:
        L = np.clip(hi * W['hi'] + glow * W['glow'] + body * W['body'], 0, 1)[..., None]
        out = out * (1 - L) + L
        out = out * (1 - (dk * W['dk'])[..., None] * 0.9) + 0.03 * (dk * W['dk'])[..., None]
        out = out + (cyan * 0.22)[..., None] * np.array([-.12, .07, .26], np.float32) + (org * 0.16)[..., None] * np.array([.24, .07, -.16], np.float32)
    res = a.copy(); res[y0:y1, x0:x1] = to8(np.clip(out, 0, 1)); return res
if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for i in [int(x) for x in sys.argv[2].split(',')]:
        a = np.asarray(Image.open(B.RAW / f'{i:04}.png').convert('RGB'))
        Image.fromarray(wave(a, i)).save(out / f'{i:04}.png')
