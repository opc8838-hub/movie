from common import *
import json,re,argparse
DEST=Path('E:/360MoveData/Users/Administrator/Desktop/applemusic/成片')
NAME={10:'hely_玻璃显标_v10',9:'hely_玻璃显标_v9',8:'hely_玻璃显标_v8',7:'hely_玻璃显标_v7',6:'hely_玻璃显标_v6',5:'hely_玻璃显标_v5',4:'hely_玻璃显标_v4',3:'hely_玻璃显标_v3',2:'hely_玻璃显标_v2'}.get(timeline().get('version'),'hely_玻璃显标_v1')
def main():
    DEST.mkdir(parents=True,exist_ok=True);cfg=timeline();work=ROOT/cfg.get('work','work');duration=cfg['frames']/cfg['fps']
    # Two-pass EBU R128 normalization: preserve both integrated loudness and -3dB true peak.
    base=[FFMPEG,'-hide_banner','-i',work/'music.wav','-af','loudnorm=I=-16:TP=-3:LRA=7:print_format=json','-f','null','-']
    result=subprocess.run([str(x) for x in base],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
    match=re.search(r'\{\s*"input_i".*?\}',result.stderr,re.S);m=json.loads(match.group());(ROOT/'out/loudness_input_v2.json').write_text(json.dumps(m,indent=2))
    norm=f'loudnorm=I=-16:TP=-3:LRA=7:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true:print_format=summary'
    run([FFMPEG,'-hide_banner','-loglevel','warning','-y','-i',work/'music.wav','-af',norm,'-ar','48000',work/'music_master.wav'])
    for suffix,crf in [('',16),('_微信',22)]:
        out=DEST/(NAME+suffix+'.mp4')
        run([FFMPEG,'-hide_banner','-loglevel','warning','-stats_period','5','-progress','pipe:1','-y','-framerate','30','-start_number','0','-i',(work.parent/('v10' if timeline().get('version')==10 else 'v9')/'frames' if timeline().get('version') in (9,10) else work/'frames')/'%04d.png','-i',work/'music_master.wav','-map','0:v','-map','1:a','-t',str(duration),'-frames:v',str(cfg['frames']),'-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709','-c:v','libx264','-profile:v','high','-preset','slow','-crf',str(crf),'-pix_fmt','yuv420p','-sws_flags','lanczos+accurate_rnd+full_chroma_int','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out])
        print(out,out.stat().st_size,flush=True)
    if (DEST/(NAME+'_微信.mp4')).stat().st_size>=10_000_000:raise RuntimeError('WeChat encode exceeds 10 MB')
    run([FFMPEG,'-hide_banner','-loglevel','warning','-stats_period','5','-progress','pipe:1','-y','-i',DEST/(NAME+'.mp4'),'-i',ROOT/'ref/reference_screenrec.mp4','-filter_complex','[0:v]scale=1280:720:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[top];[1:v]crop=592:334:0:335,fps=30,scale=1280:720:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration=2,setpts=PTS-STARTPTS[bottom];[top][bottom]vstack=inputs=2[v]','-map','[v]','-map','0:a','-t',str(duration),'-r','30','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-sws_flags','lanczos+accurate_rnd+full_chroma_int','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-c:a','copy','-movflags','+faststart',DEST/(NAME+'_对比参考.mp4')])
    progress(NAME[-2:]+' 出片：双遍响度处理；正式版、微信版、上下对比版输出',str(DEST))
if __name__=='__main__':main()
