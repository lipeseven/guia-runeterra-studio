# Testes do kit/imagens.
#   .venv\Scripts\python.exe F1\horizontal\kit\imagens\testes.py          -> offline (fixture OpenF1, sem rede, sem OCR)
#   .venv\Scripts\python.exe F1\horizontal\kit\imagens\testes.py --rede   -> + caso real (YouTube + OCR + recorte)
#
# Offline: leitura do contador, relógio da sessão e a validação com casos CERTOS e ERRADOS montados a partir do que o
# OCR leu de verdade nos quadros do "Race Highlights | 2026 Sao Paulo Grand Prix" (FORMULA 1, lkb5kqDJYXk).
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.stdout.reconfigure(encoding="utf-8")

import leitura  # noqa: E402
import relogio  # noqa: E402
import validar as V  # noqa: E402

PACOTE = json.loads((AQUI / "dados_teste" / "openf1_11412.json").read_text(encoding="utf-8"))
HL = {"id": "lkb5kqDJYXk", "title": "Race Highlights | 2026 Sao Paulo Grand Prix", "channel": "FORMULA 1",
      "upload_date": "20261108"}
LEC55 = {"sessao": 11412, "piloto": 16, "volta": 55}
HAM62 = {"sessao": 11412, "piloto": 44, "volta": 62}

falhas: list[str] = []
n = 0


def checa(cond: bool, nome: str, extra=""):
    global n
    n += 1
    if not cond:
        falhas.append(f"{nome} {extra}")
        print(f"  FALHOU: {nome} {extra}")


def obs(*itens):
    """obs((t, ["textos"...]), ...) ou (t, [...], corte)"""
    return [{"t": i[0], "textos": i[1], "corte": (i[2] if len(i) > 2 else False)} for i in itens]


# ---------------------------------------------------------------- contador (textos reais do OCR)
print("contador")
casos = {"LAP64/71": 64, "LAP1I71": 1, "LAP3171": 3, "LAP17171": 17, "LAP 11 171": 11, "LAP63171": 63,
         "LAP 20/71": 20, "LAP4171": 4, "LAP18171": 18, "LAP35/71": 35, "LAP38173": None, "LAP99/71": None,
         "Max that's25laps": None, "LAPTOP 12": None}
for txt, esp in casos.items():
    got = leitura.volta_do_texto(["FIA", "FIAFormulal", txt, "1", "NOR"], 71)
    checa(got == esp, f"volta_do_texto({txt!r})", f"= {got}, esperado {esp}")
checa(leitura.volta_do_texto(["LAP", "24", "MSC"], 71) == 24, "LAP e número em itens separados")
checa(leitura.volta_do_texto(["LAP | 42"], 71) == 42, "onboard 'LAP | 42'")
checa(leitura.total_do_texto(["LAP64/71"]) == 71, "total 71")
checa(leitura.tem_nome(["HAMILTON", "FERRARI"], "Hamilton"), "nome Hamilton")
checa(leitura.tem_nome(["HAMlLTON"], "Hamilton"), "nome com 1 erro de OCR")
checa(not leitura.tem_nome(["HAM", "LEC", "+2.5"], "Hamilton"), "sigla da torre não conta")
checa(not leitura.tem_nome(["HULKENBERG"], "Leclerc"), "outro piloto não conta")
checa(leitura.marcas(["REPLAY"]) == ["replay"], "marca replay")
checa("bandeira_amarela" in leitura.marcas(["YELLOW FLAG", "TRACK HAZARD"]), "marca bandeira amarela")

# ---------------------------------------------------------------- relógio
print("relógio")
V_ = PACOTE["voltas"]
j55 = relogio.janela_volta(V_, 16, 55)
checa(relogio.hora(j55[0]) == "18:16:09", "início da volta 55 do LEC", relogio.hora(j55[0]))
checa(relogio.contadores_esperados(j55, V_) == [55, 56], "contador esperado na volta 55 do LEC",
      relogio.contadores_esperados(j55, V_))
