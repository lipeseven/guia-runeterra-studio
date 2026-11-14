import json,os,cv2,numpy as np
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
V=P+r"\saida\final_v3.mp4"
OUT=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f\F1\horizontal\testes\placar\rodada2"
os.makedirs(OUT,exist_ok=True)
fin=json.load(open(P+r"\horizontal\final\final.json",encoding='utf-8'))
nums=["01","02","03","04","05","06","07","08","09a","09b","10","11","12","13","14","15","16","17","18","19"]
GPS={"447ab02a","e0df513b","a37e2524","d5a93934","76c5a688"}
MOV=GPS|{"747ede00","dd4ffd33","528c1e00","a68a79fb"}
need={}  # frame -> list of (sheet,key,pos)
sheets={}
for n,c in zip(nums,fin["cenas"]):
    q0,q1=c["Q0"],c["Q1"]; L=q1-q0
    idx=[q0+2]+[int(q0+L*k/7) for k in range(1,7)]+[q1-3]
    name=f"c{n}_{c['id']}_8q"; sheets[name]=(idx,4)
    seqs=[(f"c{n}_{c['id']}_seq12",q0+L//2-6)]
    if c['id'] in MOV: seqs.append((f"c{n}_{c['id']}_seq12b",q0+int(L*0.8)-6))
    for nm,s in seqs: sheets[nm]=(list(range(s,s+12)),4)
# extra: specific frames full res
extra=json.load(open(os.path.join(os.path.dirname(__file__),'extra.json'))) if os.path.exists(os.path.join(os.path.dirname(__file__),'extra.json')) else {}
for nm,(idx,cols) in sheets.items():
    for i in idx: need.setdefault(i,[]).append(nm)
for nm,idx in extra.items():
    for i in idx: need.setdefault(i,[]).append("X:"+nm)
got={}
cap=cv2.VideoCapture(V); i=0
mx=max(need)
while i<=mx:
    ok,f=cap.read()
    if not ok: break
    if i in need:
        for nm in need[i]:
            if nm.startswith("X:"):
                cv2.imwrite(os.path.join(OUT,f"{nm[2:]}_q{i}.jpg"),f,[cv2.IMWRITE_JPEG_QUALITY,88])
            else:
                got[(nm,i)]=f
    i+=1
W,H=480,270
for nm,(idx,cols) in sheets.items():
    tiles=[]
    for i in idx:
        t=cv2.resize(got[(nm,i)],(W,H),interpolation=cv2.INTER_AREA)
        cv2.putText(t,f"q{i} {i/60:.2f}s",(6,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),1,cv2.LINE_AA)
        tiles.append(t)
    rows=[np.hstack(tiles[r*cols:(r+1)*cols]) for r in range(len(tiles)//cols)]
    cv2.imwrite(os.path.join(OUT,nm+".jpg"),np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,82])
print("ok",len(sheets))
