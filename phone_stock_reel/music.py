import numpy as np, scipy.signal as ss, wave, sys
SR=44100; BPM=120; B=60/BPM; DUR=22.0
N=int(SR*(DUR+1.5)); L=np.zeros(N); R=np.zeros(N)
rng=np.random.default_rng(7)
def add(sig,t,g=1.0,pan=0.0):
    i=int(t*SR); n=min(len(sig),N-i)
    if n<=0: return
    L[i:i+n]+=sig[:n]*g*np.sqrt((1-pan)/2)*1.414; R[i:i+n]+=sig[:n]*g*np.sqrt((1+pan)/2)*1.414
def env(n,a,d): 
    t=np.arange(n)/SR; e=np.minimum(t/max(a,1e-4),1)*np.exp(-t/d); return e
def hz(m): return 440*2**((m-69)/12)
def kick(sub_note=None,length=0.45):
    n=int(SR*length); t=np.arange(n)/SR
    f=45+110*np.exp(-t/0.03); ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.exp(-t/0.28)+0.3*np.sin(ph*2)*np.exp(-t/0.02)
    click=rng.standard_normal(n)*np.exp(-t/0.003)*0.3
    return np.tanh(1.6*(s+click))
def b808(note,length):
    n=int(SR*length); t=np.arange(n)/SR
    f=hz(note)*(1+0.8*np.exp(-t/0.04)); ph=2*np.pi*np.cumsum(f)/SR
    e=np.minimum(t/0.005,1)*np.exp(-t/(length*0.6)); e[-400:]*=np.linspace(1,0,400)
    return np.tanh(2.2*np.sin(ph))*e
def clap():
    n=int(SR*0.35); t=np.arange(n)/SR; x=rng.standard_normal(n)
    b,a=ss.butter(2,[900/(SR/2),5000/(SR/2)],'band'); x=ss.lfilter(b,a,x)
    e=np.zeros(n)
    for k,o in enumerate([0,0.011,0.022,0.031]):
        i=int(o*SR); e[i:]+=np.exp(-(t[:n-i])/(0.012 if k<3 else 0.14))
    return x*e*1.4
def hat(open_=False):
    n=int(SR*(0.25 if open_ else 0.06)); t=np.arange(n)/SR; x=rng.standard_normal(n)
    b,a=ss.butter(2,7500/(SR/2),'high'); x=ss.lfilter(b,a,x)
    return x*np.exp(-t/(0.09 if open_ else 0.014))*0.5
def supersaw(notes,length,cut=2500):
    n=int(SR*length); t=np.arange(n)/SR; s=np.zeros(n)
    for m in notes:
        for d in (-0.12,-0.05,0,0.05,0.12):
            f=hz(m+d); s+=2*((t*f+rng.random())%1)-1
    s/=len(notes)*5
    b,a=ss.butter(2,cut/(SR/2)); s=ss.lfilter(b,a,s)
    e=np.minimum(t/0.08,1)*np.minimum((length-t)/0.15,1); return s*e
def pluck(m,length=0.22):
    n=int(SR*length); t=np.arange(n)/SR; f=hz(m)
    s=(2*((t*f)%1)-1)+0.5*np.sin(2*np.pi*f*2*t)
    b,a=ss.butter(2,3500/(SR/2)); s=ss.lfilter(b,a,s)
    return s*np.exp(-t/0.09)*np.minimum(t/0.002,1)
def riser(length):
    n=int(SR*length); t=np.arange(n)/SR; x=rng.standard_normal(n); out=np.zeros(n); blk=1024
    for i in range(0,n,blk):
        fc=300+9000*(i/n)**2; b,a=ss.butter(2,[fc*0.7/(SR/2),min(fc*1.3,20000)/(SR/2)],'band')
        out[i:i+blk]=ss.lfilter(b,a,x[i:i+blk])
    tone=np.sin(2*np.pi*np.cumsum(200+1400*(t/length)**2)/SR)*0.15
    return (out*0.6+tone)*(t/length)**1.5
