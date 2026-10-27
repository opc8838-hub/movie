"""jd 拉斯维加斯歌词 MV 一键出片：python render.py [--base] [--mask] [--preview t1,t2,..] [--nodesk]
阶段 A  做底片 work/base.rgb（素材原色，不加任何滤镜）
阶段 M  rembg 抠 L13 的人，缓存到 work/mask_l13/
阶段 B  叠字/手写 + 音频，输出 out/jd_lasvegas_v1.mp4（并复制桌面 + 发微信版）
所有可调参数在本文件头部。"""
import os, re, sys, subprocess, shutil, glob, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ===================== 参数 =====================
ROOT = os.path.dirname(os.path.abspath(__file__))
FF = r'E:\claude工作区\back-to-work-video\tools\ffmpeg.exe'
W, H, FPS = 1920, 1080, 30
TOTAL = 27.5
NF = int(round(TOTAL * FPS))           # 825
MUSIC_END = 23.53
SRC = lambda *a: os.path.join(ROOT, 'src', *a)
WORK = os.path.join(ROOT, 'work')
OUTD = os.path.join(ROOT, 'out')
BASE = os.path.join(WORK, 'base.rgb')
MASKD = os.path.join(WORK, 'mask_l13')
OUT = os.path.join(OUTD, 'jd_lasvegas_v1.mp4')
OUT_SHARE = os.path.join(OUTD, 'jd_lasvegas_v1_share.mp4')
DESK = r'E:\360MoveData\Users\Administrator\Desktop\jd最新\成片'
CRF, CRF_SHARE = 16, 23

LIVE = lambda i: glob.glob(SRC('livp', i, '*.mov'))[0]
IMG = lambda i: SRC('img_%s.jpg' % i)

# 镜头切点（秒）。片段 = (起,止)
CUTS = [0, 2.57, 3.20, 5.27, 7.00, 7.97, 9.13, 10.03, 12.43, 13.30, 14.17, 15.57, 16.87, 18.00, 19.07, 20.13, 23.53, 27.50]
CF = [int(round(c * FPS)) for c in CUTS]        # 帧号边界
# 每镜：kind live/img/split；src=ss起点秒；crop=(x,y,w,h)源像素（None=整幅）
SHOTS = [
    dict(name='L2',  kind='live', id='222646', ss=0.0, crop=None),
    dict(name='L1',  kind='live', id='222629', ss=1.0, crop=(0, 470, 720, 405)),
    dict(name='L6',  kind='live', id='222819', ss=0.3, crop=None),
    dict(name='split', kind='split'),
    dict(name='I2',  kind='img', f='223028', box=(0, 430, 1080, 608), focus=None),
    dict(name='L12', kind='live', id='222941', ss=0.0, crop=None),
    dict(name='I3',  kind='img', f='223041', box=(0, 150, 1620, 911), focus=None),
    dict(name='L11', kind='live', id='222934', ss=0.3, crop=None),
    dict(name='L10', kind='live', id='222924', ss=0.0, crop=None),
    dict(name='L5',  kind='live', id='222723', ss=0.0, crop=(0, 260, 720, 405)),
    dict(name='L9',  kind='live', id='222918', ss=0.5, crop=None),
    dict(name='L8',  kind='live', id='222859', ss=1.5, crop=None),
    dict(name='I1',  kind='img', f='223009', box=(152, 0, 1920, 1080), focus=None),
    dict(name='I4',  kind='img', f='223140', box=(0, 730, 1080, 608), focus=None),
    dict(name='L7',  kind='live', id='222852', ss=1.7, crop=(0, 460, 720, 405)),
    dict(name='L13', kind='live', id='222949', ss=0.0, crop=None, speed=2.97 / 3.4),
    dict(name='L3',  kind='live', id='222654', ss=0.0, crop=None, speed=2.97 / 3.97),
]
IMG_ZOOM = (1.00, 1.06)
# 三格分屏
GAP = 24
CELL_W = (W - 2 * GAP) // 3                      # 624
SPLIT_START = 5.27
SPLIT_CELLS = [  # (亮起时间, 素材id, 源起点秒, 裁切中心x比例)
    (5.37, '222717', 0.0, 0.46),
    (5.70, '222723', 0.6, 0.42),
    (6.13, '222852', 0.0, 0.50),
]

