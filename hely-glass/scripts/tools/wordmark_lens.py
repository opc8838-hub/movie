"""v3 wordmark reveal: swirl lens -> horizontal stretch with per-channel dispersion -> settle.
Pure numpy/cv2. Wordmark is never rotated; only the lens content swirls (inside the lens)."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image

W, H, CX, CY = 1920, 1080, 960, 540
HW = 403.0  # half width of the wordmark (806 px = 42%)
SS = 2      # supersample of base
# tunable parameters (see docs/DECISIONS.md)
P = dict(Bk=1.0, S0=3.4, Mmax=0.9, kmin=0.15, Dmax=0.30, Dtail=0.2, Vmax=0.30, ripple=0.15, yel=0.85, aK=0.30, blur=0.3)

V8 = True   # v8: no grey layers around the opening wordmark (bubble only brightens, gone by 0.55 s; shock arcs gone by 0.58 s)
CL = (0.2, -0.5, 1.0)  # left: blue lone channel (less stretched) -> blue/violet outer fringe
CR = (1.0, -0.3, -0.3)  # right: red outer fringe

def sm(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def eo3(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return 1 - (1 - t) ** 3

_cache = {}
def lockup(dark):
    key = 'd' if dark else 'l'
    if key not in _cache:
        im = Image.open(ROOT / 'assets/logo' / ('lockup_on_dark.png' if dark else 'lockup_on_light.png')).convert('RGBA')
        w = int(round(HW * 2 * SS)); h = int(round(im.height * w / im.width))
        im = im.resize((w, h), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255
        bg = np.array([0, 0, 0] if dark else [233, 233, 233], np.float32) / 255
        rgb = a[..., :3] * a[..., 3:] + bg * (1 - a[..., 3:])  # straight composite (a[...,:3] is un-premultiplied)
        _cache[key] = (rgb, h / SS / 2)
    return _cache[key]

def params_at(tau, dark, hh, tail=1.0):
    B = P['Bk'] * hh * 2 * 0.5 * 1.0
    A = B + (1.10 * HW - B) * eo3(0.28, 0.56, tau)
    g = sm(0.14, 0.24, tau)
    a = HW * (0.22 + 0.56 * sm(0.33, 0.72, tau))
    k = 1 - (1 - (P['kmin'] + (0.85 - P['kmin']) * sm(0.38, 0.78, tau) + 0.15 * sm(1.0, 1.5, tau))) * g
    D = (P['Dmax'] * sm(0.22, 0.34, tau) * (1 - sm(0.45, 0.95, tau)) + P['Dtail'] * sm(0.22, 0.34, tau) * (1 - sm(0.95, 1.6, tau))) * g
    V = P['Vmax'] * (1 - sm(0.32, 0.72, tau)) * g
    S = P['S0'] * (1 - sm(0.08, 0.50, tau))
    M = 1 + P['Mmax'] * (1 - sm(0, 0.42, tau))
    return dict(A=A, B=B, a=a, k=k, D=D, V=V, S=S, M=M)

def render(tau, dark, grow=1.0, end_clean=0.0):
    """returns float32 HxWx3 RGB 0..1. grow scales the lens (ending: roundel -> lens). end_clean 0..1 forces clean."""
    base, hh = lockup(dark)
    bgc = np.array([0, 0, 0] if dark else [233, 233, 233], np.float32) / 255
    img = np.empty((H, W, 3), np.float32); img[:] = bgc
    q = params_at(tau, dark, hh)
    if end_clean > 0:
        q['k'] = 1 - (1 - q['k']) * (1 - end_clean); q['D'] *= (1 - end_clean); q['V'] *= (1 - end_clean)
    A, B = q['A'] * grow, q['B'] * grow
    # ---- lens ROI ----
    rx, ry = int(1.1 * HW + 40), int(1.8 * hh + 50)
    x0, x1, y0, y1 = CX - rx, CX + rx, CY - ry, CY + ry
    gx, gy = np.mgrid[y0:y1, x0:x1].astype(np.float32)[::-1]  # gx=x grid, gy=y grid
    Xr, Yr = gx - CX, gy - CY
    nn = 2 + 2 * sm(0.12, 0.40, tau)
    f = (np.abs(Xr) / A) ** nn + (np.abs(Yr) / B) ** nn
    gg = f ** (1 / nn)
    rr = np.sqrt(Xr ** 2 + Yr ** 2)
    dist = rr * (1 - gg) / np.maximum(gg, 1e-3)  # approx px inside edge (negative outside)
    mask = np.clip(dist / 14.0 + 0.5, 0, 1)
    bh, bw = base.shape[:2]
    chans = []
    a_ = q['a']; k = q['k']
    nblur = 5 if (1 - k) > 0.02 else 1
    for ci, c in enumerate((+1, 0, -1)):  # R,G,B
        acc = np.zeros(Xr.shape, np.float32)
        for j in np.linspace(-1, 1, nblur) if nblur > 1 else [0.0]:
            ax = np.abs(Xr); sg = np.sign(Xr)
            cc = np.where(Xr < 0, CL[ci], CR[ci])
            kc = k * (1 + cc * q['D'])
            Xs = np.where(ax > a_, sg * (a_ + (ax - a_) * kc), Xr)
            Xs = Xs + sg * np.where(ax > a_, j * P['blur'] * (1 - k) * k * (ax - a_), 0)
            Ys = Yr / (1 + q['V'] * sm(a_, max(A, a_ + 1), ax))
            # swirl then magnify (inverse order)
            rh = np.sqrt(Xs ** 2 + Ys ** 2)
            phi = q['S'] * (1 - np.minimum(rh / A, 1)) ** 2
            cs, sn = np.cos(phi), np.sin(phi)
            Xq = Xs * cs - Ys * sn; Yq = Xs * sn + Ys * cs
            Xq /= q['M']; Yq /= q['M']
            mx = ((Xq + bw / SS / 2) * SS).astype(np.float32); my = ((Yq + bh / SS / 2) * SS).astype(np.float32)
            acc += cv2.remap(base[..., ci], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=float(bgc[ci]))
        chans.append(acc / (nblur if nblur > 1 else 1))
    lens = np.stack(chans, -1)
    # yellow suppression: B darker than both R,G reads as yellow fringe -> pull B up (blue/violet left, red/cyan right)
    yel = np.clip(np.minimum(lens[..., 0], lens[..., 1]) - lens[..., 2], 0, 1)
    lens[..., 2] += yel * P['yel']
    grn = np.clip(lens[..., 1] - np.maximum(lens[..., 0], lens[..., 2]), 0, 1)
    lens[..., 1] -= grn * 0.85
    if dark:
        bl = cv2.GaussianBlur(lens, (0, 0), 9)
        lens = lens + 0.22 * bl * (1 - sm(0.7, 1.2, tau))
    roi = img[y0:y1, x0:x1]
    roi[:] = roi * (1 - mask[..., None]) + lens * mask[..., None]
    # faint hairline only (no hard frame)
    rimw = (1 - sm(0.30, 0.80, tau)) if dark else (1 - sm(0.20, 0.40, tau))
    inside3 = np.clip(1 - np.abs(dist - 2.0) / 3.0, 0, 1) * (dist > 0)
    roi += (inside3 * rimw * (6 if dark else 3) / 255)[..., None] * (np.array([0.80, 0.87, 0.97], np.float32) if dark else 1.0)
    # ---- v6: bright elliptical bubble + grey elliptical rim that follow the lens (A,B); no concentric rings ----
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); X = xx - CX; Y = yy - CY
    ee = np.sqrt((X / (1.25 * A)) ** 2 + (Y / (1.25 * B)) ** 2)      # 1 at the ellipse boundary
    vis = (1 - 0.8 * sm(0.4, 1.4, tau)) * (1 - end_clean)
    if dark:
        cool = np.array([0.30, 0.50, 1.0], np.float32)
        bubble = 0.16 * (1 - sm(0.15, 1.0, ee)) + 0.05 * np.exp(-((ee - 1.12) / 0.22) ** 2)      # soft cool bubble + faint cool rim
        img += (bubble * vis * (1 - sm(0.75, 1.25, tau)) ** 0.5)[..., None] * cool
        # turbulence texture ring just outside, very faint
        ang = np.arctan2(Y, X)
        tex = np.sin(3 * ang + 6 * ee - 9 * tau * (1 - sm(0.05, 0.5, tau))) * np.exp(-((ee - 1.3) / 0.25) ** 2)
        img += (np.clip(tex, 0, None) * 0.02 * vis)[..., None] * cool
    else:
        bubble = (12 / 255) * (1 - sm(0.15, 1.0, ee)) * (0.35 + 0.65 * np.exp(-(ee / 0.55) ** 2))
        if V8:
            img += (bubble * (1 - sm(0.20, 0.55, tau)) * (1 - end_clean))[..., None]
        else:
            rim = -(8 / 255) * np.exp(-((ee - 1.08) / 0.18) ** 2)
            ang = np.arctan2(Y, X)
            tex = np.sin(3 * ang + 6 * ee - 9 * tau * (1 - sm(0.05, 0.5, tau))) * np.exp(-((ee - 1.35) / 0.25) ** 2)
            img += ((bubble + rim + tex * (2.5 / 255)) * vis)[..., None]
    # ---- v7: left/right vertical arc shock waves "( )" pushed out from the lens sides + glass-ball double rim ----
    Yh = 0.7 * B * 1.8; curv = 0.30 * Yh
    for tk in (0.15, 0.40):
        dt = tau - tk
        if dt <= 0: continue
        env_t = np.exp(-dt / 0.25) * (1 - end_clean)
        if V8 and not dark: env_t = env_t * (1 - sm(0.40, 0.58, tau))
        xs = A * 1.05 + 1.6 * HW * dt
        envY = np.exp(-0.5 * (Y / (0.35 * Yh)) ** 2)
        for side in (-1, 1):
            for j in range(3):
                xa = xs + 18 * j - curv * (Y / Yh) ** 2                       # arc bulges outward at mid height
                u = (side * X - xa) / 10.0
                prof = -u * np.exp(-u * u / 2) * 1.65 * (0.62 ** j)
                if dark:
                    img += (np.clip(prof, 0, None) * envY * env_t * (40 / 255))[..., None] * np.array([0.75, 0.85, 1.0], np.float32)
                else:
                    img += (prof * envY * env_t * (20 / 255))[..., None]
    # glass-ball double rim around the bubble ellipse
    a_e, b_e = 1.25 * A, 1.25 * B
    e0 = np.sqrt((X / a_e) ** 2 + (Y / b_e) ** 2) + 1e-6
    gr = np.sqrt((X / (a_e ** 2 * e0)) ** 2 + (Y / (b_e ** 2 * e0)) ** 2) + 1e-6
    dpx = (e0 - 1.0) / gr
    rim_t = (1 - sm(0.8, 1.2, tau)) * (1 - end_clean) * sm(0.0, 0.08, tau)
    line = np.exp(-0.5 * (dpx / 1.4) ** 2) + 0.8 * np.exp(-0.5 * ((dpx - 8) / 1.4) ** 2)
    if dark:
        img += (line * rim_t * (14 / 255))[..., None] * np.array([0.75, 0.85, 1.0], np.float32)
    elif not V8:
        img -= (line * rim_t * (4 / 255))[..., None]
    return img

def to8(img):
    return np.clip(np.rint(img * 255), 0, 255).astype(np.uint8)

def frame_opening(i):
    return to8(render(i / 30, False))

def frame_ending(i, mark=None):
    t = i / 30; tau = (t - 8.6) / 1.25
    gr = 0.29 + 0.71 * sm(0, 0.12, tau)
    img = render(tau, True, grow=gr, end_clean=sm(1.10, 1.26, tau))
    return to8(img)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(ROOT / 'work/v3/wm'))
    ap.add_argument('--which', default='both'); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.which in ('both', 'open'):
        for i in range(34):
            Image.fromarray(frame_opening(i)).save(out / f'{i:04}.png')
    if a.which in ('both', 'end'):
        for i in range(258, 306):
            Image.fromarray(frame_ending(i)).save(out / f'{i:04}.png')
