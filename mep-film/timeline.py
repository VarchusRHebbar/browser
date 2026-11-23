# Re-time scenes so each narration line fits, then patch film.html, audio.py and vo start times.
import json, re
meta = json.load(open('vo_meta.json'))
ids = ['s0','s1','s2','s3','s4','s5','s6','s7']
old = [7.5,10,9.5,10,10,8.5,7,7]; lead = [0.9,0.7,0.7,0.7,0.7,0.7,0.6,1.0]; OV = 0.5
scenes, start = [], 0.0
for i, lid in enumerate(ids):
    L = max(old[i], lead[i] + meta[lid]['dur'] + (0.9 if i < 7 else 1.6))
    scenes.append((round(start,2), round(start+L+OV,2))); meta[lid]['start'] = round(start + lead[i], 2)
    start += L
D = round(scenes[-1][1] - OV + 0.0, 2); scenes[-1] = (scenes[-1][0], D)
json.dump({"scenes": scenes, "D": D, "vo": meta}, open('timeline.json','w'), indent=1)
s = open('film.html').read()
names = ['S0','S1','S2','S3','S4','S5','S6','S7']
arr = ",\n  ".join(f"[{n}, {a}, {b}]" for n,(a,b) in zip(names, scenes))
s = re.sub(r"const SCENES = \[.*?\n\];", "const SCENES = [\n  " + arr + "\n];", s, flags=re.S)
s = re.sub(r"DURATION = [\d.]+", f"DURATION = {D}", s)
open('film.html','w').write(s)
a = open('audio.py').read()
a = re.sub(r"sr=44100; D=[\d.]+;", f"sr=44100; D={D};", a)
a = re.sub(r"^cues=\[.*?\]", "cues=" + str([x for x,_ in scenes]), a, flags=re.M)
open('audio.py','w').write(a)
print(D, scenes)
