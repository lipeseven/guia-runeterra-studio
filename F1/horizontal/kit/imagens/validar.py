# Validação: o trecho de vídeo bate com a afirmação {sessao, piloto, volta, evento}?
#
# Função pura (sem rede, sem OCR): recebe o pacote do OpenF1, os metadados da fonte e as OBSERVAÇÕES do trecho
# (o que o OCR leu em cada quadro). Assim os casos certos e errados são testáveis offline (testes.py).
#
# Cada checagem dá "ok", "falhou", "ambiguo" ou "nao_verificado". O trecho só é VALIDADO se todas as checagens
# pedidas derem "ok". Qualquer "falhou" = REPROVADO (a imagem contradiz a afirmação). O resto = NÃO VALIDADO
# (não deu para provar): nunca entra no vídeo sem o Felipe olhar.
from __future__ import annotations

import re
from datetime import datetime

import leitura
import relogio

LIMIAR_CONFIANCA = 0.6   # fração mínima das janelas do contador visto que cai dentro da volta pedida
FOLGA_TEMPO_NA_TELA = 20.0  # s: sem contador, tempo de volta terminada até 20 s depois da pedida ainda é "o mesmo momento"

TIPOS = {  # palavras do título que indicam a sessão
    "race": ["RACE", "CORRIDA", "GRANDE PREMIO"],
    "sprint": ["SPRINT"],
    "qualifying": ["QUALIFYING", "QUALI", "CLASSIFICACAO", "POLE LAP"],
    "practice": ["PRACTICE", "FP1", "FP2", "FP3", "TREINO LIVRE"],
}


def _tipo_sessao(s: dict) -> str:
    nome = (s.get("session_name") or s.get("session_type") or "").lower()
    if "sprint" in nome and ("quali" in nome or "shootout" in nome):
        return "sprint_quali"
    if "sprint" in nome:
        return "sprint"
    if "quali" in nome:
        return "qualifying"
    if "practice" in nome:
        return "practice"
    return "race"


def tem_contador(s: dict) -> bool:
    """Corrida e sprint mostram 'LAP C/N' na TV; classificação e treinos não (lá a volta é provada pelo tempo)."""
    return _tipo_sessao(s) in ("race", "sprint")


def checar_sessao(pacote: dict, fonte: dict, observacoes: list[dict]) -> dict:
    s = pacote["sessao"]
    titulo = leitura.normalizar(fonte.get("title") or "")
    desc = leitura.normalizar(fonte.get("description") or "")
    notas, falhas = [], []
    ano = str(s.get("year") or s.get("date_start", "")[:4])
    anos = set(re.findall(r"\b(19[5-9]\d|20[0-9]\d)\b", titulo))
    ano_ok = ano in anos
    if anos and not ano_ok:
        falhas.append(f"título fala de {', '.join(sorted(anos))}, sessão é de {ano}")
    lugares = {leitura.normalizar(x) for x in (s.get("location"), s.get("country_name"), s.get("circuit_short_name"))
               if x}
    if s.get("meeting_name"):
        lugares.add(leitura.normalizar(s["meeting_name"]).replace(" GRAND PRIX", "").strip())
    lugar = next((l for l in lugares if l and l in titulo), None)
    tipo = _tipo_sessao(s)
    proprio = TIPOS.get(tipo if tipo != "sprint_quali" else "sprint", [])
    tipo_ok = any(p in titulo for p in proprio)
    outros = [p for k, ps in TIPOS.items() if k not in (tipo, "sprint" if tipo == "sprint_quali" else "")
              for p in ps if re.search(r"\b" + p + r"\b", titulo)]
    if tipo == "race" and "SPRINT" in titulo:
        outros.append("SPRINT")
    if outros and not tipo_ok:
        falhas.append(f"título é de outra sessão ({', '.join(sorted(set(outros)))}); a afirmação é de {s.get('session_name')}")
    up = fonte.get("upload_date")
    if up and s.get("date_start"):
        dia = datetime.fromisoformat(s["date_start"]).strftime("%Y%m%d")
        if up < dia:
            falhas.append(f"vídeo publicado em {up}, antes da sessão ({dia})")
    # total de voltas da sessão = o do OpenF1 (maior volta registrada); só corrida/sprint mostram "LAP C/N"
    total = relogio.total_voltas(pacote["voltas"])
    lidos = {t for o in observacoes if (t := leitura.total_do_texto(o.get("textos", [])))}
    total_ok = False
    if lidos and total and tem_contador(s):
        if lidos - {total}:
            falhas.append(f"contador da TV mostra /{', /'.join(map(str, sorted(lidos)))}, a sessão teve {total} voltas")
        else:
            total_ok = True
            notas.append(f"contador da TV mostra /{total} = total de voltas da sessão")
    if ano_ok:
        notas.append(f"ano {ano} no título")
    if lugar:
        notas.append(f"lugar '{lugar}' no título")
    if tipo_ok:
        notas.append(f"tipo de sessão ({s.get('session_name')}) no título")
    if falhas:
        st = "falhou"
    elif ano_ok and lugar and (tipo_ok or total_ok):  # (sem contador, só o tipo no título prova a sessão)
        st = "ok"
    else:
        st = "nao_verificado"
    return {"status": st, "detalhe": "; ".join(falhas or notas) or "título não identifica a sessão"}