def impact():
    n=int(SR*2.5); t=np.arange(n)/SR
    boom=np.sin(2*np.pi*np.cumsum(30+80*np.exp(-t/0.08))/SR)*np.exp(-t/0.7)
    x=rng.standard_normal(n); b,a=ss.butter(2,3000/(SR/2),'high')
    crash=ss.lfilter(b,a,x)*np.exp(-t/0.6)*0.35
    return np.tanh(1.5*boom)+crash
def whoosh(length=0.4,up=True):
    n=int(SR*length); t=np.arange(n)/SR; x=rng.standard_normal(n); out=np.zeros(n); blk=512
    for i in range(0,n,blk):
        p=i/n; p=p if up else 1-p; fc=500+6000*p
        b,a=ss.butter(2,[fc*0.6/(SR/2),min(fc*1.5,20000)/(SR/2)],'band'); out[i:i+blk]=ss.lfilter(b,a,x[i:i+blk])
    return out*np.sin(np.pi*t/length)**2*0.5
# Progression F minor: Fm Db Ab Eb (1 bar = 2s each)
prog=[[53,56,60,65],[49,53,56,61],[56,60,63,68],[51,55,58,63]]
roots=[29,25,32,27]
bars=int(DUR/(4*B))+1
# Intro bar 0 (0-2s): filtered pad, riser, ticking hats
add(supersaw(prog[0],2.0,cut=700),0,0.5)
add(riser(2.0),0,0.55)
for k in range(8): add(hat(),k*0.25,0.35*(k/8+0.3))
for k in range(8): add(hat(),1.5+k*0.0625,0.3)
CUTS=[2,4,6,8,10,12,14,17]
for bi in range(1,bars):
    t0=bi*4*B
    if t0>=DUR: break
    ch=prog[bi%4]; r=roots[bi%4]
    breakdown = 14<=t0<17
    add(supersaw(ch,4*B,cut=1400 if breakdown else 3200),t0,0.42)
    # arp plucks
    arp=[ch[0]+12,ch[2]+12,ch[1]+12,ch[3]+12]
    for k in range(8): add(pluck(arp[k%4]),t0+k*B/2,0.16,pan=0.4 if k%2 else -0.4)
    if breakdown: continue
    # drums: kick pattern (beats 1, 2.5(and), 3.75?) 
    for kt in [0,1.5*B,2.5*B]: add(kick(),t0+kt,0.9)
    add(b808(r,1.4*B),t0,0.55); add(b808(r,1.0*B),t0+1.5*B,0.5); add(b808(r+(12 if bi%2 else 7),1.4*B),t0+2.5*B,0.45)
    for ct in [B,3*B]: add(clap(),t0+ct,0.6)
    for k in range(16):
        if bi%2==1 and k>=12: continue
        add(hat(),t0+k*B/4,0.33 if k%2==0 else 0.2,pan=0.25)
    if bi%2==1:
        for k in range(12): add(hat(),t0+3*B+k*B/12,0.22,pan=0.25)
    add(hat(True),t0+3.5*B,0.25,pan=-0.3)
# breakdown 14-17: halftime with slow kick; riser into 17
for kt in [14.0,15.0,16.0]: add(kick(),kt,0.6)
add(clap(),15.0,0.5); add(clap(),16.0,0.5)
for k in range(8): add(clap(),16.5+k*0.0625,0.25*(k+1)/8)
add(riser(1.5),15.5,0.5)
# impacts on drops and whooshes on cuts
add(impact(),2.0,0.8); add(impact(),17.0,0.85)
for c in CUTS: 
    if c not in (2,17): add(whoosh(0.35),c-0.3,0.45)
# ending: final hit + fade
add(impact(),21.0,0.4)
mix=np.stack([L,R],1)
# master: glue, sidechain-ish pump from kick not needed; fade end
fade_s=int(20.8*SR); fade_e=int((DUR)*SR)
mix[fade_s:fade_e]*=np.linspace(1,0,fade_e-fade_s)[:,None]**1.5; mix[fade_e:]=0
mix=np.tanh(mix*1.2/np.max(np.abs(mix))*1.8)
mix=mix/np.max(np.abs(mix))*0.89
mix=mix[:int(DUR*SR)]
with wave.open(sys.argv[1],'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*32767).astype('<i2').tobytes())
print('ok')
