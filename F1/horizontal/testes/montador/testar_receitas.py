"""Receitas novas do uso real (card "Nove milésimos", 2026-11-14), sem render (~1 s):
cartão de capítulo, foco num texto, GPS com câmera alta + HUD + rodapé, pares recusados com mensagem clara,
narração do rascunho caindo na voz guia e a verificação do SFX contra o pico do próprio som.
uso: .venv\\Scripts\\python.exe F1\\horizontal\\testes\\montador\\testar_receitas.py"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "montador"))
import montar as MT        # noqa: E402
import receitas as R       # noqa: E402

falhas = 0


def checa(ok: bool, nome: str, extra: str = "") -> None:
    global falhas
    print(("  ok    " if ok else "  FALHA ") + nome + ("" if ok else f" {extra}"))
    falhas += 0 if ok else 1


PAL = [{"t": w, "i": k * 0.5, "f": k * 0.5 + 0.4} for k, w in enumerate("um dois três quatro cinco seis sete oito".split())]


def cena(kits, texto=None, motor="remotion"):
    return {"id": "x1", "motor": motor, "t0": 0.0, "t1": 3.0, "kits": kits, "texto": texto or [], "transicao": {"tipo": "corte"}}


def recusa(c, trecho, nome):
    try:
        R.receita(c, PAL, 0, 0)
        checa(False, nome, "(não recusou)")
    except R.SemReceita as e:
        checa(trecho in str(e), nome, f"({e})")


def main() -> int:
    print("1. cartões de capítulo")
    j = R.receita(cena([{"kit": "cartoes", "params": {"tipo": "capitulo", "numero": 2, "titulo": "O troco", "sessao": 9908}}]), PAL, 12, 0)
    cam = j["props"]["camadas"][0]
    c = cam["cena"]["cartoes"][0]
    checa(cam["kit"] == "cartoes" and c["numero"] == 2 and c["titulo"] == "O troco", "capítulo vira camada do kit/cartoes")
    checa("tracado" in c and c["tracado"]["d"].startswith("M") and c["tracado"]["largura"] > 100, "traçado da comparação da sessão 9908")
    checa(c["ate"] > j["quadros"] / 60, "cartão fica até o fim da cena (sem sumir antes do corte)")
    j2 = R.receita(cena([{"kit": "cartoes", "params": {"tipo": "capitulo", "numero": 1, "titulo": "Sem pista", "sessao": 1}}]), PAL, 0, 0)
    checa("tracado" not in j2["props"]["camadas"][0]["cena"]["cartoes"][0], "sessão sem comparação: cartão sem traçado (não é erro)")
    recusa(cena([{"kit": "cartoes", "params": {"tipo": "pessoa", "nome": "X"}}]), "capitulo", "pessoa recusada com mensagem")
    recusa(cena([{"kit": "cartoes", "params": {"tipo": "capitulo", "numero": 1, "titulo": "T"}},
                 {"kit": "anotacao", "params": {"tipo": "oval", "alvo": 0}}], ["Texto"]), "tela cheia", "capítulo + anotação recusado")
    recusa(cena([{"kit": "cartoes", "params": {"tipo": "capitulo", "titulo": "T"}}]), "numero", "capítulo sem número recusado")

    print("2. foco num texto")
    j = R.receita(cena([{"kit": "foco", "params": {"alvo": 0, "i": 2}}], ["1:16.514", "contra 1:16.523"]), PAL, 0, 0)
    kits = [x["kit"] for x in j["props"]["camadas"]]
    checa(kits == ["anotacao", "foco"], "foco sem anotação ainda desenha os textos", str(kits))
    an, fo = j["props"]["camadas"]
    f = fo["cena"]["focos"][0]
    alvo_t0 = R._layout_textos(["1:16.514", "contra 1:16.523"])[1]["t0"]["caixa"]
    checa(f["alvo"]["caixa"] == alvo_t0 and abs(f["em"] - 1.0) < 1e-6, "janela = caixa do texto 0, entra na palavra 2 (1,0 s)")
    checa(an["cena"]["anotacoes"] == [], "camada de textos sem traços")
    j = R.receita(cena([{"kit": "foco", "params": {"alvo": {"x": 10, "y": 20, "w": 30, "h": 40}}},
                        {"kit": "anotacao", "params": {"tipo": "oval", "alvo": 0, "i": 1}}], ["Texto"]), PAL, 0, 0)
    checa(j["props"]["camadas"][-1]["cena"]["focos"][0]["alvo"]["caixa"] == {"x": 10.0, "y": 20.0, "w": 30.0, "h": 40.0}, "foco em caixa explícita")
    recusa(cena([{"kit": "foco", "params": {"alvo": 5}}], ["Só um"]), "alvo", "foco em texto inexistente recusado")

    print("3. GPS: câmera alta, HUD e rodapé")
    gps = {"sessao": 9908, "carros": [{"piloto": 16, "volta": 16}, {"piloto": 44, "volta": 16}], "fator": 2.2, "camera_gps": "alta"}
    try:
        j = R.receita(cena([{"kit": "gps", "params": gps}], motor="hyperframes"), PAL, 0, 0)
        cfg = j["cfg"]
        checa(cfg["camera"] == "alta" and cfg["hud"] is True, "câmera alta e HUD ligado por padrão")
        checa(cfg["nota"].startswith("acelerado 2,2×") and "OpenF1" in cfg["nota"] and "classificação" in cfg["nota"], "rodapé acelerado + fonte", cfg["nota"])
        j = R.receita(cena([{"kit": "gps", "params": {**gps, "fator": 0.5, "camera_gps": "fixa"}}], motor="hyperframes"), PAL, 0, 0)
        checa(j["cfg"]["nota"].startswith("câmera lenta 2×"), "rodapé câmera lenta", j["cfg"]["nota"])
        j = R.receita(cena([{"kit": "gps", "params": {**gps, "fator": 1, "nota": "", "hud": False}}], motor="hyperframes"), PAL, 0, 0)
        checa(j["cfg"]["nota"] == "" and j["cfg"]["hud"] is False, "nota vazia e HUD desligado pela SPEC")
    except R.FaltaAtivo as e:
        checa(False, "GPS de Monza (kit/gps/voltas 9908 + modelos 3D)", str(e))
    recusa(cena([{"kit": "gps", "params": {**gps, "camera_gps": "drone"}}], motor="hyperframes"), "alta", "câmera desconhecida recusada")

    print("3b. GPS: rótulos na fala, velocidade segurada, mundo, minimapa, etiquetas e curvas")
    try:
        j = R.receita(cena([{"kit": "gps", "params": {**gps, "rotulos": [{"i": 2, "texto": "Antes da frenagem"}, {"i": 9, "texto": "x"}],
                                                       "marcar": [{"i": 4}]}}], motor="hyperframes"), PAL, 0, 0)
        cfg = j["cfg"]
        checa(cfg["rotulos"] == [{"t": 1.0, "texto": "Antes da frenagem"}, {"t": 0.0, "texto": "x"}] and cfg["marcas"] == [{"t": 2.0, "dur": 1.6}],
              "rótulo e marca no tempo da palavra (palavra fora da lista = 0)", str(cfg["rotulos"]))
        checa(cfg["mundo"] and cfg["minimapa"] and cfg["etiquetas"], "mundo, minimapa e etiquetas ligados por padrão")
        checa(isinstance(cfg["curvas"], list), "curvas: lista (Monza sem curvas numeradas = vazia)", str(cfg["curvas"]))
        cv = R._curvas_gps([{"circuito": "Mexico City"}], {})
        checa(cv == [{"n": 1, "frac": round(1222 / 4304, 5)}], "Mexico City: placa da Curva 1 na fração certa", str(cv))
        checa(R._curvas_gps([{"circuito": "Mexico City"}], {"curvas": False}) == [], "curvas: false tira as placas")
    except R.FaltaAtivo as e:
        checa(False, "GPS de Monza", str(e))

    print("3c. duelo (cartoes tipo duelo)")
    pal = PAL + [{"t": "30.008", "i": 4.5, "f": 4.9}, {"t": "30.030.", "i": 5.2, "f": 5.8}]
    d = {"kit": "cartoes", "params": {"tipo": "duelo", "titulo": "Setor 2", "sessao": 9908, "unidade": "s", "destaque": 0,
                                      "lados": [{"piloto": 16, "valor": "26.582", "i": 8}, {"piloto": 44, "valor": "26.686", "i": 9}]}}
    j = R.receita({**cena([d]), "t1": 6.0}, pal, 0, 0)
    c = j["props"]["camadas"][0]
    checa(c["kit"] == "duelo" and [l["sigla"] for l in c["lados"]] == ["LEC", "HAM"] and c["lados"][0]["cor"],
          "duelo: sigla e cor da equipe vêm da comparação da sessão", str(c["lados"]))
    checa([l["em"] for l in c["lados"]] == [4.5, 5.2] and c["destaqueEm"] > 5.2, "cada lado entra na própria palavra; destaque depois")
    recusa(cena([d, {"kit": "anotacao", "params": {"tipo": "oval", "alvo": 0}}], ["x"]), "duelo", "duelo + anotação recusado")
    try:
        R.receita(cena([{"kit": "cartoes", "params": {**d["params"], "lados": [{"piloto": 99, "valor": "1"}, {"piloto": 44, "valor": "2"}]}}]), PAL, 0, 0)
        checa(False, "piloto fora da sessão recusado")
    except R.FaltaAtivo:
        checa(True, "piloto fora da sessão recusado")

    j = R.receita({**cena([{"kit": "cartoes", "params": {**d["params"], "forma": "barras", "escala": [26, 27]}}]), "t1": 6.0}, pal, 0, 0)
    checa(j["props"]["camadas"][0]["forma"] == "barras" and j["props"]["camadas"][0]["escala"] == [26, 27], "duelo em barras com escala")
    recusa(cena([{"kit": "cartoes", "params": {**d["params"], "forma": "pizza"}}]), "forma", "forma de duelo desconhecida recusada")
    checa(R._arquibancadas_gps([{"circuito": "Mexico City"}])[0]["f0"] == round(3560 / 4304, 5), "arquibancadas do México em fração da volta")
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.py", Path(td) / "b.py"
        a.write_bytes(b"x = 1\r\ny = 2\r\n")
        b.write_bytes(b"x = 1\ny = 2\n")
        checa(R.hash_arquivo(a) == R.hash_arquivo(b), "hash do código igual com CRLF e LF (cache vale entre cópias)")

    print("4. narração do rascunho")
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        pasta = proj / "horizontal"
        (proj / "trabalho" / "gravacao").mkdir(parents=True)
        pasta.mkdir()
        checa(MT.narracao(pasta) is None, "sem nada: sem narração")
        (proj / "trabalho" / "voz_guia.wav").write_bytes(b"x")
        checa(MT.narracao(pasta).name == "voz_guia.wav", "rascunho usa a voz guia")
        checa(MT.narracao(pasta, "final") is None, "final NUNCA usa a voz guia")
        (proj / "trabalho" / "gravacao" / "limpa.wav").write_bytes(b"x")
        checa(MT.narracao(pasta).name == "limpa.wav" and MT.narracao(pasta, "final").name == "limpa.wav", "gravação vale mais que a voz guia")

    print(f"\n{'0 falhas' if not falhas else f'{falhas} FALHA(S)'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