def tempo_posterior(voltas: list[dict], piloto: int, n: int, x: float):
    """Tempo x visto na tela é de uma volta (de qualquer piloto) que terminou mais de FOLGA_TEMPO_NA_TELA s depois da
    volta n do piloto? Devolve (fim, volta, fim_alvo) ou None. Entre voltas com o mesmo tempo, vale a que terminou mais
    cedo (conservador: só acusa 'depois' quando nenhuma hipótese cabe)."""
    va = next((v for v in voltas if v.get("driver_number") == piloto and v.get("lap_number") == n), None)
    if not va or not va.get("date_start") or not va.get("lap_duration"):
        return None
    fim_alvo = relogio.ts(va["date_start"]) + va["lap_duration"]
    cands = [(relogio.ts(v["date_start"]) + v["lap_duration"], v) for v in voltas
             if v.get("lap_duration") and v.get("date_start") and abs(v["lap_duration"] - x) < 0.0015]
    if not cands:
        return None
    fim, v = min(cands, key=lambda c: c[0])
    return (fim, v, fim_alvo) if fim > fim_alvo + FOLGA_TEMPO_NA_TELA else None


def checar_volta_por_tempo(pacote: dict, afirmacao: dict, observacoes: list[dict]) -> dict:
    """Sessão sem contador na TV (classificação, treinos): a volta é provada pelo TEMPO dela escrito na tela
    (o OpenF1 tem o tempo de cada volta ao milésimo). Tempo de OUTRA volta do mesmo piloto na tela = falhou."""
    voltas = pacote["voltas"]
    piloto, n = int(afirmacao["piloto"]), int(afirmacao["volta"])
    minhas = {v["lap_number"]: v.get("lap_duration") for v in voltas if v.get("driver_number") == piloto}
    if n not in minhas:
        return {"status": "falhou", "detalhe": f"OpenF1 não tem a volta {n} do carro {piloto}"}
    alvo = minhas[n]
    base = {"modo": "tempo_na_tela", "tempo_esperado": leitura.formatar_tempo(alvo) if alvo else None}
    if not alvo:
        return {**base, "status": "nao_verificado", "confianca": 0.0,
                "detalhe": f"sessão sem contador de volta na TV e a volta {n} do carro {piloto} não tem tempo no OpenF1"}
    obs = sorted(observacoes, key=lambda o: o["t"])
    vistos = [(o["t"], x) for o in obs if "replay" not in leitura.marcas(o.get("textos", []))
              for x in leitura.tempos_do_texto(o.get("textos", []))]
    base["tempos_vistos"] = [[t, leitura.formatar_tempo(x)] for t, x in vistos]
    # tempo de OUTRA volta do mesmo piloto na tela: o trecho mostra aquela volta (vale mesmo se o tempo pedido também
    # aparece: na classificação a torre continua mostrando o melhor tempo enquanto ele faz outras voltas)
    outras = {m: d for m, d in minhas.items() if d and m != n}
    erradas = sorted({(m, d) for _, x in vistos for m, d in outras.items() if abs(x - d) < 0.0015})
    if erradas:
        return {**base, "status": "falhou", "confianca": 0.0,
                "detalhe": "; ".join(f"tempo {leitura.formatar_tempo(d)} = volta {m} do carro {piloto}" for m, d in erradas)
                           + f", não a volta {n} ({leitura.formatar_tempo(alvo)})"}
    # Relógio da sessão: um tempo só aparece na tela depois que a volta dele terminou. Se o trecho mostra o tempo de
    # uma volta (de QUALQUER piloto) que terminou bem depois da volta pedida, o trecho é de depois (ex.: gráfico
    # "BEST LAP" comparando VER x LEC sobre a imagem do carro do VER, minutos depois da volta do LEC).
    depois = [(t, x, *d) for t, x in vistos if (d := tempo_posterior(voltas, piloto, n, x))]
    if depois:
        t, x, fim, v, fim_alvo = depois[0]
        return {**base, "status": "falhou", "confianca": 0.0,
                "detalhe": f"em t = {t} s a tela mostra {leitura.formatar_tempo(x)} = volta {v['lap_number']} do carro "
                           f"{v['driver_number']}, que terminou às {relogio.hora(fim)} UTC; a volta {n} do carro {piloto} "
                           f"terminou às {relogio.hora(fim_alvo)}: o trecho é de depois"}
    em = sorted({t for t, x in vistos if abs(x - alvo) < 0.0015})
    txt = f"tempo {leitura.formatar_tempo(alvo)} da volta {n} do carro {piloto}"
    if em:
        # Prova forte = o tempo APARECE no trecho (ausente num quadro anterior do mesmo plano, sem corte entre eles):
        # é o fechamento da volta. Se ele já está na tela desde o início, pode ser a torre mostrando o tempo minutos
        # depois (o melhor tempo fica lá) -> ambíguo, não valida sozinho.
        t1 = em[0]
        antes = [o for o in obs if o["t"] < t1 and "replay" not in leitura.marcas(o.get("textos", []))]
        fecha = None
        for o in reversed(antes):
            if any(c.get("corte") for c in obs if o["t"] < c["t"] <= t1):
                break
            fecha = o["t"]
            break
        base["fechamento"] = {"t_sem_tempo": fecha, "t_com_tempo": t1} if fecha is not None else None
        if fecha is not None:
            return {**base, "status": "ok", "confianca": 1.0,
                    "detalhe": f"{txt} aparece na tela entre t = {fecha} e {t1} s (fechamento da volta, mesmo plano)"}
        return {**base, "status": "ambiguo", "confianca": 0.5,
                "detalhe": f"{txt} já está na tela desde t = {t1} s: pode ser a torre mostrando o tempo depois da volta "
                           "(trecho sem o momento em que o tempo aparece)"}
    return {**base, "status": "nao_verificado", "confianca": 0.0,
            "detalhe": f"sessão sem contador de volta na TV; o tempo da volta {n} ({leitura.formatar_tempo(alvo)}) "
                       "não aparece escrito no trecho"}


