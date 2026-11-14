"""UMA mixagem final: narração + trilha + SFX do kit/sfx (por âncora de palavra e no pico de cada transição).

- SFX: `Banco` do kit/sfx (mesma escolha de variação, pico do som na âncora, ganho por categoria × intensidade).
  Pedidos da SPEC (`cena.sfx[]`: categoria + palavra `i` + `ponto`) e das transições (`pedidosSfx`: whoosh no wipe/zoom,
  pico no quadro de pico). Arquivos do banco: `kit/sfx/banco/` desta cópia ou da pasta principal (fica fora do Git).
- Trilha (opcional): levada a `TRILHA_LUFS` e abaixada sob a voz (sidechain).
- Tudo num só grafo do ffmpeg (filtro por arquivo) → `mix_bruta.wav`; loudness MEDIDA (ebur128 do ffmpeg) e ganho
  para `ALVO_LUFS`, limitador no fim → `master.wav`; mede de novo e grava no relatório. Sem narração, não aplica ganho
  (o nível dos SFX fica o do kit) e avisa.
- Junto sai `sfx.wav` (só os SFX, mesma linha do tempo) para a verificação de sincronia.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HORIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HORIZ / "kit" / "sfx"))
import sfx as SFX  # noqa: E402

SR = 48000
ALVO_LUFS = -14.0       # mesma referência da voz limpa do painel (tools/audio/limpar_gravacao.py)
TETO_DBTP = -1.5
TRILHA_LUFS = -26.0
DUCK = "threshold=0.03:ratio=6:attack=40:release=450:makeup=1"
# SFX sob a voz (rodada 1 do placar: impacto do fecho 1,7 dB acima da voz, capítulos a 2–3 dB dela): compressão leve
# do barramento de SFX pela voz; o golpe continua a passar (ataque de 15 ms), a cauda abaixa ~3–5 dB enquanto ela fala
DUCK_SFX = "threshold=0.05:ratio=3:attack=15:release=300:makeup=1"


def pasta_banco() -> Path:
    for base in [HORIZ.parents[1], *HORIZ.parents[1].parents]:
        p = base / "F1" / "horizontal" / "kit" / "sfx"
        if (p / "banco").is_dir():
            return p
    raise FileNotFoundError("banco do kit/sfx não existe (rode F1/horizontal/kit/sfx/gerar.py: o banco fica fora do Git)")


def eventos(cenas: list[dict], palavras: list[dict], transicoes: list[dict], semente: int = 0) -> list[SFX.Evento]:
    """SFX da SPEC (por palavra) + SFX das transições (no pico). Ordem da linha do tempo (a variação depende dela)."""
    b = SFX.Banco(semente=semente)
    pedidos = []
    for c in cenas:
        for s in c.get("sfx") or []:
            p = palavras[int(s["i"])]
            pedidos.append({"categoria": s["categoria"], "t": float(p[s.get("ponto", "i")]), "intensidade": s.get("intensidade", 0.7),
                            "palavra": p.get("t"), "_cena": c["id"]})
    for t in transicoes:
        if t and t.get("sfx"):
            pedidos.append({"categoria": t["sfx"], "t": float(t["tPico"]), "intensidade": t.get("intensidade", 0.7),
                            **({"variacao": t["variacao"]} if t.get("variacao") else {}), "palavra": f"transição {t['tipo']}"})
    pedidos.sort(key=lambda p: p["t"])
    evs = []
    for p in pedidos:
        if p["categoria"] == "capitulo":
            evs += b.capitulo(p["t"], p["intensidade"])
        else:
            evs.append(b.para(p["categoria"], p["t"], p["intensidade"], p.get("variacao"), palavra=p.get("palavra")))
    return evs


def creditos(evs: list[SFX.Evento]) -> list[str]:
    """Créditos dos SFX CC BY usados (vão na descrição do vídeo publicado); CC0/sintetizados não pedem crédito."""
    try:
        return SFX.Banco().creditos(evs)
    except (FileNotFoundError, KeyError, OSError):
        return []


def medir(wav: Path) -> dict:
    """Loudness integrada (LUFS) e pico verdadeiro (dBTP) pelo ebur128 do ffmpeg (BS.1770-4)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    resumo = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", resumo)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", resumo)
    f = lambda m: float("-inf") if not m or m.group(1) == "-inf" else float(m.group(1))   # noqa: E731
    return {"lufs": f(i), "pico_dbtp": f(tp)}


def _sh(cmd: list) -> None:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg (mixagem) falhou: {r.stderr[-1500:]}")


