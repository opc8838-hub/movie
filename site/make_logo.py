"""从手写 logo 原图和动画帧，生成网站用的透明 logo、favicon、开场手写视频。
用法：python -X utf8 site/make_logo.py"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'assets')
SRC = r'E:\claude工作区\b2w-mv1\src\logo.png'
TMP = os.path.join(tempfile.gettempdir(), 'b2w_logo_frames')
os.makedirs(TMP, exist_ok=True)
subprocess.run([sys.executable, '-X', 'utf8', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_anim.py')], check=True, env={**os.environ, 'LOGO_OUT': TMP})
FRAMES = os.path.join(TMP, '%04d.png')
FF = r'E:\claude工作区\back-to-work-video\tools\ffmpeg.exe'
g = np.asarray(Image.open(SRC).convert('L')).astype(np.float32)
bg = np.median(g)
ink = np.clip((bg - g) / (bg - 10), 0, 1)
ink = np.clip((ink - 0.10) / 0.82, 0, 1)
ys, xs = np.where(ink > 0.2)
pad = 6
box = (xs.min() - pad, ys.min() - pad, xs.max() + pad + 1, ys.max() + pad + 1)
def save(name, inkarr, val):
    a = (inkarr * 255).astype(np.uint8)
    rgba = np.dstack([np.full_like(a, val)] * 3 + [a])
    Image.fromarray(rgba, 'RGBA').save(os.path.join(A, name), optimize=True)
crop = ink[box[1]:box[3], box[0]:box[2]]
save('logo-black.png', crop, 0); save('logo-white.png', crop, 255)
print('logo', crop.shape)
# B2W 方块字：竖线右边
line_x = 1039 - box[0]
mark = crop[:, line_x + 30:]
my, mx = np.where(mark > 0.2)
mark = mark[my.min():my.max() + 1, mx.min():mx.max() + 1]
save('mark-black.png', mark, 0); save('mark-white.png', mark, 255)
s = max(mark.shape) + 40
fav = np.zeros((s, s), np.float32)
oy, ox = (s - mark.shape[0]) // 2, (s - mark.shape[1]) // 2
fav[oy:oy + mark.shape[0], ox:ox + mark.shape[1]] = mark
Image.fromarray(((fav) * 255).astype(np.uint8)).resize((180, 180), Image.LANCZOS).save(os.path.join(A, 'favicon.png'))
print('mark', mark.shape)
# 开场：白字黑底（反相）和黑字白底（原样）。尾帧多停一下由网页控制
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-movflags', '+faststart', '-an']
SC = 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int'
subprocess.run([FF, '-y', '-v', 'error', '-framerate', '30', '-start_number', '0', '-i', FRAMES, '-vf', 'negate,' + SC] + ENC + [os.path.join(A, 'logo-write-dark.mp4')], check=True)
subprocess.run([FF, '-y', '-v', 'error', '-framerate', '30', '-start_number', '0', '-i', FRAMES, '-vf', SC] + ENC + [os.path.join(A, 'logo-write-light.mp4')], check=True)
c = Image.new('RGB', (1200, 630), '#000')
l = Image.open(os.path.join(A, 'logo-white.png'))
lw = 820
lr = l.resize((lw, int(l.height * lw / l.width)), Image.LANCZOS)
c.paste(lr, ((1200 - lw) // 2, (630 - lr.height) // 2), lr)
c.save(os.path.join(A, 'og.jpg'), quality=88)
for n in os.listdir(A):
    if os.path.isfile(os.path.join(A, n)): print(n, os.path.getsize(os.path.join(A, n)) // 1024, 'KB')