def checar_volta(pacote: dict, afirmacao: dict, observacoes: list[dict]) -> dict:
    if not tem_contador(pacote["sessao"]):
        return checar_volta_por_tempo(pacote, afirmacao, observacoes)
    voltas = pacote["voltas"]
    piloto, n = int(afirmacao["piloto"]), int(afirmacao["volta"])
    jan = relogio.janela_volta(voltas, piloto, n)
    if not jan:
        return {"status": "falhou", "detalhe": f"OpenF1 não tem a volta {n} do carro {piloto}"}
    esperados = relogio.contadores_esperados(jan, voltas)
    base = {"janela_piloto": [relogio.hora(jan[0]), relogio.hora(jan[1])], "contadores_esperados": esperados}
    total = relogio.total_voltas(voltas)
    obs = sorted(observacoes, key=lambda o: o["t"])
    replays = [o["t"] for o in obs if "replay" in leitura.marcas(o.get("textos", []))]
    vistos = []
    for o in obs:
        c = o.get("volta", leitura.volta_do_texto(o.get("textos", []), total))
        if c and o["t"] not in replays:
            vistos.append((o["t"], c))
    base["contadores_vistos"] = [[t, c] for t, c in vistos]
    base["quadros_replay"] = replays
    texto_jan = f"volta {n} do carro {piloto} = {base['janela_piloto'][0]}–{base['janela_piloto'][1]} UTC"
    if not vistos:
        return {**base, "status": "nao_verificado", "confianca": 0.0,
                "detalhe": f"nenhum contador de volta legível no trecho ({texto_jan}; contador esperado {esperados})"}
    fora = sorted({c for _, c in vistos if c not in esperados})
    if fora:
        partes = []
        for c in fora:
            jc = relogio.janela_contador(c, voltas)
            partes.append(f"contador {c} = {relogio.hora(jc[0])}–{relogio.hora(jc[1])}" if jc else f"contador {c}")
        return {**base, "status": "falhou", "confianca": 0.0,
                "detalhe": f"{'; '.join(partes)} UTC, fora da {texto_jan} (esperado {esperados})"}
    cs = sorted({c for _, c in vistos})
    j0 = relogio.janela_contador(cs[0], voltas)
    j1 = relogio.janela_contador(cs[-1], voltas)
    uniao = (j0[0], j1[1])
    conf = relogio.cruzamento(uniao, jan) / max(1e-6, uniao[1] - uniao[0])
    base["confianca"] = round(conf, 3)
    # Âncora: o contador virou de C para C+1 dentro do mesmo plano -> o relógio do vídeo vira relógio da sessão.
    ancora = None
    for (ta, ca), (tb, cb) in zip(vistos, vistos[1:]):
        corte = any(o.get("corte") for o in obs if ta < o["t"] <= tb)
        if cb == ca + 1 and not corte and tb - ta <= 2.0:
            t_ini = relogio.inicios_lider(voltas)[cb]
            ancora = {"t_video": round((ta + tb) / 2, 3), "t_sessao": relogio.hora(t_ini), "erro_s": round((tb - ta) / 2, 2)}
            plano = [o["t"] for o in obs]  # quadros do mesmo plano da virada
            ini_plano = max([o["t"] for o in obs if o.get("corte") and o["t"] <= ta] or [obs[0]["t"]])
            fim_plano = min([o["t"] for o in obs if o.get("corte") and o["t"] > tb] or [obs[-1]["t"] + 1e-3])
            no_plano = [t for t in plano if ini_plano <= t < fim_plano]
            est = [t_ini + (t - ancora["t_video"]) for t in no_plano]
            dentro = all(jan[0] - ancora["erro_s"] <= x <= jan[1] + ancora["erro_s"] for x in est)
            ancora["dentro_da_volta"] = dentro
            ancora["trecho_sessao"] = [relogio.hora(min(est)), relogio.hora(max(est))]
            break
    base["ancora"] = ancora
    if ancora and not ancora["dentro_da_volta"]:
        return {**base, "status": "falhou",
                "detalhe": f"pela virada do contador em {ancora['t_video']} s o trecho cobre "
                           f"{ancora['trecho_sessao'][0]}–{ancora['trecho_sessao'][1]} UTC, fora da {texto_jan}"}
    if ancora:
        return {**base, "status": "ok", "detalhe": f"contador {cs} e virada {cs[0]}→{cs[0] + 1} ancorada: trecho em "
                f"{ancora['trecho_sessao'][0]}–{ancora['trecho_sessao'][1]} UTC, dentro da {texto_jan}"}
    det = f"contador {cs} (esperado {esperados}); {round(conf * 100)}% do tempo desse contador cai na {texto_jan}"
    if conf >= LIMIAR_CONFIANCA:
        return {**base, "status": "ok", "detalhe": det}
    return {**base, "status": "ambiguo", "detalhe": det + f" (< {round(LIMIAR_CONFIANCA * 100)}%: pode ser a volta vizinha)"}


