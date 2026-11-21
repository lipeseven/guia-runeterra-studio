"""Teste Blender: Hamilton (classificação 11408, volta 12) no S do Senna, no mod vhe_interlagos do Assetto Corsa.

Roda DENTRO do Blender (5.3), sobre a CÓPIA da cena do Felipe com o mod importado pelo KN5 Tools:
  blender -b F1/dados/testes_vhe/interlagos_vhe_full.blend --python F1/horizontal/blender/senna.py -- [opções]
Opções (depois de "--"):
  --motor eevee|cycles   --pct 50 (resolução, % de 1920x1080)   --quadros 1,200,300 | 1-480 | todos
  --amostras N (EEVEE: TAA; Cycles: amostras)   --saida <pasta>   --salvar <arquivo.blend> (salva a cena montada)
  --sem-desfoque (sem motion blur)   --dados (grava dados_quadros.json para a camada de dados no Remotion)
O carro anda no TRAÇADO do kit/gps (voltas/11408_44_12_Interlagos_vhe_ideal.json): posição ao longo da pista = relógio
s(t) do OpenF1 (GPS + telemetria); lateral = linha ideal do próprio mod (INFERIDA, o OpenF1 não mede lateral).
Altura, arfagem e rolagem do carro vêm de raios verticais nas 4 rodas contra as malhas de física (1road/1kerb/1curb/...).
"""
import bpy, bmesh, json, math, os, re, sys, time
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

AQUI = os.path.dirname(os.path.abspath(__file__))
F1 = os.path.dirname(os.path.dirname(AQUI))
VOLTA = os.path.join(F1, "horizontal", "kit", "gps", "voltas", "11408_44_12_Interlagos_vhe_ideal.json")


def achar_dados():
    p = AQUI
    while True:
        c = os.path.join(p, "F1", "dados")
        if os.path.isdir(os.path.join(c, "modelos3d")):
            return c
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit("não achei F1/dados")
        p = q


DADOS = achar_dados()
def _achar_modelo(nome):
    """Acha o .glb em modelos3d ou em qualquer subpasta (carros/, pistas/...)."""
    raiz = os.path.join(DADOS, "modelos3d")
    for pasta, _, arqs in os.walk(raiz):
        if nome in arqs:
            return os.path.join(pasta, nome)
    return os.path.join(raiz, nome)


CARRO_GLB = _achar_modelo("ferrari_sf26.glb")

FPS = 60
T0 = 2.0            # tempo de volta no quadro 1 (s depois da linha de chegada: reta dos boxes, antes da freada)
N_QUADROS = 480     # 8 s a 60 q/s
# cortes (quadro inicial, nome da câmera)
CORTES = [(1, "cam_transmissao"), (241, "cam_zebra"), (349, "cam_onboard")]
COMPRIMENTO = 5.4   # m (mesmo tamanho do carro nas cenas three.js)
OB = (0.35, -0.05)   # câmera onboard: (adiante, acima) do topo da tomada de ar (o modelo não tem piloto)


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = dict(motor="eevee", pct=50, quadros="1,120,216,260,300,400", amostras=None, saida=None, salvar=None,
             desfoque=True, dados=False, versao="v", sol_elev=26.0, sol_azim=-35.0, sol=6.0, ceu=0.12, ceu_cam=0.3, asf=2.0,
             exposicao=0.0, esconder="")
    i = 0
    while i < len(a):
        k = a[i]
        if k == "--sem-desfoque": o["desfoque"] = False
        elif k == "--dados": o["dados"] = True
        else:
            o[k[2:]] = a[i + 1]; i += 1
        i += 1
    return o