# ---- 字体 ----
FONT_BOLD = r'E:\claude工作区\self-love-video\fonts\Archivo-VF.ttf'   # 对比后选 Archivo：粗窄、字重 900
FONT_AXES_BOLD = (900, 76)        # (字重, 字宽)
FONT_AXES_LIGHT = (400, 100)      # 参考片里 "you/were/Let/go" 那种细体
ROUND = 5                         # 字形圆角（像素，2x 画布上）
ORANGE = (255, 153, 14)
PINK = (255, 214, 212)
SALMON = (250, 128, 112)
TEAL = (62, 204, 190)
SKY = (140, 192, 212)
REDORG = (255, 118, 64)
RED = (240, 46, 66)
# ---- 手写 ----
HAND_FONT = r'E:\claude工作区\jd-mv\work\OddballTM-Regular.otf'
HAND_TEXT = 'Jandy.'
HAND_SIZE = 230
HAND_START, HAND_WRITE = 25.40, 1.20
HAND_POS = (620, 890)           # 文字中心
HAND_SOFT = 70
MASK_FEATHER = 2.2              # 人像 mask 羽化(px)
HAND_SHADOW = 0.18
FADE_OUT = (26.9, 27.5)
# =================================================

SC_OUT = 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int'


def ffmpeg_frames(args, w, h, n=None):
    """用 ffmpeg 管道逐帧产出 rgb24 (h,w,3)。"""
    cmd = [FF, '-v', 'error'] + args + ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    k = 0
    while n is None or k < n:
        b = p.stdout.read(size)
        while b and len(b) < size:
            c = p.stdout.read(size - len(b))
            if not c:
                break
            b += c
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
        k += 1
    p.stdout.close()
    p.kill()
    p.wait()


def live_frames(sh, n, w=W, h=H, start=None, crop=None, ss=None, speed=None, cw=None, ch=None):
    """Live 源 -> n 帧（30fps 恒定，bt709 解码，lanczos 放大）。slow 用 setpts + framerate 帧混合。"""
    ss = sh['ss'] if ss is None else ss
    crop = sh.get('crop') if crop is None else crop
    speed = sh.get('speed') if speed is None else speed
    vf = ['fps=30']
    if speed:
        vf += ['setpts=PTS/%.5f' % speed, 'framerate=fps=30:interp_start=0:interp_end=255:scene=100']
    if crop:
        vf.append('crop=%d:%d:%d:%d' % (crop[2], crop[3], crop[0], crop[1]))
    vf.append('scale=%d:%d:flags=lanczos+accurate_rnd+full_chroma_int:in_color_matrix=bt709:in_range=tv,format=rgb24' % (w, h))
    f = list(ffmpeg_frames(['-ss', '%.4f' % ss, '-i', LIVE(sh['id']), '-vf', ','.join(vf), '-frames:v', str(n + 2)], w, h, n + 2))
    if not f:
        raise RuntimeError('no frames ' + sh['name'])
    while len(f) < n:       # 保险：不够就取最后一帧（正常不会发生）
        print('WARN short', sh['name'], len(f), n)
        f.append(f[-1])
    return f[:n]


def img_frames(sh, n):
    im = Image.open(IMG(sh['f'])).convert('RGB')
    bx, by, bw, bh = sh['box']
    cx, cy = bx + bw / 2.0, by + bh / 2.0
    out = []
    for i in range(n):
        z = IMG_ZOOM[0] + (IMG_ZOOM[1] - IMG_ZOOM[0]) * i / max(n - 1, 1)
        w2, h2 = bw / z, bh / z
        box = (cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2)
        out.append(np.asarray(im.resize((W, H), Image.LANCZOS, box=box)))
    return out


