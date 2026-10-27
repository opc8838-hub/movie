import sys, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np
from PIL import Image
import echo_wave_v12 as E
SRC = ROOT / 'work/v8/frames'; OUT = ROOT / 'work/v12/frames'; OUT.mkdir(parents=True, exist_ok=True)
a, b = map(int, sys.argv[1].split(':'))
for i in range(a, b):
    p = OUT / f'{i:04}.png'
    if p.exists() and p.stat().st_size > 0 and i not in range(34, 258): continue
    if 34 <= i < 258:
        img = np.asarray(Image.open(E.B.RAW / f'{i:04}.png').convert('RGB'))
        Image.fromarray(E.wave(img, i)).save(p, compress_level=2)
    else:
        shutil.copyfile(SRC / f'{i:04}.png', p)
