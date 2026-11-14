"""Teste do montador com um mini-spec de 3 cenas curtas (kits existentes; NÃO é um vídeo de verdade).

Projeto fictício em `testes/montador/saida/projeto/horizontal/` (fora do Git):
  c1  0–3 s  Remotion     kit/graficos  velocidade × distância, Monza 2025 Q (9908) LEC v16 × HAM v16   (corte; impacto em "Leclerc,")
  c2  3–6 s  HyperFrames  kit/gps       os dois carros pelo GPS, pista plana de Monza, câmera perseguindo  (wipe 24 q + whoosh)
  c3  6–9 s  Remotion     kit/anotacao  "0,117 s" com oval à mão                                            (zoom 30 q + whoosh; pop em "0,117")
Narração e trilha são SINTÉTICAS (ruído com envelope de sílabas e acorde senoidal), só para exercitar a mixagem:
nenhuma voz de IA. A SPEC passa no esquema do diretor (`diretor/esquemas/spec.schema.json`).

Confere: verificação do montador aprovada (quadros por cena, junções, sincronia, loudness); medidas independentes com
ffprobe; cache (2ª montagem sem render; trocar o texto da c3 re-renderiza SÓ a c3); cena por demanda; mensagens claras
de falta (ativo inexistente, kit sem receita). Copia as folhas de quadros para `testes/montador/`.
    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\montador\\testar.py [--limpar]   (~2–4 min na 1ª vez; precisa de internet
    para o gsap/three.js do CDN na cena HyperFrames)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
HORIZ = AQUI.parents[1]
sys.path.insert(0, str(HORIZ / "montador"))
sys.path.insert(1, str(HORIZ / "diretor"))
sys.path.insert(2, str(HORIZ / "kit" / "sfx"))

import medir           # noqa: E402
import montar as MT    # noqa: E402
from esquema import validar  # noqa: E402

import segmentos as S  # noqa: E402

SAIDA = AQUI / "saida"
PASTA = SAIDA / "projeto" / "horizontal"
SR = 48000
TETO_TESTE = 4.0   # s: com cenas de 3 s, cada cena vira um bloco e as transições viram junções
falhas: list[str] = []
n_ok = 0

# conta as invocações do Remotion (lote × cena avulsa) sem mudar o que o montador faz
CHAMADAS = {"LoteDoc": 0, "CenaDoc": 0}
_sh_original = S._sh


def _sh_contando(cmd, cwd=None):
    for nome in CHAMADAS:
        if nome in [str(x) for x in cmd]:
            CHAMADAS[nome] += 1
    return _sh_original(cmd, cwd)


S._sh = _sh_contando


def pacotes(mp4: Path, decodificar: bool = False) -> list[str]:
    """Hash de cada pacote de vídeo (sem decodificar) ou de cada quadro decodificado."""
    cod = [] if decodificar else ["-c", "copy"]
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v", *cod, "-f", "framemd5", "-"],
                       capture_output=True, text=True)
    return [ln.rsplit(",", 1)[-1].strip() for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]


def sem_recodificar(final: Path, segs: list[dict]) -> tuple[bool, str]:
    """Concat sem recodificar: todo quadro decodificado idêntico ao do segmento, e os pacotes idênticos byte a byte
    salvo os quadros-chave (o concat repete SPS/PPS na frente deles: +49 bytes, mesmo conteúdo)."""
    a, b = sum((pacotes(Path(s["arquivo"])) for s in segs), []), pacotes(final)
    da, db = sum((pacotes(Path(s["arquivo"]), True) for s in segs), []), pacotes(final, True)
    dif = sum(1 for x, y in zip(a, b) if x != y)
    ok = len(a) == len(b) and da == db and dif <= len(segs) + len(a) // 120 + 1
    return ok, f"({len(a)} × {len(b)} pacotes, {dif} diferentes (só quadros-chave), quadros decodificados iguais: {da == db})"


def checa(cond, nome, detalhe=""):
    global n_ok
    if cond:
        n_ok += 1
        print("  ok  ", nome)
    else:
        falhas.append(f"{nome} {detalhe}")
        print("  FALHA", nome, detalhe)


FRASES = [("Em Monza, Leclerc foi mais rápido que Hamilton na reta.", 0.0),
          ("Os dois carros dividem a mesma pista, cada um no próprio GPS.", 3.0),
          ("No fim, a diferença foi de 0,117 segundo.", 6.0)]
FIM = 9.0


def palavras() -> list[dict]:
    out = []
    for k, (frase, t0) in enumerate(FRASES):
        ws = frase.split()
        t1 = FRASES[k + 1][1] if k + 1 < len(FRASES) else FIM
        passo = (t1 - t0 - 0.25) / len(ws)
        for j, w in enumerate(ws):
            out.append({"t": w, "i": round(t0 + j * passo, 3), "f": round(t0 + (j + 0.82) * passo, 3)})
    return out


def idx(pal: list[dict], palavra: str) -> int:
    return next(k for k, p in enumerate(pal) if p["t"] == palavra)


def spec(pal: list[dict], texto_c3: list[str]) -> dict:
    inicios = [sum(len(x.split()) for x, _ in FRASES[:k]) for k in range(len(FRASES))]
    fins = inicios[1:] + [len(pal)]
    base = []
    for k, (frase, t0) in enumerate(FRASES):
        em = " ".join(frase.split()[:3])
        base.append({"id": hashlib.sha1(em.encode()).hexdigest()[:8], "em": em, "i0": inicios[k], "i1": fins[k], "t0": t0,
                     "t1": FRASES[k + 1][1] if k + 1 < len(FRASES) else FIM, "capitulo": "c1", "afirmacoes": [], "texto": []})
    c1, c2, c3 = base
    c1.update(objetivo="a diferença de velocidade aparece no gráfico", motor="remotion", transicao={"tipo": "corte", "quadros": 0},
              kits=[{"kit": "graficos", "params": {"tipo": "velocidade", "sessao": 9908, "a": {"piloto": 16, "volta": 16},
                                                   "b": {"piloto": 44, "volta": 16}, "dur": 2.2}}],
              sfx=[{"categoria": "impacto", "em": "Leclerc", "i": idx(pal, "Leclerc"), "intensidade": 0.8}])
    c2.update(objetivo="os dois carros na mesma pista, cada um no próprio GPS", motor="hyperframes", camera="perseguição",
              transicao={"tipo": "wipe", "quadros": 24},
              kits=[{"kit": "gps", "params": {"sessao": 9908, "carros": [{"piloto": 16, "volta": 16}, {"piloto": 44, "volta": 16}],
                                              "fator": 1, "inicio": 40.0, "camera_gps": "perseguicao"}}], sfx=[])
    c3.update(objetivo="o número da diferença, circulado", motor="remotion", transicao={"tipo": "zoom", "quadros": 30},
              texto=texto_c3,
              kits=[{"kit": "anotacao", "params": {"tipo": "oval", "alvo": 0, "em": "0,117", "i": idx(pal, "0,117")}}],
              sfx=[{"categoria": "pop", "em": "0,117", "i": idx(pal, "0,117"), "intensidade": 0.7}])
    return {"versao": 1, "fps": 60, "largura": 1920, "altura": 1080, "roteiro_hash": "0" * 12, "historia_hash": "0" * 12,
            "tempos": "medidos", "cenas": base}


def narracao_sintetica(pal: list[dict], saida: Path) -> None:
    """Ruído filtrado com envelope de sílaba em cada palavra (só para ter uma 'voz' no lugar certo). Não é voz."""
    n = int(FIM * SR)
    x = np.zeros(n)
    rng = np.random.default_rng(7)
    for p in pal:
        a, b = int(p["i"] * SR), int(p["f"] * SR)
        t = np.arange(b - a) / SR
        sil = max(1, round(len(p["t"]) / 3))
        env = np.sin(np.pi * np.clip(t / (t[-1] + 1e-9), 0, 1)) * (0.6 + 0.4 * np.abs(np.sin(np.pi * sil * t / (t[-1] + 1e-9))))
        ruido = np.convolve(rng.standard_normal(b - a), np.hanning(24) / 12, "same")
        f0 = 140 + 30 * rng.random()
        x[a:b] += env * (0.5 * ruido + 0.5 * np.sin(2 * np.pi * f0 * t) * np.sign(np.sin(2 * np.pi * f0 * 0.5 * t)))
    x *= 10 ** ((-14 - medir.lufs_integrado(np.stack([x, x], 1))) / 20)
    medir.gravar(str(saida), np.clip(x, -0.95, 0.95))


def trilha_sintetica(saida: Path) -> None:
    t = np.arange(int(6 * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t + k)) for k, f in enumerate((110, 164.8, 220, 277.2)))
    medir.gravar(str(saida), 0.08 * x / 4)


def ffprobe(mp4: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,duration", "-of", "json", str(mp4)],
                       capture_output=True, text=True)
    return {s["codec_type"]: s for s in json.loads(r.stdout)["streams"]}


def main() -> int:
    if "--limpar" in sys.argv:
        shutil.rmtree(SAIDA, ignore_errors=True)
    for d in ("trechos", "rascunho", "verificacao", "estado.json", "storyboard", "blocos", "prompts", "ajustes_diretos.json", "final", "historia.json"):   # cada rodada começa sem cache (o teste do cache depende disso)
        p = PASTA / d
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    PASTA.mkdir(parents=True, exist_ok=True)
    pal = palavras()
    (PASTA / "roteiro.txt").write_text(" ".join(f for f, _ in FRASES) + "\n", encoding="utf-8")
    (PASTA / "palavras.json").write_text(json.dumps(pal, ensure_ascii=False, indent=1), encoding="utf-8")
    sp = spec(pal, ["0,117 s", "Leclerc × Hamilton · classificação de Monza 2025"])
    (PASTA / "spec.json").write_text(json.dumps(sp, ensure_ascii=False, indent=1), encoding="utf-8")
    narracao_sintetica(pal, PASTA / "narracao.wav")
    trilha_sintetica(PASTA / "trilha.wav")

    print("1. mini-spec")
    checa(not validar(sp, "spec"), "mini-spec válido no esquema do diretor", str(validar(sp, "spec"))[:300])
    checa([c["motor"] for c in sp["cenas"]] == ["remotion", "hyperframes", "remotion"], "1 cena HyperFrames + 2 Remotion")

    print("2. montagem (rascunho 1280x720; blocos com teto de 4 s para exercitar junções e concat sem recodificar)")
    rel = MT.montar(PASTA, "rascunho", exigir_estado=False, teto_bloco=TETO_TESTE)
    print("  ", MT.resumo(rel))
    v = rel["verificacao"]
    for e in v["erros"]:
        print("   ERRO", e)
    for a in v["avisos"]:
        print("   aviso", a)
    checa(v["status"] == "aprovado", "verificação do montador aprovada", f"({len(v['erros'])} erros)")
    pr = ffprobe(Path(rel["arquivo"]))
    checa(int(pr["video"]["nb_read_frames"]) == 540 and pr["video"]["r_frame_rate"] == "60/1", "540 quadros a 60 q/s (9 s)",
          f"({pr['video']['nb_read_frames']} {pr['video']['r_frame_rate']})")
    checa((pr["video"]["width"], pr["video"]["height"]) == (1280, 720), "1280x720")
    checa("audio" in pr and abs(float(pr["audio"]["duration"]) - 9.0) < 0.03, "áudio com a duração do vídeo", f"({pr.get('audio', {}).get('duration')})")
    med = v["medidas"]
    checa([c["quadros"] for c in med["cenas"]] == [180, 180, 180], "180 quadros por cena")
    checa(all(s["melhor_desloc"] == 0 for c in med["cenas"] for s in c["amostras"] if not s["parado"]),
          "quadros puros no lugar certo (deslocamento 0)")
    j = {x["tipo"]: x for x in med["juncoes"]}
    checa(j.get("wipe", {}).get("n") == 24 and j.get("zoom", {}).get("n") == 30, "junções wipe 24 q e zoom 30 q")
    checa(all(not x["pretos"] and not x["repetidos"] for x in med["juncoes"]), "junções sem quadro preto nem repetido")
    sfx = med.get("sfx", [])
    checa(len(sfx) == 4 and {s["categoria"] for s in sfx} == {"impacto", "pop", "whoosh"}, "4 SFX (impacto, pop, 2 whoosh)",
          f"({[s['categoria'] for s in sfx]})")
    checa(all(abs(s["erro_ms"]) <= 12 for s in sfx if s["categoria"] in ("impacto", "pop")), "impacto e pop no pico (≤ 12 ms)",
          f"({[(s['categoria'], s['erro_ms']) for s in sfx]})")
    checa(abs(med.get("audio_alinhamento_ms", 99)) <= 1.0, "áudio do MP4 alinhado ao master (≤ 1 ms)", f"({med.get('audio_alinhamento_ms')})")
    lf = med.get("loudness_mp4", {})
    checa(abs(lf.get("lufs", 0) + 14) <= 0.7 and lf.get("pico_dbtp", 0) <= -1.0, "loudness do MP4 −14 LUFS, pico ≤ −1 dBTP", f"({lf})")
    segs = rel["blocos"]["segmentos"]
    checa([s["tipo"] for s in segs] == ["bloco", "juncao", "bloco", "juncao", "bloco"], "3 blocos + 2 junções (wipe e zoom inteiros)",
          f"({[s['tipo'] for s in segs]})")
    checa(CHAMADAS["LoteDoc"] == 1 and CHAMADAS["CenaDoc"] == 0, "as 2 cenas Remotion num lote só (o motor abre 1 vez)", f"({CHAMADAS})")
    ok, det = sem_recodificar(Path(rel["arquivo"]), segs)
    checa(ok, "vídeo final = pacotes dos blocos/junções (concat SEM recodificar)", det)

    print("3. cache e cena por demanda")
    rel2 = MT.montar(PASTA, "rascunho", exigir_estado=False, teto_bloco=TETO_TESTE)
    checa(all(c["do_cache"] for c in rel2["cenas"]), "2ª montagem: nenhuma cena renderizada de novo")
    checa(rel2["blocos"]["codificados"] == 0, "2ª montagem: nenhum bloco codificado de novo", f"({rel2['blocos']['codificados']})")
    sp2 = spec(pal, ["0,117 s", "Leclerc × Hamilton · Monza 2025"])
    (PASTA / "spec.json").write_text(json.dumps(sp2, ensure_ascii=False, indent=1), encoding="utf-8")
    rel3 = MT.montar(PASTA, "rascunho", exigir_estado=False, teto_bloco=TETO_TESTE)
    checa([c["do_cache"] for c in rel3["cenas"]] == [True, True, False], "texto da c3 mudou: só a c3 re-renderizada",
          f"({[c['do_cache'] for c in rel3['cenas']]})")
    checa([s["do_cache"] for s in rel3["blocos"]["segmentos"]] == [True, True, True, False, False],
          "c3 mudou: só a junção c2→c3 e o bloco da c3 recodificados", f"({[s['do_cache'] for s in rel3['blocos']['segmentos']]})")
    checa(rel3["verificacao"]["status"] == "aprovado", "montagem com a c3 nova aprovada")
    rel4 = MT.montar(PASTA, "rascunho", exigir_estado=False)   # teto padrão (45 s): o mini-spec inteiro cabe num bloco
    checa(len(rel4["blocos"]["segmentos"]) == 1 and rel4["verificacao"]["status"] == "aprovado", "teto padrão: 1 bloco, aprovado",
          f"({len(rel4['blocos']['segmentos'])}, {rel4['verificacao']['erros'][:2]})")
    so = MT.montar(PASTA, "rascunho", cenas=[sp2["cenas"][1]["id"]], exigir_estado=False)
    checa(list(so["cenas"]) == [sp2["cenas"][1]["id"]] and so["cenas"][sp2["cenas"][1]["id"]]["do_cache"], "cena por demanda (só c2, do cache)")

    print("4. mensagens de falta")
    ruim = json.loads(json.dumps(sp2))
    ruim["cenas"][0]["kits"][0]["params"]["sessao"] = 1
    ruim["cenas"][1]["kits"] = [{"kit": "imagens", "params": {"afirmacao": "a1"}}]
    (PASTA / "spec.json").write_text(json.dumps(ruim, ensure_ascii=False), encoding="utf-8")
    try:
        MT.planejar(PASTA, exigir_estado=False)
        checa(False, "falta de ativo barrada")
    except MT.NaoMonta as e:
        msg = str(e)
        checa("falta comparação 1_16-16_44-16.json" in msg and "preparar.py" in msg, "falta de comparação: diz qual e o comando", msg[:200])
        checa("imagens ainda sem receita no HyperFrames" in msg, "kit sem receita: mensagem clara", msg[:300])
    try:
        MT.planejar(PASTA, exigir_estado=True)
        checa(False, "sem estado: barrado")
    except MT.NaoMonta as e:
        checa("aprove ★" in str(e), "SPEC não aprovada: barrado com o motivo", str(e)[:200])
    (PASTA / "spec.json").write_text(json.dumps(sp2, ensure_ascii=False, indent=1), encoding="utf-8")

    print("5. gancho do painel (ponte diretor/painel.py → montador em processo à parte → estado.json)")
    import etapas as E
    from comum import gravar_json, hash_dados
    est = E.novo("projeto")
    for n, st in (("historia", "aprovado"), ("spec", "aprovado"), ("ativos", "gerado"), ("verificacao", "gerado")):
        est["etapas"][n]["status"] = st
    est["etapas"]["spec"]["hash"] = hash_dados(sp2)
    gravar_json(PASTA / "verificacao" / "verificacao.json", {"status": "aprovado", "erros": [], "pendencias": [], "avisos": []})
    E.gravar(PASTA, est)
    ped = json.dumps({"cmd": "passo", "passo": "rascunho", "pasta": str(PASTA), "slug": "projeto"}).encode()
    r = subprocess.run([sys.executable, str(HORIZ / "diretor" / "painel.py")], input=ped, capture_output=True)
    resp = json.loads(r.stdout.decode("utf-8"))
    checa(resp.get("ok") and resp["passo"].get("montando"), "passo rascunho dispara o montador", str(resp)[:300])
    checa(E.ler(PASTA)["etapas"]["rascunho"]["status"] in ("andamento", "gerado"), "estado: rascunho em andamento")
    r2 = json.loads(subprocess.run([sys.executable, str(HORIZ / "diretor" / "painel.py")], input=ped, capture_output=True).stdout.decode())
    checa(not r2.get("ok") and "já está sendo montado" in r2.get("erro", ""), "2º clique durante a montagem: recusado", str(r2)[:200])
    import time
    for _ in range(240):
        if E.ler(PASTA)["etapas"]["rascunho"]["status"] != "andamento":
            break
        time.sleep(1)
    reg = E.ler(PASTA)["etapas"]["rascunho"]
    checa(reg["status"] == "gerado" and "verificação aprovado" in reg.get("resumo", ""), "montador terminou: rascunho gerado (★ pendente)",
          f"({reg})")
    try:
        E.aprovar(PASTA, "rascunho")
        checa(True, "rascunho aprovável ★")
    except ValueError as e:
        checa(False, "rascunho aprovável ★", str(e))

    print("6. storyboard: prévia por cena, ★ da cena, ações diretas (só a cena afetada renderiza de novo)")
    import storyboard as SB
    from PIL import Image

    def ponte(**ped):
        r = subprocess.run([sys.executable, str(HORIZ / "diretor" / "painel.py")], capture_output=True,
                           input=json.dumps({"pasta": str(PASTA), "slug": "projeto", **ped}).encode())
        return json.loads(r.stdout.decode("utf-8"))

    c1, c2, c3 = (c["id"] for c in sp2["cenas"])
    sb = SB.ler(PASTA)
    checa([c["estado"] for c in sb["cenas"]] == ["sem_previa"] * 3, "storyboard: 3 cenas sem prévia ainda",
          f"({[c['estado'] for c in sb['cenas']]})")
    checa(sb["cenas"][0]["frases"][0]["texto"].startswith("Em Monza") and sb["cenas"][2]["momentos"][1]["rotulo"].startswith("anotacao oval"),
          "frases faladas e momentos-chave (anotação + SFX) por cena", str(sb["cenas"][2]["momentos"])[:200])
    r = ponte(cmd="aprovar_cena", cena=c1)
    checa(not r["ok"] and "prévia" in r["erro"], "★ da cena recusada sem prévia", str(r)[:200])
    g = SB.gerar(PASTA, [c1, c3])
    checa(set(g["feitas"]) == {c1, c3} and all(x["do_cache"] for x in g["feitas"].values()),
          "prévia de cenas já montadas sai do cache do rascunho (sem render)", str(g)[:300])
    sb = SB.ler(PASTA)
    q1 = sb["cenas"][0]["quadros"]
    checa(len(q1) == len(sb["cenas"][0]["momentos"]) and all(Path(q["arquivo"]).exists() for q in q1)
          and Image.open(q1[0]["arquivo"]).size == (480, 270), "quadros da prévia (480×270) nos momentos-chave", str(q1)[:200])
    checa(ponte(cmd="aprovar_cena", cena=c1)["ok"] and SB.ler(PASTA)["cenas"][0]["estado"] == "aprovada", "cena aprovada ★")
    fim_antes = np.asarray(Image.open(q1[-1]["arquivo"]).convert("L"), float)

    # ação direta: zoom na c1 (Remotion) → só a c1 muda; SPEC continua aprovada; rascunho desatualizado
    r = ponte(cmd="ajustar", cena=c1, acao={"acao": "movimento", "tipo": "aproximar", "intensidade": 0.12}, previa=False)
    checa(r["ok"] and r["ajuste"]["afetadas"] == [c1], "movimento na c1: só a c1 afetada", str(r)[:300])
    est = E.ler(PASTA)
    checa(est["etapas"]["spec"]["status"] == "aprovado" and est["etapas"]["rascunho"]["status"] == "desatualizado",
          "SPEC segue aprovada (ação do Felipe) e o rascunho fica desatualizado", str({k: v["status"] for k, v in est["etapas"].items()}))
    checa(json.loads((PASTA / "spec.json").read_text(encoding="utf-8"))["cenas"][0]["movimento"]["tipo"] == "aproximar"
          and not validar(json.loads((PASTA / "spec.json").read_text(encoding="utf-8")), "spec"), "spec.json com o movimento e válido")
    checa(SB.ler(PASTA)["cenas"][0]["estado"] == "desatualizada", "cena aprovada que mudou fica desatualizada")
    r = ponte(cmd="ajustar", cena=c2, acao={"acao": "movimento", "tipo": "pan_dir"}, previa=False)
    checa(r["ok"] and r["ajuste"]["afetadas"] == [c2], "movimento na c2 (HyperFrames): só a c2 afetada", str(r)[:300])
    r = ponte(cmd="ajustar", cena=c3, acao={"acao": "transicao", "tipo": "fade"}, previa=False)
    checa(r["ok"] and set(r["ajuste"]["afetadas"]) == {c2, c3}, "entrada da c3 vira fade: c2 (saída) e c3 afetadas", str(r)[:300])
    r = ponte(cmd="ajustar", cena=c1, acao={"acao": "sfx", "j": 0, "categoria": "sino"}, previa=False)
    checa(r["ok"] and r["ajuste"]["afetadas"] == [], "trocar o SFX: nenhuma cena renderiza (só o áudio muda)", str(r)[:300])
    r = ponte(cmd="ajustar", cena=c1, acao={"acao": "kit", "kit": "graficos", "param": "tipo", "valor": "delta"}, previa=False)
    checa(not r["ok"] and "não é ação direta" in r["erro"], "mudança fora das ações diretas recusada (vai ao orquestrador)", str(r)[:200])
    r = ponte(cmd="ajustar", cena=c2, acao={"acao": "corte", "indice": 30}, previa=False)
    checa(not r["ok"] and "corte precisa ficar" in r["erro"], "corte fora da cena anterior/atual recusado", str(r)[:200])

    # prévia nova da c1 (render só dela) e a montagem com as ações (verificação por quadro dos 2 motores)
    CHAMADAS.update(LoteDoc=0, CenaDoc=0)
    g = SB.gerar(PASTA, [c1])
    checa(g["feitas"].get(c1, {}).get("do_cache") is False and CHAMADAS["CenaDoc"] == 1, "prévia da c1: renderizada de novo, só ela",
          f"({g}, {CHAMADAS})")
    q1n = SB.ler(PASTA)["cenas"][0]["quadros"]
    fim_depois = np.asarray(Image.open(q1n[-1]["arquivo"]).convert("L"), float)
    dif = float(np.abs(fim_depois - fim_antes).mean())
    checa(dif > 2.0, "zoom aparece na prévia (último quadro diferente do antes)", f"(diferença média {dif:.1f})")
    CHAMADAS.update(LoteDoc=0, CenaDoc=0)
    rel5 = MT.montar(PASTA, "rascunho", exigir_estado=False, teto_bloco=TETO_TESTE)
    checa([c["do_cache"] for c in rel5["cenas"]] == [True, False, False], "montagem depois das ações: c1 do cache da prévia, c2 e c3 renderizadas",
          f"({[c['do_cache'] for c in rel5['cenas']]})")
    checa(rel5["verificacao"]["status"] == "aprovado", "montagem com movimento (2 motores) e fade aprovada na verificação",
          str(rel5["verificacao"]["erros"][:3]))
    sfx5 = rel5["verificacao"]["medidas"].get("sfx", [])
    checa(any(s["categoria"] == "sino" for s in sfx5), "SFX trocado (sino) entrou na mixagem", f"({[s['categoria'] for s in sfx5]})")

    # pedido que não é ação direta (voz): pedido da cena + prompt só dela para o orquestrador
    r = ponte(cmd="pedido_cena", cena=c2, texto="quero os carros mais separados na tela", origem="voz")
    checa(r["ok"] and r["pedido"]["prompt"] and Path(r["pedido"]["prompt"][0]).name == f"pedido_{c2}.prompt.txt",
          "pedido por voz vira prompt só da c2", str(r)[:300])
    est = E.ler(PASTA)
    checa(est["etapas"]["spec"]["status"] == "prompt_pronto" and est["pedidos"][-1]["cena"] == c2
          and "ditado por voz" in est["pedidos"][-1]["texto"], "SPEC aguardando o orquestrador com o pedido da c2")
    checa("quero os carros mais separados" in (PASTA / "prompts" / f"pedido_{c2}.prompt.txt").read_text(encoding="utf-8"),
          "prompt da cena traz o pedido")

    final_7c(ponte, E)

    for f in sorted((PASTA / "rascunho" / "verificacao").glob("folha_*.jpg")):
        shutil.copy2(f, AQUI / f.name)
    shutil.copy2(PASTA / "rascunho" / "verificacao" / "verificacao_montagem.json", AQUI / "verificacao_montagem.json")
    print(f"\nvídeo: {rel3['arquivo']}\n{n_ok} checagens ok, {len(falhas)} falhas")
    return 1 if falhas else 0


def final_7c(ponte, E) -> None:
    """Fase 7c: o vídeo final DE VERDADE (1920×1080, 60 q/s) do mini-spec, com a "gravação limpa" do card (a narração
    sintética copiada para trabalho/gravacao/limpa.wav: o caminho e a regra são os do final; a voz é a de teste)."""
    import os
    import storyboard as SB
    from comum import hash_dados
    B = MT.B
    print("7. vídeo final (fase 7c): 1920×1080 60 q/s, narração gravada, NVENC e x264, só o bloco afetado refeito")
    limpa = PASTA.parent / "trabalho" / "gravacao" / "limpa.wav"
    limpa.unlink(missing_ok=True)
    shutil.rmtree(PASTA / "final", ignore_errors=True)
    try:
        MT.planejar(PASTA, exigir_estado=False, modo="final")
        checa(False, "final sem a gravação limpa: barrado")
    except MT.NaoMonta as e:
        checa("narração gravada e limpa" in str(e), "final sem a gravação limpa: barrado (a voz guia/narracao.wav não vale)", str(e)[:200])
    limpa.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PASTA / "narracao.wav", limpa)
    checa(MT.narracao(PASTA, "final") == limpa and MT.narracao(PASTA) == PASTA / "narracao.wav", "final usa SÓ a gravação limpa; rascunho segue com narracao.wav")

    # estado: o pedido por voz da seção 6 sai (fixture) e a SPEC atual fica ★
    est = E.ler(PASTA)
    for p in est["pedidos"]:
        if p["status"] == "aberto":
            p["status"] = "recusado"
    sp_atual = json.loads((PASTA / "spec.json").read_text(encoding="utf-8"))
    est["etapas"]["spec"].update(status="aprovado", hash=hash_dados(sp_atual))
    from comum import gravar_json
    gravar_json(PASTA / "historia.json", {"titulo": "Leclerc × Hamilton em Monza", "tese": "mini-spec do teste do montador",
                                          "tempos": "medidos", "capitulos": [{"id": "c1", "titulo": "Monza", "funcao": "gancho",
                                                                              "ritmo": "denso", "em": "Em Monza,", "i": 0}],
                                          "afirmacoes": []})
    E.gravar(PASTA, est)
    c1, c2, c3 = (c["id"] for c in sp_atual["cenas"])
    r = ponte(cmd="final_checar", narracao="guia")
    checa(not r["ok"] and "sua gravação" in r["erro"], "final recusado com a voz guia valendo", str(r)[:200])
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(not r["ok"] and "aprove ★ no storyboard" in r["erro"], "final recusado sem todas as cenas ★", str(r)[:300])
    SB.gerar(PASTA, None)
    for c in (c1, c2, c3):
        ponte(cmd="aprovar_cena", cena=c)
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(not r["ok"] and "verificação reprovou" in r["erro"], "final recusado com a verificação da SPEC atual reprovada (mini-spec à mão)",
          str(r)[:200])
    # conserta o mini-spec como o diretor faria: história válida, hashes da SPEC e o número “2025” que não é dito na c3
    from comum import hash_texto
    hist = {"versao": 1, "titulo": "Leclerc × Hamilton em Monza", "tese": "mini-spec do teste do montador",
            "roteiro_hash": hash_texto((PASTA / "roteiro.txt").read_text(encoding="utf-8")), "tempos": "medidos",
            "capitulos": [{"id": "c1", "titulo": "Monza", "funcao": "gancho", "ritmo": "denso", "em": "Em Monza,", "i": 0}], "afirmacoes": []}
    gravar_json(PASTA / "historia.json", hist)
    sp_atual.update(roteiro_hash=hist["roteiro_hash"], historia_hash=hash_dados(hist))
    sp_atual["cenas"][2]["texto"] = ["0,117 s", "Leclerc × Hamilton · Monza"]
    (PASTA / "spec.json").write_text(json.dumps(sp_atual, ensure_ascii=False, indent=1), encoding="utf-8")
    est = E.ler(PASTA)
    est["etapas"]["spec"].update(status="aprovado", hash=hash_dados(sp_atual))
    est["etapas"]["verificacao"]["status"] = "desatualizado"
    E.gravar(PASTA, est)
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(not r["ok"] and "cena 3" in r["erro"] and "verificação" not in r["erro"], "texto da c3 mudou: final pede ★ da c3 de novo", str(r)[:200])
    SB.gerar(PASTA, [c3])
    ponte(cmd="aprovar_cena", cena=c3)
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(r["ok"] and r["final"]["cenas"] == 3 and "--final" in r["final"]["comando"], "todas as cenas ★: final liberado (comando do montador)", str(r)[:300])

    # o mesmo comando que o motor do painel roda (processo à parte, linhas PROG para a barra)
    t0 = __import__("time").time()
    p = subprocess.run([sys.executable, *r["final"]["comando"]], cwd=r["final"]["pasta_montador"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    seg_final = __import__("time").time() - t0
    progs = [ln.split(" ", 2) for ln in p.stdout.splitlines() if ln.startswith("PROG ")]
    fr = [float(x[1]) for x in progs]
    checa(p.returncode == 0, "montador --final terminou", p.stdout[-600:])
    checa(fr and fr == sorted(fr) and fr[-1] == 1.0 and any(x[2].startswith("bloco 1 de") for x in progs)
          and any(x[2].startswith("cena 3 de 3") for x in progs), "progresso cena a cena e bloco a bloco, crescente até 100 %",
          str([x[2] for x in progs])[:300])
    info = json.loads((PASTA / "final" / "final.json").read_text(encoding="utf-8"))
    pr = ffprobe(Path(info["arquivo"]))
    checa((pr["video"]["width"], pr["video"]["height"]) == (1920, 1080) and pr["video"]["r_frame_rate"] == "60/1"
          and int(pr["video"]["nb_read_frames"]) == 540, "final 1920×1080, 60/1, 540 quadros (ffprobe)", str(pr["video"]))
    checa(abs(float(pr["audio"]["duration"]) - 9.0) < 0.03, "áudio do final com a duração do vídeo", str(pr["audio"].get("duration")))
    lf = info["loudness_mp4"] or {}
    checa(info["verificacao"]["status"] == "aprovado" and abs(lf.get("lufs", 0) + 14) <= 0.7 and lf.get("pico_dbtp", 0) <= -1.0,
          "final aprovado na verificação por quadro; −14 LUFS e pico ≤ −1 dBTP medidos no MP4", f"({info['verificacao']['erros'][:2]}, {lf})")
    checa(info["narracao"] == str(limpa) and info["spec_hash"] == hash_dados(sp_atual), "final com a gravação limpa e o hash da SPEC")
    checa(info["codificador"] == "h264_nvenc", "esta máquina: NVENC", info["codificador"])
    print(f"   final 1080p60 de 9 s em {seg_final:.0f} s; {info['resumo']}")
    res = ponte(cmd="resumo")
    checa(res["final"]["spec_hash"] == res["spec_hash"], "ponte: final em dia com a SPEC")

    # x264: máquina "sem NVENC" (o ffmpeg recusa o NVENC de verdade) → sonda cai no x264
    os.environ["F1_SEM_NVENC"] = "1"
    B._CODEC.clear()
    try:
        relx = MT.montar(PASTA, "final", exigir_estado=False, teto_bloco=TETO_TESTE)
        x264 = b"x264 - core" in Path(relx["arquivo"]).read_bytes()
        checa(relx["codificador"] == "libx264" and all(s["codec"] == "libx264" for s in relx["blocos"]["segmentos"]) and x264,
              "sem NVENC: todos os blocos em x264 (SEI do x264 no MP4)", f"({relx['codificador']}, x264 no arquivo: {x264})")
        checa(relx["verificacao"]["status"] == "aprovado", "final em x264 aprovado na verificação", str(relx["verificacao"]["erros"][:2]))
        # NVENC que passa na sonda e cai no meio dos blocos: o vídeo inteiro vira x264 (concat exige um codificador só)
        B._CODEC[False] = "h264_nvenc"
        rely = MT.montar(PASTA, "final", exigir_estado=False, teto_bloco=TETO_TESTE)
        checa(rely["codificador"] == "libx264" and any("NVENC falhou" in a for a in rely["avisos"])
              and rely["verificacao"]["status"] == "aprovado", "NVENC caiu no bloco: refeito em x264, com aviso",
              f"({rely['codificador']}, {rely['avisos'][-1:]})")
    finally:
        os.environ.pop("F1_SEM_NVENC", None)
        B._CODEC.clear()

    # correção depois do final: ação direta na c3 → final barrado até o ★ → só a c3 e o bloco dela refeitos
    rel_a = MT.montar(PASTA, "final", exigir_estado=False, teto_bloco=TETO_TESTE)
    checa(rel_a["codificador"] == "h264_nvenc" and all(c["do_cache"] for c in rel_a["cenas"]), "final de novo: cenas 1080p do cache")
    r = ponte(cmd="ajustar", cena=c3, acao={"acao": "movimento", "tipo": "aproximar", "intensidade": 0.08}, previa=False)
    checa(r["ok"] and r["ajuste"]["afetadas"] == [c3], "correção pós-final na c3 (ação direta)", str(r)[:200])
    res = ponte(cmd="resumo")
    checa(res["final"]["spec_hash"] != res["spec_hash"], "ponte: final desatualizado depois da correção")
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(not r["ok"] and "cena 3" in r["erro"], "final barrado até a c3 ser ★ de novo", str(r)[:200])
    SB.gerar(PASTA, [c3])
    ponte(cmd="aprovar_cena", cena=c3)
    r = ponte(cmd="final_checar", narracao="gravacao")
    checa(r["ok"], "c3 ★: final liberado", str(r)[:200])
    rel_b = MT.montar(PASTA, "final", exigir_estado=False, teto_bloco=TETO_TESTE)
    checa([c["do_cache"] for c in rel_b["cenas"]] == [True, True, False], "só a c3 renderizada de novo em 1080p",
          f"({[c['do_cache'] for c in rel_b['cenas']]})")
    checa([s["do_cache"] for s in rel_b["blocos"]["segmentos"]] == [True, True, True, False, False],
          "só a junção c2→c3 e o bloco da c3 recodificados", f"({[s['do_cache'] for s in rel_b['blocos']['segmentos']]})")
    checa(rel_b["verificacao"]["status"] == "aprovado", "final corrigido aprovado na verificação", str(rel_b["verificacao"]["erros"][:2]))
    for f in sorted((PASTA / "final" / "verificacao").glob("folha_*.jpg")):
        shutil.copy2(f, AQUI / f"final_{f.name}")


if __name__ == "__main__":
    sys.exit(main())
