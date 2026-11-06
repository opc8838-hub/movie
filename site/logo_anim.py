"""站内版手写 logo 动画，改自 b2w-mv1/logo_anim.py。用法见 make_logo.py。"""

import os
import sys

import cv2
import numpy as np

ROOT = r'E:\claude工作区\b2w-mv1'
OUT = os.path.join(os.environ.get('LOGO_OUT', '.'), '%04d.png')
W, H, FPS = 1920, 1080, 30
DUR = 2.4                                  # logo 段总长（秒），含结尾停留
SCALE = 1.0                                # logo 在 1920 宽画面里的缩放（相对原图 1448 宽 → 见 place()）


def imread(p, flag=cv2.IMREAD_GRAYSCALE):
    return cv2.imdecode(np.fromfile(p, np.uint8), flag)


def imwrite(p, a):
    cv2.imencode(os.path.splitext(p)[1], a)[1].tofile(p)


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 3


# ---------- 读 logo → 墨迹浓度 ink(0..1)，放到 1920×1080 ----------
g = imread(os.path.join(ROOT, 'src', 'logo.png')).astype(np.float32)
bg = np.median(g)                                           # 底色 ~251，不是纯白
ink_src = np.clip((bg - g) / (bg - 10), 0, 1)
ink_src = np.clip((ink_src - 0.10) / 0.82, 0, 1)                # 去掉 JPEG 噪点形成的灰边
k = 1.12                                                    # 原图 1448 → 画面里 logo 宽 ~1100px
ox = W / 2 - (109 + 1340) / 2 * k                          # logo 视觉中心放画面正中
oy = H / 2 - (389 + 665) / 2 * k
ink = cv2.warpAffine(ink_src, np.float32([[k, 0, ox], [0, k, oy]]), (W, H), flags=cv2.INTER_CUBIC)
ink = np.clip(ink, 0, 1)


def to_canvas(x, y):
    return x * k + ox, y * k + oy


# ---------- 分区（原图坐标）----------
def box(x0, y0, x1, y1):
    a, b = to_canvas(x0, y0)
    c, d = to_canvas(x1, y1)
    m = np.zeros((H, W), bool)
    m[int(b):int(d), int(a):int(c)] = True
    return m


R_SCRIPT = box(90, 370, 1010, 612) | box(90, 612, 350, 645)   # 手写，B 的左下一撇伸到 y≈630
R_STUDIO = box(350, 612, 800, 665)
R_LINE = box(1030, 405, 1048, 645)
R_B2W = box(1095, 390, 1350, 660)

# ---------- 手写：路径距离 ----------
mask = (ink > 0.08) & R_SCRIPT
mask_u8 = mask.astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
comps = [i for i in range(1, n) if st[i, 4] > 150]
comps.sort(key=lambda i: st[i, 0])
dist = np.full((H, W), np.inf, np.float32)
lengths = []
kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
for i in comps:
    x, y, w, h, _ = st[i]
    sub = (lab[y:y + h, x:x + w] == i)
    d = np.full(sub.shape, np.inf, np.float32)
    ys, xs = np.nonzero(sub)
    j = np.argmin(xs + 0.3 * ys)                            # 起笔：最左（偏上）
    front = np.zeros(sub.shape, np.uint8)
    front[ys[j], xs[j]] = 1
    reached = front.copy()
    step = 0
    while True:
        d[(reached > 0) & np.isinf(d)] = step
        nxt = cv2.dilate(reached, kern) & sub.astype(np.uint8)
        if nxt.sum() == reached.sum():
            break
        reached = nxt
        step += 1
    lengths.append(step)
    dd = dist[y:y + h, x:x + w]
    dd[sub] = d[sub]
lengths = np.array(lengths, np.float32)

# 时间轴：各块按笔画长度瓜分 [T0, T1]，块之间留一点提笔间隙
T0, T1, GAP = 0.06, 0.95, 0.03
total = T1 - T0 - GAP * (len(comps) - 1)
starts, t = [], T0
for L in lengths:
    starts.append(t)
    t += total * L / lengths.sum() + GAP
tmap = np.full((H, W), np.inf, np.float32)               # 每个像素"被写到"的时刻
for i, s, L in zip(comps, starts, lengths):
    m = lab == i
    tmap[m] = s + dist[m] / lengths.sum() * total
