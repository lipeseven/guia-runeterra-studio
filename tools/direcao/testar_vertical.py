# Testes automáticos das capacidades do diretor do vertical (sem pytest: roda direto e sai com código 1 se algo falhar).
#   .venv\Scripts\python.exe tools\direcao\testar_vertical.py
# Confere (2026-11-14): números na tela liberados pelo Felipe (briefing e pedidos), som por arquivo (caminhos, validação,
# normalização, cache dos sons do catálogo intacto), estilo da legenda nas props, logos de arquivo (lista, aviso do
# arquivo que falta, cópia para a pasta pública) e os circuitos Silverstone/Mônaco na biblioteca.
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ["GRS_CANAL"] = "f1"
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

import vertical as V  # noqa: E402

FALHAS: list[str] = []
OK = 0


def checa(cond: bool, msg: str) -> None:
    global OK
    if cond:
        OK += 1
    else:
        FALHAS.append(msg)
        print("FALHOU:", msg)


def palavras_de(texto: str) -> list[dict]:
    return [{"t": w, "i": k * 0.4, "f": k * 0.4 + 0.35} for k, w in enumerate(texto.split())]


# ------------------------------------------------------------------ 1. números na tela
print("1. números na tela")
checa("6201" in V._por_extenso("tem seis vírgula duzentos e um quilômetros"), "por extenso: seis vírgula duzentos e um = 6201")
checa("17" in V._por_extenso("são dezessete curvas"), "por extenso: dezessete = 17")
checa("2026" in V._por_extenso("em dois mil e vinte e seis"), "por extenso: dois mil e vinte e seis = 2026")
checa(V._chave_num("6,201") == V._chave_num("6.201") == "6201", "6,201 e 6.201 são o mesmo número")

pal = palavras_de("Las Vegas tem dezessete curvas e uma reta enorme.")
planos = [
    {"id": "a", "i": 0, "em": "Las Vegas", "placas": [{"texto": "6,201", "unidade": "KM"}]},
    {"id": "b", "i": 3, "em": "curvas", "codigo": 'obj(c.w, "x", () => rotulo("17 CURVAS"));\nrotulo("5,8 KM");'},
]
av = V.avisos_numeros(planos, pal, [])
checa(any("cena 1" in a and "6,201" in a for a in av), "placa com 6,201 fora da fala vira aviso")
checa(any("cena 2" in a and "5,8" in a for a in av), "rótulo do código com 5,8 fora da fala vira aviso")
checa(not any("17" in a.split(":")[1] for a in av if "cena 2" in a), "17 está na fala (por extenso): não é aviso")
av2 = V.avisos_numeros(planos, pal, ["6,201 km"])
checa(not any("cena 1" in a for a in av2), "6,201 liberado no briefing: sem aviso")
checa(any("5,8" in a for a in av2), "liberar 6,201 não libera os outros (5,8 continua avisado)")

brief = "Cabeçalho\n\n## CENAS\n- algo 99\n\n## NÚMEROS NA TELA (pedido do Felipe)\n- 6,201 km (comprimento de Las Vegas)\n- 1:32.5\n\n## EVITAR\n- 3 coisas"
lib = V.numeros_liberados(brief)
checa(lib == ["6,201 km (comprimento de Las Vegas)", "1:32.5"], f"seção NÚMEROS NA TELA do briefing do diretor: {lib}")
orig = "====\n1. ROTEIRO\n====\nTexto.\n====\nNUMEROS NA TELA\n====\n- 6,201 km\n====\nFONTES\n====\n- 404"
checa(V.numeros_liberados(orig) == ["6,201 km"], "seção NÚMEROS NA TELA no formato original (linhas de =)")
checa(V.numeros_liberados("") == [] and V.numeros_liberados("## CENAS\n- 5") == [], "sem a seção: nada liberado")

lp = V.liberar_dos_pedidos(["1:32.5"], [{"plano": "a", "texto": "cena 5: coloca o comprimento 6,201 km na tela"}])
checa(lp == ["1:32.5", "6,201"], f"pedido do Felipe libera só o número dele, não o número da cena: {lp}")

d = {"planos": planos, "avisos": ["número fora da fala (cena 9): 1", "outro aviso"], "numeros_liberados": ["6,201"]}
d = V.checar_regras(d, pal, "## NÚMEROS NA TELA\n- 5,8 km")
checa("outro aviso" in d["avisos"] and not any("cena 9" in a for a in d["avisos"]), "avisos antigos de número saem, os outros ficam")
checa(not any(a.startswith("número fora da fala") for a in d["avisos"]), "liberados do vídeo + do briefing: sem aviso de número")

