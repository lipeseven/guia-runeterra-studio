import json
W=r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f"
P=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
fin=json.load(open(P+r"\horizontal\final\final.json",encoding='utf-8'))
med=json.load(open(W+r"\_aval\medidas.json",encoding='utf-8'))
K=["a_dados","b_sincronia","c_clareza","d_movimento","e_estetica","f_sfx"]
PES=dict(zip(K,[25,15,20,15,15,10]))
# num, r1 (nota antiga da cena de origem), criterios, defeitos, causa, correcao
S={
"c8b897f1":("01",84,[24,13,18,14,7,8],["e: só texto em fundo claro (igual à rodada 1)"],"","aceitável como abertura"),
"447ab02a":("02",66,[23,12,15,13,10,6],["c: carros fundidos; etiquetas HAM/RUS coladas (q311, q418)","e: mundo ainda ralo (ladrilhos + 2-3 caixas), sem arquibancada perto da linha","f: nenhum SFX em 6,2 s (buraco 2,2–15,9 s)"],
  "montador/hyperframes/gps.html:166 (deslocamento fixo de 46 px entre etiquetas); kit/gps (carro de trás translúcido não separa os modelos)",
  "separar etiquetas pela ordem na tela (quem está atrás embaixo) e com linha-guia até o carro; whoosh/passagem leve ao cruzar a linha"),
"747ede00":("03",82,[23,12,15,14,11,7],["subtítulo '76,514' (formato diferente); rodapé em inglês; linhas sobrepostas a volta inteira (igual à rodada 1)"],"",""),
"abbcf455":("04",85,[25,14,17,14,7,7],["oval passa por cima do '1:' (q1016); pop 15 dB abaixo da voz (provavelmente mascarado)"],"",""),
"791bf924":("05",82,[25,14,18,14,6,6],["layout idêntico ao da cena 4"],"",""),
"f7de54d4":("06",87,[24,13,19,14,11,7],[],"",""),
"a68a79fb":("07",82,[25,9,17,14,12,6],["S2/S3/Volta entram antes de ditos; clique do '25' 15,6 dB abaixo da voz (RMS)"],"",""),
"e0df513b":("08",61,[23,12,15,13,10,7],["c: na Curva 1 só um carro visível, etiquetas RUS/HAM empilhadas (q1996–q2093)","c: rótulo '349 · 345' continua na tela com o HUD a 100 km/h (q2093) — ok, mas a placa '1' gigante cobre o rodapé (q2093)"],
  "gps.html:166; posição da placa da curva em kit/gps","",),
"dd4ffd33":("09a",81,[21,13,16,14,11,5],["a: faixa '22 m' sobre distância integrada (preparar.py:191, ±15 m) sem aviso na tela","f: sem SFX"],"kit/graficos/py/preparar.py:191","rodapé 'distância aproximada' e/ou distância pelo GPS"),
"712d73a7":("09b",81,[24,13,18,12,8,5],["d/e: cartões vazios 1,6 s (q2385–q2463); riser do capítulo 2 começa em 41,33 s sob '104 contra 100'"],"montador/receitas.py:219 (_duelo: cartões entram vazios)","entrar o cartão junto com o número"),
"c247ab85":("10",86,[24,13,19,14,10,7],["riser começa 2,3 s antes (41,33 s, ainda na 9b)"],"",""),
"528c1e00":("11",71,[19,13,15,14,11,5],["a/c: a faixa 'curvas rápidas' (2.520–3.020 m) mostra as duas linhas iguais — não se vê RUS ganhar nada; '22 milésimos' não aparece","f: tecla do '22' 28 dB abaixo da voz (inaudível)"],
  "SPEC (destaque d0/d1 sem fonte) + kit/graficos sem delta confiável (preparar.py:191)","mostrar o número 30.030 × 30.008 / '−0,022 s' na faixa ou ampliar a diferença; SFX acima de −15 dB relativos"),
"a37e2524":("12",65,[22,13,13,13,10,4],["c: etiqueta RUS cobre a HAM (q3355, q3398, `q3355_cheio.jpg`), carros um dentro do outro","a: '100% de acelerador' só em texto, sem dado na tela","f: sem SFX (buraco 47,2–56,7 s)"],
  "montador/hyperframes/gps.html:161-166","etiquetas lado a lado/ordem por profundidade; HUD 'marcado' com acelerador"),
"d96a46d3":("13",79,[25,14,19,13,8,5],["clique do '30.008' 28 dB abaixo da voz (inaudível)"],"montador/mixagem.py:30 (DUCK_SFX)",""),
"d5a93934":("14",64,[23,13,14,13,10,4],["c: etiquetas sobrepostas / RUS sem carro visível embaixo (q3602–q3613, q3744)","f: sem SFX"],"gps.html:161-166",""),
"f6d5a7f0":("15",71,[25,13,18,12,7,5],["d/e: cartões vazios 2 s (63,7–65,7 s) e 2 s parados no fim; 4º duelo igual em 35 s (9b, 13, 15, 16)","clique 23 dB abaixo da voz"],"SPEC: mesmo kit 'duelo' 4×","variar (um como barra, outro com foto/cor cheia)"),
"760ea8f0":("16",65,[24,12,18,11,6,5],["d/e: 8,1 s quase parados: 1,2 s de cartões vazios, cartão HAM vazio 3,5 s (72,3–75,8 s); mesmo layout do 15","pop do '350' 26 dB abaixo da voz"],
  "receitas.py:219 + SPEC","mostrar o speed trap na pista/minimapa (onde fica a armadilha) ou barras crescendo; menos tempo vazio"),
"408641ec":("17",83,[24,14,18,14,6,7],["só texto"],"",""),
"76c5a688":("18",70,[18,13,9,13,11,7],["a/c: etiqueta 'HAM' aparece em cima do carro da frente (Mercedes) e 'RUS' flutua sobre pista vazia (q4945, `q4945_cheio.jpg`) — o espectador lê o carro errado","c: carro de trás (HAM) translúcido com o rastro ciano visível através dele"],
  "montador/hyperframes/gps.html:161 (+2,2 m acima do carro projetado na câmera de perseguição cai sobre o carro da frente) e :166 (−46 px fixo)",
  "na perseguição, ancorar a etiqueta no próprio carro (abaixo/ao lado) ou desligar etiquetas e usar só as cores; esconder o rastro dentro do carro translúcido"),
"e9aa5677":("19",80,[24,14,18,14,7,5],["f: sino agora inteiro mas inaudível: RMS −51 dBFS, 33 dB abaixo da voz (cai sob 'E uma diferença...' com sidechain −6,8 dB)"],
  "SPEC (sino em 'Uma' sob fala contínua) + montador/mixagem.py:30 (DUCK_SFX)","sino depois de 'cronômetro.' com cauda estendida, ou sino fora do sidechain"),
}
cenas={}; tot=0; soma=0; crit={k:0 for k in K}
for c in fin["cenas"]:
    n,r1,v,defe,causa,corr=S[c["id"]]; q=c["Q1"]-c["Q0"]; s=q/60; nota=sum(v)
    cenas[f"c{n}_{c['id']}"]={"q0":c["Q0"],"q1":c["Q1"],"s":round(s,2),"nota":nota,"rodada1":r1,"delta":nota-r1,
       "criterios":dict(zip(K,v)),"defeitos":defe,"causa":causa,"correcao":corr}
    tot+=s; soma+=s*nota
    for k,x in zip(K,v): crit[k]+=s*x
glob=round(soma/tot,1)
pc={k:round(100*crit[k]/tot/PES[k]) for k in K}
abaixo=[k for k,v in cenas.items() if v["nota"]<80]
out={"video":"F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v3.mp4","rodada":2,"data":"2026-11-14","pesos":PES,
 "global":glob,"global_rodada1":73.8,"por_criterio_pct":pc,"meta_atingida":(not abaixo and glob>=80),"cenas_abaixo_de_80":abaixo,
 "mapa_rodada1":"cena 9 (dd4ffd33) da rodada 1 virou 9a (dd4ffd33, nova receita) + 9b (712d73a7, nova); demais ids iguais",
 "cenas":cenas,"medidas":{k:med[k] for k in ["gps","gps_chao","anot","regioes","hud_resumo","hud","trilha","sfx","mix_rms_db"]}}
json.dump(out,open(W+r"\F1\horizontal\docs\placar_rodada2.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
print(glob,pc,abaixo)
for k,v in cenas.items(): print(k,v["s"],v["nota"],v["rodada1"],v["delta"])
print([ (e["evento"],e["sfx_pico_db"]) for e in med["sfx"]][-1])
