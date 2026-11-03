import numpy as np, cv2, subprocess, sys, math, os
from PIL import Image, ImageDraw, ImageFont
U=os.environ.get('SRC_DIR','source')
A=os.path.join(U,'IMG_7132.MP4'); Bv=os.path.join(U,'IMG_7133.MOV'); C=os.path.join(U,'IMG_7134.MOV')
W,H,FPS=1080,1920,30; DUR=22.0; NF=int(DUR*FPS)
BEAT=0.5
OUT=sys.argv[1]; AUD=sys.argv[2]; ONLY=[float(x) for x in sys.argv[3:]]  # preview times
F_BLACK='/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
F_BOLD='/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
F_SEMI='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
F_EMOJI='/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
def clamp(x,a=0,b=1): return max(a,min(b,x))
def eo(x): x=clamp(x); return 1-(1-x)**3
def eio(x): x=clamp(x); return x*x*(3-2*x)
def eback(x,s=1.9): x=clamp(x)-1; return 1+(s+1)*x**3+s*x**2

# ---------- segments: (out_start, out_end, src, src_start, src_end, cam) ----------
# cam(u) -> zoom, dx, dy (fraction of src), rot(deg); timemap(u)->src fraction
lin=lambda u:u
def ramp_fast_slow(u): # speed ramp: fast then slow
    return 1-(1-u)**2.2
def ramp_slow_fast(u): return u**1.8
SEGS=[
 (0.0, 2.0, A, 0.0, 3.35, lambda u:(1.25+0.35*eio(u), 0.0, 0.0, -8+10*eio(u)), ramp_slow_fast),
 (2.0, 4.0, Bv,0.2, 2.6,  lambda u:(1.55-0.25*eo(u),-0.10,0.02, 0), ramp_fast_slow),
 (4.0, 6.0, Bv,4.6, 6.9,  lambda u:(1.45+0.10*u, 0.06,-0.08, 1.5-3*u), lin),
 (6.0, 8.0, C, 2.4, 4.6,  lambda u:(1.35+0.15*u, 0.0, 0.10, 0), ramp_fast_slow),
 (8.0,10.0, Bv,8.2,10.4,  lambda u:(1.40-0.12*eo(u), 0.05, 0.05, -1+2*u), ramp_fast_slow),
 (10.0,12.0,Bv,12.4,14.2, lambda u:(1.30+0.12*u, 0.08,0.0, 0), lin),
 (12.0,14.0,C, 5.4, 7.6,  lambda u:(1.50-0.15*eo(u),-0.05,0.06, 1-2*u), ramp_fast_slow),
 (14.0,17.0,Bv,14.4,16.4, lambda u:(1.42+0.14*u, 0.10,-0.04, -2+3*u), lin),   # slow-mo close-up
 (17.0,22.0,Bv,19.3,23.05,lambda u:(1.55-0.50*eo(u*1.15), 0.0, 0.0, 0), lambda u: eo(u)),
]
CUTS=[s[0] for s in SEGS[1:]]
DROPS=[2.0,17.0]

