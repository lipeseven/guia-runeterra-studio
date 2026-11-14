import json,os
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
for f in ['saida/final_v3.mp4','horizontal/final/final.mp4']:
    q=os.path.join(P,f); print(f, os.path.getsize(q) if os.path.exists(q) else None)
s=json.load(open(P+r'\horizontal\spec.json',encoding='utf-8'))
print(list(s.keys()) if isinstance(s,dict) else type(s))
cs=s.get('cenas',s)
for c in cs:
    d={k:v for k,v in c.items() if k not in('id',)}
    print(c.get('id'), json.dumps(d,ensure_ascii=False)[:1000]); print()
