"""MiniMax 接口小工具（国内版 api.minimaxi.com）。

  python mm.py music out/music_a.mp3 "prompt..."
  python mm.py fl2v first.png last.png out/flip.mp4 "prompt..." [--res 1080P]
  python mm.py i2v first.png out/x.mp4 "prompt..." [--model MiniMax-Hailuo-2.3] [--res 1080P]
"""
import base64
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = 'https://api.minimaxi.com'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def key():
    for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
        if line.startswith('MINIMAX_API_KEY='):
            return line.split('=', 1)[1].strip()


def call(path, body=None, timeout=600):
    req = urllib.request.Request(HOST + path, headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json'})
    if body is not None:
        req.data = json.dumps(body).encode()
    with OPENER.open(req, timeout=timeout) as r:
        return json.loads(r.read())


def img_b64(p):
    ext = os.path.splitext(p)[1].lstrip('.').lower().replace('jpg', 'jpeg')
    return 'data:image/%s;base64,%s' % (ext, base64.b64encode(open(p, 'rb').read()).decode())


def download(url, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with OPENER.open(url, timeout=120) as r:
        with open(out, 'wb') as f:
            f.write(r.read())
    print('saved', out)


def music(out, prompt, model='music-3.0'):
    body = {'model': model, 'prompt': prompt, 'is_instrumental': True, 'output_format': 'url',
            'audio_setting': {'sample_rate': 44100, 'bitrate': 256000, 'format': 'mp3'}}
    r = call('/v1/music_generation', body)
    if r.get('base_resp', {}).get('status_code') != 0:
        print(json.dumps(r, ensure_ascii=False)[:600])
        if model == 'music-3.0':
            print('retry with music-3.0-free')
            return music(out, prompt, 'music-3.0-free')
        sys.exit(1)
    print(json.dumps(r.get('extra_info', {}), ensure_ascii=False))
    download(r['data']['audio'], out)


def wait_video(task_id, out):
    while True:
        time.sleep(15)
        try:
            r = call('/v1/query/video_generation?task_id=' + task_id, timeout=60)
        except Exception as e:                      # 网络抖动：下一轮再查
            print(time.strftime('%H:%M:%S'), 'retry', e, flush=True)
            continue
        st = r.get('status')
        print(time.strftime('%H:%M:%S'), st, flush=True)
        if st == 'Success':
            f = call('/v1/files/retrieve?file_id=' + r['file_id'])
            download(f['file']['download_url'], out)
            return
        if st == 'Fail':
            print(json.dumps(r, ensure_ascii=False))
            sys.exit(1)


def video(out, body):
    r = call('/v1/video_generation', body)
    print(json.dumps(r, ensure_ascii=False))
    if r.get('base_resp', {}).get('status_code') != 0:
        sys.exit(1)
    wait_video(r['task_id'], out)


def opt(args, name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a.pop(0)
    res = opt(a, '--res', '1080P')
    model = opt(a, '--model', None)
    if cmd == 'music':
        music(a[0], a[1])
    elif cmd == 'fl2v':
        video(a[2], {'model': model or 'MiniMax-Hailuo-02', 'first_frame_image': img_b64(a[0]),
                     'last_frame_image': img_b64(a[1]), 'prompt': a[3], 'duration': 6,
                     'resolution': res, 'prompt_optimizer': False})
    elif cmd == 'get':
        wait_video(a[0], a[1])
    elif cmd == 'i2v':
        video(a[1], {'model': model or 'MiniMax-Hailuo-2.3', 'first_frame_image': img_b64(a[0]),
                     'prompt': a[2], 'duration': 6, 'resolution': res, 'prompt_optimizer': False})
