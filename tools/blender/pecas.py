"""Catálogo de peças de carro de F1 (roda dentro do Blender: MCP ou `blender -b -P`).

`aprender(colecao)` lê um carro com as peças NOMEADAS (ex.: ferrari_sf26_v2.glb, que só serve de professor: a malha
dele nunca vai para vídeo) e grava em catalogo_pecas.json onde fica cada peça, num referencial do próprio carro:
  u = posição ao longo do carro (0 = eixo dianteiro, 1 = eixo traseiro; bico < 0, asa traseira > 1),
  v = lado (x dividido pela meia bitola: ±1 = centro das rodas),
  w = altura em diâmetros de roda (0 = chão).
Assim o catálogo vale para qualquer carro, de qualquer tamanho ou escala.

`marcar(colecao)` pega um carro sem nomes (ex.: ferrari_sf26.glb, dividido por material), acha as rodas (referencial),
separa a malha em partes soltas e dá a cada parte o nome da peça que o mapa do catálogo mais indica nos vértices dela.
Resultado: um objeto por peça (asa_dianteira, bico, asa_traseira, roda_de, suspensao_te, halo...), com a cor da peça.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import bmesh
import bpy
import mathutils
import mathutils.bvhtree

CATALOGO = Path(__file__).with_name("catalogo_pecas.json")
PASSO = (0.04, 0.1, 0.08)  # tamanho da célula do mapa em (u, v, w)

# nome da peça no carro professor (sem o sufixo de número do arquivo) → peça do catálogo; canto pelo sufixo LF/RF/LR/RR
REGRAS = [
    (r"^(FRONT_WING|FWING|FRONT_WING_RED)$", "asa_dianteira"),
    (r"^FRONT$", "bico"),  # no professor, "FRONT" é o bico; "NOSE2" é um grupo com a carroceria inteira
    (r"^(DRS\d|DRS3_SUB0|rearwingmoving_top|rearwing_decal)$", "asa_traseira"),
    (r"^HALO", "halo"),
    (r"^EXHAUST", "escapamento"),
    (r"^(FLOOR|WOOD_FLOOR|SQUARE_CARBON)", "assoalho"),
    (r"^(TYRE|RIM|HUB|CALIPER|WHEEL|rim|wheel|hub_caliper)", "roda"),
    (r"^(SUSP|SUS_|suspension)", "suspensao"),
    (r"^wing_mirror", "retrovisor"),
    (r"^(COCKPIT|SEAT|HEADREST|LEG_FOAM|CINTURE|g_Cinture|STEER|SW_|E_Lever|LCD|DISPLAY)", "cockpit"),
    (r"^(ANTENNA|CAMERAS)", "antena"),
    (r"^(CAR_CHASSIS|CAR_CARBON|CAR_DECALS|DRIVER_COLOR|INTERNAL)", "carroceria"),
]
CANTO = {"LF": "de", "FL": "de", "fl": "de", "RF": "dd", "FR": "dd", "fr": "dd",
         "LR": "te", "RL": "te", "rl": "te", "bl": "te", "RR": "td", "rr": "td", "br": "td"}
CORES = {"asa_dianteira": (0.1, 0.55, 1), "bico": (0.55, 0.3, 1), "asa_traseira": (1, 0.75, 0.1), "halo": (1, 0.3, 0.6),
         "escapamento": (1, 0.35, 0.1), "assoalho": (0.35, 0.35, 0.4), "roda": (0.15, 0.15, 0.15), "suspensao": (0.2, 0.9, 0.9),
         "retrovisor": (0.9, 0.9, 0.2), "cockpit": (0.6, 0.9, 0.3), "antena": (1, 1, 1), "carroceria": (0.6, 0.6, 0.6)}


def _base(nome: str) -> str:
    return re.sub(r"(\.\d+)?_\d+$", "", nome)


def _peca(nome: str) -> str | None:
    b = _base(nome)
    for padrao, peca in REGRAS:
        if re.search(padrao, b):
            if peca in ("roda", "suspensao"):
                m = re.search(r"_(LF|RF|LR|RR|FL|FR|RL|fl|fr|rl|rr|bl|br)_?$", b) or re.search(r"(LF|RF|LR|RR)", b)
                return f"{peca}_{CANTO[m.group(1)]}" if m and m.group(1) in CANTO else None
            return peca
    return None


def _nome(o) -> str:
    """Nome da peça: no .glb do Sketchfab a malha se chama Object_N e o nome fica nos pais."""
    while o is not None:
        if not o.name.startswith("Object_"):
            return _base(o.name)
        o = o.parent
    return ""


def _malhas(colecao) -> list:
    return [o for o in colecao.all_objects if o.type == "MESH"]


def _pontos(o, max_n: int = 4000) -> list[mathutils.Vector]:
    mw = o.matrix_world
    vs = o.data.vertices
    passo = max(1, len(vs) // max_n)
    return [mw @ vs[i].co for i in range(0, len(vs), passo)]


class Referencial:
    """Eixo longo do carro, frente, eixos das rodas, bitola e diâmetro da roda → (u, v, w)."""

    def __init__(self, rodas: list[mathutils.Vector], diametro: float, todos: list[mathutils.Vector]):
        xs, ys = [p.x for p in todos], [p.y for p in todos]
        self.longo = 1 if (max(ys) - min(ys)) > (max(xs) - min(xs)) else 0  # eixo do comprimento (0 = x, 1 = y)
        self.lado = 1 - self.longo
        self.z0 = min(p.z for p in todos)
        cs = sorted(rodas, key=lambda r: r[self.longo])
        a = (cs[0][self.longo] + cs[1][self.longo]) / 2
        b = (cs[2][self.longo] + cs[3][self.longo]) / 2
        ext = (max(p[self.longo] for p in todos) - min(p[self.longo] for p in todos)) * 0.06
        alto_a = max((p.z for p in todos if p[self.longo] < a - ext), default=0)
        alto_b = max((p.z for p in todos if p[self.longo] > b + ext), default=0)
        # frente = a ponta mais baixa (atrás fica a asa traseira, alta)
        self.frente, self.tras = (a, b) if alto_a < alto_b else (b, a)
        self.centro_lado = sum(r[self.lado] for r in rodas) / 4
        self.meia_bitola = sum(abs(r[self.lado] - self.centro_lado) for r in rodas) / 4
        self.diametro = diametro
        # lado direito do piloto = v > 0 (frente × cima)
        s = 1 if self.frente > self.tras else -1
        self.sinal = s if self.longo == 1 else -s

    def uvw(self, p) -> tuple[float, float, float]:
        u = (p[self.longo] - self.frente) / (self.tras - self.frente)
        v = self.sinal * (p[self.lado] - self.centro_lado) / self.meia_bitola
        return u, v, (p.z - self.z0) / self.diametro

    def para_json(self) -> dict:
        return {k: getattr(self, k) for k in ("longo", "lado", "frente", "tras", "centro_lado", "meia_bitola", "diametro", "z0", "sinal")}


def _celula(u, v, w) -> str:
    return f"{round(u / PASSO[0])},{round(v / PASSO[1])},{round(w / PASSO[2])}"


def _rodas_por_nome(colecao) -> tuple[list[mathutils.Vector], float]:
    centros, diam = [], []
    for canto in ("LF", "RF", "LR", "RR"):
        pts = [p for o in _malhas(colecao) if re.match(rf"^TYRE_{canto}", _nome(o)) for p in _pontos(o, 3000)]
        if not pts:
            raise RuntimeError(f"pneu {canto} não encontrado no carro professor")
        mn = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        centros.append((mn + mx) / 2)
        diam.append(mx.z - mn.z)
    return centros, sum(diam) / 4


def aprender(colecao) -> dict:
    """Carro professor (peças com nome) → catalogo_pecas.json (mapa célula → votos por peça)."""
    bpy.context.view_layer.update()
    rodas, diam = _rodas_por_nome(colecao)
    todos = [p for o in _malhas(colecao) for p in _pontos(o, 600)]
    ref = Referencial(rodas, diam, todos)
    mapa: dict[str, Counter] = defaultdict(Counter)
    caixas: dict[str, list[float]] = {}
    sem_nome = Counter()
    for o in _malhas(colecao):
        peca = _peca(_nome(o))
        if not peca:
            sem_nome[_nome(o)] += 1
            continue
        for p in _pontos(o):
            u, v, w = ref.uvw(p)
            mapa[_celula(u, v, w)][peca] += 1
            c = caixas.setdefault(peca, [u, u, v, v, w, w])
            c[:] = [min(c[0], u), max(c[1], u), min(c[2], v), max(c[3], v), min(c[4], w), max(c[5], w)]
    cat = {"passo": PASSO, "professor": colecao.name, "referencial": ref.para_json(),
           "caixas": {k: [round(x, 3) for x in c] for k, c in caixas.items()},
           "mapa": {k: dict(c) for k, c in mapa.items()}}
    CATALOGO.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    return {"pecas": sorted(caixas), "celulas": len(mapa), "sem_nome": sem_nome.most_common(12)}


def _ilhas(bm) -> list[list]:
    bm.verts.ensure_lookup_table()
    visto, saida = set(), []
    for v0 in bm.verts:
        if v0.index in visto:
            continue
        pilha, ilha = [v0], []
        visto.add(v0.index)
        while pilha:
            v = pilha.pop()
            ilha.append(v)
            for e in v.link_edges:
                u = e.other_vert(v)
                if u.index not in visto:
                    visto.add(u.index)
                    pilha.append(u)
        saida.append(ilha)
    return saida


def _rodas_por_material(colecao) -> tuple[list[mathutils.Vector], float]:
    """Carro sem nomes: os pneus são o material de banda de rodagem; os 4 cantos saem pelos quadrantes."""
    pts = [p for o in _malhas(colecao) for s in o.material_slots if s.material and re.search(r"tyre_tread|tire_tread|tread", s.material.name, re.I)
           for p in _pontos(o, 20000)]
    if not pts:
        raise RuntimeError("não achei o material do pneu (tread) neste carro")
    mx = max(p.x for p in pts) - min(p.x for p in pts)
    my = max(p.y for p in pts) - min(p.y for p in pts)
    longo, lado = (1, 0) if my > mx else (0, 1)
    ml = (max(p[longo] for p in pts) + min(p[longo] for p in pts)) / 2
    ms = (max(p[lado] for p in pts) + min(p[lado] for p in pts)) / 2
    centros, diam = [], []
    for a in (-1, 1):
        for b in (-1, 1):
            q = [p for p in pts if (p[longo] - ml) * a > 0 and (p[lado] - ms) * b > 0]
            mn = mathutils.Vector((min(p.x for p in q), min(p.y for p in q), min(p.z for p in q)))
            mx_ = mathutils.Vector((max(p.x for p in q), max(p.y for p in q), max(p.z for p in q)))
            centros.append((mn + mx_) / 2)
            diam.append(mx_.z - mn.z)
    return centros, sum(diam) / 4


PESO_CORRECAO = 6  # um exemplo corrigido pelo Felipe vale por vários do professor


def corrigir(colecao, para: str) -> dict:
    """Modo correção: no Edit Mode, o Felipe clica numa face de cada pedaço errado (pode ser em várias peças ao mesmo
    tempo). Cada pedaço é expandido para a parte solta inteira, sai da peça onde estava e vai para `para`
    ("carroceria" = volta para o corpo). A correção entra no catálogo como exemplo: o próximo carro já erra menos."""
    editados = list(bpy.context.objects_in_mode) or []
    if not editados:
        raise RuntimeError("entre no Edit Mode e clique numa face de cada pedaço errado")
    escolhas: dict[str, set[int]] = {}
    for o in editados:
        bm = bmesh.from_edit_mesh(o.data)
        sel = [f for f in bm.faces if f.select]
        if not sel:
            continue
        # expande pela ligação: um clique = a parte solta inteira
        faces, pilha = set(sel), list(sel)
        while pilha:
            f = pilha.pop()
            for v in f.verts:
                for g in v.link_faces:
                    if g not in faces:
                        faces.add(g)
                        pilha.append(g)
        escolhas[o.name] = {f.index for f in faces}
    bpy.ops.object.mode_set(mode="OBJECT")
    if not escolhas:
        raise RuntimeError("nenhuma face selecionada")
    rodas, diam = _rodas_por_material(colecao)
    ref = Referencial(rodas, diam, [p for o in _malhas(colecao) for p in _pontos(o, 600)])
    cat = json.loads(CATALOGO.read_text(encoding="utf-8"))
    exemplos = 0
    pedacos = []
    for nome, ids in escolhas.items():
        o = bpy.data.objects[nome]
        mw = o.matrix_world
        for i in ids:
            for k in o.data.polygons[i].vertices[:: max(1, len(o.data.polygons[i].vertices) // 2)]:
                cel = cat["mapa"].setdefault(_celula(*ref.uvw(mw @ o.data.vertices[k].co)), {})
                cel[para] = cel.get(para, 0) + PESO_CORRECAO
                exemplos += 1
        copia = o.copy()
        copia.data = o.data.copy()
        colecao.objects.link(copia)
        for alvo, manter in ((copia, ids), (o, None)):
            bm = bmesh.new()
            bm.from_mesh(alvo.data)
            bm.faces.ensure_lookup_table()
            fora = [f for f in bm.faces if (f.index not in manter if manter is not None else f.index in ids)]
            bmesh.ops.delete(bm, geom=fora, context="FACES")
            bm.to_mesh(alvo.data)
            bm.free()
        pedacos.append(copia)
    destino = next((o for o in colecao.all_objects if o.type == "MESH" and o.get("peca") == para and o.name == para), None)
    if destino is None and para == "carroceria":
        destino = next((o for o in colecao.all_objects if o.type == "MESH" and o.get("peca") == "carroceria"), None)
    bpy.ops.object.select_all(action="DESELECT")
    for p in pedacos:
        p.select_set(True)
    if destino is not None:
        destino.select_set(True)
        bpy.context.view_layer.objects.active = destino
    else:
        bpy.context.view_layer.objects.active = pedacos[0]
    if len(pedacos) + (destino is not None) > 1:
        bpy.ops.object.join()
    alvo = bpy.context.view_layer.objects.active
    if destino is None:
        alvo.name = alvo.data.name = para
    alvo["peca"] = para
    alvo.color = (*CORES.get(para.split("_")[0] if para.split("_")[0] in CORES else para, (1, 0, 1)), 1)
    cat.setdefault("correcoes", 0)
    cat["correcoes"] += 1
    CATALOGO.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    bpy.ops.object.select_all(action="DESELECT")
    return {"pedacos": sum(len(i) for i in escolhas.values()), "objetos": list(escolhas), "para": para, "exemplos": exemplos}


def marcar(colecao, minimo_votos: int = 2) -> dict:
    """Carro sem nomes → um objeto por peça, pelo catálogo. Parte solta sem voto suficiente fica como carroceria."""
    cat = json.loads(CATALOGO.read_text(encoding="utf-8"))
    mapa = cat["mapa"]
    bpy.context.view_layer.update()
    rodas, diam = _rodas_por_material(colecao)
    todos = [p for o in _malhas(colecao) for p in _pontos(o, 600)]
    ref = Referencial(rodas, diam, todos)
    faces_por: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    originais = _malhas(colecao)
    bms = {}
    adesivos = []  # (objeto, ilha): ganham o nome da peça em que estão colados, na 2ª passada
    for o in originais:
        mw = o.matrix_world
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bms[o.name] = bm
        for ilha in _ilhas(bm):
            votos = Counter()
            passo = max(1, len(ilha) // 60)
            for v in ilha[::passo]:
                u, vv, w = ref.uvw(mw @ v.co)
                cel = mapa.get(_celula(u, vv, w))
                if not cel:  # célula vazia no professor: olha as vizinhas
                    i, j, k = (round(u / PASSO[0]), round(vv / PASSO[1]), round(w / PASSO[2]))
                    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                        cel = mapa.get(f"{i + d[0]},{j + d[1]},{k + d[2]}")
                        if cel:
                            break
                if cel:
                    total = sum(cel.values())
                    for peca, n in cel.items():
                        votos[peca] += n / total
            us = [ref.uvw(mw @ v.co) for v in ilha[::passo]]
            peca = None
            if votos and sum(votos.values()) >= minimo_votos * 0.3:
                melhor, n = votos.most_common(1)[0]
                # mapa dividido entre peças = parte de ligação: fica na carroceria
                peca = melhor if n / sum(votos.values()) >= 0.6 else "carroceria"
            # adesivo é da carroceria onde estiver colado (perto da suspensão, o mapa votaria "suspensão")
            mats = {o.material_slots[f.material_index].material.name.lower() for f in ilha[0].link_faces
                    if f.material_index < len(o.material_slots) and o.material_slots[f.material_index].material}
            if any("decal" in m for m in mats):
                adesivos.append((o, ilha))
                continue
            # regra de forma: alto e atrás do eixo traseiro é asa traseira (no professor as placas laterais vinham na carroceria)
            if peca in (None, "carroceria") and min(u for u, _, _ in us) > 1.03 and min(w for _, _, w in us) > 0.9:
                peca = "asa_traseira"
            if peca is None:
                continue
            if peca == "carroceria":
                continue
            for v in ilha:
                faces_por[peca][o.name].update(v.link_faces)
    # 2ª passada: adesivo fica com a SUPERFÍCIE em que está deitado (distância até as faces de cada peça, carroceria
    # inclusive). Vértice mais próximo não serve: a carroceria tem poucos vértices e o halo muitos, e o adesivo da
    # carroceria ao lado do halo ia para o halo.
    if adesivos:
        de_adesivo = {(o.name, f.index) for o, ilha in adesivos for v in ilha for f in v.link_faces}
        com_peca = {(nome_obj, f.index) for por_obj in faces_por.values() for nome_obj, fs in por_obj.items() for f in fs}
        superficies: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
        for o in originais:
            mw = o.matrix_world
            bm = bms[o.name]
            bm.faces.ensure_lookup_table()
            dono = {}
            for peca, por_obj in faces_por.items():
                for f in por_obj.get(o.name, ()):
                    dono[f.index] = peca
            for f in bm.faces:
                if (o.name, f.index) in de_adesivo:
                    continue
                peca = dono.get(f.index, "carroceria")
                vs, ps = superficies[peca]
                base = len(vs)
                vs += [mw @ v.co for v in f.verts]
                ps.append(list(range(base, base + len(f.verts))))
        arvores = {peca: mathutils.bvhtree.BVHTree.FromPolygons(vs, ps) for peca, (vs, ps) in superficies.items() if ps}
        for o, ilha in adesivos:
            mw = o.matrix_world
            amostra = [mw @ v.co for v in ilha[::max(1, len(ilha) // 10)]]
            dist = {}
            for peca, arv in arvores.items():
                ds = [arv.find_nearest(pt, 0.05)[3] for pt in amostra]
                ds = [d for d in ds if d is not None]
                if len(ds) >= len(amostra) * 0.6:
                    dist[peca] = sum(ds) / len(ds)
            if dist:
                peca = min(dist, key=dist.get)
                if peca != "carroceria":
                    for v in ilha:
                        faces_por[peca][o.name].update(v.link_faces)
    # cada peça vira um objeto (as faces saem do original, com material e UV)
    criados = Counter()
    for peca, por_obj in faces_por.items():
        novos = []
        for nome_obj, fs in por_obj.items():
            o = bpy.data.objects[nome_obj]
            bm = bms[nome_obj]
            copia = o.copy()
            copia.data = o.data.copy()
            colecao.objects.link(copia)
            bc = bmesh.new()
            bc.from_mesh(copia.data)
            bc.faces.ensure_lookup_table()
            ids = {f.index for f in fs}
            bmesh.ops.delete(bc, geom=[f for f in bc.faces if f.index not in ids], context="FACES")
            bc.to_mesh(copia.data)
            bc.free()
            novos.append(copia)
            criados[peca] += len(ids)
        bpy.ops.object.select_all(action="DESELECT")
        for n in novos:
            n.select_set(True)
        bpy.context.view_layer.objects.active = novos[0]
        if len(novos) > 1:
            bpy.ops.object.join()
        alvo = bpy.context.view_layer.objects.active
        alvo.name = peca
        alvo.data.name = peca
        alvo["peca"] = peca
        alvo.color = (*CORES.get(peca.split("_")[0] if peca.split("_")[0] in CORES else peca, (1, 0, 1)), 1)
    # o que virou peça sai dos objetos originais
    for nome_obj, bm in bms.items():
        tirar = set()
        for por_obj in faces_por.values():
            tirar |= {f.index for f in por_obj.get(nome_obj, ())}
        if tirar:
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in tirar], context="FACES")
            bm.to_mesh(bpy.data.objects[nome_obj].data)
        bm.free()
    for o in originais:
        o.color = (*CORES["carroceria"], 1)
        o["peca"] = "carroceria"
    bpy.ops.object.select_all(action="DESELECT")
    return {"faces_por_peca": dict(criados), "referencial": ref.para_json()}
