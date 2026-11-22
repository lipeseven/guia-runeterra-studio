"""Fase C: junta os blocos (concat sem recodificar) + áudio, gera folha de contatos e INDEX.md. python -B montar.py"""
import json
import subprocess
from pathlib import Path

AQUI = Path(__file__).parent
OF = AQUI.parents[4] / "dados/comum/oficina_craft/biblioteca/catalogo_horizontal/video"
plano = json.loads((AQUI / "plano.json").read_text(encoding="utf-8"))
fps = plano["fps"]
lista = json.loads((OF / "_blocos/lista.json").read_text(encoding="utf-8"))
ff = lambda *a: subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)

(OF / "_tmp/concat.txt").write_text("".join(f"file '{x['arq']}'\n" for x in lista), encoding="utf-8")
ff("-f", "concat", "-safe", "0", "-i", str(OF / "_tmp/concat.txt"), "-c", "copy", str(OF / "_tmp/mudo.mp4"))
ff("-i", str(OF / "_tmp/mudo.mp4"), "-i", str(OF / "_tmp/audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
   "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(OF / "catalogo_horizontal.mp4"))

# folha de contatos: um quadro por trecho (60 % do trecho), 6 colunas
sel = "+".join(f"eq(n\\,{x['a'] + int((x['b'] - x['a']) * 0.6)})" for x in lista)
lin = -(-len(lista) // 6)
ff("-i", str(OF / "catalogo_horizontal.mp4"), "-vf", f"select='{sel}',scale=384:216,tile=6x{lin}:padding=4:color=white",
   "-frames:v", "1", "-q:v", "4", str(OF / "folha.jpg"))

# INDEX.md
tc = lambda q: f"{int(q / fps // 60)}:{q / fps % 60:05.2f}"
ORIG = {"c/estudio": "Fase A `renders/estudio_*` (`renders/scripts/estudio.py --clipe e1|e2|e3`)",
        "c/pista": "Fase A `renders/pista_*` (`renders/scripts/pista.py --clipe p1..p4`)",
        "c/freio": "Fase A `renders/freio_giro_dof/` (`freio.py` + `compor_freio.py`)",
        "d/": "Fase B `dados/` (`F1/horizontal/testes/catalogo/index.tsx` + `render_dados.ps1`)",
        "q/": "quadro congelado (último quadro do clipe, extraído no `preparar.sh`)"}
orig = lambda s: next((v for k, v in ORIG.items() if s.startswith(k)), s)
COMP = {"capitulo": "`Capitulo` (v1/src/cartoes.tsx) + SFX riser+impacto (`Banco.capitulo`)",
        "solta": "`Solta` (v1/src/cartoes.tsx)", "pessoa": "`Pessoa` (v1/src/cartoes.tsx), foto `kit/cartoes/exemplo/foto_exemplo.jpg`",
        "freio_palavra": "`FreioPalavra` (index.tsx): render opaco → `Palavra` (v1/src/textos.tsx) → mesmo render em alfa por cima",
        "ambiente_some": "`AmbienteSome` (index.tsx): freio opaco dissolve (1,8–4,2 s) para o render alfa sobre fundo liso",
        "trans": "`Trans` (index.tsx, transição nova)", "linha": "`Linha` (v1/src/linha.tsx)", "clipe": "`Clipe` (index.tsx)"}
def refazer(t):
    p = [COMP.get(t["tipo"], t["tipo"])]
    if t["tipo"] == "trans":
        p.append(f"efeito `{t['efeito']}` em {t['t']} s; A = `{t['a']['midia']['src']}`, B = `{t['b']['midia']['src']}`")
    if t["tipo"] == "linha":
        p.append(" → ".join(f"`{i['midia']['src'].split('/')[-1]}`" + (f" ({i['entrada']['tipo']})" if i.get("entrada") else "") for i in t["itens"]))
    m = t.get("midia")
    if m:
        p.append(f"mídia `{m['src']}`" + (f" desde {m['de']} s" if m.get("de") else "") + (f" a {m['vel']}x" if m.get("vel") else "") + f" — {orig(m['src'])}")
    if t.get("crop"):
        p.append("pan-crop " + " → ".join(f"{k[1]}x@({k[2]},{k[3]})" for k in t["crop"]))
    for o in t.get("overlays", []):
        p.append(f"overlay `{o['src'].split('/')[-1]}` {int(o['op'] * 100)} %")
    for k, nome in (("palavras", "Palavra"), ("anotacoes", "Anotacoes"), ("rotulos", "Rotulo"), ("icones", "ícones hub/icones")):
        if t.get(k):
            p.append(f"{len(t[k])}× {nome}")
    if t.get("palavra"):
        p.append("Palavra")
    if t.get("contador"):
        p.append("Contador")
    if t.get("filtro"):
        p.append(f"filtro `{t['filtro']}` + véu claro {t.get('lavar')}")
    if t.get("sfx"):
        p.append("SFX " + ", ".join(f"{c}@{s}s" for c, s, _ in t["sfx"]))
    return "; ".join(p)

L = ["# INDEX — catálogo do horizontal (fase C)", "",
     f"Vídeo: `video/catalogo_horizontal.mp4` — 1920x1080, 60 q/s, {lista[-1]['b'] + 1} quadros ({tc(lista[-1]['b'] + 1)}), {len(lista)} trechos, sem fala.",
     "Folha de contatos: `video/folha.jpg` (um quadro por trecho, na ordem). Créditos de áudio: `video/CREDITOS.md`.", "",
     "**Refazer tudo** (código em `F1/horizontal/testes/catalogo/montagem/`):",
     "1. `sh preparar.sh` (converte clipes/overlays/ícones para `video/_public`);",
     "2. `node render.mjs` (um bloco por trecho em `video/_blocos`, cache pelo hash do trecho; `--forcar id` refaz um; `--quadros id:seg` tira quadro pequeno);",
     "3. `.venv\\Scripts\\python.exe -B audio.py` (SFX do kit + trilha própria → `_tmp/audio.wav`, `CREDITOS.md`);",
     "4. `.venv\\Scripts\\python.exe -B montar.py` (concat sem recodificar + áudio, folha, este INDEX).",
     "Mudar um trecho = editar a entrada dele em `plano.json` (id abaixo) e repetir 2–4 (só o bloco alterado é renderizado).", "",
     "| nº | recurso | início | fim | id | como refazer |", "|---|---|---|---|---|---|"]
for i, (x, t) in enumerate(zip(lista, plano["trechos"])):
    L.append(f"| {i + 1:02d} | {t['nome']} | {tc(x['a'])} | {tc(x['b'] + 1)} | `{t['id']}` | {refazer(t)} |")
(OF / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("ok", tc(lista[-1]["b"] + 1), len(lista))