def split_frames(n):
    """三格分屏：黑底，格 624 宽，硬切亮起，各格从亮起时刻开始播放。"""
    t0 = SPLIT_START
    cells = []
    for (ton, vid, ss, cxr) in SPLIT_CELLS:
        k0 = int(round((ton - t0) * FPS))
        m = n - k0
        sh = dict(id=vid)
        # 竖版素材：整幅放大到高 1080，再按人所在位置裁 624 宽
        info = {'222717': (720, 976), '222723': (720, 912), '222852': (720, 1008)}[vid]
        sw = int(round(info[0] * H / info[1]))
        fr = live_frames(sh, m, w=sw, h=H, crop=None, ss=ss, speed=None)
        x0 = int(round(min(max(cxr * sw - CELL_W / 2, 0), sw - CELL_W)))
        cells.append((k0, [f[:, x0:x0 + CELL_W] for f in fr]))
    out = []
    for i in range(n):
        fr = np.zeros((H, W, 3), np.uint8)
        for c, (k0, cf) in enumerate(cells):
            if i >= k0:
                x = c * (CELL_W + GAP)
                fr[:, x:x + CELL_W] = cf[i - k0]
        out.append(fr)
    return out


def build_base():
    os.makedirs(WORK, exist_ok=True)
    with open(BASE, 'wb') as fo:
        total = 0
        for k, sh in enumerate(SHOTS):
            n = CF[k + 1] - CF[k]
            if sh['kind'] == 'live':
                fr = live_frames(sh, n)
            elif sh['kind'] == 'img':
                fr = img_frames(sh, n)
            else:
                fr = split_frames(n)
            for f in fr:
                fo.write(np.ascontiguousarray(f).tobytes())
            total += len(fr)
            print('shot', sh['name'], n, 'frames')
    print('base frames', total)


def base_mm():
    return np.memmap(BASE, np.uint8, 'r', shape=(NF, H, W, 3))


def shot_of(frame):
    for k in range(len(SHOTS)):
        if CF[k] <= frame < CF[k + 1]:
            return k
    return len(SHOTS) - 1



# ===================== 歌词 =====================
CREAM = (255, 240, 222)
SKYL = (190, 226, 242)
LY = []          # 歌词条目


def Wd(t, text, x, y, cap, color=ORANGE, **kw):
    """t 出现时间；(x,y)=字的中心(align=c)或左端(align=l)；cap=大写字母高度(px)。
    kw: rot 旋转度(逆时针) light 细体 grow 逐字出现间隔秒 follow 接在上一个词后 until 消失时间
        behind 画在人像后面 gap 间距 dy 基线偏移 align l/c"""
    d = dict(t=t, text=text, x=x, y=y, cap=cap, color=color)
    d.update(kw)
    LY.append(d)