# 抗锯齿边缘的淡墨像素：取附近已写像素的时刻
far = ~np.isfinite(tmap)
near = (ink > 0.004) & R_SCRIPT & far
tm_fill = np.where(np.isfinite(tmap), tmap, 99).astype(np.float32)
tm_fill = cv2.erode(tm_fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
tmap[near] = tm_fill[near]

# STUDIO 每个字母的中心 x（用于字距收拢）
studio_mask = (ink > 0.08) & R_STUDIO
n2, lab2, st2, cen2 = cv2.connectedComponentsWithStats(studio_mask.astype(np.uint8), connectivity=8)
letters = sorted([i for i in range(1, n2) if st2[i, 4] > 30], key=lambda i: st2[i, 0])
studio_cx = np.mean([cen2[i][0] for i in letters])


def frame(t):
    out = np.zeros((H, W), np.float32)
    # 1) 手写：笔尖前沿 0.05s 的软边
    a = ease((t - tmap) / 0.035)
    out = np.maximum(out, ink * a * R_SCRIPT)

    # 2) 竖线：从中点向上下长出
    p = ease_out((t - 0.82) / 0.3)
    if p > 0:
        x0c, y0c = to_canvas(1030, 417)
        x1c, y1c = to_canvas(1048, 636)
        mid = (y0c + y1c) / 2
        half = (y1c - y0c) / 2 * p
        m = np.zeros((H, W), np.float32)
        m[int(mid - half):int(mid + half) + 1, :] = 1
        out = np.maximum(out, ink * m * R_LINE)

    # 3) B2W：从下往上露出 + 轻微上移
    p = ease_out((t - 0.92) / 0.38)
    if p > 0:
        _, yt = to_canvas(0, 395)
        _, yb = to_canvas(0, 655)
        lift = (1 - p) * 26
        M = np.float32([[1, 0, 0], [0, 1, lift]])
        sh = cv2.warpAffine(ink * R_B2W, M, (W, H))
        reveal = np.zeros((H, W), np.float32)
        cut = yb - (yb - yt) * p
        reveal[int(max(0, cut)):, :] = 1
        out = np.maximum(out, sh * reveal)

    # 4) STUDIO：字距从宽收拢 + 淡入，逐字错开
    for n_i, i in enumerate(letters):
        q = ease_out((t - 1.0 - n_i * 0.03) / 0.42)
        if q <= 0:
            continue
        x, y, w, h, _ = st2[i]
        dx = (cen2[i][0] - studio_cx) * 0.35 * (1 - q)
        piece = np.zeros((H, W), np.float32)
        piece[y:y + h, x:x + w] = ink[y:y + h, x:x + w] * (lab2[y:y + h, x:x + w] == i)
        piece = cv2.dilate(piece, np.ones((2, 2), np.uint8)) if False else piece
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        out = np.maximum(out, cv2.warpAffine(piece, M, (W, H)) * q)

    # 整体极慢推近，让停留不死板
    s = 1 + 0.025 * ease(t / DUR)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
    out = cv2.warpAffine(out, M, (W, H))
    return out


def render(path_fmt):
    os.makedirs(os.path.dirname(path_fmt), exist_ok=True)
    n = int(round(DUR * FPS))
    for f in range(n):
        o = frame(f / FPS)
        img = (255 - o * 255).clip(0, 255).astype(np.uint8)     # 黑墨 = 10，底 = 纯白
        imwrite(path_fmt % f, img)
    print('logo frames', n)


if __name__ == '__main__':
    if '--check' in sys.argv:
        ts = [0.2, 0.45, 0.7, 0.9, 1.05, 1.2, 1.5, 2.35]
        tiles = [cv2.resize((255 - frame(t) * 245).clip(0, 255).astype(np.uint8), (640, 360)) for t in ts]
        for im, t in zip(tiles, ts):
            cv2.putText(im, '%.2fs' % t, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 120, 2)
        grid = np.vstack([np.hstack(tiles[i:i + 4]) for i in (0, 4)])
        imwrite(os.path.join(ROOT, 'work', 'logo_check.jpg'), grid)
        print('starts', np.round(starts, 2), 'lengths', lengths)
    else:
        render(OUT)
