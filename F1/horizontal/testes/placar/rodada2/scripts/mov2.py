import json,cv2,numpy as np
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
W=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f"
OUT=W+r"\F1\horizontal\testes\placar\rodada2"
res=json.load(open(W+r"\_aval\medidas.json",encoding='utf-8'))
fin=json.load(open(P+r"\horizontal\final\final.json",encoding='utf-8'))
C={c['id']:(c['Q0'],c['Q1']) for c in fin['cenas']}
GPS=["447ab02a","e0df513b","a37e2524","d5a93934","76c5a688"]
# recortes do chão em 960x540 (sem HUD, minimapa, rótulo e carro)
CROPS=[(40,150,260,380),(700,960,170,330)]  # x0,x1,y0,y1
SEQ=list(range(3602,3614))
cap=cv2.VideoCapture(P+r"\saida\final_v3.mp4"); i=0; prev=None
mv={g:[] for g in GPS}; bb=[]; seq=[]
hw=[cv2.createHanningWindow((c[1]-c[0],c[3]-c[2]),cv2.CV_32F) for c in CROPS]
while i<5160:
    ok,f=cap.read()
    if not ok: break
    g=cv2.cvtColor(cv2.resize(f,(960,540),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)
    if prev is not None:
        for gid in GPS:
            q0,q1=C[gid]
            if q0+20<=i<q1-20:
                vs=[]
                for (x0,x1,y0,y1),h in zip(CROPS,hw):
                    (dx,dy),r=cv2.phaseCorrelate(prev[y0:y1,x0:x1],g[y0:y1,x0:x1],h); vs.append((dx,dy,r))
                mv[gid].append((i,vs))
    if 1150<=i<1195:
        m=(f[:,:,2]>150)&(f[:,:,1]<90)&(f[:,:,0]<90); ys,xs=np.nonzero(m); bb.append((xs.min(),xs.max(),ys.min(),ys.max()))
    if i in SEQ: seq.append(cv2.resize(f,(640,360)))
    prev=g; i+=1
R={}
for gid,v in mv.items():
    out={}
    for k in range(len(CROPS)):
        a=np.array([[x[1][k][0],x[1][k][1]] for x in v]); rr=np.array([x[1][k][2] for x in v]); n=np.hypot(a[:,0],a[:,1])
        good=rr>0.2
        j=np.hypot(*(np.diff(a,axis=0).T))
        rev=sum(1 for t in range(1,len(a)) if good[t] and good[t-1] and n[t]>1 and n[t-1]>1 and (a[t]@a[t-1])<0)
        out[f"recorte{k}"]={"vel_med_px960":round(float(np.median(n[good])),2) if good.any() else None,"vel_p90":round(float(np.percentile(n[good],90)),2) if good.any() else None,
          "pct_quadros_confiaveis":round(100*float(good.mean()),0),"reversoes":rev,"salto_p99":round(float(np.percentile(j,99)),2)}
    R[gid]=out
res["gps_chao"]=R
a=np.array(bb); res["anot"]["791bf924"]={"quadros":len(bb),"var_bbox_px":[int(a[:,k].max()-a[:,k].min()) for k in range(4)],"obs":"janela 1150-1194 (antes do wipe da cena 6)"}
json.dump(res,open(W+r"\_aval\medidas.json","w"),indent=1,ensure_ascii=False)
rows=[np.hstack(seq[r*4:(r+1)*4]) for r in range(3)]
img=np.vstack(rows)
for k,q in enumerate(SEQ): cv2.putText(img,f"q{q}",((k%4)*640+6,(k//4)*360+22),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
cv2.imwrite(OUT+r"\c14_d5a93934_seq12_q3602.jpg",img,[cv2.IMWRITE_JPEG_QUALITY,80])
print(json.dumps(R,indent=0)); print(res["anot"]["791bf924"])
