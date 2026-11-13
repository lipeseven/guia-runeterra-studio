# Leitura do quadro (OCR local, RapidOCR/onnxruntime) e interpretação do que a transmissão escreve:
# contador "LAP C/71", nomes de piloto, REPLAY, bandeiras.
from __future__ import annotations

import re
import unicodedata

_ocr = None


def _motor():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR  # pip install rapidocr-onnxruntime (no .venv do projeto)
        _ocr = RapidOCR()
    return _ocr


def ler(img, regiao: tuple[float, float, float, float] | None = None) -> list[dict]:
    """OCR de um quadro BGR (numpy). regiao = (x0, y0, x1, y1) em fração da imagem. Caixas voltam em fração."""
    h, w = img.shape[:2]
    ox = oy = 0
    if regiao:
        x0, y0, x1, y1 = regiao
        ox, oy = int(x0 * w), int(y0 * h)
        img = img[oy:int(y1 * h), ox:int(x1 * w)]
    res, _ = _motor()(img)
    saida = []
    for caixa, texto, conf in res or []:
        xs = [p[0] + ox for p in caixa]
        ys = [p[1] + oy for p in caixa]
        saida.append({"texto": texto, "conf": round(float(conf), 3),
                      "caixa": [round(min(xs) / w, 4), round(min(ys) / h, 4), round(max(xs) / w, 4), round(max(ys) / h, 4)]})
    return saida


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


_BARRA = str.maketrans({"I": "/", "L": "/", "|": "/", "\\": "/", "l": "/", "1": "1"})


def volta_do_texto(textos: list[str], total: int | None = None) -> int | None:
    """Lê o contador da transmissão. O OCR costuma trocar a barra por 1/I/l ou sumir com ela:
    'LAP64/71' -> 64, 'LAP1I71' -> 1, 'LAP3171' -> 3, 'LAP17171' -> 17, 'LAP 11 171' -> 11, 'LAP | 42' -> 42."""
    itens = [normalizar(t) for t in textos]
    for i, item in enumerate(itens):
        m = re.search(r"LAP(?![A-Z])", item)
        if not m:
            continue
        resto = item[m.end():]
        if not re.search(r"[0-9]", resto) and i + 1 < len(itens):   # "LAP" e o número em itens separados
            resto = itens[i + 1]
        m2 = re.match(r"[\s|:]*([0-9][0-9IL|/\\ ]{0,10})", resto)
        if not m2:
            continue
        s = m2.group(1).strip().replace(" ", "").translate(_BARRA)
        s = re.sub(r"[^0-9/]", "", s)
        n = _interpretar(s, total)
        if n is not None:
            return n
    return None


def _interpretar(s: str, total: int | None) -> int | None:
    if not s:
        return None
    if "/" in s:
        a, _, b = s.partition("/")
        b = b.strip("/")
        if not a.isdigit():
            return None
        if total and b and b.isdigit() and int(b) != total:
            # total lido diferente do da sessão: só aceita se for a barra lida como "1" ("1/71" visto como "/171")
            if not (b.endswith(str(total)) and b[:-len(str(total))] in ("1", "")):
                return _ok(None, total)
        return _ok(int(a), total)
    if total:
        t = str(total)
        if s.endswith("1" + t) and len(s) > len(t) + 1:      # barra lida como "1"
            return _ok(int(s[:-len(t) - 1]), total)
        if s.endswith(t) and len(s) > len(t):                 # barra sumiu
            return _ok(int(s[:-len(t)]), total)
    if len(s) <= 2:                                            # câmera onboard: "LAP 42"
        return _ok(int(s), total)
    return None


def _ok(n: int | None, total: int | None) -> int | None:
    if n is None or n < 1 or (total and n > total):
        return None
    return n


def total_do_texto(textos: list[str]) -> int | None:
    """Total de voltas escrito no contador ('LAP 64/71' -> 71), quando a barra foi lida."""
    junto = " ".join(normalizar(t) for t in textos).replace(" ", "")
    m = re.search(r"LAP\d{1,2}/(\d{2})", junto)
    return int(m.group(1)) if m else None


def _parecido(a: str, b: str) -> bool:
    """a contém b com no máximo 1 erro de OCR (para nomes com 6+ letras)."""
    if b in a:
        return True
    if len(b) < 6:
        return False
    for i in range(0, max(1, len(a) - len(b) + 2)):
        trecho = a[i:i + len(b)]
        if len(trecho) == len(b) and sum(x != y for x, y in zip(trecho, b)) <= 1:
            return True
    return False


def tem_nome(textos: list[str], sobrenome: str) -> bool:
    """Sobrenome completo na tela (a sigla de 3 letras da torre não conta: todos os pilotos estão nela)."""
    alvo = re.sub(r"[^A-Z]", "", normalizar(sobrenome))
    if len(alvo) < 4:
        return False
    return any(_parecido(re.sub(r"[^A-Z]", "", normalizar(t)), alvo) for t in textos)


MARCAS = {
    "replay": r"REPLAY",
    "bandeira_amarela": r"YELLOW\s*FLAG|DOUBLE\s*YELLOW",
    "safety_car": r"SAFETY\s*CAR",
    "vsc": r"VIRTUAL\s*SAFETY",
    "pit": r"IN\s*PIT|PIT\s*STOP|PITLANE|PIT\s*LANE",
    "bandeira_vermelha": r"RED\s*FLAG",
    "chegada": r"CHEQUERED",
}


def marcas(textos: list[str]) -> list[str]:
    junto = " ".join(normalizar(t) for t in textos)
    return [k for k, rx in MARCAS.items() if re.search(rx, junto)]
