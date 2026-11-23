import numpy as np, wave
sr=44100; D=78.62; n=int(sr*D); t=np.arange(n)/sr
rng=np.random.default_rng(3)
out=np.zeros(n)
# drone (D2 + A2) breathing
env=np.clip(t/4,0,1)*np.clip((D-t)/3,0,1)
out+=0.06*env*(np.sin(2*np.pi*73.42*t)+0.6*np.sin(2*np.pi*110*t+1)+0.25*np.sin(2*np.pi*146.8*t))*(0.75+0.25*np.sin(2*np.pi*t/9))
# plucks: D minor pentatonic
scale=[293.66,349.23,392.0,440.0,523.25,587.33,698.46,784.0]
def pluck(t0,f,amp):
    L=int(sr*3.5); i=int(t0*sr)
    if i>=n: return
    tt=np.arange(min(L,n-i))/sr
    bend=f*(1+0.012*np.exp(-tt*6))       # slight pitch bend like a guzheng
    ph=2*np.pi*np.cumsum(bend)/sr
    s=(np.sin(ph)+0.45*np.sin(2*ph)*np.exp(-tt*3)+0.2*np.sin(3*ph)*np.exp(-tt*5))
    s*=np.exp(-tt*1.6)*np.minimum(1,tt*400)
    out[i:i+len(tt)]+=amp*s
cues=[0.0, 9.12, 20.28, 31.84, 43.21, 54.5, 64.05, 71.05]
tt0=1.0
while tt0<D-4:
    near=min(abs(tt0-c) for c in cues)
    if rng.random()<0.75:
        f=scale[rng.integers(0,len(scale))]
        pluck(tt0,f,0.11 if near>0.5 else 0.15)
        if rng.random()<0.3: pluck(tt0+0.12,f*1.5 if f<600 else f/2,0.07)
    tt0+=rng.choice([0.5,0.75,1.0,1.0,1.5])
for c in cues: pluck(c+0.05,146.83,0.18); pluck(c+0.05,220,0.08)   # low gong-ish strike on each scene
pluck(D-6,293.66,0.16); pluck(D-5.5,440,0.12); pluck(D-5,587.33,0.12)
# reverb: convolve with decaying noise
ir_len=int(sr*2.8); ir=rng.standard_normal(ir_len)*np.exp(-np.arange(ir_len)/sr*2.2); ir[0]=0
wet=np.fft.irfft(np.fft.rfft(out,2*n)*np.fft.rfft(ir,2*n))[:n]
mix=out*0.75+wet*0.035
mix*=np.clip((D-t)/2.5,0,1)
mix/=np.abs(mix).max()/0.85
st=np.stack([mix,np.roll(mix,300)],1)
w=wave.open('score.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((st*32767).astype(np.int16).tobytes()); w.close()
