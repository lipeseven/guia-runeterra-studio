import json,os,cv2,numpy as np,soundfile as sf
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
W=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f"
OUT=W+r"\F1\horizontal\testes\placar\rodada2"
fin=json.load(open(P+r"\horizontal\final\final.json",encoding='utf-8'))
C={c['id']:(c['Q0'],c['Q1']) for c in fin['cenas']}
GPS=["447ab02a","e0df513b","a37e2524","d5a93934","76c5a688"]
ANOT={"c8b897f1":(60,97),"abbcf455":(1020,1052),"791bf924":(1180,1215),"408641ec":(4800,4840),"e9aa5677":(5220,5420)}
EXTRA=[469,1848,1858,1895,2093,3355,3398,3744,4945,4987,5030,5100,3960,2440]
res={"gps":{},"anot":{},"regioes":{}}
cap=cv2.VideoCapture(P+r"\saida\final_v3.mp4")
prev=None; i=0
mot={g:[] for g in GPS}; bb={a:[] for a in ANOT}
lab=[];cl=[];cr=[]
while True:
    ok,f=cap.read()
    if not ok: break
    if i in EXTRA: cv2.imwrite(OUT+f"\\q{i}_cheio.jpg",f,[cv2.IMWRITE_JPEG_QUALITY,85])
    g=cv2.cvtColor(cv2.resize(f,(480,270),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)
    for gid in GPS:
        q0,q1=C[gid]
        if q0+20<=i<q1-20 and prev is not None:
            (dx,dy),r=cv2.phaseCorrelate(prev,g,cv2.createHanningWindow((480,270),cv2.CV_32F))
            mot[gid].append((i,dx,dy,r))
    for a,(s,e) in ANOT.items():
        if s<=i<e:
            b,gg,rr=f[:,:,0].astype(int),f[:,:,1].astype(int),f[:,:,2].astype(int)
            m=(rr>150)&(gg<90)&(b<90)
            ys,xs=np.nonzero(m)
            bb[a].append((i,int(xs.min()),int(xs.max()),int(ys.min()),int(ys.max()),int(m.sum())) if len(xs) else (i,None))
    reg=f[880:950,500:1420]; lab.append(int((reg.min(axis=2)>240).sum()))
    gl=cv2.cvtColor(f[520:720,240:920],cv2.COLOR_BGR2GRAY); cl.append(int((gl<70).sum()))
    gr=cv2.cvtColor(f[520:720,1000:1680],cv2.COLOR_BGR2GRAY); cr.append(int((gr<70).sum()))
    prev=g; i+=1
for gid,v in mot.items():
    a=np.array([[x[1],x[2]] for x in v]); n=np.hypot(a[:,0],a[:,1])
    j=np.hypot(*(np.diff(a,axis=0).T))
    rev=sum(1 for k in range(1,len(a)) if n[k]>0.3 and n[k-1]>0.3 and (a[k]@a[k-1])<0)
    stall=sum(1 for k in range(1,len(a)-1) if n[k]<0.15 and n[k-1]>0.6 and n[k+1]>0.6)
    res["gps"][gid]={"quadros":len(a),"vel_med_px":round(float(np.median(n)),3),"vel_p95":round(float(np.percentile(n,95)),3),
      "salto_p99_px":round(float(np.percentile(j,99)),3),"salto_max_px":round(float(j.max()),3),"q_salto_max":int(v[int(j.argmax())+1][0]),
      "reversoes":rev,"paradas_isoladas":stall,"resposta_med":round(float(np.median([x[3] for x in v])),3)}
for a,v in bb.items():
    vv=[x for x in v if x[1] is not None]
    arr=np.array([x[1:5] for x in vv])
    res["anot"][a]={"quadros":len(v),"com_traco":len(vv),"var_bbox_px":[int(arr[:,k].max()-arr[:,k].min()) for k in range(4)] if len(vv) else None,
       "var_area_px":int(max(x[5] for x in vv)-min(x[5] for x in vv)) if vv else None}
def primeiro(serie,q0,q1,lim):
    for k in range(q0,q1):
        if serie[k]>lim: return k
    return None
R={}
for gid in GPS:
    q0,q1=C[gid]; base=min(lab[q0+5:q0+40]);
    ups=[k for k in range(q0+1,q1) if lab[k]-lab[k-1]>3000]
    R["rotulo_"+gid]=[(k,round(k/60,2)) for k in ups]
for cid in ["712d73a7","d96a46d3","f6d5a7f0","760ea8f0"]:
    q0,q1=C[cid]
    L=primeiro(cl,q0,q1,max(cl[q0:q1])*0.5); Rr=primeiro(cr,q0,q1,max(cr[q0:q1])*0.5)
    R["duelo_"+cid]={"esq_q":L,"esq_s":round(L/60,2) if L else None,"dir_q":Rr,"dir_s":round(Rr/60,2) if Rr else None}
res["regioes"]=R
# HUD x OpenF1
cmp=json.load(open(r"C:\Users\Felipe\Downloads\exclusive Claude\F1\horizontal\kit\graficos\comparacoes\11400_44-19_63-21.json",encoding='utf-8'))
bruto={p['sigla']:p['bruto'] for p in cmp['pilotos']}
cen={"447ab02a":(70.25,1),"e0df513b":(7.2,1),"a37e2524":(31.0,1),"d5a93934":(57.5,2),"76c5a688":(10.2,0.5)}
hud=json.load(open(W+r"\_aval\hud.json"))
out=[]
for gid,lst in hud.items():
    ini,fat=cen[gid]; q0=C[gid][0]
    for q,h,r in lst:
        t=ini+(q-q0)/60*fat
        vh=float(np.interp(t,bruto['HAM']['t'],bruto['HAM']['vel'])); vr=float(np.interp(t,bruto['RUS']['t'],bruto['RUS']['vel']))
        out.append({"cena":gid,"q":q,"t_volta":round(t,2),"HAM_hud":h,"HAM_openf1":round(vh),"RUS_hud":r,"RUS_openf1":round(vr),"dH":h-round(vh),"dR":r-round(vr)})
res["hud"]=out
d=np.array([[o['dH'],o['dR']] for o in out]).ravel()
res["hud_resumo"]={"n":len(d),"erro_abs_med":round(float(np.mean(np.abs(d))),1),"erro_abs_max":int(np.abs(d).max()),"p90":round(float(np.percentile(np.abs(d),90)),1)}
# audio
voz,sr=sf.read(P+r"\trabalho\gravacao\limpa.wav",always_2d=True); voz=voz.mean(1)
tri,_=sf.read(W+r"\_aval\tri_duck.wav",always_2d=True); tri=tri.mean(1)
mix,_=sf.read(P+r"\horizontal\final\audio\mix_bruta.wav",always_2d=True); mix=mix.mean(1)
stem,_=sf.read(P+r"\horizontal\final\audio\sfx.wav",always_2d=True); stem=stem.mean(1)
N=len(mix); voz=np.pad(voz,(0,max(0,N-len(voz))))[:N]; tri=np.pad(tri,(0,max(0,N-len(tri))))[:N]
sfxp=mix-voz-tri
db=lambda x:20*np.log10(np.sqrt(np.mean(x**2))+1e-9)
pk=lambda x:20*np.log10(np.max(np.abs(x))+1e-9)
win=int(0.4*sr); M=[]
for k in range(0,N-win,win):
    v=db(voz[k:k+win]); t=db(tri[k:k+win]); M.append((k/sr,v,t))
fala=[(t,v,tr) for t,v,tr in M if v>-35]; sil=[(t,v,tr) for t,v,tr in M if v<=-45]
mg=np.array([v-tr for t,v,tr in fala])
res["trilha"]={"rms_total_db":round(db(tri),1),"voz_rms_total_db":round(db(voz),1),"janelas_fala":len(fala),"margem_voz_sobre_trilha_med_db":round(float(np.median(mg)),1),
  "margem_min_db":round(float(mg.min()),1),"t_margem_min":round(fala[int(mg.argmin())][0],1),"pct_janelas_margem_<10dB":round(100*float((mg<10).mean()),1),
  "pct_janelas_margem_<6dB":round(100*float((mg<6).mean()),1),"trilha_em_silencio_med_db":round(float(np.median([tr for t,v,tr in sil])),1) if sil else None,
  "trilha_fim_s":round(len(_ if False else tri[np.abs(tri)>1e-4])/sr,1)}
nz=np.nonzero(np.abs(tri)>1e-4)[0]; res["trilha"]["trilha_ultimo_som_s"]=round(nz[-1]/sr,2) if len(nz) else None
ev=[(0.0,2.23,"impacto Nove",0.0),(15.88,0.8,"pop 514",16.04),(19.89,1.11,"wipe/capitulo a",21.02),(20.36,1.56,"capitulo b",21.02),(20.84,2.5,"capitulo c",21.02),
 (25.40,0.045,"clique 25",25.40),(26.69,2.75,"zoom cena 8",27.12),(30.74,0.27,"pop 349",30.80),(41.33,3.1,"riser cap 2",44.08),(43.26,3.0,"cap 2 b",44.08),(44.05,1.0,"cap 2 c",44.08),
 (47.04,0.165,"tecla 22",47.04),(56.68,0.38,"clique 30.008",56.68),(65.63,0.27,"clique 1:16.514",65.66),(72.11,0.19,"pop 350",72.12),(79.10,0.34,"alerta nao",79.24),
 (80.75,0.56,"zoom cena 18",81.00),(85.92,1.78,"impacto Nove",85.96),(86.97,2.48,"sino Uma",86.98)]
E=[]
for t0,du,nm,ancora in ev:
    a=int(t0*sr); b=min(N,int((t0+du)*sr)); s=sfxp[a:b]; st=stem[a:b]
    E.append({"evento":nm,"t":t0,"dur":du,"ancora_s":ancora,"pico_s":round(t0+int(np.argmax(np.abs(s)))/sr,3),"pico_menos_ancora_ms":int(1000*(t0+np.argmax(np.abs(s))/sr-ancora)),
      "sfx_rms_db":round(db(s),1),"sfx_pico_db":round(pk(s),1),"voz_rms_db":round(db(voz[a:b]),1),"trilha_rms_db":round(db(tri[a:b]),1),
      "sfx_menos_voz_db":round(db(s)-db(voz[a:b]),1),"duck_db":round(db(s)-db(st),1)})
res["sfx"]=E
fim=N/sr; res["sfx_buracos_s"]=[(round(E[k]['t']+E[k]['dur'],1),round(E[k+1]['t'],1)) for k in range(len(E)-1) if E[k+1]['t']-(E[k]['t']+E[k]['dur'])>6]
res["mix_rms_db"]=round(db(mix),1)
json.dump(res,open(W+r"\_aval\medidas.json","w"),indent=1,ensure_ascii=False)
print(json.dumps({k:v for k,v in res.items() if k!='hud'},indent=0,ensure_ascii=False))
for o in out: print(o)
