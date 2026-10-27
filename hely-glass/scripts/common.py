from pathlib import Path
import datetime, json, subprocess
ROOT=Path(__file__).resolve().parent
FFMPEG=Path('E:/claude工作区/back-to-work-video/tools/ffmpeg.exe')
def progress(message, paths):
    p=ROOT/'docs/PROGRESS.md'; p.parent.mkdir(exist_ok=True)
    with p.open('a',encoding='utf-8') as f: f.write(f'- {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {message} | {paths}\n')
def run(args):
    subprocess.run([str(x) for x in args],check=True)
def timeline(): return json.loads((ROOT/'timeline.json').read_text(encoding='utf-8'))