checa(relogio.contador_em(j55[0], V_) == 55, "contador no início da volta 55 do LEC")
checa(relogio.contadores_esperados(relogio.janela_volta(V_, 16, 1), V_) == [1, 2], "contador na volta 1")
checa(relogio.janela_volta(V_, 16, 80) is None, "volta inexistente")

# ---------------------------------------------------------------- validação: casos certos e errados
print("validação")


def val(af, fonte, o, leg=None):
    return V.validar(af, PACOTE, fonte, o, leg or [])


# 1) ERRO do teste HyperFrames: texto da volta 55, imagem da volta 1 (rh_20.mp4 = 00:20–00:26 do Race Highlights)
r = val(LEC55, HL, obs((0, ["FIAFormulal", "LAP1I71", "1", "ANT"]), (1, ["LAP1/71"]), (2, ["LAP1/71", "LECLERC"])))
checa(r["status"] == "reprovado" and not r["validado"], "volta 1 para afirmação da volta 55 -> reprovado", r["status"])
checa(r["checagens"]["volta"]["status"] == "falhou", "checagem de volta falha")
checa("17:03:21" in r["checagens"]["volta"]["detalhe"], "evidência mostra o horário da volta 1",
      r["checagens"]["volta"]["detalhe"])

# 2) volta 64 (o trecho 05:40 do mesmo vídeo) para a volta 55 -> reprovado
r = val(LEC55, HL, obs((0, ["LAP64/71", "LECLERC"]), (1, ["LAP64/71"])))
checa(r["status"] == "reprovado", "volta 64 para afirmação da volta 55 -> reprovado", r["status"])

# 3) contador 55 sozinho: 45% da janela do contador cai na volta 55 do LEC (ele estava ~40 s atrás do líder) -> ambíguo
r = val(LEC55, HL, obs((0, ["LAP55/71", "LECLERC"]), (1, ["LAP55/71"])))
checa(r["checagens"]["volta"]["status"] == "ambiguo" and r["status"] == "nao_validado",
      "contador 55 sem âncora -> ambíguo / não validado", r["checagens"]["volta"])

# 4) contador 56 com nome na tela: 55% -> ainda abaixo do limiar de 60%
r = val(LEC55, HL, obs((0, ["LAP56/71", "LECLERC"])))
checa(r["status"] == "nao_validado", "contador 56 (55%) -> não validado", r["checagens"]["volta"].get("confianca"))

# 5) virada 55 -> 56 no mesmo plano: âncora no relógio (18:16:43) cai dentro da volta 55 do LEC -> validado
r = val(LEC55, HL, obs((0, ["LAP55/71", "LECLERC"]), (0.5, ["LAP55/71"]), (1.0, ["LAP56/71"]), (1.5, ["LAP56/71"])))
checa(r["status"] == "validado", "virada 55->56 ancorada dentro da volta -> validado", r["evidencia"])
checa(r["checagens"]["volta"]["ancora"]["dentro_da_volta"], "âncora dentro da volta")

# 6) mesma virada, mas o plano continua 60 s depois da âncora (passa do fim da volta 55 do LEC, 18:17:24) -> reprovado
o6 = obs((0, ["LAP55/71", "LECLERC"]), (0.5, ["LAP56/71"])) + [{"t": float(t), "textos": ["LAP56/71"], "corte": False}
                                                               for t in range(1, 61)]
r = val(LEC55, HL, o6)
checa(r["status"] == "reprovado", "plano ancorado que sai da volta -> reprovado", r["checagens"]["volta"]["detalhe"])

# 7) virada com CORTE de câmera entre os quadros não vale como âncora
r = val(LEC55, HL, obs((0, ["LAP55/71", "LECLERC"]), (0.5, ["LAP56/71"], True)))
checa(r["checagens"]["volta"]["ancora"] is None, "virada com corte não ancora")

