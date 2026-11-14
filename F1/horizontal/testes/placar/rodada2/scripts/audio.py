import json,numpy as np,soundfile as sf
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
W=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f"
res=json.load(open(W+r"\_aval\medidas.json",encoding='utf-8'))
rd=lambda p:sf.read(p,always_2d=True)
voz,sr=rd(P+r"\trabalho\gravacao\limpa.wav"); voz=voz.mean(1)*0.70710678  # mono -> estéreo (-3 dB por canal)
tri,_=rd(W+r"\_aval\tri_duck.wav"); tri=tri.mean(1)
mix,_=rd(P+r"\horizontal\final\audio\mix_bruta.wav"); mix=mix.mean(1)
stem,_=rd(P+r"\horizontal\final\audio\sfx.wav"); stem=stem.mean(1)
N=len(mix); f=lambda x:np.pad(x,(0,max(0,N-len(x))))[:N]; voz,tri=f(voz),f(tri)
sfxp=mix-voz-tri
db=lambda x:20*np.log10(np.sqrt(np.mean(x**2))+1e-12)
pk=lambda x:20*np.log10(np.max(np.abs(x))+1e-12)
win=int(0.4*sr); M=[]
for k in range(0,N-win,win): M.append((k/sr,db(voz[k:k+win]),db(tri[k:k+win])))
fala=[m for m in M if m[1]>-38]; sil=[m for m in M if m[1]<=-50]
mg=np.array([v-t for _,v,t in fala])
nz=np.nonzero(np.abs(tri)>1e-4)[0]
res["trilha"]={"trilha_rms_db":round(db(tri),1),"voz_rms_db":round(db(voz),1),"janelas_fala_400ms":len(fala),
 "margem_voz_sobre_trilha_mediana_db":round(float(np.median(mg)),1),"margem_p10_db":round(float(np.percentile(mg,10)),1),
 "margem_min_db":round(float(mg.min()),1),"t_margem_min_s":round(fala[int(mg.argmin())][0],1),
 "pct_fala_margem_<10dB":round(100*float((mg<10).mean()),1),"pct_fala_margem_<6dB":round(100*float((mg<6).mean()),1),
 "janelas_margem_<6dB_s":[round(fala[k][0],1) for k in np.nonzero(mg<6)[0]],
 "trilha_nas_pausas_mediana_db":round(float(np.median([t for _,_,t in sil])),1) if sil else None,"n_pausas":len(sil),
 "trilha_ultimo_som_s":round(nz[-1]/sr,2)}
for e in res["sfx"]:
    a=int(e["t"]*sr); b=min(N,int((e["t"]+e["dur"])*sr)); s=sfxp[a:b]
    pi=int(np.argmax(np.abs(s)))
    e.update({"pico_s":round(e["t"]+pi/sr,3),"pico_menos_ancora_ms":int(round(1000*(e["t"]+pi/sr-e["ancora_s"]))),
      "sfx_rms_db":round(db(s),1),"sfx_pico_db":round(pk(s),1),"voz_rms_db":round(db(voz[a:b]),1),"trilha_rms_db":round(db(tri[a:b]),1),
      "sfx_menos_voz_db":round(db(s)-db(voz[a:b]),1),"reducao_sidechain_db":round(db(s)-db(stem[a:b]),1)})
    # pico local: 150 ms em volta do pico do SFX
    c=max(0,a+pi-3600); d=min(N,a+pi+3600)
    e["pico_sfx_menos_pico_voz_150ms_db"]=round(pk(sfxp[c:d])-pk(voz[c:d]),1)
res["mix_rms_db"]=round(db(mix),1)
json.dump(res,open(W+r"\_aval\medidas.json","w"),indent=1,ensure_ascii=False)
print(json.dumps(res["trilha"],ensure_ascii=False))
for e in res["sfx"]: print(e["evento"],e["t"],"pico",e["pico_s"],"d",e["pico_menos_ancora_ms"],"sfx",e["sfx_rms_db"],"voz",e["voz_rms_db"],"s-v",e["sfx_menos_voz_db"],"pk-pk",e["pico_sfx_menos_pico_voz_150ms_db"],"duck",e["reducao_sidechain_db"])
