# Gera eua.json. Fontes (baixe numa pasta vazia):
#   https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json
#   https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json
# uso: .venv\Scripts\python.exe -I F1\comum\remotion\modelos\geo\preparar_eua.py <pasta_baixada> F1\comum\remotion\modelos\geo\eua.json
# Converte us-atlas 3.0.1 (TopoJSON, Census Bureau cartographic boundaries, domínio público; pacote ISC)
# em geo/eua.json compacto: 48 estados contíguos + DC (anéis externos lon/lat) e os condados de Nevada.
import json, sys

src, dst = sys.argv[1], sys.argv[2]


def decode(topo):
    sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]
    arcs = []
    for a in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def arc(i):
        return arcs[i] if i >= 0 else arcs[~i][::-1]

    def ring(ids):
        out = []
        for i in ids:
            p = arc(i)
            out.extend(p if not out else p[1:])
        return out
    return ring


def dp(pts, tol):
    if len(pts) < 5:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    st = [(0, len(pts) - 1)]
    while st:
        a, b = st.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1; L = (dx * dx + dy * dy) ** 0.5 or 1e-12
        best, bi = -1, -1
        for i in range(a + 1, b):
            x, y = pts[i]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True; st += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def aneis(geom, ring, tol, minimo):
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
    out = []
    for poly in polys:
        r = ring(poly[0])
        xs = [p[0] for p in r]; ys = [p[1] for p in r]
        if (max(xs) - min(xs)) * (max(ys) - min(ys)) < minimo:
            continue  # ilhotas minúsculas
        m = len(r) // 2  # anel fechado: simplifica em duas metades (DP com extremos iguais não guarda nada)
        s = dp(r[:m + 1], tol)[:-1] + dp(r[m:], tol)
        if len(s) >= 4:
            out.append([[round(x, 3), round(y, 3)] for x, y in s])
    return out


FORA = {"02", "15", "60", "66", "69", "72", "78"}
FINOS = {"32", "06", "41", "16", "49", "04"}  # Nevada e vizinhos: mais pontos (zoom no estado)
st = json.load(open(src + "/states-10m.json", encoding="utf-8"))
ring = decode(st)
estados = {}
for g in st["objects"]["states"]["geometries"]:
    if g["id"] in FORA:
        continue
    estados[g["id"]] = {"nome": g["properties"]["name"], "aneis": aneis(g, ring, 0.004 if g["id"] in FINOS else 0.02, 0.002)}
# cor sóbria por estado: vizinhos (que dividem um arco da topologia) nunca com a mesma cor (coloração gulosa)
def arcos(g):
    s = set()
    def walk(x):
        if isinstance(x, int):
            s.add(x if x >= 0 else ~x)
        else:
            for y in x:
                walk(y)
    walk(g["arcs"])
    return s
geo = {g["id"]: arcos(g) for g in st["objects"]["states"]["geometries"] if g["id"] in estados}
viz = {a: {b for b in geo if b != a and geo[a] & geo[b]} for a in geo}
for a in sorted(viz, key=lambda x: -len(viz[x])):
    usadas = {estados[b].get("cor") for b in viz[a]}
    estados[a]["cor"] = next(c for c in range(9) if c not in usadas)
co = json.load(open(src + "/counties-10m.json", encoding="utf-8"))
ring2 = decode(co)
condados = {}
for g in co["objects"]["counties"]["geometries"]:
    if g["id"].startswith("32"):
        condados[g["id"]] = {"nome": g["properties"]["name"], "aneis": aneis(g, ring2, 0.004, 0)}
out = {"fonte": "us-atlas 3.0.1 (US Census Bureau cartographic boundary files 1:10.000.000, domínio público; pacote ISC); anéis externos lon/lat, simplificados (Douglas-Peucker 0,02°; Nevada e vizinhos 0,004°)",
       "estados": estados, "condados_nv": condados}
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(estados), len(condados), sum(len(a) for e in estados.values() for a in e["aneis"]))
