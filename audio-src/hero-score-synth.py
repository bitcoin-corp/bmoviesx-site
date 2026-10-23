import numpy as np, wave
sr=44100; B=0.5; D=30.0; N=int(sr*D)
rng=np.random.default_rng(7)
t=np.arange(N)/sr
out=np.zeros((2,N))
def put(sig,t0,amp=1.0,pan=0.0):
    i=int(t0*sr); j=min(N,i+len(sig))
    if i>=N or j<=i: return
    s=sig[:j-i]*amp
    out[0,i:j]+=s*(1-max(0,pan)); out[1,i:j]+=s*(1+min(0,pan))
def env_t(n): return np.arange(n)/sr
# kick
n=int(.4*sr);tt=env_t(n);ph=2*np.pi*(45*tt+95/35*(1-np.exp(-35*tt)));kick=np.sin(ph)*np.exp(-tt*9)
kick=np.tanh(kick*1.6)
# clap / snare
n=int(.28*sr);tt=env_t(n);no=rng.standard_normal(n);no=no-np.convolve(no,np.ones(5)/5,'same')
clap=no*np.exp(-tt*22)*0.9+np.sin(2*np.pi*190*tt)*np.exp(-tt*28)*0.5
# hats
n=int(.08*sr);tt=env_t(n);h=rng.standard_normal(n);hat=(h-np.roll(h,1))*np.exp(-tt*70)
n=int(.2*sr);tt=env_t(n);h=rng.standard_normal(n);ohat=(h-np.roll(h,1))*np.exp(-tt*18)
duck=np.ones(N)
roots=[55.0,43.65,65.41,49.0]   # A1 F1 C2 G1
chords=[[220,261.63,329.63],[174.61,220,261.63],[261.63,329.63,392],[196,246.94,293.66]]
nb=int(D/B)
def lp(x,k): 
    return np.convolve(x,np.ones(k)/k,'same')
for b in range(nb):
    t0=b*B; sec=0 if b<8 else (1 if b<16 else 2)
    if b>=53: break
    if b>=8:
        put(kick,t0,0.9)
        # sidechain duck
        i=int(t0*sr); m=int(.22*sr); d=1-0.7*np.exp(-np.arange(min(m,N-i))/sr*14); duck[i:i+len(d)]=np.minimum(duck[i:i+len(d)],d)
    if b>=16 and b%2==1: put(clap,t0,0.45)
    if b>=4:
        put(hat,t0+B/2,0.5 if b<16 else 0.7)
        if b>=16: 
            put(hat,t0+B/4,0.25);put(hat,t0+3*B/4,0.3)
        if b%4==3 and b>=16: put(ohat,t0+B/2,0.35)
# bass (8ths), pad, pluck
bass=np.zeros(N);pad=np.zeros(N);plk=np.zeros(N)
for bar in range(int(D/(4*B))+1):
    r=roots[bar%4];ch=chords[bar%4];b0=bar*4*B
    if b0>=53*B: break
    # pad with slow swell
    n=int(min(4*B+0.6,D-b0)*sr)
    if n>0:
        tt=env_t(n);p=sum(np.sin(2*np.pi*f*(1+d)*tt)+0.5*np.sin(2*np.pi*f*2*(1+d)*tt) for f in ch for d in(-.003,.003))
        e=np.minimum(1,tt/1.2)*np.minimum(1,(4*B+0.6-tt)/0.6)
        i=int(b0*sr);pad[i:i+n]+=p*e*0.035
    if bar*4>=8:
        for k in range(8):
            tn=b0+k*B/2
            if tn>=53*B: break
            n=int(.24*sr);tt=env_t(n);f=r*(2 if k in(3,7) and bar%2 else 1)
            s=sum(np.sin(2*np.pi*f*h*tt)/h for h in range(1,6))
            s=np.tanh(s*1.2)*np.exp(-tt*7)
            i=int(tn*sr);bass[i:i+n]+=s[:max(0,min(n,N-i))]*(0.5 if k%2==0 else 0.38)
    if bar*4>=16:
        for k in range(8):
            tn=b0+k*B/2
            if tn>=53*B: break
            f=ch[k%3]*2*(2 if k>=4 else 1)
            n=int(.3*sr);tt=env_t(n);s=(np.sin(2*np.pi*f*tt)+0.4*np.sin(2*np.pi*f*2*tt))*np.exp(-tt*9)
            i=int(tn*sr);plk[i:i+n]+=s[:max(0,min(n,N-i))]*0.05
# riser beats 49-53
r0=int(49*B*sr);r1=int(53*B*sr);n=r1-r0;tt=np.arange(n)/n
no=rng.standard_normal(n);no=no-lp(no,6)
riser=no*(tt**2.2)*0.5
bass*=duck;pad*=(0.55+0.45*duck)
mono=bass+pad+plk
out[0]+=mono;out[1]+=mono
out[0,r0:r1]+=riser;out[1,r0:r1]+=riser[::-1]*0.9
# card tail: pad only, fade
end=int(53*B*sr)
out[:,:]=out
# intro fade, tail fade
fi=int(1.0*sr);out[:,:fi]*=np.linspace(0,1,fi)
ft=int(1.0*sr);out[:,-ft:]*=np.linspace(1,0,ft)
out/=np.abs(out).max()*1.05
w=wave.open('hero-score.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr)
w.writeframes((out.T*32767).astype('<i2').tobytes());w.close()
print('ok')