s = V.sistema()
checa("SEMPRE é cumprido" in s and "NÚMEROS NA TELA" in s, "prompt do diretor: pedido do Felipe sempre cumprido + seção NÚMEROS NA TELA")
txt = {
    "grafico": {"tipo": "numero", "valor": 311.0, "unidade": "KM/H"}, "contador": {"de": 0, "ate": 6.201},
    "titulo": {"texto": "CIRCUITO", "sub": "6,201 KM"},
}
tt = V.textos_na_tela(txt)
checa("311" in tt and "6.201" in tt and "6,201 KM" in tt, f"textos na tela de gráfico/contador/título: {tt}")

# ------------------------------------------------------------------ 2. som por arquivo
print("2. som por arquivo")
tmp = Path(tempfile.mkdtemp(prefix="testar_vertical_"))
projeto = tmp / "projeto"
trabalho = projeto / "trabalho"
trabalho.mkdir(parents=True)
sr = 44100
tom = np.concatenate([np.zeros(int(0.3 * sr)), 0.1 * np.sin(2 * np.pi * 880 * np.arange(int(0.5 * sr)) / sr)]).astype(np.float32)
(projeto / "sons").mkdir()
sf.write(str(projeto / "sons" / "bipe.wav"), tom, sr)
sf.write(str(tmp / "absoluto.wav"), tom, sr)
sf.write(str(trabalho / "voz.wav"), np.full(int(6 * sr), 0.05, dtype=np.float32), sr)

checa(V.achar_som(str(tmp / "absoluto.wav")) == (tmp / "absoluto.wav").resolve(), "caminho absoluto")
checa(V.achar_som("sons/bipe.wav", projeto) == (projeto / "sons" / "bipe.wav").resolve(), "relativo à pasta do projeto")
try:
    V.achar_som("sons/nao_existe.wav", projeto)
    checa(False, "som inexistente devia dar erro")
except FileNotFoundError as e:
    checa("som não encontrado" in str(e), "som inexistente: erro claro")
try:
    V.achar_som("sons/bipe.txt", projeto)
    checa(False, "extensão errada devia dar erro")
except FileNotFoundError:
    checa(True, "")
pastas = [p.as_posix() for p in V.pastas_de_som(projeto)]
checa(any(p.endswith("dados/comum/freesound_cache") for p in pastas) and any(p.endswith("F1/horizontal/kit/sfx/banco") for p in pastas)
      and any(p.endswith("dados/comum") for p in pastas), "pastas liberadas: dados/comum, freesound_cache, kit/sfx/banco")

pl_som = [{"id": "s", "i": 0, "som": {"arquivo": "sons/bipe.wav", "em": "Las Vegas", "volume": 5, "duracao": 0.2}},
          {"id": "t", "i": 1, "sons": [{"arquivo": "sons/sumiu.wav", "em": "Vegas"}]}]
av = V.avisos_sons(pl_som, projeto)
checa(len(av) == 1 and "sumiu.wav" in av[0] and "cena 2" in av[0], f"aviso do som que não existe: {av}")

r = V.som_de_arquivo({"arquivo": "sons/bipe.wav", "volume": 5, "duracao": 0.2}, trabalho)
a, _ = sf.read(r["arquivo"])
checa(abs(20 * np.log10(np.abs(a).max()) + 3) < 0.2, "normalizado com pico em -3 dBFS (como o catálogo)")
checa(len(a) / sr < 0.75, "silêncio do início aparado")
checa(r["volume"] == 1.0 and r["duracao"] == 0.2 and r["categoria"] == "arquivo", f"volume limitado a 1 e duração pedida: {r}")
r2 = V.som_de_arquivo({"arquivo": "sons/bipe.wav"}, trabalho)
checa(r2["volume"] == V.SOM_ARQ_VOLUME and 0.4 < r2["duracao"] < 0.75, f"padrões de volume/duração: {r2}")

