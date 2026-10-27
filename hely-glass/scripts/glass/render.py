import sys,asyncio,base64,json,argparse,threading,http.server,functools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
from playwright.async_api import async_playwright
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
async def main(ranges):
    cfg=timeline();work=cfg.get('work','work');tracks={s['id']:json.loads((ROOT/work/f'shot{s["id"]}/track.json').read_text()) for s in cfg['shots'] if (ROOT/work/f'shot{s["id"]}/track.json').exists()}
    server=http.server.ThreadingHTTPServer(('127.0.0.1',8794),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
    dest=ROOT/work/('frames_raw' if cfg.get('version') in (3,4,5,6,7,8) else 'frames');dest.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=['--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader']);page=await b.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
        page.on('pageerror',lambda e:print('JS ERROR',e,flush=True))
        await page.goto('http://127.0.0.1:8794/glass/'+({8:'render_v3.html',7:'render_v3.html',6:'render_v3.html',5:'render_v3.html',4:'render_v3.html',3:'render_v3.html',2:'render_v2.html'}.get(cfg.get('version'),'render.html')));await page.evaluate('window.ready')
        if cfg.get('tune'):await page.evaluate('t=>{window.tune=t}',cfg['tune'])
        indices=[i for start,end in ranges for i in range(start,end)]
        for i in indices:
            data={'frame':i}
            for s in cfg['shots']:
                if s['start']<=i<s['end']:
                    k=i-s['start'];data.update(tracks[s['id']][k]);data.update(frame=i,shot=s['id'],bg=f'/{work}/shot{s["id"]}/{k:04}.png');break
            out=await page.evaluate('d=>renderFrame(d)',data);(dest/f'{i:04}.png').write_bytes(base64.b64decode(out))
            if cfg.get('version')==8:
                gi=await page.evaluate('()=>{const f=(window.lastGlass||{}).frame||{};return {ps:f.uPlateScale,n:f.uShapeN,pa:f.uPlateAlpha,op:f.uOptics,dr:f.uDrop,tile:(window.lastGlass||{}).tile}}')
                gp=ROOT/work/'glassinfo'/f'{i:04}.json';gp.parent.mkdir(exist_ok=True);gp.write_text(json.dumps(gi))
            if i%15==0:print('render',i,'/',indices[-1]+1,flush=True)
        await b.close()
    server.shutdown()
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--frames',default=f'0:{timeline()["frames"]}');a=ap.parse_args();ranges=[tuple(map(int,x.split(':'))) for x in a.frames.split(',')];asyncio.run(main(ranges))
