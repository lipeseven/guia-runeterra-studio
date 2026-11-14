"""Monta placar_rodada3.json (F1/horizontal/docs/) com as notas do avaliador e as medidas de _aval/ (video, audio, hud).
Rodar depois de video.py, audio.py e hud.py."""
import json, os
from comum import FIN, NUMS, TMP, REPO

K = ["a_dados", "b_sincronia", "c_clareza", "d_movimento", "e_estetica", "f_sfx"]
PES = dict(zip(K, [25, 15, 20, 15, 15, 10]))
R1 = {"01": 84, "02": 66, "03": 82, "04": 85, "05": 82, "06": 87, "07": 82, "08": 61, "09a": 81, "09b": 81, "10": 86, "11": 71,
      "12": 65, "13": 79, "14": 64, "15": 71, "16": 65, "17": 83, "18": 70, "19": 80}
R2 = {"01": 84, "02": 79, "03": 82, "04": 84, "05": 83, "06": 88, "07": 83, "08": 80, "09a": 80, "09b": 80, "10": 87, "11": 77,
      "12": 75, "13": 84, "14": 77, "15": 80, "16": 76, "17": 83, "18": 71, "19": 82}
# num -> (critérios, observações)
S = {
 "01": ([24, 13, 18, 14, 7, 8], "igual à rodada 2 (quadros idênticos ao v3); só texto em fundo claro"),
 "02": ([23, 13, 17, 13, 11, 7], "etiquetas com perninha, 0 sobreposição e 0 troca de lado; arquibancadas listradas dão cor; clique em 'classificação' audível; carros ainda fundidos quando colados (q418)"),
 "03": ([23, 12, 15, 14, 11, 7], "igual à rodada 2 ('76,514', rodapé em inglês, linhas sobrepostas)"),
 "04": ([25, 14, 17, 14, 7, 8], "pop do '514' agora no nível da voz (−0,3 dB RMS); oval estável (0 px)"),
 "05": ([25, 14, 18, 14, 6, 6], "igual à rodada 2; layout idêntico ao da cena 4"),
 "06": ([24, 13, 19, 14, 11, 7], "igual; o hit do capítulo cai ~0,6 s depois de 'setores' (já era assim)"),
 "07": ([25, 9, 17, 14, 12, 7], "clique do '25' agora audível (pico +6 dB sobre a voz); S2/S3/Volta ainda entram antes de ditos"),
 "08": ([23, 12, 16, 13, 10, 8], "etiquetas lado a lado na Curva 1, mas TROCAM de lado 3× (q1915, q2005, q2073; salto de ~94 px num quadro); placa '1' ainda cobre o canto do rodapé (q2093); pop '349' audível"),
 "09a": ([21, 13, 16, 14, 11, 5], "igual à rodada 2: faixa '~22 m' sobre distância integrada sem aviso; sem SFX"),
 "09b": ([24, 14, 18, 13, 8, 5], "começa no '104' com o número (sem cartão vazio); mesmo layout das cenas 13 e 15; riser do cap. 2 começa sob '104 contra 100'"),
 "10": ([24, 13, 19, 14, 10, 7], "igual"),
 "11": ([22, 13, 17, 13, 10, 7], "a faixa agora diz o número oficial (RUS 0,022 s, legível); mas o 'destaque' é o gráfico inteiro rosa (não destaca nada) e as linhas seguem indistinguíveis; 82 % dos quadros parados, 3,6 s seguidos"),
 "12": ([22, 13, 16, 13, 10, 7], "etiquetas separadas, mas trocam de lado 2× (q3167, q3255) e encostam 9 quadros; '100% de acelerador' só em texto; carros fundidos (q3187); mundo ralo; pop '100%' audível"),
 "13": ([25, 14, 19, 13, 8, 7], "clique do '30.008' audível; 2º de três duelos com o mesmo layout"),
 "14": ([23, 14, 14, 12, 12, 7], "arquibancadas dão vida e a cena vai até a bandeirada; câmera lisa (salto p99 0,43 px); mas as etiquetas TROCAM de lado 7× em 6,5 s (q3593, 3655, 3672, 3745, 3768, 3785, 3797) e se encostam 9 quadros; HUD em q3937 já passou do fim da volta de HAM (282 × 275 OpenF1)"),
 "15": ([25, 14, 18, 13, 7, 7], "começa no '1:16.514' com o número; dois cliques audíveis; 3º duelo igual; 93 % dos quadros parados"),
 "16": ([23, 14, 18, 12, 9, 7], "virou barras (boa troca): barras crescem na palavra (350 em 72,13 s × fala 72,12; 347 em 75,72 × 75,70) e terminam no valor certo; mas 2,1 s de eixos vazios no início, barra RUS sozinha 3,4 s, metade de baixo da tela vazia; eixo cortado 340–352 faz 3 km/h parecer 2,4× (está escrito, em letra miúda)"),
 "17": ([24, 14, 18, 14, 6, 7], "igual; alerta do 'não' ainda 8 dB abaixo do pico da voz"),
 "18": ([23, 13, 16, 13, 11, 8], "CORRIGIDO: 'HAM' no carro de trás (Ferrari) e 'RUS' no da frente (q4945); 1 troca em q5108 ao entrar na curva; os dois carros parecem pretos (Ferrari sem vermelho); clique 'frenagens' audível"),
 "19": ([24, 14, 18, 14, 7, 6], "sino agora 17,5 dB abaixo da voz em RMS (era 33), ataque 12 dB abaixo do pico da voz mas 14 dB acima de voz+trilha na banda 710–1420 Hz: deve soar fraco sob 'Uma pole'; ainda não está depois da frase"),
}
cenas = {}; tot = soma = 0; crit = {k: 0 for k in K}
for n, c in zip(NUMS, FIN["cenas"]):
    v, obs = S[n]; s = (c["Q1"] - c["Q0"]) / 60; nota = sum(v)
    cenas[f"c{n}_{c['id']}"] = {"q0": c["Q0"], "q1": c["Q1"], "s": round(s, 2), "nota": nota, "rodada1": R1[n], "rodada2": R2[n], "delta_r2": nota - R2[n],
                                "criterios": dict(zip(K, v)), "obs": obs}
    tot += s; soma += s * nota
    for k, x in zip(K, v): crit[k] += s * x
glob = round(soma / tot, 1); pc = {k: round(100 * crit[k] / tot / PES[k]) for k in K}
abaixo = [k for k, v in cenas.items() if v["nota"] < 80]
med = {nm: json.load(open(os.path.join(TMP, nm + ".json"), encoding="utf-8")) for nm in ("video", "audio", "hud")}
out = {"video": "F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v4.mp4", "rodada": 3, "data": "2026-11-14", "pesos": PES,
       "global": glob, "global_rodada1": 73.8, "global_rodada2": 79.8, "por_criterio_pct": pc, "meta_atingida": (not abaixo and glob >= 80),
       "cenas_abaixo_de_80": abaixo, "mapa_ids": "9b = 09e13e9a (era 712d73a7), 15 = fe9cb062 (era f6d5a7f0); demais iguais",
       "cenas": cenas, "medidas": med}
json.dump(out, open(os.path.join(REPO, r"F1\horizontal\docs\placar_rodada3.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(glob, pc, abaixo)
for k, v in cenas.items(): print(k, v["s"], v["nota"], v["rodada2"], v["delta_r2"])