# ---------------------------------------------------------------- volta (porta do kit/gps/src/gps.js)
def carregar_volta():
    v = json.load(open(VOLTA, encoding="utf-8"))
    R, C = v["relogio"], v["caminho"]
    S, dt, t0 = R["s"], R["dt"], R["t0"]
    n = len(S)
    d = [(S[i + 1] - S[i]) / dt for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        a, b = d[i - 1], d[i]
        m[i] = 0.0 if a * b <= 0 else 2 * a * b / (a + b)
    tfim = t0 + (n - 1) * dt

    def s(t):
        tt = min(tfim, max(t0, t))
        x = (tt - t0) / dt
        i = min(n - 2, max(0, int(math.floor(x))))
        u = x - i
        h00 = (1 + 2 * u) * (1 - u) ** 2; h10 = u * (1 - u) ** 2; h01 = u * u * (3 - 2 * u); h11 = u * u * (u - 1)
        return h00 * S[i] + h10 * dt * m[i] + h01 * S[i + 1] + h11 * dt * m[i + 1]

    # caminho em coordenadas do Blender: kit (glTF, Y para cima) -> Blender (x, -z, y) — o mesmo giro do KN5 Tools
    X = [Vector((x, -z, y)) for x, y, z in zip(C["x"], C["y"], C["z"])]
    ds = C["ds"]

    def p(sv):
        x = min(len(X) - 1.0, max(0.0, sv / ds))
        i = min(len(X) - 2, int(math.floor(x)))
        return X[i].lerp(X[i + 1], x - i)

    L = v["lateral"]

    def lat(sv):
        x = min(len(X) - 1.0, max(0.0, sv / ds)); i = min(len(X) - 2, int(x)); f = x - i
        g = lambda arr: (arr[i] if arr[i] is not None else float("nan")) * (1 - f) + (arr[i + 1] if arr[i + 1] is not None else float("nan")) * f
        return dict(borda_esq=g(L["borda_esq"]), borda_dir=g(L["borda_dir"]), zebra=g(L["zebra"]), fora_asfalto=g(L["fora_asfalto"]))

    return v, s, p, lat


def rumo(p, sv, meio=3.0):
    d = p(sv + meio) - p(sv - meio)
    d.z = 0
    return d.normalized()


def curvatura(p, sv):
    a, b = rumo(p, sv - 2.5), rumo(p, sv + 2.5)
    ang = math.atan2(a.x * b.y - a.y * b.x, a.dot(b))
    return ang / 5.0   # 1/m, + = para a esquerda


# ---------------------------------------------------------------- cena
def preparar_pista(cena, ganho_asf=2.0):
    """Esconde o que não é visual no AC e acerta materiais (PBR) — sem apagar nada da cópia."""
    escondidos = 0
    for c in bpy.data.collections:
        if c.name in ("VHE_obj_collider",):
            c.hide_render = True
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        mats = [m.name for m in o.data.materials if m]
        if "COLLIDER" in mats or re.match(r"^1wall_collider", o.name, re.I):
            o.hide_render = True; o.hide_viewport = True; escondidos += 1
    asf = 0
    precisa = set()
    for m in bpy.data.materials:
        if m.get("kn5_shader", "").startswith("ksMultilayer"):
            dt_ = json.loads(m.get("kn5_textures", "{}")).get("txDetailR")
            if dt_:
                precisa.add(dt_)
    caminhos = texturas_kn5(sorted(precisa))
    for m in bpy.data.materials:
        sh = m.get("kn5_shader", "")
        if not m.node_tree:
            continue
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not b:
            continue
        nome = m.name.upper()
        if sh.startswith("ksMultilayer"):
            asf += 1
            grama = nome.startswith(("GRASS", "SANDGRASS", "SANDA"))
            pintado = nome in ("RDILE", "RDILF", "RDILG", "RDILYL", "RDILKG", "RDILYG")   # escapes pintados (verde/amarelo)
            multicamada(m, caminhos, ganho=2.6 if grama else ganho_asf, satur=0.55 if pintado else (1.15 if grama else 1.0))
            b.inputs["Metallic"].default_value = 0.0
            if "Specular IOR Level" in b.inputs:
                b.inputs["Specular IOR Level"].default_value = 0.2 if grama else 0.3
            if grama:
                if b.inputs["Roughness"].is_linked:
                    nt = m.node_tree; nt.links.remove(b.inputs["Roughness"].links[0])
                b.inputs["Roughness"].default_value = 0.95
            for n in m.node_tree.nodes:
                if n.type == "NORMAL_MAP":
                    n.inputs["Strength"].default_value = 0.6
        elif nome in ("GROOVE", "MARBLES"):   # camadas de borracha por cima do asfalto: escuras e foscas
            # no Cycles a cor do .dds (via KN5 Tools) sai clara e cobre a pista toda (no EEVEE a camada coplanar quase
            # não aparece): borracha = cor fixa escura (média real da textura: 0,22/0,14), alfa da própria textura
            bc = b.inputs["Base Color"]
            if bc.is_linked:
                m.node_tree.links.remove(bc.links[0])
            bc.default_value = (0.035, 0.035, 0.035, 1) if nome == "GROOVE" else (0.02, 0.02, 0.02, 1)
            b.inputs["Roughness"].default_value = 0.85
            if "Specular IOR Level" in b.inputs:
                b.inputs["Specular IOR Level"].default_value = 0.15
        elif sh == "ksTree" or nome.startswith(("TREE", "BUSH")):
            b.inputs["Roughness"].default_value = 0.85
            m.surface_render_method = "DITHERED"
            if "Subsurface Weight" in b.inputs:   # folhas: um pouco de luz atravessando
                b.inputs["Transmission Weight"].default_value = 0.0
        else:
            r = b.inputs["Roughness"]
            if not r.is_linked and r.default_value < 0.25 and b.inputs["Metallic"].default_value < 0.5:
                r.default_value = 0.45
    return dict(escondidos=escondidos, materiais_asfalto=asf)


MOD = r"C:\Users\Felipe\Downloads\vhe_interlagos"


def texturas_kn5(nomes):
    """Extrai do .kn5 as texturas que o KN5 Tools não ligou (máscara/detalhes do ksMultilayer) -> .dds em cache."""
    pasta = os.path.join(DADOS, "testes_vhe", "blender_senna", "kn5_tex")
    os.makedirs(pasta, exist_ok=True)
    faltam = [n for n in nomes if not os.path.exists(os.path.join(pasta, n))]
    if faltam:
        sys.path.insert(0, os.path.join(F1, "horizontal", "kit", "gps", "py"))
        import assetto
        for k in sorted(os.listdir(MOD)):
            if k.lower().endswith(".kn5"):
                d = assetto.ler_kn5(os.path.join(MOD, k))
                for n in faltam:
                    if n in d["texturas"] and not os.path.exists(os.path.join(pasta, n)):
                        open(os.path.join(pasta, n), "wb").write(d["texturas"][n])
    return {n: os.path.join(pasta, n) for n in nomes if os.path.exists(os.path.join(pasta, n))}


def multicamada(m, caminhos, ganho=2.0, satur=1.0):
    """ksMultilayer do AC: cor = txDiffuse x detalhe (UV x multR) x ksDiffuse x ganho. O alfa do txDiffuse é máscara de
    brilho (NÃO transparência): vira rugosidade. A máscara do mod (txMask) vem vazia no Pillow/Blender (lida como 0),
    então só o detalhe R entra (nas pistas deste mod R=G=B na maioria)."""
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bc = b.inputs["Base Color"]
    if not bc.is_linked:
        return False
    dif = bc.links[0].from_node
    if dif.type != "TEX_IMAGE":
        return False
    tex = json.loads(m.get("kn5_textures", "{}"))
    props = json.loads(m.get("kn5_properties", "{}"))
    det = tex.get("txDetailR")
    mult = props.get("multR", 1.0) or 1.0
    kd = props.get("ksDiffuse", 0.4)
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (mult, mult, 1)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    cor = dif.outputs["Color"]
    if det and det in caminhos:
        td = nt.nodes.new("ShaderNodeTexImage")
        td.image = bpy.data.images.load(caminhos[det], check_existing=True)
        nt.links.new(mp.outputs["Vector"], td.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
        mx.inputs[0].default_value = 1.0
        nt.links.new(cor, mx.inputs[6]); nt.links.new(td.outputs["Color"], mx.inputs[7])
        cor = mx.outputs[2]
    g = nt.nodes.new("ShaderNodeMix"); g.data_type = "RGBA"; g.blend_type = "MULTIPLY"
    g.inputs[0].default_value = 1.0
    v = kd * ganho
    g.inputs[7].default_value = (v, v, v, 1)
    nt.links.new(cor, g.inputs[6])
    cor = g.outputs[2]
    if satur != 1.0:
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = satur
        nt.links.new(cor, hs.inputs["Color"]); cor = hs.outputs["Color"]
    nt.links.new(cor, bc)
    # alfa do diffuse = máscara de brilho do AC -> rugosidade 0,78 (fosco) .. 0,45 (polido pelos pneus)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.88
    mr.inputs["To Max"].default_value = 0.62
    nt.links.new(dif.outputs["Alpha"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return True


def bvh_superficies():
    verts, polys = [], []
    nomes = []
    for o in bpy.data.objects:
        if o.type == "MESH" and re.match(r"^1(road|kerb|curb|grass|outer|sand|pitlane)", o.name, re.I):
            mw = o.matrix_world
            base = len(verts)
            verts += [mw @ v.co for v in o.data.vertices]
            polys += [[base + i for i in p.vertices] for p in o.data.polygons]
            nomes.append(o.name)
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), nomes


def chao(bvh, xy, z_ref):
    hit = bvh.ray_cast(Vector((xy.x, xy.y, z_ref + 4.0)), Vector((0, 0, -1)), 12.0)
    return hit[0].z if hit[0] is not None else None


def importar_carro(cena):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=CARRO_GLB)
    novos = [o for o in bpy.data.objects if o not in antes]
    malhas = [o for o in novos if o.type == "MESH"]
    col = bpy.data.collections.new("CARRO_HAM")
    cena.collection.children.link(col)
    for o in novos:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    # assa transformações e junta tudo num objeto
    for o in novos:
        o.select_set(False)
    for o in malhas:
        if o.data.users > 1:
            o.data = o.data.copy()
    vazios = [o.name for o in novos if o.type != "MESH"]
    bpy.context.view_layer.objects.active = malhas[0]
    for o in malhas:
        o.select_set(True)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    corpo = bpy.context.view_layer.objects.active
    corpo.name = "HAM_corpo"
    for n in vazios:
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n])
    me = corpo.data
    # comprimento no eixo Y
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    if (max(xs) - min(xs)) > (max(ys) - min(ys)):
        me.transform(Matrix.Rotation(math.pi / 2, 4, "Z"))
    ys = [v.co.y for v in me.vertices]; xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    k = COMPRIMENTO / (max(ys) - min(ys))
    me.transform(Matrix.Scale(k, 4) @ Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, -min(zs))))
    roda_re = re.compile(r"tyre|tire|wheel_hub|disc|rim", re.I)
    idx_roda = {i for i, m in enumerate(me.materials) if m and roda_re.search(m.name)}

    def alto(y0, y1):
        mm = 0
        for p in me.polygons:
            if p.material_index in idx_roda:
                continue
            for vi in p.vertices:
                c = me.vertices[vi].co
                if y0 < c.y < y1:
                    mm = max(mm, c.z)
        return mm
    if alto(-2.7, -2.0) < alto(2.0, 2.7):   # frente = ponta mais baixa; queremos a frente em +Y
        me.transform(Matrix.Rotation(math.pi, 4, "Z"))
    me.update()
    # rodas: separa as faces de roda por canto
    rodas = {}
    for canto in ("ED", "DD", "ET", "DT"):   # E/D = esquerda/direita, D/T = dianteira/traseira
        bpy.ops.object.select_all(action="DESELECT")
        corpo.select_set(True); bpy.context.view_layer.objects.active = corpo
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(corpo.data)
        n = 0
        for f in bm.faces:
            c = f.calc_center_median()
            ok = f.material_index in idx_roda and ((c.x < 0) == (canto[0] == "E")) and ((c.y > 0) == (canto[1] == "D"))
            f.select_set(ok); n += ok
        bmesh.update_edit_mesh(corpo.data)
        if n:
            bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        if n:
            novo = [o for o in bpy.context.selected_objects if o != corpo][0]
            novo.name = f"HAM_roda_{canto}"
            bpy.ops.object.select_all(action="DESELECT")
            novo.select_set(True); bpy.context.view_layer.objects.active = novo
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
            rodas[canto] = novo
    raiz = bpy.data.objects.new("HAM_carro", None)
    col.objects.link(raiz)
    corpo.parent = raiz
    info = {}
    for canto, r in rodas.items():
        dims = r.dimensions
        info[canto] = dict(centro=list(r.location), raio=dims.z / 2)
        if canto[1] == "D":
            piv = bpy.data.objects.new(f"HAM_esterco_{canto}", None)
            col.objects.link(piv)
            piv.location = r.location.copy()
            piv.parent = raiz
            r.parent = piv
            r.location = (0, 0, 0)
        else:
            r.parent = raiz
    # pintura: verniz (coat) por cima da textura da Ferrari
    for m in corpo.data.materials:
        if m and m.node_tree and re.search(r"paint", m.name, re.I):
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if b:
                b.inputs["Metallic"].default_value = 0.25
                b.inputs["Roughness"].default_value = 0.22
                if "Coat Weight" in b.inputs:
                    b.inputs["Coat Weight"].default_value = 1.0
                    b.inputs["Coat Roughness"].default_value = 0.03
    # cabeça do piloto (para a câmera onboard)
    cab = None
    idx_pil = {i for i, m in enumerate(corpo.data.materials) if m and re.search(r"driver|helmet|casco", m.name, re.I)}
    if idx_pil:
        pts = [corpo.data.vertices[vi].co for p in corpo.data.polygons if p.material_index in idx_pil for vi in p.vertices]
        if pts:
            cab = sum(pts, Vector()) / len(pts)
            cab.z = max(q.z for q in pts)
    info["cabeca"] = list(cab) if cab else None
    xs = [v.co.x for v in corpo.data.vertices]
    info["largura"] = max(xs) - min(xs)
    return raiz, corpo, rodas, info