def decode(path,t0,t1):
    p=subprocess.run(['ffmpeg','-v','error','-ss',str(t0),'-i',path,'-t',str(t1-t0+0.1),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
    pr=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:stream_side_data=rotation','-of','default=nw=1',path],capture_output=True,text=True).stdout
    d=dict(l.split('=') for l in pr.split() if '=' in l); w,h=int(d['width']),int(d['height'])
    if 'rotation' in d and abs(int(float(d['rotation'])))==90: w,h=h,w
    fr=np.frombuffer(p.stdout,np.uint8); n=len(fr)//(w*h*3)
    return fr[:n*w*h*3].reshape(n,h,w,3), pr

# ---------- grading ----------
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
rr=np.sqrt(((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.60))**2)
VIG=np.clip(1-0.55*np.clip(rr-0.35,0,1)**1.6,0,1)[...,None].astype(np.float32)
rng=np.random.default_rng(3)
GRAIN=[(rng.standard_normal((H//2,W//2)).astype(np.float32)) for _ in range(6)]
lut=np.linspace(0,1,256)
def scurve(x): return np.clip(x+0.18*np.sin(2*np.pi*x)*-0.5*(1-np.abs(2*x-1))*0+0.0,0,1)
# build tone LUT: lift blacks slightly down, S-curve, slight highlight roll-off
x=lut; tone=np.clip(0.5+ (x-0.5)*1.18,0,1); tone=tone**1.12
tone=np.clip(tone*0.97+0.008,0,1)
TONE=(tone*255).astype(np.float32)
def grade(img, t, fi):
    f=img.astype(np.float32)/255
    lum=f@np.array([0.299,0.587,0.114],np.float32)
    # saturation
    sat=0.86; f=lum[...,None]+(f-lum[...,None])*sat
    f=np.clip(f,0,1)
    f=cv2.LUT((f*255).astype(np.uint8),TONE.astype(np.uint8)).astype(np.float32)/255
    l=lum[...,None]
    sh=np.clip(1-l*2.2,0,1); hi=np.clip(l*1.6-0.6,0,1)
    f=f+sh*np.array([-0.025,0.01,0.035],np.float32)+hi*np.array([0.02,0.008,-0.012],np.float32)
    # glow
    small=cv2.resize(f,(W//4,H//4),interpolation=cv2.INTER_AREA)
    hl=np.clip(small-0.72,0,1)*2.2
    gl=cv2.GaussianBlur(hl,(0,0),9); gl=cv2.resize(gl,(W,H),interpolation=cv2.INTER_LINEAR)
    f=f+gl*0.28
    # sharpen
    bl=cv2.GaussianBlur(f,(0,0),1.6); f=f+(f-bl)*0.55
    f=f*VIG*0.95
    g=cv2.resize(GRAIN[fi%6],(W,H),interpolation=cv2.INTER_LINEAR)[...,None]
    f=f+g*0.018
    return f

def camera(src, z, dx, dy, rot, pulse):
    h,w=src.shape[:2]
    s0=max(W/w,H/h)*z*pulse
    cx=w/2+dx*w; cy=h/2+dy*h
    # keep within bounds
    halfw=W/2/s0; halfh=H/2/s0
    a=math.radians(rot); ext_w=(halfw*abs(math.cos(a))+halfh*abs(math.sin(a))); ext_h=(halfw*abs(math.sin(a))+halfh*abs(math.cos(a)))
    cx=min(max(cx,ext_w),w-ext_w) if 2*ext_w<w else w/2
    cy=min(max(cy,ext_h),h-ext_h) if 2*ext_h<h else h/2
    M=cv2.getRotationMatrix2D((cx,cy),rot,s0); M[0,2]+=W/2-cx; M[1,2]+=H/2-cy
    return cv2.warpAffine(src,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)

def kick_pulse(t):
    # beat pulse during drum sections (kicks at 0, .75, 1.25 of bar)
    if t<2 or 14<=t<17: return 1.0
    bar=t%2.0; best=9
    for k in (0,0.75,1.25):
        if bar>=k: best=min(best,bar-k)
    return 1+0.022*math.exp(-best/0.09)

# ---------- text system ----------
_fc={}
def font(p,s):
    k=(p,s)
    if k not in _fc: _fc[k]=ImageFont.truetype(p,s)
    return _fc[k]
EF=ImageFont.truetype(F_EMOJI,109)
def emoji_img(ch,size):
    im=Image.new('RGBA',(160,160),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((10,10),ch,font=EF,embedded_color=True)
    im=im.crop(im.getbbox()); r=size/im.height
    return im.resize((max(1,int(im.width*r)),size),Image.LANCZOS)
_tc={}
def text_img(txt,fp,size,track=0.0,fill='silver',emoji=None):
    k=(txt,fp,size,track,fill,emoji)
    if k in _tc: return _tc[k]
    f=font(fp,size); asc,desc=f.getmetrics()
    widths=[f.getlength(c) for c in txt]; tw=int(sum(widths)+track*size*max(len(txt)-1,0))+4
    eimg=emoji_img(emoji,int(size*0.92)) if emoji else None
    ew=(eimg.width+int(size*0.22)) if eimg else 0
    if tw+ew>940 and size>20:
        r=text_img(txt,fp,int(size*940/(tw+ew)),track,fill,emoji); _tc[k]=r; return r
    pad=int(size*0.35)
    im=Image.new('L',(tw+ew+2*pad,asc+desc+2*pad),0); d=ImageDraw.Draw(im); x=pad
    for c,wd in zip(txt,widths): d.text((x,pad),c,font=f,fill=255); x+=wd+track*size
    a=np.array(im).astype(np.float32)/255
    hh,ww=a.shape
    if fill=='silver':
        g=np.linspace(0,1,hh)[:,None]
        col=np.stack([1-0.16*g,1-0.12*g,1-0.06*g],-1)*np.ones((1,ww,1))
        col[:int(hh*0.5)]=np.minimum(col[:int(hh*0.5)]+0.0,1)
    else:
        col=np.ones((hh,ww,3))*np.array(fill,np.float32)/255
    rgba=np.dstack([col,a]).astype(np.float32)
    if eimg:
        e=np.array(eimg).astype(np.float32)/255; ex=pad+tw+int(size*0.22); ey=pad+int((asc-eimg.height)*0.62)
        ey=max(0,ey); reg=rgba[ey:ey+e.shape[0],ex:ex+e.shape[1]]; e=e[:reg.shape[0],:reg.shape[1]]
        reg[...,:3]=e[...,:3]; reg[...,3]=e[...,3]
    _tc[k]=rgba; return rgba

def pill(txt,fp,size,bg,fg=(255,255,255),track=0.04,padx=0.55,pady=0.32,emoji=None,outline=None):
    k=('pill',txt,fp,size,bg,fg,emoji,outline)
    if k in _tc: return _tc[k]
    t=text_img(txt,fp,size,track,fg,emoji)
    # trim transparent margins
    ys,xs=np.where(t[...,3]>0.02); t=t[ys.min():ys.max()+1,xs.min():xs.max()+1]
    px,py=int(size*padx),int(size*pady); hh,ww=t.shape[0]+2*py,t.shape[1]+2*px
    m=Image.new('L',(ww*4,hh*4),0); ImageDraw.Draw(m).rounded_rectangle((0,0,ww*4-1,hh*4-1),radius=hh*2,fill=255)
    m=np.array(m.resize((ww,hh),Image.LANCZOS)).astype(np.float32)/255
    if isinstance(bg,tuple) and len(bg)==4: col=np.array(bg[:3])/255; ba=bg[3]/255
    else: col=np.array(bg)/255; ba=1.0
    out=np.zeros((hh,ww,4),np.float32); out[...,:3]=col; out[...,3]=m*ba
    if outline:
        er=cv2.erode(m,np.ones((5,5),np.uint8)); ring=np.clip(m-er,0,1)
        out[...,:3]=out[...,:3]*(1-ring[...,None])+np.array(outline)/255*ring[...,None]; out[...,3]=np.maximum(out[...,3],ring)
    reg=out[py:py+t.shape[0],px:px+t.shape[1]]; a=t[...,3:4]
    reg[...,:3]=reg[...,:3]*(1-a)+t[...,:3]*a; reg[...,3:4]=np.maximum(reg[...,3:4],a)
    _tc[k]=out; return out

def comp(frame,rgba,cx,cy,scale=1.0,alpha=1.0,blur=0.0,shadow=0.6,glow=0.0,rot=0.0):
    if alpha<=0.003 or scale<=0.01: return
    im=rgba
    if abs(scale-1)>1e-3 or rot:
        h,w=im.shape[:2]; M=cv2.getRotationMatrix2D((w/2,h/2),rot,scale)
        nw,nh=int(w*scale)+40,int(h*scale)+40; M[0,2]+=nw/2-w/2; M[1,2]+=nh/2-h/2
        im=cv2.warpAffine(im,M,(nw,nh),flags=cv2.INTER_LINEAR)
    if blur>0.3: im=cv2.GaussianBlur(im,(0,0),blur)
    h,w=im.shape[:2]; x0=int(cx-w/2); y0=int(cy-h/2)
    a=im[...,3:4]*alpha
    def put(layer_rgb,layer_a,ox,oy):
        X0,Y0=max(0,x0+ox),max(0,y0+oy); X1,Y1=min(W,x0+ox+w),min(H,y0+oy+h)
        if X1<=X0 or Y1<=Y0: return
        sx,sy=X0-(x0+ox),Y0-(y0+oy)
        la=layer_a[sy:sy+Y1-Y0,sx:sx+X1-X0]; lr=layer_rgb[sy:sy+Y1-Y0,sx:sx+X1-X0] if layer_rgb.ndim==3 else layer_rgb
        fr=frame[Y0:Y1,X0:X1]; fr*= (1-la); fr+= lr*la
    if shadow>0:
        sa=cv2.GaussianBlur(a,(0,0),max(6,14*scale))
        if sa.ndim==2: sa=sa[...,None]
        put(np.zeros(3,np.float32),sa*shadow,0,int(8*scale))
    if glow>0:
        ga=cv2.GaussianBlur(a,(0,0),22)
        if ga.ndim==2: ga=ga[...,None]
        X0,Y0=max(0,x0),max(0,y0); X1,Y1=min(W,x0+w),min(H,y0+h)
        if X1>X0 and Y1>Y0:
            frame[Y0:Y1,X0:X1]+=ga[Y0-y0:Y1-y0,X0-x0:X1-x0]*glow*np.array([1,1,1],np.float32)
    put(im[...,:3],a,0,0)

# Text timeline. each item: dict(t_in,t_out,kind,...)
def pop(t,tin,tout,dur=0.28,outdur=0.18):
    """returns (scale,alpha,blur,dy) for a pop-in / blur-out"""
    if t<tin or t>tout: return None
    u=(t-tin)/dur; v=(tout-t)/outdur
    sc=0.55+0.45*eback(u) if u<1 else 1.0
    al=clamp(u*2.5)*clamp(v); bl=max(0,(1-clamp(u*1.6))*10)+max(0,(1-clamp(v))*12)
    if v<1: sc*=1+0.12*(1-v)
    return sc,al,bl
def slide(t,tin,tout,dist=70,dur=0.35,outdur=0.2):
    if t<tin or t>tout: return None
    u=eo((t-tin)/dur); v=clamp((tout-t)/outdur)
    return u, u*v, (1-u)*dist - (1-v)*30, (1-u)*8+(1-v)*10

RED=(255,59,48); GOLD=(236,206,150)
def draw_text(frame,t):
    TY=720  # main text line y (upper-middle, Reels-safe)
    # 1. WAIT FOR IT... 👀  (0.0-1.95) word by word on beats
    if t<1.98:
        words=[('WAIT',0.05),('FOR',0.5),('IT',1.0)]
        size=150; imgs=[text_img(w,F_BLACK,size,0.02) for w,_ in words]
        gap=38; tot=sum(i.shape[1] for i in imgs)-2*int(size*0.35)*len(imgs)+gap*2
        x=W/2-tot/2
        for (w,ti),im in zip(words,imgs):
            inner=im.shape[1]-2*int(size*0.35)
            p=pop(t,ti,1.95,dur=0.25)
            if p: comp(frame,im,x+inner/2,TY,p[0],p[1],p[2],0.7)
            x+=inner+gap
        # dots tick on 16ths
        nd=int(clamp((t-1.25)/0.125,0,3)) if t>=1.25 else 0
        if nd: comp(frame,text_img('.'*nd,F_BLACK,150,0.05),x+30,TY,1.0,clamp((1.95-t)/0.15),0,0.6)
        p=pop(t,1.5,1.95,dur=0.3)
        if p: comp(frame,emoji_rgba('👀',140),W/2,TY+190,p[0],p[1],p[2],0.5)
        # small kicker
        s=slide(t,0.25,1.95)
        if s: comp(frame,text_img('SOMETHING NEW IS COMING',F_SEMI,36,0.32,(220,225,235)),W/2,TY-150+s[2]*0.4,1,s[1]*0.85,s[3],0.6)
    # 2. NEW STOCK ALERT 🚨 (2.0-3.95)
    if 2.0<=t<3.98:
        p=pop(t,2.0,3.95,dur=0.3)
        if p: comp(frame,text_img('NEW STOCK',F_BLACK,170,0.0),W/2,TY,p[0],p[1],p[2],0.7,glow=0.18*p[1])
        p=pop(t,2.5,3.95,dur=0.3)
        if p:
            wob=1+0.04*math.sin((t-2.5)*2*math.pi*4)*math.exp(-(t-2.5)*2.5)
            comp(frame,pill('ALERT',F_BLACK,120,RED,emoji='🚨'),W/2,TY+200,p[0]*wob,p[1],p[2],0.6,glow=0.25*p[1],rot=-3)
    # 3. FRESH ARRIVALS / JUST LANDED (4.0-7.95)
    if 4.0<=t<7.98:
        s=slide(t,4.0,7.95,dist=90)
        if s:
            # tracking expands
            tr=0.02+0.06*(1-s[0])
            comp(frame,text_img('FRESH ARRIVALS',F_BLACK,128,round(tr,3)),W/2,TY+s[2],1,s[1],s[3],0.7)
        p=pop(t,5.0,7.95,dur=0.3)
        if p: comp(frame,text_img('JUST LANDED',F_BLACK,150,0.0,GOLD),W/2,TY+175,p[0],p[1],p[2],0.7,glow=0.15*p[1])
        s=slide(t,6.0,7.95,dist=40)
        if s: comp(frame,text_img('FRESH PIECES  •  FRESH STOCK',F_SEMI,38,0.25,(225,228,235)),W/2,TY+320+s[2],1,s[1]*0.9,s[3],0.6)
    # 4. MULTIPLE MODELS. PREMIUM PICKS. (8.0-13.95) + model chips
    if 8.0<=t<13.98:
        s=slide(t,8.0,13.95,dist=90)
        if s: comp(frame,text_img('MULTIPLE MODELS.',F_BLACK,124,0.0),W/2,TY+s[2],1,s[1],s[3],0.7)
        p=pop(t,9.0,13.95,dur=0.3)
        if p: comp(frame,text_img('PREMIUM PICKS.',F_BLACK,124,0.0,GOLD),W/2,TY+160,p[0],p[1],p[2],0.7,glow=0.15*p[1])
        chips=['iPHONE 12 PRO','iPHONE 13','iPHONE 14 PRO','iPHONE 15 PRO MAX','iPHONE 16','iPHONE 17 AIR']
        pos=[(300,1060),(780,1060),(330,1170),(760,1170),(300,1280),(780,1280)]
        for i,(c,(cx,cy)) in enumerate(zip(chips,pos)):
            ti=10.0+i*0.5
            p=pop(t,ti,13.95,dur=0.25)
            if p:
                fl=1+0.015*math.sin((t-ti)*3+i)
                comp(frame,pill(c,F_BOLD,40,(18,18,22,200),(240,240,245),0.06,outline=(120,124,135)),cx,cy+4*math.sin((t+i)*2.2),p[0]*fl,p[1],p[2],0.45)
    # 5. WHICH ONE IS YOUR FAVOURITE? (14.0-16.95) word by word, half-time beats
    if 14.0<=t<16.98:
        l1=[('WHICH',14.0),('ONE',14.5),('IS',15.0)]; l2=[('YOUR',15.5),('FAVOURITE?',16.0)]
        for line,yy,sz,col in ((l1,TY,130,'silver'),(l2,TY+165,130,GOLD)):
            imgs=[text_img(w,F_BLACK,sz,0.0,col) for w,_ in line]; pad=int(sz*0.35); gap=34
            tot=sum(i.shape[1]-2*pad for i in imgs)+gap*(len(imgs)-1)
            if tot>940:
                sz=int(sz*940/tot); imgs=[text_img(w,F_BLACK,sz,0.0,col) for w,_ in line]; pad=int(sz*0.35); gap=int(gap*940/tot)
                tot=sum(i.shape[1]-2*pad for i in imgs)+gap*(len(imgs)-1)
            x=W/2-tot/2
            for (w,ti),im in zip(line,imgs):
                inner=im.shape[1]-2*pad; s=slide(t,ti,16.95,dist=60,dur=0.3)
                if s: comp(frame,im,x+inner/2,yy+s[2],1,s[1],s[3],0.7)
                x+=inner+gap
        p=pop(t,16.25,16.95,dur=0.3)
        if p: comp(frame,text_img('COMMENT BELOW',F_SEMI,36,0.32,(225,228,235),'👇'),W/2,TY+330,p[0],p[1]*0.95,p[2],0.6)
    # 6. DM NOW TO RESERVE YOURS (17.0-22)
    if t>=17.0:
        p=pop(t,17.0,22.5,dur=0.35)
        if p:
            br=1+0.03*math.exp(-((t-17)%1.0)/0.12) if t<20.8 else 1
            comp(frame,text_img('DM NOW',F_BLACK,230,0.0),W/2,TY-20,p[0]*br,p[1],p[2],0.75,glow=0.22*p[1])
        s=slide(t,17.5,22.5,dist=60)
        if s: comp(frame,text_img('TO RESERVE YOURS',F_BLACK,92,0.06,GOLD),W/2,TY+175+s[2],1,s[1],s[3],0.7)
        p=pop(t,18.5,22.5,dur=0.35)
        if p:
            pul=1+0.035*(0.5+0.5*math.sin((t-18.5)*2*math.pi*1.0))
            comp(frame,pill('SEND US A DM',F_BLACK,60,(255,255,255),(10,10,12),0.06,emoji='📩'),W/2,TY+380,p[0]*pul,p[1],p[2],0.55,glow=0.2*p[1])
        s=slide(t,19.5,22.5,dist=30)
        if s: comp(frame,text_img('NEW STOCK AVAILABLE NOW',F_SEMI,36,0.32,(225,228,235)),W/2,TY+520+s[2],1,s[1]*0.9,s[3],0.6)
_ec={}
def emoji_rgba(ch,size):
    k=(ch,size)
    if k not in _ec:
        e=np.array(emoji_img(ch,size)).astype(np.float32)/255; p=20
        o=np.zeros((e.shape[0]+2*p,e.shape[1]+2*p,4),np.float32); o[p:-p,p:-p]=e; _ec[k]=o
    return _ec[k]

# ---------- effects ----------
def light_sweep(f,t,t0,dur=0.7,strength=0.22,ang=0.35):
    u=(t-t0)/dur
    if u<0 or u>1: return
    pos=-0.4+1.8*eio(u)
    d=(xx/W*math.cos(ang)+yy/H*math.sin(ang)*0.6)-pos
    band=np.exp(-(d/0.06)**2)[...,None]*strength*math.sin(math.pi*u)
    f+=band*np.array([1.0,0.97,0.92],np.float32)
SWEEPS=[2.05,6.0,9.0,12.0,17.2,19.6]
def zoom_blur(f,amt):
    acc=f.copy(); n=5
    for i in range(1,n):
        s=1+amt*i/n; M=cv2.getRotationMatrix2D((W/2,H/2),0,s)
        acc+=cv2.warpAffine(f,M,(W,H),borderMode=cv2.BORDER_REFLECT)
    return acc/n
def text_backdrop(f,t):
    # soft dark band behind text for legibility
    a=0.0
    if t<22: a=0.42
    if a>0:
        f*= (1-a*BAND)
yb=np.exp(-((yy-860)/430)**2)[...,None].astype(np.float32)
BAND=yb

# ---------- main ----------
frames_out=ONLY if ONLY else None
if frames_out is None:
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',AUD,
        '-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p','-profile:v','high','-movflags','+faststart',
        '-c:a','aac','-b:a','320k','-shortest',OUT],stdin=subprocess.PIPE)
fi=0
for (o0,o1,path,s0,s1,cam,tm) in SEGS:
    targets=[t for t in (ONLY or []) if o0<=t<o1]
    if ONLY and not targets: continue
    src,_=decode(path,s0,s1); nsrc=len(src)
    ts=targets if ONLY else [ (k+0.5)/FPS for k in range(int(round(o0*FPS)),int(round(o1*FPS))) ]
    for t in ts:
        u=(t-o0)/(o1-o0)
        sp=tm(u)*(nsrc-1.001); i0=int(sp); fr=sp-i0
        img=src[min(int(round(sp)),nsrc-1)]
        z,dx,dy,rot=cam(u)
        # pre-cut push & post-cut settle
        for c in CUTS:
            if c-0.12<t<c: z*=1+0.10*((t-(c-0.12))/0.12)**2
            if c<=t<c+0.15: z*=1+0.06*(1-eo((t-c)/0.15))
        out=camera(img,z,dx,dy,rot,kick_pulse(t))
        f=grade(out,t,fi)
        # intro darkness: open from dark
        if t<2.0: f*=0.55+0.3*eio(t/0.4)
        if 14.0<=t<17.0: f*=0.85
        if t>=20.6: f*=1-0.35*eio((t-20.6)/1.2)
        for c in CUTS:
            if abs(t-c)<0.1: f=zoom_blur(f,0.06*(1-abs(t-c)/0.1))
        for sw in SWEEPS: light_sweep(f,t,sw)
        f*=(1-0.40*BAND)
        # flashes
        for c in CUTS:
            if c<=t<c+0.25:
                k=math.exp(-(t-c)/(0.07 if c in DROPS else 0.04))*(0.85 if c in DROPS else 0.35)
                f=f*(1-k)+k*np.array([1,0.98,0.95],np.float32)
        if t<0.12: f*=t/0.12+0.0  # first-frame black pop
        draw_text(f,t)
        rgb=(np.clip(f,0,1)*255+0.5).astype(np.uint8)
        if ONLY: Image.fromarray(rgb).save(f'{OUT}_{t:05.2f}.jpg',quality=88)
        else: enc.stdin.write(rgb.tobytes())
        fi+=1
    print(f'seg {o0}-{o1} done',flush=True)
if not ONLY: enc.stdin.close(); enc.wait(); print('encoded')