# 注意：每条在所在镜头结束(切点)时自动消失；跨镜头的句子在新镜头开头重新出现
# --- L2 开场（0–2.57）
Wd(1.77, "I'm", 1480, 170, 107)
Wd(2.07, "Gon", 960, 870, 107)
Wd(2.27, "nnnaaaaa", 0, 0, 52, light=True, grow=0.07, follow=True, gap=6)
# --- L1 （2.57–3.20）
Wd(2.67, "Pack", 280, 330, 130)
# --- L6 （3.20–5.27）
Wd(3.20, "Pack", 1480, 600, 130)
Wd(3.30, "My", 250, 210, 90, color=PINK)
Wd(4.20, "Things", 1600, 790, 81, color=SALMON, light=True)
Wd(4.65, "And", 1420, 940, 113, color=TEAL)
# --- 三格分屏（5.27–7.00）
Wd(5.37, "Leave", 312, 250, 107)
Wd(5.70, "You", 960, 330, 71, color=TEAL)
Wd(6.13, "Be", 1560, 220, 146)
Wd(6.43, "hind", 0, 0, 71, light=True, follow=True, gap=8)
# --- I2 （7.00–7.97）
Wd(7.13, "This", 560, 250, 123)
Wd(7.47, "Feeling's", 640, 800, 113)
# --- L12 （7.97–9.13）
Wd(8.17, "Old", 1650, 250, 130, rot=22)
Wd(8.77, "Then", 1560, 440, 146, rot=22)
# --- I3 （9.13–10.03）
Wd(9.57, "I", 70, 850, 227, color=RED)
Wd(9.57, "I", 1850, 850, 227, color=RED)
Wd(9.60, "Know", 960, 850, 227, color=REDORG)
# --- L11 （10.03–12.43）
Wd(10.27, "That", 390, 900, 243)
Wd(10.57, "I've", 1690, 900, 175)
Wd(10.87, "Made", 250, 500, 97, rot=55)
Wd(11.07, "of", 430, 340, 81, rot=30)
Wd(11.50, "my", 610, 245, 81, rot=8, light=True)
Wd(11.87, "Mind", 850, 215, 97, rot=-15)
# --- L10 （12.43–13.30）
Wd(12.57, "I", 120, 420, 97)
Wd(12.87, "hope", 120, 590, 130, align='l')
Wd(13.10, "youuuuu", 120, 750, 75, light=True, grow=0.06, align='l')
# --- L5 （13.30–14.17）
Wd(13.57, "Fee", 1330, 520, 130, align='l')
Wd(13.80, "lllllll", 0, 0, 130, follow=True, grow=0.05, gap=0)
# --- L9 （14.17–15.57）
Wd(14.27, "What", 330, 170, 130)
Wd(14.70, "I", 640, 370, 97, color=PINK)
Wd(15.00, "Felt", 1000, 830, 130, color=SKYL)
# --- L8 （15.57–16.87）
Wd(15.70, "When", 1650, 300, 130, color=SKYL)
Wd(16.00, "you", 1760, 420, 75, color=SKYL, light=True)
Wd(16.27, "Shat", 1330, 620, 130)
Wd(16.63, "tered", 0, 0, 75, follow=True, light=True, gap=8)
# --- I1 （16.87–18.00）
Wd(16.87, "My", 700, 170, 130, until=17.27)
Wd(17.27, "Soul", 700, 170, 130, until=17.67)
# --- I4 （18.00–19.07）
Wd(18.07, "Cause", 700, 270, 120, color=CREAM)
Wd(18.37, "you", 0, 0, 80, color=CREAM, follow=True, light=True, gap=14)
Wd(18.67, "were", 1380, 520, 150, color=CREAM, light=True)
# --- L7 （19.07–20.13）
Wd(19.07, "cruel", 1250, 560, 80, until=19.47)
Wd(19.47, "and", 1250, 480, 90, until=19.77)
Wd(19.77, "I'm", 1250, 480, 107, until=19.97)
Wd(19.97, "a", 1250, 480, 90)
# --- L13 （20.13–23.53）
Wd(20.13, "Fool", 770, 440, 480, behind=True)
Wd(21.17, "SO", 1700, 680, 150)
Wd(21.87, "Please", 1680, 550, 92)
Wd(22.17, "Let", 1540, 460, 52, light=True)
Wd(22.47, "me", 1720, 410, 85)
Wd(22.77, "go", 1830, 350, 56, light=True)
# --- L3 结尾（23.53–27.5）
Wd(23.90, "Welcome", 1010, 120, 85, align='l')
Wd(24.25, "back", 0, 0, 85, follow=True, gap=24)
Wd(24.60, "to", 1010, 240, 85, align='l')
Wd(24.95, "Las Vegas,", 0, 0, 85, follow=True, gap=24)

_fonts = {}


def get_font(fs, axes):
    k = (fs, axes)
    if k not in _fonts:
        f = ImageFont.truetype(FONT_BOLD, fs)
        f.set_variation_by_axes(list(axes))
        _fonts[k] = f
    return _fonts[k]


def smooth_alpha(img2x):
    """2x 画布上的 L 图：高斯+阈值把字形拐角变圆。"""
    a = img2x.filter(ImageFilter.GaussianBlur(ROUND * 0.6))
    arr = np.asarray(a, np.float32) / 255.0
    arr = np.clip((arr - 0.5) * 3.2 + 0.5, 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8))


