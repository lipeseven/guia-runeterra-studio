import json
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
a=json.load(open(P+r"\horizontal\palavras.json",encoding='utf-8'))
b=json.load(open(P+r"\direcao\tempos_gravacao.json",encoding='utf-8'))
print("maxdiff",max(abs(x['i']-y['i']) for x,y in zip(a,b)))
print(" ".join(f"{k}:{w['t']}@{w['i']:.2f}" for k,w in enumerate(b)))