# 8) CERTO: Hamilton, volta 62 (incidente com bandeira amarela), contador 63 -> 80% -> validado com evento
o8 = obs((0, ["LAP63/71", "YELLOW FLAG", "TRACK HAZARD"]), (1, ["LAP63/71", "HAMILTON"]))
r = val({**HAM62, "evento": "bandeira_amarela"}, HL, o8)
checa(r["status"] == "validado", "Hamilton volta 62 com bandeira amarela -> validado", r["evidencia"])
checa(r["checagens"]["volta"]["confianca"] >= 0.6, "confiança >= 60%", r["checagens"]["volta"]["confianca"])

# 9) pit: HAM parou na volta 62 (OpenF1 pit lap 62) -> evento ok; LEC parou nas voltas 16 e 61, não na 58 -> reprovado
#    (a parada da volta 61 do LEC tem horário dentro da volta 62 dele: a linha de chegada passa no pit lane, então
#     o kit aceita tanto o lap_number quanto o horário dentro da volta)
r = val({**HAM62, "evento": "pit"}, HL, o8)
checa(r["checagens"]["evento"]["status"] == "ok", "pit do HAM na volta 62 -> ok", r["checagens"]["evento"])
c58 = relogio.contadores_esperados(relogio.janela_volta(V_, 16, 58), V_)[-1]
r = val({"sessao": 11412, "piloto": 16, "volta": 58, "evento": "pit"}, HL, obs((0, [f"LAP{c58}/71", "LECLERC"])))
checa(r["status"] == "reprovado" and r["checagens"]["evento"]["status"] == "falhou", "pit inexistente -> reprovado")

# 10) evento sem checagem automática -> não validado (nunca passa calado)
r = val({**HAM62, "evento": "chuva forte"}, HL, o8)
checa(r["status"] == "nao_validado", "evento desconhecido -> não validado", r["status"])

# 11) piloto: contador certo mas sem nome na tela nem na narração -> não validado
r = val(HAM62, HL, obs((0, ["LAP63/71"]), (1, ["LAP63/71", "HULKENBERG"])))
checa(r["status"] == "nao_validado" and r["checagens"]["piloto"]["status"] == "nao_verificado",
      "sem nome do piloto -> não validado")

# 12) piloto pela narração (legenda) -> ok, marcado como 'narracao'
r = val(HAM62, HL, obs((0, ["LAP63/71"])), [{"i": 0.2, "f": 2.0, "texto": "and Hamilton is in the gravel"}])
checa(r["status"] == "validado" and r["checagens"]["piloto"]["forca"] == "narracao", "piloto pela narração")

# 13) piloto que não correu
r = val({**HAM62, "piloto": 99}, HL, o8)
checa(r["status"] == "reprovado", "carro 99 não existe -> reprovado")

# 14) quadros de REPLAY não contam como contador
r = val(HAM62, HL, obs((0, ["REPLAY", "LAP63/71", "HAMILTON"])))
checa(r["checagens"]["volta"]["status"] == "nao_verificado", "contador em replay não conta")

# 15) sem contador legível -> não validado
r = val(HAM62, HL, obs((0, ["HAMILTON", "FERRARI"])))
checa(r["status"] == "nao_validado", "sem contador -> não validado")

# 16) sessão errada pelo título
for titulo, nome in [("Qualifying Highlights | 2026 Sao Paulo Grand Prix", "classificação"),
                     ("Sprint Highlights | 2026 Sao Paulo Grand Prix", "sprint"),
                     ("Race Highlights | 2025 Sao Paulo Grand Prix", "ano 2025")]:
    r = val({**HAM62, "evento": "bandeira_amarela"}, {**HL, "title": titulo}, o8)
    checa(r["status"] == "reprovado" and r["checagens"]["sessao"]["status"] == "falhou", f"título de {nome} -> reprovado")