def mixar(evs: list[SFX.Evento], dur: float, saida: Path, narracao: Path | None, trilha: Path | None) -> dict:
    """Grafo único: narração (0 dB) + trilha (ganho medido, abaixada sob a voz) + SFX → mix_bruta.wav e sfx.wav;
    depois ganho para o alvo e limitador → master.wav. Devolve o relatório de loudness."""
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    banco = pasta_banco()
    n = int(round(dur * SR))
    entradas, filtros, mix = [], [], []
    fmt = f"aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo"
    k = 0
    if narracao:
        entradas += ["-i", narracao]
        filtros.append(f"[{k}:a]{fmt},apad=whole_len={n},atrim=end_sample={n},asplit=3[voz][vozsc][vozsfx]")
        mix.append("[voz]")
        k += 1
    rel = {"narracao": str(narracao) if narracao else None, "trilha": str(trilha) if trilha else None, "avisos": []}
    if trilha:
        g = TRILHA_LUFS - medir(trilha)["lufs"]
        entradas += ["-stream_loop", "-1", "-i", trilha]
        filtros.append(f"[{k}:a]{fmt},atrim=end_sample={n},volume={g:.2f}dB[tri0]")
        if narracao:
            filtros.append(f"[tri0][vozsc]sidechaincompress={DUCK}[tri]")
        else:
            filtros.append("[tri0]anull[tri]")
        mix.append("[tri]")
        rel["trilha_ganho_db"] = round(g, 2)
        k += 1
    elif narracao:
        filtros.append("[vozsc]anullsink")
    rot = []
    for e in evs:
        entradas += ["-i", banco / e.arquivo]
        atraso = int(round(e.inicio * SR))
        filtros.append(f"[{k}:a]{fmt},atrim=start_sample={int(round(e.corte_ini * SR))}:end_sample={int(round((e.corte_ini + e.dur) * SR))},"
                       f"asetpts=PTS-STARTPTS,afade=t=out:st={max(0.0, e.dur - SFX.SAIDA_S):.5f}:d={SFX.SAIDA_S},"
                       f"volume={e.ganho_db}dB,adelay={atraso}S|{atraso}S[s{k}]")
        rot.append(f"[s{k}]")
        k += 1
    if rot:
        filtros.append(f"{''.join(rot)}amix=inputs={len(rot)}:normalize=0:duration=longest,apad=whole_len={n},atrim=end_sample={n},asplit=2[sfx0][sfxstem]")
        if narracao:   # sfx.wav (stem) fica SEM o ducking: a verificação mede o pico de cada som nele
            filtros.append(f"[sfx0][vozsfx]sidechaincompress={DUCK_SFX}[sfx]")
        else:
            filtros.append("[sfx0]anull[sfx]")
        mix.append("[sfx]")
    else:
        filtros.append(f"anullsrc=r={SR}:cl=stereo,atrim=end_sample={n},asplit=2[sfx][sfxstem]")
        mix.append("[sfx]")
        if narracao:
            filtros.append("[vozsfx]anullsink")
    filtros.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=end_sample={n}[mix]" if len(mix) > 1
                   else f"{mix[0]}anull[mix]")
    script = saida / "filtro_audio.txt"
    script.write_text(";\n".join(filtros), encoding="utf-8")
    bruta, stem, master = saida / "mix_bruta.wav", saida / "sfx.wav", saida / "master.wav"
    _sh(["ffmpeg", "-y", "-v", "error", *entradas, "-/filter_complex", script,
         "-map", "[mix]", "-c:a", "pcm_f32le", "-ar", SR, bruta, "-map", "[sfxstem]", "-c:a", "pcm_f32le", "-ar", SR, stem])
    antes = medir(bruta)
    if narracao and antes["lufs"] != float("-inf"):
        ganho = ALVO_LUFS - antes["lufs"]
    else:
        ganho = 0.0
        rel["avisos"].append("sem narração: loudness não normalizada (SFX no nível do kit)")
    teto = 10 ** (TETO_DBTP / 20)
    _sh(["ffmpeg", "-y", "-v", "error", "-i", bruta, "-af",
         f"volume={ganho:.3f}dB,aresample={SR * 4},alimiter=limit={teto:.4f}:attack=2:release=60:level=disabled,aresample={SR}",
         "-c:a", "pcm_s24le", "-ar", SR, master])
    depois = medir(master)
    rel.update({"antes": antes, "ganho_db": round(ganho, 2), "master": depois, "alvo_lufs": ALVO_LUFS if narracao else None,
                "teto_dbtp": TETO_DBTP, "arquivos": {"bruta": str(bruta), "sfx": str(stem), "master": str(master)},
                "eventos": [{"categoria": e.categoria, "id": e.id, "t": e.t, "inicio": e.inicio, "dur": e.dur, "ganho_db": e.ganho_db,
                             "palavra": e.palavra, "arquivo": str(banco / e.arquivo), "corte_ini": e.corte_ini} for e in evs]})
    return rel
