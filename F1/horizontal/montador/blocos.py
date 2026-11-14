"""Blocos de saída (fase 7b): o vídeo é uma fila de blocos codificados à parte e juntados SEM recodificar.

- Bloco = cenas inteiras vizinhas, até `TETO_BLOCO_S` de vídeo (medição em `medir_motores.py`, números no README).
- Fronteira de bloco só entre cenas que NÃO continuam uma na outra (mesmo gráfico / mesmo GPS = `continua`). Prefere
  um CORTE (junção sem nada a recodificar); sem corte possível, usa uma transição (wipe/zoom/fade) INTEIRA como
  segmento próprio de junção, que depende só das duas cenas vizinhas. Sem fronteira permitida, o bloco passa do teto
  (aviso), nunca corta uma transição ou um gráfico/GPS contínuo no meio.
- Cache: `<pasta>/blocos/<modo>_<hash>.mp4`; hash = peças do bloco (hash do trecho de cada cena + quadros usados +
  estado da transição) + resolução + codificador. Mudou uma cena → só os blocos/junções que usam o trecho dela mudam.
- Junção final: `ffmpeg -f concat` com `-c:v copy` (nenhum quadro recodificado) + o áudio da mixagem única (AAC).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import juncao as J

FPS = 60
TETO_BLOCO_S = 45.0
VERSAO = 1
_CODEC: dict[bool, str] = {}


def _chave_kit(u: dict) -> tuple:
    p = u.get("params") or {}
    if u["kit"] == "graficos":
        return ("graficos", p.get("tipo"), p.get("sessao"), json.dumps(p.get("a"), sort_keys=True), json.dumps(p.get("b"), sort_keys=True))
    if u["kit"] == "gps":
        return ("gps", p.get("sessao"), json.dumps(p.get("carros"), sort_keys=True))
    return (u["kit"], None)


def continua(a: dict, b: dict) -> bool:
    """A cena b continua a mesma peça da a (mesmo gráfico ou o mesmo GPS em sequência): não separar em blocos."""
    if a["motor"] != b["motor"]:
        return False
    ka = {_chave_kit(u) for u in a.get("kits", []) if u["kit"] in ("graficos", "gps")}
    kb = {_chave_kit(u) for u in b.get("kits", []) if u["kit"] in ("graficos", "gps")}
    return bool(ka & kb)


def agrupar(cenas: list[dict], n_entrada: list[int], teto_s: float = TETO_BLOCO_S) -> tuple[list[dict], list[str]]:
    """[{de, ate (índices de cena, ate exclusivo), juncao: bool (a fronteira antes de `de` é uma transição)}], avisos."""
    dur = [(int(round(c["t1"] * FPS)) - int(round(c["t0"] * FPS))) / FPS for c in cenas]
    pode = [False] + [not continua(cenas[k - 1], cenas[k]) for k in range(1, len(cenas))]
    blocos, avisos, s, k = [], [], 0, 1
    while k <= len(cenas):
        if k < len(cenas) and sum(dur[s:k + 1]) <= teto_s:
            k += 1
            continue
        if k == len(cenas):
            blocos.append((s, k))
            break
        # passou do teto ao juntar a cena k: fecha no melhor ponto permitido em (s, k]
        cortes = [b for b in range(s + 1, k + 1) if pode[b] and n_entrada[b] == 0]
        trans = [b for b in range(s + 1, k + 1) if pode[b]]
        b = (cortes or trans or [None])[-1]
        if b is None:   # nada permitido até aqui: o bloco cresce até a próxima fronteira permitida
            prox = next((x for x in range(k + 1, len(cenas)) if pode[x]), None)
            avisos.append(f"bloco a partir da cena {cenas[s]['id']} passa de {teto_s:.0f} s (cenas contínuas, sem fronteira permitida)")
            if prox is None:
                blocos.append((s, len(cenas)))
                break
            b = prox
        blocos.append((s, b))
        s, k = b, b + 1
    out = [{"de": a, "ate": b, "juncao": a > 0 and n_entrada[a] > 0, "segundos": round(sum(dur[a:b]), 3)} for a, b in blocos]
    return out, avisos


def segmentos(pcs: list[dict], cenas: list[dict], blocos: list[dict]) -> list[dict]:
    """Peças do vídeo (juncao.pecas) → segmentos: [{tipo: bloco|juncao, pecas: [...], cenas: [...]}] em ordem."""
    ordem = {c["id"]: k for k, c in enumerate(cenas)}
    bloco_de = {k: n for n, b in enumerate(blocos) for k in range(b["de"], b["ate"])}
    segs, atual = [], None
    for p in pcs:
        k = ordem[p["cena"]]
        n = bloco_de[k]
        if p["tipo"] == "transicao" and blocos[n]["de"] == k and blocos[n]["juncao"]:
            segs.append({"tipo": "juncao", "pecas": [p], "cenas": [cenas[k - 1]["id"], p["cena"]]})
            atual = None
            continue
        if atual is None or atual["bloco"] != n:
            b = blocos[n]
            atual = {"tipo": "bloco", "bloco": n, "pecas": [], "cenas": [c["id"] for c in cenas[b["de"]:b["ate"]]],
                     "segundos": b["segundos"]}
            segs.append(atual)
        atual["pecas"].append(p)
    return segs


class TrocaCodec(RuntimeError):
    """O NVENC falhou no meio dos blocos: o vídeo inteiro passa para o x264 (concat sem recodificar exige o mesmo)."""


def codec(rascunho: bool) -> str:
    """NVENC se esta máquina codifica com ele; senão x264. Decidido uma vez: os blocos de um vídeo usam o mesmo.
    `F1_SEM_NVENC=1` (testes) faz o NVENC falhar de verdade no ffmpeg (ver `juncao.parametros_codec`)."""
    if rascunho not in _CODEC:
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=256x144:r=60:d=0.1", "-c:v",
                            *J.parametros_codec("h264_nvenc", rascunho), "-f", "null", "-"], capture_output=True)
        _CODEC[rascunho] = "h264_nvenc" if r.returncode == 0 else "libx264"
    return _CODEC[rascunho]


def _hash(seg: dict, trechos: dict, transicoes: dict, W: int, H: int, cod: str, rascunho: bool) -> str:
    h = hashlib.sha1()
    pecas = []
    for p in seg["pecas"]:
        if p["tipo"] == "trecho":
            pecas.append(["t", trechos[p["cena"]]["hash"], trechos[p["cena"]]["quadros"], p["de"], p["ate"]])
        else:   # transição: o estado do kit + os dois trechos que ela mistura
            k = p["cena"]
            pecas.append(["x", transicoes[k]["hash_estado"], transicoes[k]["a"], transicoes[k]["b"], p["n"]])
    h.update(json.dumps({"v": VERSAO, "pecas": pecas, "W": W, "H": H, "cod": J.parametros_codec(cod, rascunho)}).encode())
    return h.hexdigest()[:14]


def codificar(segs: list[dict], trechos: dict, transicoes: dict, pasta: Path, modo: str, W: int, H: int, tmp: Path,
              forcar: bool = False, log=print) -> list[dict]:
    """Cada segmento → MP4 sem áudio (cache por hash). Devolve os segmentos com arquivo/hash/do_cache."""
    rascunho = modo == "rascunho"
    cod = codec(rascunho)
    pasta_b = Path(pasta) / "blocos"
    pasta_b.mkdir(parents=True, exist_ok=True)
    out = []
    for n, s in enumerate(segs):
        h = _hash(s, trechos, transicoes, W, H, cod, rascunho)
        arq = pasta_b / f"{modo}_{h}.mp4"
        meta = arq.with_suffix(".json")
        quadros = sum((p["ate"] - p["de"]) if p["tipo"] == "trecho" else p["n"] for p in s["pecas"])
        m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        cache = not forcar and arq.exists() and m.get("quadros") == quadros
        t0 = time.perf_counter()
        if not cache:
            try:
                J.encodar_final(s["pecas"], None, arq, W, H, rascunho, tmp, codec=cod)
            except RuntimeError as e:
                if cod != "h264_nvenc":
                    raise
                _CODEC[rascunho] = "libx264"   # o resto do vídeo (e as próximas montagens deste processo) em x264
                raise TrocaCodec(f"NVENC falhou no segmento {n} ({str(e)[-300:]}): refazendo em x264") from e
            n_lido = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                                         "stream=nb_read_frames", "-of", "csv=p=0", str(arq)], capture_output=True, text=True).stdout.strip() or -1)
            if n_lido != quadros:
                raise RuntimeError(f"segmento {n} ({s['tipo']}): {n_lido} quadros, esperados {quadros}")
            meta.write_text(json.dumps({"quadros": quadros, "cenas": s["cenas"], "tipo": s["tipo"], "codec": cod}, ensure_ascii=False),
                            encoding="utf-8")
        seg_s = round(time.perf_counter() - t0, 2)
        log(f"  {s['tipo']:6} {n:02d} {len(s['cenas'])} cena(s) {quadros / FPS:6.2f} s  "
            + ("cache" if cache else f"codificado em {seg_s:.1f} s"))
        out.append({**{k: v for k, v in s.items() if k != "pecas"}, "arquivo": str(arq), "hash": h, "quadros": quadros,
                    "do_cache": cache, "codec": cod, "segundos_codificar": None if cache else seg_s})
    return out


def concatenar(segs: list[dict], audio: Path | None, saida: Path, rascunho: bool, tmp: Path) -> None:
    """Junta os segmentos com o concat do ffmpeg SEM recodificar o vídeo (`-c:v copy`) e põe o áudio da mixagem."""
    lista = Path(tmp) / "concat.txt"
    lista.write_text("".join(f"file '{Path(s['arquivo']).as_posix()}'\n" for s in segs), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista)]
    mapa = ["-map", "0:v"]
    if audio:
        cmd += ["-i", str(audio)]
        mapa += ["-map", "1:a", "-c:a", "aac", "-b:a", "256k" if rascunho else "320k", "-ar", "48000"]
    cmd += [*mapa, "-c:v", "copy", "-movflags", "+faststart", str(saida)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg (concat dos blocos) falhou: {r.stderr[-1500:]}")


def limpar(pasta: Path, modo: str, usados: list[dict], manter: int = 0) -> None:
    """Tira do cache os blocos deste modo que não estão no vídeo atual (`manter` = quantos antigos guardar)."""
    vivos = {Path(s["arquivo"]).name for s in usados}
    velhos = sorted((p for p in (Path(pasta) / "blocos").glob(f"{modo}_*.mp4") if p.name not in vivos),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    for p in velhos[manter:]:
        p.unlink(missing_ok=True)
        p.with_suffix(".json").unlink(missing_ok=True)