r = val({**HAM62, "evento": "bandeira_amarela"}, {**HL, "title": "Race Highlights | 2026 Las Vegas Grand Prix"}, o8)
checa(r["checagens"]["sessao"]["status"] != "ok", "título de Las Vegas não valida São Paulo")

# 17) total de voltas lido diferente do da sessão (/24 = sprint) -> reprovado
r = val(HAM62, {**HL, "title": "Highlights"}, obs((0, ["LAP 23/24", "HAMILTON"])))
checa(r["checagens"]["sessao"]["status"] == "falhou", "contador /24 numa corrida de 71 -> sessão falha")

# 18) vídeo publicado antes da sessão
r = val({**HAM62, "evento": "bandeira_amarela"}, {**HL, "upload_date": "20261101"}, o8)
checa(r["checagens"]["sessao"]["status"] == "falhou", "publicado antes da sessão -> falha")

# 19) título sem tipo de sessão mas contador /71 confirma a corrida
r = val({**HAM62, "evento": "bandeira_amarela"},
        {**HL, "title": "Nine Minutes Of Max Verstappen Tearing Through The Field At Interlagos | 2026 Sao Paulo Grand Prix"}, o8)
checa(r["checagens"]["sessao"]["status"] == "ok", "título sem 'race' + contador /71 -> sessão ok", r["checagens"]["sessao"])

# 20) volta mais rápida (Antonelli, volta 55, segundo os dados do teste HyperFrames)
durs = [v for v in V_ if v.get("lap_duration")]
mais = min(durs, key=lambda v: v["lap_duration"])
r = val({"sessao": 11412, "piloto": mais["driver_number"], "volta": mais["lap_number"], "evento": "volta_mais_rapida"},
        HL, obs((0, ["LAP55/71"])))
checa(r["checagens"]["evento"]["status"] == "ok", f"volta mais rápida = carro {mais['driver_number']} volta {mais['lap_number']}")
r = val({**LEC55, "evento": "volta_mais_rapida"}, HL, obs((0, ["LAP55/71"])))
checa(r["checagens"]["evento"]["status"] == "falhou", "volta 55 do LEC não é a mais rápida")


# ---------------------------------------------------------------- rede (opcional)
def rede():
    import imagens
    print("rede: Leclerc volta 55 (não existe em vídeo oficial) e Hamilton volta 62 (incidente)")
    r = imagens.achar(LEC55)
    print("  LEC55:", r["status"], r["arquivo"])
    checa(not r["validado"], "LEC55 real não é validado (não há imagem oficial da volta)")
    vistos = [c for ch in [r.get("checagens", {})] for c in ch.get("volta", {}).get("contadores_vistos", [])]
    checa(all(c[1] in (55, 56) for c in vistos), "LEC55 real nunca devolve outra volta", vistos)
    checa(not any("volta 1" in (r.get("arquivo") or "") for _ in [0]), "LEC55 real não devolve a volta 1")
    hf = Path(r"C:\Users\Felipe\teste-motores\hyperframes\externo\rh_20.mp4")
    if hf.exists():
        rv = imagens.validar_arquivo(hf, LEC55, "https://www.youtube.com/watch?v=lkb5kqDJYXk", ini_na_fonte=20)
        print("  rh_20.mp4 (teste HyperFrames) para LEC55:", rv["status"], "|", rv["checagens"]["volta"]["detalhe"])
        checa(rv["status"] == "reprovado", "rh_20.mp4 (volta 1) reprovado para a volta 55")
    r = imagens.achar({**HAM62, "evento": "bandeira_amarela"})
    print("  HAM62:", r["status"], r["arquivo"])
    checa(r["validado"] and r["arquivo"] and Path(r["arquivo"]).exists(), "HAM62 real validado com arquivo")


if "--rede" in sys.argv:
    rede()

print(f"\n{n} checagens, {len(falhas)} falhas")
sys.exit(1 if falhas else 0)