pal6 = palavras_de("Las Vegas tem uma reta enorme no meio")
brutos = [{"em": "Las Vegas", "codigo": "camera(c.w,[0,1,5],[0,0,0]);", "som": {"arquivo": "sons/bipe.wav", "em": "reta"}}]
res, _ = V.resolver(brutos, pal6)
checa(res[0].get("som", {}).get("i") == 4, "resolver mantém o som só com arquivo e acha a palavra")
sons = V.sons({"planos": res}, pal6, trabalho)
checa(len(sons) == 1 and sons[0]["categoria"] == "arquivo" and abs(sons[0]["t"] - pal6[4]["i"]) < 0.05, f"sons(): som por arquivo sem busca CLAP: {sons}")
sons_b = V.sons({"planos": [{**res[0], "som": {"arquivo": "sons/sumiu.wav", "i": 4}}]}, pal6, trabalho)
checa(sons_b == [], "arquivo que sumiu: o render segue sem ele")
checa(not (trabalho / "sons_vertical.json").exists(), "com arquivo faltando a escolha não é guardada (entra quando o arquivo chegar)")

# cache dos sons do catálogo: a chave continua a de antes (vídeos antigos não trocam de som)
planos_cat = [{"id": "c", "i": 0, "som": {"o_que": "short soft bubble pop", "i": 2}}]
t_cat = round(pal6[2]["i"], 3)
chave_antiga = hashlib.sha1(json.dumps(["um-toque-2", [(t_cat, "short soft bubble pop")]], ensure_ascii=False).encode()).hexdigest()
falso = trabalho / "pop_falso.wav"
sf.write(str(falso), tom, sr)
guardado = [{"t": t_cat, "o_que": "short soft bubble pop", "arquivo": str(falso), "categoria": "pop", "volume": 0.24, "inicio": 0, "duracao": 0.3}]
(trabalho / "sons_vertical.json").write_text(json.dumps({"chave": chave_antiga, "sons": guardado}), encoding="utf-8")
checa(V.sons({"planos": planos_cat}, pal6, trabalho) == guardado, "escolha guardada dos sons do catálogo continua valendo (mesma chave)")

# ------------------------------------------------------------------ 3. legenda
print("3. legenda")
dl = {"planos": [{"id": "a", "i": 0}], "chaves": []}
checa("legenda" not in V._props(dl, pal6), "sem estilo: props como antes")
estilo = {"fundo": "#0e1118", "opacidade": 0.6, "raio": 20, "margem": 16, "branca": True}
checa(V._props({**dl, "legenda": estilo}, pal6)["legenda"] == estilo, "estilo da legenda do vídeo vai nas props")
b0 = V.blocos(dl, pal6, "f")[0]["impressao"]
checa(b0 == V.blocos({**dl}, pal6, "f")[0]["impressao"] and b0 != V.blocos({**dl, "legenda": estilo}, pal6, "f")[0]["impressao"],
      "trocar o estilo da legenda refaz os blocos; sem estilo, a impressão é a de antes")
kit = (V.RAIZ / "F1" / "comum" / "remotion" / "kit.tsx").read_text(encoding="utf-8")
checa("EstiloLegenda" in kit and "branca" in kit and "opacidade" in kit and "raio" in kit and "margem" in kit, "kit.tsx: Legenda com estilo")

# ------------------------------------------------------------------ 4. logos
print("4. logos")
pasta_logos = tmp / "logos"
pasta_logos.mkdir()
from PIL import Image  # noqa: E402

Image.new("RGBA", (200, 100), (0, 60, 160, 255)).save(pasta_logos / "fia.png")
checa(set(V.logos_disponiveis(pasta_logos)) == {"fia"}, "logos disponíveis pela pasta (nome do arquivo = chave)")
pl_logo = [{"id": "l", "codigo": 'const l = obj(c.w, "livro", () => criarLivro({ capa: "logo:fia" }));\nlogo("logo:Fifa");'}]
checa(V.logos_usados(pl_logo) == {"fia", "fifa"}, "logos citados no código")
av = V.avisos_logos(pl_logo, pasta_logos)
checa(len(av) == 1 and "fifa.png" in av[0] and "coloque o arquivo" in av[0], f"aviso diz o arquivo exato que falta: {av}")
publico = tmp / "publico"
mapa = V.copiar_logos(publico, pl_logo, pasta_logos)
checa(mapa == {"fia": "logos/fia.png"} and (publico / "logos" / "fia.png").exists(), "logo citado copiado para a pasta pública")
checa("logos" in V._props(dl, pal6, mapa) and "logos" not in V._props(dl, pal6, {}), "mapa dos logos nas props só quando há logo")
checa("LOGOS DISPONÍVEIS" in V._docs() and "nao_feitos" in V._lista_logos(), "prompt lista os logos e diz o que fazer se faltar")
nomes = V._nomes_api(V.RAIZ / "F1" / "vertical" / "video")
checa({"logo", "aplicarLogo", "criarPainelLogo", "criarLivro"} <= set(nomes), "API do código das cenas tem os logos")
checa((V.RAIZ / "F1" / "comum" / "arte" / "logos").is_dir(), "pasta F1/comum/arte/logos existe")

