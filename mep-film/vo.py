# Emotional narration with Kokoro: each phrase gets its own pace and a pause after it.
import json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
K = Kokoro('../kmodel/kokoro-v1.0.onnx', '../kmodel/voices-v1.0.bin')
VOICE = K.get_voice_style('bm_george')*0.7 + K.get_voice_style('bm_fable')*0.3
# (id, scene window start, end, [(phrase, speed, pause_after_sec)])
LINES = [
 ("s0", 0.9, 7.0, [("Look at any city.", 0.88, 0.45), ("Steel. Glass. Stone.", 0.82, 0.5), ("But the real story... is hidden.", 0.8, 0)]),
 ("s1", 7.6, 16.6, [("Every building has a body.", 0.9, 0.4), ("Mechanical systems let it breathe.", 0.98, 0.15), ("Electricity makes it glow.", 0.98, 0.15), ("And plumbing lets life flow through it.", 0.94, 0)]),
 ("s2", 17.2, 25.6, [("And our cities are still rising.", 0.95, 0.35), ("By 2050, nearly seven in ten of us will live in them.", 1.02, 0.35), ("Every new tower needs these hidden veins.", 0.95, 0)]),
 ("s3", 26.2, 35.2, [("Yet buildings drive more than a third of the world's energy emissions.", 1.0, 0.4), ("To heal the planet, we must rebuild them.", 0.9, 0.3), ("Heat pumps. Solar. Smarter power.", 0.95, 0)]),
 ("s4", 35.7, 44.6, [("Then came A.I.", 0.85, 0.4), ("Data centres are hungry, for power, and for cooling.", 0.98, 0.3), ("Their demand could more than double by 2030.", 0.98, 0)]),
 ("s5", 45.2, 52.6, [("Now, buildings are learning to think.", 0.92, 0.3), ("Sensors. Automation. Clean air.", 0.95, 0.3), ("M.E.P. is their nervous system.", 0.92, 0)]),
 ("s6", 53.0, 59.4, [("But there aren't enough hands.", 0.85, 0.35), ("The work is growing faster than the people trained for it.", 1.04, 0)]),
 ("s7", 60.1, 65.6, [("Because the future...", 0.8, 0.45), ("is built on what you cannot see.", 0.8, 0)]),
]
SR = 24000; meta = {}
for lid, start, end, phrases in LINES:
    parts = []
    for text, speed, pause in phrases:
        a, sr = K.create(text, voice=VOICE, speed=speed, lang='en-gb'); assert sr == SR
        nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0]-240): nz[-1]+1200]   # trim silences
        parts += [a, np.zeros(int(pause*SR), dtype=np.float32)]
    w = np.concatenate(parts); sf.write(f'vo_{lid}.wav', w, SR)
    d = len(w)/SR; meta[lid] = {"start": start, "dur": d}
    print(f"{lid} dur={d:5.2f}  window={end-start:5.2f}  {'OK' if d <= end-start else 'OVER by %.2f' % (d-(end-start))}")
json.dump(meta, open('vo_meta.json', 'w'))