def checar_piloto(pacote: dict, afirmacao: dict, observacoes: list[dict], legendas: list[dict]) -> dict:
    p = pacote["pilotos"].get(str(afirmacao["piloto"]))
    if not p:
        return {"status": "falhou", "detalhe": f"carro {afirmacao['piloto']} não correu nessa sessão"}
    nome = p.get("last_name") or (p.get("broadcast_name") or "").split()[-1]
    em = [o["t"] for o in observacoes if leitura.tem_nome(o.get("textos", []), nome)]
    if em:
        return {"status": "ok", "nome": nome, "forca": "tela",
                "detalhe": f"nome '{nome.upper()}' escrito na tela em t = {em[:5]} s"}
    alvo = leitura.normalizar(nome)
    fal = [round(l["i"], 1) for l in legendas if alvo in leitura.normalizar(l["texto"])]
    if fal:
        return {"status": "ok", "nome": nome, "forca": "narracao",
                "detalhe": f"'{nome}' citado na narração (legenda) em t = {fal[:5]} s; não escrito na tela"}
    return {"status": "nao_verificado", "nome": nome,
            "detalhe": f"'{nome}' não aparece escrito na tela nem na narração do trecho"}


EVENTOS = {
    "pit": "pit", "parada": "pit", "pit_stop": "pit", "box": "pit",
    "ultrapassagem": "ultrapassagem", "overtake": "ultrapassagem",
    "bandeira_amarela": "bandeira_amarela", "incidente": "bandeira_amarela", "rodada": "bandeira_amarela",
    "volta_mais_rapida": "volta_mais_rapida", "volta_rapida": "volta_mais_rapida",
}


