"""把成片压成网页用的版本，放到 media/<slug>.mp4。已存在就跳过，可以中断后重跑。
用法：python -X utf8 site/transcode.py"""
import os, subprocess, sys, json
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'media')
FF = r'E:\claude工作区\back-to-work-video\tools\ffmpeg.exe'
W = r'E:\claude工作区'
# slug: (源文件, 最大高或宽, crf, 最高码率)
J = [
 ('back-to-work', W+r'\back-to-work-video\out\v4\back-to-work-v4.mp4'),
 ('zerog', W+r'\sanxingdui-zerog\out\sanxingdui-zerog-1920x1080.mp4'),
 ('self-love', W+r'\成片\SelfLove-秋日复刻-JandyZhang.mp4'),
 ('sanxingdui-b2w', r'E:\三星堆成品1对比\成品.mp4'),
 ('mv1', r'E:\MV系列\mv1\B2W_MV1_成片.mp4'),
 ('mv2', r'E:\MV系列\MV2\B2W_MV2_成片.mp4'),
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
 ('lianying', W+r'\lianying-launch\final\连盈LY600_v8.mp4'),
 ('lianying-trailer', r'E:\连盈_预告片素材\预告片_v4.mp4'),
 ('tanji', r'E:\360MoveData\Users\Administrator\Desktop\碳基社区介绍片\碳基社区介绍片_v1.mp4'),
 ('jd-film', r'E:\jd\jd_成片_v5b.mp4'),
 ('keynote-talk', r'E:\宣讲\宣讲_成片.mp4'),
 ('hely-stroll', r'E:\宣传视频\Hely_漫步一天_v2.mp4'),
 ('hely-glass', r'E:\applemusic\成片\hely_玻璃显标_v12.mp4'),
 ('jd-lasvegas', r'E:\jd最新\成片\jd_拉斯维加斯_v1.mp4'),
 ('quiet-hours', r'E:\东京女装快闪\QuietHours_v1.mp4'),
 ('dg-guomao', r'E:\东莞国贸动画\东莞国贸_v1.mp4'),
 ('dg-seasons', r'E:\东莞国贸动画\东莞国贸_四季_v1.mp4'),
 ('live-portal', r'E:\新动效\成片\立体世界卡片_方案A_演示_v2.mp4'),
 ('illust-portal', r'E:\插画\成片\插画立体世界_演示.mp4'),
 ('nobody', r'E:\Nobody选素材\Nobody_完整版_v6_左脸酒窝定格.mp4'),
 ('fairy-linda', r'E:\衣服视频\交付\代码重剪_v2\FAIRY_LINDA_15秒_代码重剪_v2_720P.mp4'),
]
LONG = {'keynote-talk': ('scale=1280:-2:flags=lanczos', '27', '1500k'),
        'lianying': (None, '25', '2600k'), 'tanji': (None, '25', '3000k')}
os.makedirs(OUT, exist_ok=True)
for slug, src in J:
    dst = os.path.join(OUT, slug + '.mp4'); tmp = dst + '.tmp.mp4'
    if os.path.exists(dst): print('skip', slug, flush=True); continue
    if not os.path.exists(src): print('MISSING', slug, src, flush=True); continue
    vf, crf, mr = LONG.get(slug, (None, '23', '4000k'))
    cmd = [FF, '-y', '-v', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a:0?']
    if vf: cmd += ['-vf', vf]
    cmd += ['-c:v', 'libx264', '-preset', 'faster', '-crf', crf, '-maxrate', mr, '-bufsize', str(int(mr[:-1]) * 2) + 'k',
            '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
            '-threads', '3', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', tmp]
    r = subprocess.run(cmd)
    if r.returncode == 0:
        os.replace(tmp, dst); print('ok', slug, os.path.getsize(dst) // 1024 // 1024, 'MB', flush=True)
    else:
        print('FAIL', slug, flush=True)
print('DONE', flush=True)