# ------------------------------------------------------------------ 5. circuitos
print("5. circuitos")
circ = json.loads((V.RAIZ / "F1" / "comum" / "remotion" / "modelos" / "geo" / "circuitos.json").read_text(encoding="utf-8"))
checa(circ["silverstone"]["comprimento"] == 5891 and len(circ["silverstone"]["curvas"]) == 18, "silverstone: 5891 m, 18 curvas")
checa(circ["monaco"]["comprimento"] == 3337 and len(circ["monaco"]["curvas"]) == 19 and "monaco_1984" in circ, "monaco atual (3337 m, 19 curvas) e monaco_1984")
geo = (V.RAIZ / "F1" / "comum" / "remotion" / "modelos" / "geografia.ts").read_text(encoding="utf-8")
fs = {c["n"]: c["f"] for c in circ["silverstone"]["curvas"]}
trechos = dict(re.findall(r'texto: "([A-Z ]+)", f: ([\d.]+)', geo.split("TRECHOS_SILVERSTONE")[1].split("];")[0]))
checa(float(trechos["ABBEY"]) == fs[1] and float(trechos["COPSE"]) == fs[9] and float(trechos["CHAPEL"]) == fs[14] and float(trechos["STOWE"]) == fs[15],
      "TRECHOS_SILVERSTONE nas posições das curvas oficiais (1 Abbey, 9 Copse, 14 Chapel, 15 Stowe)")
checa("silverstone: TRECHOS_SILVERSTONE" in geo and "monaco: TRECHOS_MONACO" in geo, "TRECHOS registra silverstone e monaco")
api = (V.RAIZ / "F1" / "vertical" / "docs" / "api_cenas.md").read_text(encoding="utf-8")
checa('"monaco"' in api and "Abbey" in api,"api_cenas.md documenta monaco e os nomes de Silverstone")

# ------------------------------------------------------------------ 6. revisão por pedido geral não apaga campos
print("6. revisão preserva campos que o diretor não devolveu (placas da cena 19)")
pal7 = palavras_de("Abre a cena. e quantas voltas faltam. Fecha aqui")
dir7 = {"planos": [
    {"id": "aaaa1111", "set": "estudio", "clima": "vazio", "codigo": "const w=c.w;", "em": "Abre a cena.", "i": 0},
    {"id": "bbbb2222", "set": "estudio", "clima": "vazio", "codigo": "const w=c.w;", "em": "e quantas voltas faltam.", "i": 3,
     "placas": [{"texto": "48/62", "unidade": "VOLTAS", "cor": "amarelo", "pos": "meio", "i": 3}], "grafico": {"tipo": "palavra", "texto": "VOLTAS"}},
]}
resposta = {"planos": [{"id": "bbbb2222", "em": "e quantas voltas faltam.", "set": "estudio", "clima": "vazio", "codigo": "const w=c.w;w.chao.color.set('#333');"}], "remover": []}
_orig = V.chamar_json
try:
    V.chamar_json = lambda *a, **k: resposta
    r7 = V.revisar(dir7, [{"texto": "as rodas devem girar", "plano": None}], pal7, "", None)
finally:
    V.chamar_json = _orig
pl7 = {"bbbb2222": next((p for p in r7["planos"] if "voltas faltam" in (p.get("em") or "")), {})}  # o resolver refaz ids e índices
checa("w.chao.color.set" in pl7["bbbb2222"].get("codigo", ""), "o código que o diretor mudou entra")
checa(bool(pl7["bbbb2222"].get("placas")) and "48/62" in json.dumps(pl7["bbbb2222"]["placas"], ensure_ascii=False),
      "placa 48/62 continua depois da revisão geral que não a devolveu")
checa(bool(pl7["bbbb2222"].get("grafico")), "gráfico da cena também continua")

print(f"\n{OK} ok, {len(FALHAS)} falha(s)")
sys.exit(1 if FALHAS else 0)
