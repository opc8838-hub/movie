"""把成片压成网页用的版本，放到 media/<slug>.mp4。已存在就跳过，可以中断后重跑。
用法：python -X utf8 site/transcode.py"""
import os, subprocess, sys, json, shutil
from fractions import Fraction
from pathlib import Path
from works import WORKS
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'media')
FF = r'E:\claude工作区\back-to-work-video\tools\ffmpeg.exe'
FP = os.environ.get('FFPROBE') or shutil.which('ffprobe')
if not FP:
    candidates = [Path(FF).with_name('ffprobe.exe')]
    candidates += sorted((Path.home() / '.cache' / 'codex-tools').glob('ffmpeg*/*/bin/ffprobe.exe'))
    FP = next((str(p) for p in candidates if p.is_file()), None)
if not FP:
    sys.exit('ffprobe not found; set FFPROBE to its executable path')
W = r'E:\claude工作区'
# slug: (源文件)
J = [
 ('hand-catch', W+r'\hand-phone\video\catch_full_v3.mp4'),
 ('back-to-work', W+r'\back-to-work-video\out\v4\back-to-work-v4.mp4'),
 ('zerog', W+r'\sanxingdui-zerog\out\sanxingdui-zerog-1920x1080.mp4'),
 ('self-love', W+r'\成片\SelfLove-秋日复刻-JandyZhang.mp4'),
 ('sanxingdui-b2w', r'E:\三星堆成品1对比\成品.mp4'),
 ('mv1', r'D:\B2W成片\微信视频2026-11-07_212830_679.mp4'),
 ('mv2', r'D:\B2W成片\微信视频2026-11-07_212818_645.mp4'),
 ('mv3', r'E:\MV系列\MV3\B2W_MV3_成片.mp4'),
 ('mv4', r'E:\MV系列\MV3\B2W_MV4_十月_成片.mp4'),
 ('sanxingdui-upgrade', r'E:\三星堆升级\三星堆升级_9x16_v10.mp4'),
 ('jomoo-1', r'E:\九牧动画demo\第一段\第一段.mp4'),
 ('jomoo-2', r'E:\九牧动画demo\第二段\第二段.mp4'),
 ('jomoo-3', r'E:\九牧动画demo\第三段\存档\第三段.mp4'),
 ('jomoo-4', r'E:\talk单独一段动画\存档\第四段.mp4'),
 ('jomoo-5', r'E:\九牧动画demo\新的一段\存档\第五段_专利墙.mp4'),
 ('jomoo-6', r'E:\九牧动画demo\新的第一段\新的第一段.mp4'),
 ('jomoo-7', r'E:\九牧动画demo\第五段\存档\连播_新的第三段+三大系统+四大空间.mp4'),
 ('hely-film', r'E:\动物\hely整片_v5_iMac27.mp4'),
 ('hely-thermal', r'E:\360MoveData\Users\Administrator\Desktop\hely-thermal-1080x1350.mp4'),
 ('lianying', r'D:\B2W成片\微信视频2026-11-07_210453_561.mp4'),
 ('lianying-trailer', r'E:\连盈_预告片素材\预告片_v4.mp4'),
 ('tanji', r'E:\360MoveData\Users\Administrator\Desktop\碳基社区介绍片\碳基社区介绍片_v1.mp4'),
 ('jd-film', r'E:\jd\jd_成片_v5b.mp4'),
 ('keynote-talk', r'E:\宣讲\宣讲_成片.mp4'),
 ('hely-stroll', r'D:\B2W成片\微信视频2026-11-07_212934_463.mp4'),
 ('hely-glass', r'E:\applemusic\成片\hely_玻璃显标_v12.mp4'),
 ('jd-lasvegas', r'E:\jd最新\成片\jd_拉斯维加斯_v1.mp4'),
 ('quiet-hours', r'E:\东京女装快闪\QuietHours_v1.mp4'),
 ('dg-guomao', r'E:\东莞国贸动画\东莞国贸_v1.mp4'),
 ('dg-seasons', r'E:\东莞国贸动画\东莞国贸_四季_v1.mp4'),
 ('live-portal', r'E:\新动效\成片\立体世界卡片_方案A_演示_v2.mp4'),
 ('illust-portal', r'D:\B2W成片\微信视频2026-11-07_212515_677.mp4'),
 ('nobody', r'E:\Nobody选素材\Nobody_完整版_v6_左脸酒窝定格.mp4'),
 ('fairy-linda', r'E:\衣服视频\交付\代码重剪_v2\FAIRY_LINDA_15秒_代码重剪_v2_720P.mp4'),
 ('hotl', r'D:\B2W成片\微信视频2026-11-07_212450_012.mp4'),
 ('mutedmen-garden', r'E:\claude工作区\mutedmen-mv\video\MutedMEN_盆栽园MV_v5.mp4'),
 ('your-present', r'D:\B2W成片\微信视频2026-11-07_212551_004.mp4'),
 ('bot-voice', r'D:\B2W成片\微信视频2026-11-07_212610_545.mp4'),
 ('spotlight', r'D:\B2W成片\微信视频2026-11-07_212620_821.mp4'),
 ('cellmotion-promo', r'D:\B2W成片\微信视频2026-11-07_212851_493.mp4'),
 ('hely-yourself', r'D:\B2W成片\微信视频2026-11-07_212923_605.mp4'),
 ('hely-noprompt', r'D:\B2W成片\微信视频2026-11-07_212909_730.mp4'),
 ('hely-style', r'D:\B2W成片\微信视频2026-11-07_212900_061.mp4'),
 ('hely-sea', r'D:\B2W成片\微信视频2026-11-07_212539_716.mp4'),
 ('story-goes-on', r'D:\B2W成片\微信视频2026-11-07_212435_426.mp4'),
 ('vision', r'D:\B2W成片\微信视频2026-11-07_212502_245.mp4'),
 ('pixel-fish', r'D:\B2W成片\微信视频2026-11-07_212600_887.mp4'),
]
LONG = {'keynote-talk': ('scale=1280:-2:flags=lanczos', '27', '1500k'),
        'lianying': (None, '25', '2200k'), 'tanji': (None, '25', '3000k')}
