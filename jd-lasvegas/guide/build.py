"""把 template.html 里的 {{图片名}} 和 {{audio}} 换成内嵌数据，生成本目录的 index.html。
用法：python jd-lasvegas/guide/build.py"""
import os, re, base64
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
s = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
audio = open(os.path.join(HERE, 'audio.json'), encoding='utf-8').read()

def rep(m):
    k = m.group(1)
    if k == 'audio':
        return audio
    data = open(os.path.join(HERE, 'img', k + '.jpg'), 'rb').read()
    return 'data:image/jpeg;base64,' + base64.b64encode(data).decode()

body = re.sub(r'\{\{([\w.]+)\}\}', rep, s)
page = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8').write(page)
print('index.html', len(page) // 1024, 'KB')
