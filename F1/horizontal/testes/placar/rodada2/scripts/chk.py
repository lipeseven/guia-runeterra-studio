import numpy as np,soundfile as sf
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
W=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f"
def rd(p):
    x,sr=sf.read(p,always_2d=True); print(p[-30:],sr,x.shape); return x.mean(1)
voz=rd(P+r"\trabalho\gravacao\limpa.wav"); tri=rd(W+r"\_aval\tri_duck.wav"); mix=rd(P+r"\horizontal\final\audio\mix_bruta.wav"); st=rd(P+r"\horizontal\final\audio\sfx.wav")
N=len(mix); f=lambda x:np.pad(x,(0,max(0,N-len(x))))[:N]
voz,tri,st=f(voz),f(tri),f(st)
db=lambda x:20*np.log10(np.sqrt(np.mean(x**2))+1e-12)
for a,b in [(50,55),(60,63),(47.0,47.3),(56.6,57.1)]:
    s=slice(int(a*48000),int(b*48000)); A=np.vstack([voz[s],tri[s],st[s]]).T
    c,*_=np.linalg.lstsq(A,mix[s],rcond=None)
    print(a,b,"coef",np.round(c,3),"res",round(db(mix[s]-A@c),1),"mix",round(db(mix[s]),1),"stem",round(db(st[s]),1),"m-v-t",round(db(mix[s]-voz[s]-tri[s]),1))