def luz_e_ceu(cena, sol_elev=26.0, sol_azim=-35.0, forca_sol=6.0, forca_ceu=0.12, forca_ceu_cam=0.3):
    w = bpy.data.worlds.new("ceu_senna")
    cena.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(sol_elev)
    sky.sun_rotation = math.radians(sol_azim)
    sky.altitude = 760.0        # Interlagos ~760 m
    sky.air_density = 1.0
    sky.aerosol_density = 1.0
    # o céu ilumina pouco (sombras com contraste, como no sol forte da referência), mas aparece mais claro na câmera
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = forca_ceu
    bgc = nt.nodes.new("ShaderNodeBackground")
    bgc.inputs["Strength"].default_value = forca_ceu_cam
    lp = nt.nodes.new("ShaderNodeLightPath")
    mx = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(sky.outputs["Color"], bgc.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    nt.links.new(bg.outputs["Background"], mx.inputs[1])
    nt.links.new(bgc.outputs["Background"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    w.mist_settings.start = 120.0
    w.mist_settings.depth = 1500.0
    w.mist_settings.falloff = "LINEAR"
    # sol (mesma direção do sol do céu): sombras suaves (ângulo 1,2°)
    sd = bpy.data.lights.new("sol", "SUN")
    sd.energy = forca_sol
    sd.angle = math.radians(1.2)
    sd.color = (1.0, 0.95, 0.88)
    sol = bpy.data.objects.new("sol", sd)
    cena.collection.objects.link(sol)
    # Blender: sky sun_rotation 0 = sol no +Y; luz aponta para -Z local
    el, az = math.radians(sol_elev), math.radians(sol_azim)
    d = Vector((-math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))  # direção PARA o sol
    sol.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    for o in bpy.data.objects:   # luz/câmera antigas da cena importada ficam desligadas
        if o.type == "LIGHT" and o != sol:
            o.hide_render = True
    return sol


def compositor(cena, bloom=0.18, nevoa=0.10):
    cena.view_layers[0].use_pass_mist = True
    ng = bpy.data.node_groups.new("comp_senna", "CompositorNodeTree")
    cena.compositing_node_group = ng
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    out = ng.nodes.new("NodeGroupOutput")
    # névoa de distância (perspectiva aérea) pela passagem de mist
    cor = ng.nodes.new("CompositorNodeRGB")
    cor.outputs[0].default_value = (0.62, 0.72, 0.86, 1.0)
    mapa = ng.nodes.new("ShaderNodeMapRange")
    mapa.inputs["To Max"].default_value = nevoa
    mix = ng.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    ng.links.new(rl.outputs["Mist"], mapa.inputs["Value"])
    ng.links.new(mapa.outputs["Result"], mix.inputs[0])
    ng.links.new(rl.outputs["Image"], mix.inputs[6])
    ng.links.new(cor.outputs[0], mix.inputs[7])
    gl = ng.nodes.new("CompositorNodeGlare")
    gl.inputs["Type"].default_value = "Bloom"
    gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = 0.9
    gl.inputs["Strength"].default_value = bloom
    gl.inputs["Size"].default_value = 0.6
    ng.links.new(mix.outputs[2], gl.inputs["Image"])
    ln = ng.nodes.new("CompositorNodeLensdist")   # leve aberração cromática de lente
    ln.inputs["Dispersion"].default_value = 0.004
    ln.inputs["Distortion"].default_value = 0.0
    ng.links.new(gl.outputs["Image"], ln.inputs["Image"])
    ng.links.new(ln.outputs["Image"], out.inputs[0])


def camera(cena, nome, lente, fstop=None, foco=None):
    cd = bpy.data.cameras.new(nome)
    cd.lens = lente
    cd.clip_start = 0.05
    cd.clip_end = 4000
    cd.sensor_width = 36
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        if isinstance(foco, (int, float)):
            cd.dof.focus_distance = foco
        elif foco is not None:
            cd.dof.focus_object = foco
    c = bpy.data.objects.new(nome, cd)
    cena.collection.objects.link(c)
    return c


def olhar(obj, de, para, rolar=0.0):
    q = (para - de).to_track_quat("-Z", "Y")
    if rolar:
        q = q @ Quaternion((0, 0, 1), rolar)
    obj.location = de
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = q


# ---------------------------------------------------------------- animação
def animar(cena, s, p, lat, bvh, raiz, rodas, info, cams):
    cab, cze, cob = cams
    eixo = abs(info["ED"]["centro"][1] - info["ET"]["centro"][1]) if "ED" in info and "ET" in info else 3.6
    bitola = abs(info["ED"]["centro"][0] - info["DD"]["centro"][0]) if "ED" in info and "DD" in info else 1.6
    raio_d = info.get("ED", {}).get("raio", 0.36); raio_t = info.get("ET", {}).get("raio", 0.36)
    y_d = info["ED"]["centro"][1] if "ED" in info else 1.8
    y_t = info["ET"]["centro"][1] if "ET" in info else -1.8
    giro_d = giro_t = 0.0
    dt = 1.0 / FPS
    raiz.rotation_mode = "QUATERNION"
    q_ant = None
    dados = []
    hist_z = []
    # posição fixa da câmera da zebra: por dentro do ápice do S 1 (zebra à esquerda), depois do ápice, olhando para trás
    s_cam = s(T0 + (CORTES[2][0] - 1) / FPS) + 10.0
    f_cam = rumo(p, s_cam)
    esq_cam = Vector((-f_cam.y, f_cam.x, 0))
    pc = p(s_cam) + esq_cam * (lat(s_cam)["borda_esq"] + 1.2)
    zc = chao(bvh, pc, pc.z)
    pc.z = (zc if zc is not None else pc.z) + 0.32
    for q in range(-2, N_QUADROS + 3):
        f = q + 1
        t = T0 + (f - 1) / FPS
        sv = s(t)
        v = (s(t + 0.004) - s(t - 0.004)) / 0.008
        c = p(sv)
        fw = rumo(p, sv)
        esq = Vector((-fw.y, fw.x, 0))
        hs = {}
        for canto, yy in (("ED", y_d), ("DD", y_d), ("ET", y_t), ("DT", y_t)):
            xx = -bitola / 2 if canto[0] == "E" else bitola / 2
            pt = c + fw * yy - esq * xx   # x local + = direita = -esq
            h = chao(bvh, pt, c.z)
            hs[canto] = h if h is not None else c.z
        zf = (hs["ED"] + hs["DD"]) / 2; zt = (hs["ET"] + hs["DT"]) / 2
        ze = (hs["ED"] + hs["ET"]) / 2; zd = (hs["DD"] + hs["DT"]) / 2
        arf = math.atan2(zf - zt, eixo)
        rol = math.atan2(ze - zd, bitola)
        zc_ = (zf * (-y_t) + zt * y_d) / (y_d - y_t)   # altura no centro (origem do carro)
        hist_z.append(zc_)
        yaw = math.atan2(-fw.x, fw.y)
        rot = (Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(arf, 4, "X") @ Matrix.Rotation(rol, 4, "Y")).to_quaternion()
        if q_ant is not None and rot.dot(q_ant) < 0:
            rot.negate()
        q_ant = rot
        raiz.location = Vector((c.x, c.y, zc_ + 0.005))
        raiz.rotation_quaternion = rot
        raiz.keyframe_insert("location", frame=f); raiz.keyframe_insert("rotation_quaternion", frame=f)
        # rodas: giro pela velocidade, esterço pela curvatura do traçado (Ackermann simples)
        giro_d -= v * dt / raio_d; giro_t -= v * dt / raio_t
        k = curvatura(p, sv)
        ester = math.atan(eixo * k)
        for canto, r in rodas.items():
            r.rotation_mode = "XYZ"
            r.rotation_euler = (giro_d if canto[1] == "D" else giro_t, 0, 0)
            r.keyframe_insert("rotation_euler", index=0, frame=f)
            if canto[1] == "D":
                r.parent.rotation_euler = (0, 0, ester)
                r.parent.keyframe_insert("rotation_euler", index=2, frame=f)
        # câmera de transmissão (alta, atrás e à esquerda): rumo médio dos últimos 0,6 s, altura do caminho (sem tremor)
        fx = Vector()
        for j in range(12):
            fx += rumo(p, s(t - 0.6 * j / 11))
        fx.z = 0; fx.normalize()
        ex = Vector((-fx.y, fx.x, 0))
        base = p(sv)
        olhar(cab, base - fx * 11.5 + ex * 2.0 + Vector((0, 0, 3.4)), base + fx * 9.0 + Vector((0, 0, 0.1)))
        cab.keyframe_insert("location", frame=f); cab.keyframe_insert("rotation_quaternion", frame=f)
        # câmera baixa da zebra: parada, acompanha o carro (alvo com 40 ms de atraso, como um operador)
        alvo = p(s(t - 0.04)); alvo.z = zc_ + 0.45
        olhar(cze, pc, alvo)
        cze.keyframe_insert("rotation_quaternion", frame=f)
        lt = lat(sv)
        dados.append(dict(quadro=f, t_volta=round(t, 4), s=round(sv, 3), vel_kmh=round(v * 3.6, 2), esterco_graus=round(math.degrees(ester), 2),
                          **{k2: (None if vv != vv else round(vv, 3)) for k2, vv in lt.items()},
                          camera=[n for (q0, n) in CORTES if q0 <= f][-1] if f >= 1 else CORTES[0][1]))
    # câmera onboard presa ao carro (T-cam atrás da cabeça do piloto, como na referência)
    cab_p = Vector(info["cabeca"]) if info.get("cabeca") else Vector((0, -0.2, 1.0))
    cob.parent = raiz
    olhar(cob, Vector((0, cab_p.y + float(OB[0]), cab_p.z + float(OB[1]))), Vector((0, cab_p.y + 12.0, cab_p.z - 0.55)))
    # interpolação linear (60 q/s amostrado; o motion blur usa as sub-posições entre quadros)
    for ob in [raiz, cab, cze] + list(rodas.values()) + [r.parent for c_, r in rodas.items() if c_[1] == "D"]:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in iter_fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    for q0, nome in CORTES:
        mk = cena.timeline_markers.new(nome, frame=q0)
        mk.camera = bpy.data.objects[nome]
    cena.camera = bpy.data.objects[CORTES[0][1]]
    return dados, dict(eixo=eixo, bitola=bitola, raio_d=raio_d, raio_t=raio_t, cam_zebra=list(pc))


def iter_fcurves(action):
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        yield from action.fcurves
        return
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def config_render(cena, o):
    r = cena.render
    r.resolution_x, r.resolution_y = 1920, 1080
    r.resolution_percentage = int(o["pct"])
    r.fps = FPS
    cena.frame_start, cena.frame_end = 1, N_QUADROS
    r.use_motion_blur = o["desfoque"]
    r.motion_blur_shutter = 0.5   # 180°
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "8"
    r.film_transparent = False
    cena.view_settings.view_transform = "AgX"
    try:
        cena.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    cena.view_settings.exposure = float(o["exposicao"])
    if o["motor"] == "cycles":
        r.engine = "CYCLES"
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type in ("OPTIX",)
        cena.cycles.device = "GPU"
        cena.cycles.samples = int(o["amostras"] or 32)
        cena.cycles.use_adaptive_sampling = True
        cena.cycles.adaptive_threshold = 0.05
        cena.cycles.use_denoising = True
        cena.cycles.denoiser = "OPTIX"
        cena.cycles.max_bounces = 4
        cena.cycles.diffuse_bounces = 2
        cena.cycles.glossy_bounces = 2
        cena.cycles.transparent_max_bounces = 8
        cena.cycles.use_fast_gi = False
        r.use_persistent_data = True   # mantém BVH/texturas entre quadros (a cena do mod é pesada)
    else:
        r.engine = "BLENDER_EEVEE"
        e = cena.eevee
        e.taa_render_samples = int(o["amostras"] or 24)
        e.use_raytracing = True
        e.ray_tracing_method = "SCREEN"
        e.use_fast_gi = True
        e.fast_gi_method = "GLOBAL_ILLUMINATION"
        e.fast_gi_distance = 6.0
        e.use_shadows = True
        e.shadow_ray_count = 2
        e.shadow_step_count = 6
        e.shadow_resolution_scale = 1.0
        e.motion_blur_steps = 1
        e.motion_blur_max = 64
        cena.world.sun_threshold = 1000.0   # o sol vem da lâmpada, não do céu


def lista_quadros(txt):
    if txt == "todos":
        return list(range(1, N_QUADROS + 1))
    out = []
    for parte in txt.split(","):
        if "-" in parte:
            a, b = parte.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(parte))
    return out


def main():
    o = args()
    t_ini = time.time()
    cena = bpy.context.scene
    v, s, p, lat = carregar_volta()
    rel = preparar_pista(cena, float(o["asf"]))
    if o["motor"] == "cycles" and not o["esconder"]:
        # bug visto no Cycles: as camadas coplanares de borracha (obj_groove) clareiam a pista inteira (azul-claro),
        # mesmo com cor escura; no EEVEE quase não aparecem (perdem no teste de profundidade). Sem elas a pista fica certa.
        o["esconder"] = "^(Groove|Marbles)$"
    if o["esconder"]:
        for ob in bpy.data.objects:
            if re.search(o["esconder"], ob.name, re.I):
                ob.hide_render = True
    bvh, nomes = bvh_superficies()
    raiz, corpo, rodas, info = importar_carro(cena)
    luz_e_ceu(cena, float(o["sol_elev"]), float(o["sol_azim"]), float(o["sol"]), float(o["ceu"]), float(o["ceu_cam"]))
    cab = camera(cena, "cam_transmissao", 40, fstop=4.0, foco=raiz)
    cze = camera(cena, "cam_zebra", 85, fstop=2.0, foco=raiz)
    cob = camera(cena, "cam_onboard", 20, fstop=8.0, foco=14.0)
    dados, geo = animar(cena, s, p, lat, bvh, raiz, rodas, info, (cab, cze, cob))
    compositor(cena)
    config_render(cena, o)
    t_mont = time.time() - t_ini
    saida = o["saida"] or os.path.join(DADOS, "testes_vhe", "blender_senna", o["versao"])
    os.makedirs(saida, exist_ok=True)
    rel_txt = dict(montagem_s=round(t_mont, 1), pista=rel, superficies_raycast=len(nomes), carro=info, geo=geo, motor=o["motor"],
                   pct=o["pct"], amostras=o["amostras"], desfoque=o["desfoque"])
    if o["dados"]:
        json.dump(dict(fonte=v["fonte"], lateral_fonte=v["lateral"]["fonte"], lateral_medida=v["lateral"]["medida"], fps=FPS,
                       t0_volta=T0, cortes=CORTES, quadros=dados), open(os.path.join(saida, "dados_quadros.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
    if o["salvar"]:
        bpy.ops.wm.save_as_mainfile(filepath=o["salvar"], copy=True)
    tempos = {}
    for f in lista_quadros(o["quadros"]):
        cena.frame_set(f)
        cena.render.filepath = os.path.join(saida, f"{f:04d}.png")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        tempos[f] = round(time.time() - t1, 2)
        print(f"QUADRO {f} {tempos[f]} s", flush=True)
    rel_txt["tempos_s"] = tempos
    json.dump(rel_txt, open(os.path.join(saida, f"relatorio_{o['motor']}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("FIM", json.dumps({k: rel_txt[k] for k in ("montagem_s", "pista", "geo")}), flush=True)


main()
