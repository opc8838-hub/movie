"""按 works.py 的封面时间，从 media/*.mp4 生成封面 jpg 和悬停预览小视频。已存在就跳过（加 --force 重做）。
用法：python -X utf8 site/make_media.py"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from works import WORKS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, 'media')
FF = r'E:\claude工作区\back-to-work-video\tools\ffmpeg.exe'
force = '--force' in sys.argv


def run(*a):
    subprocess.run([FF, '-y', '-v', 'error', *a], check=True)


def poster(slug, src, t, w, h):
    out = os.path.join(M, slug + '.jpg')
    if os.path.exists(out) and not force:
        return
    sc = 'scale=1000:-2:flags=lanczos' if w >= h else 'scale=720:-2:flags=lanczos'
    run('-ss', str(t), '-i', os.path.join(M, src + '.mp4'), '-frames:v', '1', '-vf', sc, '-q:v', '3', out)


def preview(slug, src, t, w, h, dur):
    out = os.path.join(M, slug + '.prev.mp4')
    if os.path.exists(out) and not force:
        return
    start = max(0, min(t, (dur or 99) - 3.5))
    sc = 'scale=640:-2:flags=lanczos,fps=30' if w >= h else 'scale=400:-2:flags=lanczos,fps=30'
    run('-ss', str(start), '-t', '3.5', '-i', os.path.join(M, src + '.mp4'), '-an', '-vf', sc,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '30', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-threads', '3', out)


for w in WORKS:
    src = w.get('poster_from', w['slug'])
    poster(w['slug'], src, w['poster'], w['w'], w['h'])
    preview(w['slug'], src, w['poster'], w['w'], w['h'], w['dur'] or 18.8)
    for p in w.get('parts', []):
        poster(p[0], p[0], p[5], p[2], p[3])
    print('ok', w['slug'], flush=True)
total = sum(os.path.getsize(os.path.join(M, f)) for f in os.listdir(M))
print('media total', total // 1024 // 1024, 'MB')
