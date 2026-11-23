# Mix narration (EQ, compression, light room reverb) over the score, ducking music under the voice.
import json, subprocess
tl = json.load(open('timeline.json')); vo = tl['vo']; D = tl['D']
ids = sorted(vo, key=lambda k: vo[k]['start'])
inputs = ['-i','score.wav'] + sum((['-i', f'vo_{i}.wav'] for i in ids), [])
f = []
for n,i in enumerate(ids, 1):
    ms = int(vo[i]['start']*1000)
    f.append(f"[{n}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
f.append("".join(f"[v{n}]" for n in range(1,len(ids)+1)) + f"amix=inputs={len(ids)}:normalize=0,"
         "highpass=f=70,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=2.5,"
         "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=3,asplit=3[vdry][vrev][vsc]")
f.append("[vrev]aecho=0.8:0.6:45|90|140:0.25|0.18|0.12,volume=0.5[vwet]")
f.append("[vdry][vwet]amix=inputs=2:normalize=0[voice]")
f.append("[0:a]volume=0.55[mus]")
f.append("[mus][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[duck]")
f.append(f"[duck][voice]amix=inputs=2:normalize=0,alimiter=limit=0.9,loudnorm=I=-15:TP=-1.5:LRA=11,apad,atrim=0:{D}[out]")
subprocess.run(['ffmpeg','-y','-loglevel','error'] + inputs + ['-filter_complex', ";".join(f), '-map','[out]','-ar','44100','mix.wav'], check=True)