ACTIVE = {w['slug'] for w in WORKS if not w.get('draft')}
LIMIT = 50_000_000
os.makedirs(OUT, exist_ok=True)
failed = []
for slug, src in J:
    if slug not in ACTIVE:
        print('draft/unused', slug, flush=True); continue
    dst = os.path.join(OUT, slug + '.mp4'); tmp = dst + '.tmp.mp4'
    if os.path.exists(dst): print('skip', slug, flush=True); continue
    if not os.path.exists(src):
        print('MISSING', slug, src, flush=True); failed.append(slug); continue
    meta = json.loads(subprocess.check_output([FP, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', src]))
    video = next(s for s in meta['streams'] if s['codec_type'] == 'video')
    width, height = video['width'], video['height']
    # 用平均帧率识别实际 50/60 帧，容许封装尾帧带来的微小误差。
    rate = float(Fraction(video['avg_frame_rate']))
    fps = next((n for n in (50, 60) if abs(rate - n) < .05), 30)
    vf, crf, mr = LONG.get(slug, (None, '23', '4000k'))
    if vf is None:
        if width >= height:
            vf = f'scale=-2:{min(height, 1080) // 2 * 2}:flags=lanczos'
        else:
            vf = f'scale={min(width, 1080) // 2 * 2}:-2:flags=lanczos'
    vf += f',fps={fps}'
    maxrate = int(mr[:-1])
    for attempt in range(6):
        print('encode', slug, vf, 'CRF', crf, 'maxrate', maxrate, flush=True)
        cmd = [FF, '-y', '-v', 'error', '-threads', '3', '-i', src, '-map', '0:v:0', '-map', '0:a:0?', '-vf', vf]
        cmd += ['-c:v', 'libx264', '-preset', 'faster', '-crf', crf, '-maxrate', f'{maxrate}k', '-bufsize', f'{maxrate * 2}k',
            '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
            '-threads', '3', '-filter_threads', '1', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', tmp]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            break
        if os.path.getsize(tmp) < LIMIT:
            os.replace(tmp, dst); print('ok', slug, os.path.getsize(dst), 'bytes', flush=True)
            break
        budget = int((48_000_000 * 8 / float(meta['format']['duration']) - 128_000) / 1000)
        maxrate = max(100, min(int(maxrate * .85), budget))
        print('retry size limit', slug, flush=True)
    if not os.path.exists(dst):
        failed.append(slug); print('FAIL', slug, flush=True)
        if os.path.exists(tmp): os.remove(tmp)
print('DONE', flush=True)
if failed: sys.exit('Failed: ' + ', '.join(failed))