def checar_evento(pacote: dict, afirmacao: dict, observacoes: list[dict]) -> dict:
    ev = afirmacao.get("evento")
    tipo = EVENTOS.get(leitura.normalizar(ev or "").lower().replace(" ", "_"))
    if not tipo:
        return {"status": "nao_verificado", "detalhe": f"evento '{ev}' sem checagem automática (tipos: {sorted(set(EVENTOS))})"}
    piloto, n = int(afirmacao["piloto"]), int(afirmacao["volta"])
    jan = relogio.janela_volta(pacote["voltas"], piloto, n)
    if not jan:
        return {"status": "falhou", "detalhe": "volta inexistente"}
    na_tela = {m for o in observacoes for m in leitura.marcas(o.get("textos", []))}
    dentro = lambda d: jan[0] <= relogio.ts(d) <= jan[1]
    if tipo == "pit":
        achou = [x for x in pacote.get("pit", []) if x.get("driver_number") == piloto
                 and (x.get("lap_number") == n or (x.get("date") and dentro(x["date"])))]
        ok = bool(achou)
        det = f"OpenF1 pit: {'parada na volta ' + str(n) if ok else 'nenhuma parada nessa volta'}"
    elif tipo == "ultrapassagem":
        achou = [x for x in pacote.get("ultrapassagens", []) if piloto in
                 (x.get("overtaking_driver_number"), x.get("overtaken_driver_number")) and dentro(x["date"])]
        ok = bool(achou)
        det = f"OpenF1 overtakes: {len(achou)} envolvendo o carro {piloto} nessa volta"
    elif tipo == "bandeira_amarela":
        achou = [x for x in pacote.get("race_control", []) if "YELLOW" in (x.get("flag") or x.get("message") or "")
                 and dentro(x["date"])]
        ok = bool(achou)
        det = f"race_control: {len(achou)} bandeira(s) amarela(s) durante a volta" + (
            f" ({relogio.hora(relogio.ts(achou[0]['date']))} UTC: {achou[0]['message'][:60]})" if achou else "")
    else:
        durs = [v["lap_duration"] for v in pacote["voltas"] if v.get("lap_duration")]
        minha = next((v["lap_duration"] for v in pacote["voltas"]
                      if v["driver_number"] == piloto and v["lap_number"] == n), None)
        ok = bool(minha) and minha == min(durs)
        det = f"volta {n}: {minha} s; mais rápida da sessão: {min(durs)} s"
    marca = {"pit": "pit", "bandeira_amarela": "bandeira_amarela"}.get(tipo)
    if marca and marca in na_tela:
        det += f"; a tela mostra '{marca}'"
    return {"status": "ok" if ok else "falhou", "detalhe": det}


def validar(afirmacao: dict, pacote: dict, fonte: dict, observacoes: list[dict], legendas: list[dict] | None = None) -> dict:
    """observacoes: [{"t": s no trecho, "textos": [str], "corte": bool (corte de câmera desde o quadro anterior)}]
    legendas: [{"i", "f", "texto"}] já no relógio do trecho."""
    if int(afirmacao["sessao"]) != int(pacote["sessao"]["session_key"]):
        raise ValueError("pacote OpenF1 é de outra sessão")
    ch = {
        "sessao": checar_sessao(pacote, fonte, observacoes),
        "volta": checar_volta(pacote, afirmacao, observacoes),
        "piloto": checar_piloto(pacote, afirmacao, observacoes, legendas or []),
    }
    if afirmacao.get("evento"):
        ch["evento"] = checar_evento(pacote, afirmacao, observacoes)
    sts = [c["status"] for c in ch.values()]
    if "falhou" in sts:
        status = "reprovado"
    elif all(s == "ok" for s in sts):
        status = "validado"
    else:
        status = "nao_validado"
    evid = [f"{k}: {v['status']} — {v['detalhe']}" for k, v in ch.items()]
    return {"validado": status == "validado", "status": status, "checagens": ch, "evidencia": evid}