def make_sprite(text, cap, light, rot=0):
    """返回 (alpha, 前进宽度, 基线 y, 左 pad)（1x 像素）；文字起点在 (pad, base)。"""
    axes = tuple(FONT_AXES_LIGHT if light else FONT_AXES_BOLD)
    fs2 = int(round(cap / 0.69 * 2))
    f = get_font(fs2, axes)
    adv = f.getlength(text)
    pad = int(fs2 * 0.3)
    base = int(fs2 * 0.95)
    cw, ch = int(adv + pad * 2), int(fs2 * 1.5)
    im = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(im).text((pad, base), text, font=f, fill=255, anchor='ls')
    if not light:
        im = smooth_alpha(im)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = im.resize((max(im.size[0] // 2, 1), max(im.size[1] // 2, 1)), Image.LANCZOS)
    return np.asarray(im, np.uint8), adv / 2.0, base / 2.0, pad / 2.0


def place_words():
    """把 LY 展开成 items：dict(t0,t1,a,x0,y0,color,behind)。"""
    items = []
    prev = None
    for d in LY:
        t0 = d['t']
        k = max(i for i in range(len(CUTS) - 1) if CUTS[i] <= t0 + 1e-6)
        t1 = min(d.get('until', 99), CUTS[k + 1])
        light = d.get('light', False)
        if d.get('rot'):
            a = make_sprite(d['text'], d['cap'], light, d['rot'])[0]
            items.append(dict(t0=t0, t1=t1, a=a, x0=d['x'] - a.shape[1] / 2.0, y0=d['y'] - a.shape[0] / 2.0,
                              color=d['color'], behind=False))
            prev = None
            continue
        if d.get('follow') and prev is not None:
            bx = prev['right'] + d.get('gap', 8)
            bl = prev['baseline'] + d.get('dy', 0)
        else:
            bl = d['y'] + d['cap'] / 2.0 + d.get('dy', 0)
            adv0 = make_sprite(d['text'], d['cap'], light)[1]
            bx = d['x'] if d.get('align', 'c') == 'l' else d['x'] - adv0 / 2.0
        adv = make_sprite(d['text'], d['cap'], light)[1]
        if d.get('grow'):
            n = len(d['text'])
            for i in range(1, n + 1):
                a, _, base, pad = make_sprite(d['text'][:i], d['cap'], light)
                ti = t0 + (i - 1) * d['grow']
                te = t0 + i * d['grow'] if i < n else 99
                items.append(dict(t0=ti, t1=min(t1, te if i < n else t1), a=a, x0=bx - pad, y0=bl - base,
                                  color=d['color'], behind=False))
        else:
            a, _, base, pad = make_sprite(d['text'], d['cap'], light)
            items.append(dict(t0=t0, t1=t1, a=a, x0=bx - pad, y0=bl - base, color=d['color'], behind=d.get('behind', False)))
        prev = dict(right=bx + adv, baseline=bl)
    return items


def blit_alpha(frame, a, x0, y0, color):
    h, w = a.shape
    x0, y0 = int(round(x0)), int(round(y0))
    X0, Y0 = max(x0, 0), max(y0, 0)
    X1, Y1 = min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0:
        return
    sub = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0].astype(np.float32)[..., None] / 255.0
    reg = frame[Y0:Y1, X0:X1]
    frame[Y0:Y1, X0:X1] = reg * (1 - sub) + np.array(color, np.float32) * sub


# ===================== 手写 Jandy =====================
def sm(x):
    x = min(max(x, 0), 1)
    return x * x * (3 - 2 * x)


class Hand:
    """照搬 jd v5b 的写字动画：软边从左到右逐笔揭开，纯白，带轻阴影。"""

    def __init__(self):
        S = 2
        font = ImageFont.truetype(HAND_FONT, HAND_SIZE * S)
        tmp = Image.new('L', (1600 * S, 700 * S), 0)
        ImageDraw.Draw(tmp).text((100 * S, 100 * S), HAND_TEXT, font=font, fill=255)
        g = tmp.crop(tmp.getbbox())
        gw, gh = g.size[0] // S, g.size[1] // S
        g = g.resize((gw, gh), Image.LANCZOS)
        self.alpha = np.zeros((H, W), np.float32)
        x0 = int(HAND_POS[0] - gw / 2)
        y0 = int(HAND_POS[1] - gh / 2)
        self.alpha[y0:y0 + gh, x0:x0 + gw] = np.asarray(g, np.float32) / 255
        sh = np.asarray(Image.fromarray((self.alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
        self.sh = np.clip(sh * 1.4, 0, 1) * HAND_SHADOW
        self.xa, self.xb = x0 - HAND_SOFT * 0.2, x0 + gw + HAND_SOFT
        self.ya, self.yb = max(y0 - 80, 0), min(y0 + gh + 80, H)
        self.xs = np.arange(W, dtype=np.float32)[None, :]

    def draw(self, frame, t):
        tt = (t - HAND_START) / HAND_WRITE
        if tt <= 0:
            return
        xf = self.xa + (self.xb - self.xa) * sm(tt)
        m = np.clip((xf - self.xs) / HAND_SOFT, 0, 1)
        m = m * m * (3 - 2 * m)
        ya, yb = self.ya, self.yb
        a = (self.alpha * m)[ya:yb, :, None]
        reg = frame[ya:yb]
        reg = reg * (1 - (self.sh * m)[ya:yb, :, None])
        frame[ya:yb] = reg * (1 - a) + 255.0 * a


# ===================== 抠图 =====================
def l13_range():
    k = [i for i, s in enumerate(SHOTS) if s['name'] == 'L13'][0]
    return CF[k], CF[k + 1]


def build_masks():
    from rembg import new_session, remove
    os.makedirs(MASKD, exist_ok=True)
    sess = new_session('isnet-general-use')      # 本机已缓存；u2net_human_seg 需要联网下载太慢
    mm = base_mm()
    lo, hi = l13_range()
    for f in range(lo, hi):
        p = os.path.join(MASKD, 'm%04d.png' % f)
        if os.path.exists(p):
            continue
        m = remove(Image.fromarray(np.array(mm[f])), session=sess, only_mask=True)
        m.save(p)
    print('masks done')


_mc = {}


def load_mask(f):
    if f not in _mc:
        _mc[f] = np.asarray(Image.open(os.path.join(MASKD, 'm%04d.png' % f)).convert('L'), np.float32) / 255.0
    return _mc[f]


def smooth_mask(f):
    lo, hi = l13_range()
    m = 0
    for g, w in ((f - 1, 0.25), (f, 0.5), (f + 1, 0.25)):
        m = m + load_mask(min(max(g, lo), hi - 1)) * w
    im = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(MASK_FEATHER))
    m = np.asarray(im, np.float32) / 255.0
    return np.clip((m - 0.56) * 1.7 + 0.5, 0, 1)


# ===================== 合成 =====================
def compose(f, mm, items, hand):
    t = f / FPS
    frame = np.array(mm[f], dtype=np.float32)
    act = [it for it in items if it['t0'] - 1e-6 <= t < it['t1'] - 1e-6]
    behind = [it for it in act if it['behind']]
    if behind:
        orig = frame.copy()
        for it in behind:
            blit_alpha(frame, it['a'], it['x0'], it['y0'], it['color'])
        m = smooth_mask(f)[..., None]
        frame = frame * (1 - m) + orig * m
    for it in act:
        if not it['behind']:
            blit_alpha(frame, it['a'], it['x0'], it['y0'], it['color'])
    hand.draw(frame, t)
    if t >= FADE_OUT[0]:
        frame *= max(0.0, 1 - (t - FADE_OUT[0]) / (FADE_OUT[1] - FADE_OUT[0]))
    return np.clip(frame + 0.5, 0, 255).astype(np.uint8)


def sheet(times, path, cols=3, tw=640, ref=False):
    mm = base_mm()
    items = place_words()
    hand = Hand()
    th = tw * 9 // 16
    n = len(times) * (2 if ref else 1)
    S = Image.new('RGB', (cols * tw, ((n + cols - 1) // cols) * th))
    k = 0
    for t in times:
        f = min(int(round(t * FPS)), NF - 1)
        ims = []
        if ref:
            r = Image.open(os.path.join(WORK, 'ref_frames', 'r%04d.png' % (min(f, 712) + 1))).convert('RGB') if t < 23.53 else Image.new('RGB', (592, 334))
            ims.append(r)
        ims.append(Image.fromarray(compose(f, mm, items, hand)))
        for im in ims:
            im = im.resize((tw, th), Image.LANCZOS)
            ImageDraw.Draw(im).text((4, 4), '%.2f' % t, fill=(255, 255, 0))
            S.paste(im, ((k % cols) * tw, (k // cols) * th))
            k += 1
    S.save(path, quality=92)


def audio_filter():
    # 输入 0 = 音乐。音乐原样；音乐实际在 23.55 收声(文件 23.78 前是静音)，之后用最后一小段做回声/混响尾巴，淡出到 27.5
    return ('[0:a]aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0,apad=whole_dur=%.3f[m];'
            '[0:a]atrim=start=22.85:end=23.55,asetpts=PTS-STARTPTS,aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0,'
            'apad=pad_dur=4,aecho=0.8:0.9:240|520|900|1400:0.55|0.42|0.30|0.18,aecho=0.8:0.9:700|1500|2300:0.6|0.4|0.25,atrim=start=0.70,asetpts=PTS-STARTPTS,'
            'adelay=23550|23550,afade=t=out:st=23.55:d=3.9[tail];'
            '[m][tail]amix=inputs=2:duration=longest:normalize=0,afade=t=out:st=26.3:d=1.2,atrim=end=%.3f[aout]' % (TOTAL, TOTAL))


def encode():
    os.makedirs(OUTD, exist_ok=True)
    mm = base_mm()
    items = place_words()
    hand = Hand()
    tmpv = os.path.join(OUTD, '_video.mp4')
    cmd = [FF, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-vf', SC_OUT, '-c:v', 'libx264', '-crf', str(CRF), '-preset', 'slow', '-pix_fmt', 'yuv420p',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-an', tmpv]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(NF):
        p.stdin.write(compose(f, mm, items, hand).tobytes())
        if f % 100 == 0:
            print('frame', f, flush=True)
    p.stdin.close()
    p.wait()
    r = subprocess.run([FF, '-y', '-v', 'error', '-i', os.path.join(WORK, 'music.m4a'), '-i', tmpv,
                        '-filter_complex', audio_filter(), '-map', '1:v', '-map', '[aout]', '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-movflags', '+faststart', '-t', str(TOTAL), OUT])
    if r.returncode:
        sys.exit('mux failed')
    os.remove(tmpv)
    print('->', OUT)


def share_and_desk(desk=True):
    subprocess.run([FF, '-y', '-v', 'error', '-i', OUT, '-vf', 'scale=1280:720:flags=lanczos', '-c:v', 'libx264', '-crf', str(CRF_SHARE),
                    '-preset', 'slow', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', OUT_SHARE], check=True)
    if desk:
        os.makedirs(DESK, exist_ok=True)
        shutil.copy(OUT, os.path.join(DESK, 'jd_拉斯维加斯_v1.mp4'))
        shutil.copy(OUT_SHARE, os.path.join(DESK, 'jd_拉斯维加斯_v1_发微信用.mp4'))
        print('copied to', DESK)


if __name__ == '__main__':
    a = sys.argv
    if '--base' in a:
        build_base()
    if '--mask' in a:
        build_masks()
    if '--sheet' in a:    # --sheet out.jpg t1,t2,.. [cols] [ref]
        i = a.index('--sheet')
        sheet([float(x) for x in a[i + 2].split(',')], a[i + 1], int(a[i + 3]) if len(a) > i + 3 else 3, ref=('ref' in a))
    if '--encode' in a:
        encode()
        share_and_desk('--nodesk' not in a)
