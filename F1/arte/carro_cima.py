"""Carro de F1 visto de cima, desenhado no VectorCraft pelo servidor MCP. Pintura do canal (petróleo, creme e coral).
Uso: python carro_cima.py <vectorcraft-cli.exe> <pasta de saída> [nome] [cor base] [clara] [escura] [faixa] [acento] [--comparar]
Só precisa da biblioteca padrão. Grava carro_cima.vectorcraft, .svg e .png.
"""
import json
import subprocess
import sys
from pathlib import Path

cli, saida = sys.argv[1], Path(sys.argv[2])
saida.mkdir(parents=True, exist_ok=True)
p = subprocess.Popen([cli, 'mcp', '--headless'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
n = [0]


def req(m, pr=None):
    n[0] += 1
    p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': n[0], 'method': m, 'params': pr or {}}) + '\n')
    p.stdin.flush()
    return json.loads(p.stdout.readline())


def call(nome, args):
    r = req('tools/call', {'name': nome, 'arguments': args})
    if r.get('error') or r['result'].get('isError'):
        raise SystemExit(f'{nome}: {json.dumps(r)[:600]}')
    return r['result']['content']


req('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'f1', 'version': '1'}})
p.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
p.stdin.flush()

L, A = 1000, 1800
call('run_command', {'command': 'artboard.setProps', 'params': {'index': 0, 'width': L, 'height': A, 'name': 'carro'}})
CX = L / 2


def grad(ini, fim, *stops, kind='linear'):
    n_ = len(stops)
    lista = []
    for k, s in enumerate(stops):
        if isinstance(s, str):
            lista.append({'offset': k / (n_ - 1), 'color': s})
        else:
            lista.append({'offset': s[0], 'color': s[1], **({'opacity': s[2]} if len(s) > 2 else {})})
    return {'gradient': {'kind': kind, 'stops': lista, 'start': list(ini), 'end': list(fim)}}


def lateral(x1, x2, y, *stops):
    return grad((x1, y), (x2, y), *stops)


def d(path, fill, nome=None, stroke='none', sw=None, op=None, ef=None):
    a = {'d': path, 'closed': True, 'fill': fill, 'stroke': stroke}
    if sw:
        a['strokeWidth'] = sw
    if nome:
        a['name'] = nome
    if op is not None:
        a['opacity'] = op
    if ef:
        a['effects'] = ef
    call('draw_path', a)


def espelho(path_fn, *a, **k):
    for s in (1, -1):
        path_fn(s, *a, **k)


def X(s, dx):
    return CX + s * dx


A_ = sys.argv[3:]
COMPARAR = '--comparar' in A_
A_ = [x for x in A_ if x != '--comparar']
NOME = A_[0] if A_ else 'carro_cima'
PET, PET_C, PET_E, CREME, CORAL = A_[1:6] if len(A_) >= 6 else ('#10877a', '#1fc2ad', '#06433f', '#f3ecd8', '#ff5a3c')
PRETO, CARB, CARB_C = '#07080b', '#15171d', '#2a2d36'

if COMPARAR:
    # fundo só para ver o desenho; não entra no recorte final
    d(f'M0 0H{L}V{A}H0Z', lateral(0, L, 0, '#3b3a3f', '#55535a', '#3e3d43'), 'fundo')
    for k in range(46):
        x = (k * 97) % L
        y = (k * 233) % A
        d(f'M{x} {y}h6v{120 + k % 7 * 30}h-6Z', '#ffffff' if k % 2 else '#000000', 'risco', op=0.05, ef=[{'effect': 'blur.gaussian', 'params': {'radius': 4}}])

# sombra no chão
d(f'M{CX - 230} 240 Q{CX} 200 {CX + 230} 240 L{CX + 280} 1560 Q{CX} 1660 {CX - 280} 1560Z', '#000000', 'sombra', op=0.5, ef=[{'effect': 'blur.gaussian', 'params': {'radius': 34}}])

# braços da suspensão
for s in (1, -1):
    for y1, y2 in ((395, 500), (495, 520), (1285, 1250), (1385, 1320)):
        x1, x2 = X(s, 300), X(s, 55 if y2 < 1000 else 120)
        call('draw_path', {'points': [[x1, y1], [x2, y2]], 'closed': False, 'fill': 'none', 'stroke': CARB, 'strokeWidth': 15, 'cap': 'round', 'name': 'braço'})

# pneus: borracha com brilho central, friso coral do composto
for s, y, w, h in ((1, 345, 112, 210), (-1, 345, 112, 210), (1, 1225, 136, 240), (-1, 1225, 136, 240)):
    x = X(s, 370)
    call('draw_shape', {'shape': 'rectangle', 'x': x - w / 2, 'y': y, 'width': w, 'height': h, 'radius': 26, 'fill': lateral(x - w / 2, x + w / 2, y, PRETO, (0.28, '#1d1f25'), (0.5, '#3b3e47'), (0.72, '#1d1f25'), (1, PRETO)), 'stroke': 'none', 'name': 'pneu'})
    for dx in (-w / 2 + 11, w / 2 - 11):
        call('draw_shape', {'shape': 'rectangle', 'x': x + dx - 3, 'y': y + 12, 'width': 6, 'height': h - 24, 'radius': 3, 'fill': CORAL, 'stroke': 'none', 'name': 'friso'})
    for k in range(5):
        yy = y + 24 + k * (h - 48) / 4
        call('draw_shape', {'shape': 'rectangle', 'x': x - w / 2 + 22, 'y': yy - 2, 'width': w - 44, 'height': 4, 'fill': '#ffffff', 'stroke': 'none', 'opacity': 0.05, 'name': 'sulco'})

# piso preto largo
d(f'M{CX - 62} 640 L{CX - 228} 830 L{CX - 262} 1180 L{CX - 228} 1470 L{CX + 228} 1470 L{CX + 262} 1180 L{CX + 228} 830 L{CX + 62} 640Z', lateral(CX - 262, CX + 262, 0, CARB, PRETO, CARB), 'piso')

# asa dianteira: três lâminas curvas com placas nas pontas
for i, (y, h, cor) in enumerate(((112, 36, CORAL), (156, 24, CREME), (188, 40, PET))):
    borda = y + 92  # altura na ponta
    miolo = 64  # meia largura do trecho plano do centro
    d(f'M{CX - 395} {borda} L{CX - miolo} {y} L{CX + miolo} {y} L{CX + 395} {borda} L{CX + 395} {borda + h} L{CX + miolo} {y + h} L{CX - miolo} {y + h} L{CX - 395} {borda + h}Z',
      lateral(CX - 395, CX + 395, 0, cor, '#ffffff', cor) if i == 1 else grad((CX, y), (CX, borda + h), PET_C if i == 2 else CORAL, cor), f'lâmina {i}')
for s in (1, -1):
    d(f'M{X(s, 382)} 165 L{X(s, 412)} 165 L{X(s, 412)} 345 L{X(s, 382)} 345Z', lateral(X(s, 382), X(s, 412), 0, CARB_C, PRETO), 'placa')
    d(f'M{X(s, 385)} 180 L{X(s, 395)} 180 L{X(s, 395)} 330 L{X(s, 385)} 330Z', CORAL, 'placa friso')

# bico longo e fino
d(f'M{CX - 18} 118 Q{CX} 84 {CX + 18} 118 L{CX + 58} 640 L{CX - 58} 640Z', lateral(CX - 58, CX + 58, 0, PET_E, PET, PET_C, PET, PET_E), 'bico')
d(f'M{CX - 8} 130 L{CX + 8} 130 L{CX + 20} 640 L{CX - 20} 640Z', CREME, 'faixa do bico', op=0.95)
d(f'M{CX - 42} 310 L{CX - 30} 310 L{CX - 42} 630 L{CX - 54} 630Z', '#ffffff', 'brilho do bico', op=0.22, ef=[{'effect': 'blur.gaussian', 'params': {'radius': 3}}])

# laterais: coral e petróleo, com recorte preto
for s in (1, -1):
    d(f'M{X(s, 58)} 690 L{X(s, 182)} 840 L{X(s, 208)} 1160 L{X(s, 160)} 1300 L{X(s, 72)} 1300Z', lateral(X(s, 58), X(s, 208), 0, PET_C, PET, PET_E), 'lateral')
    d(f'M{X(s, 96)} 835 L{X(s, 170)} 900 L{X(s, 186)} 1090 L{X(s, 112)} 1040Z', lateral(X(s, 96), X(s, 186), 0, '#ff8a5e', CORAL), 'faixa coral')
    d(f'M{X(s, 110)} 762 L{X(s, 172)} 836 L{X(s, 120)} 826Z', PRETO, 'entrada de ar')

# tampa do motor, afinando até a asa traseira
d(f'M{CX - 72} 640 Q{CX - 90} 860 {CX - 86} 1010 L{CX - 42} 1500 L{CX + 42} 1500 L{CX + 86} 1010 Q{CX + 90} 860 {CX + 72} 640Z',
  lateral(CX - 90, CX + 90, 0, PET_E, PET, PET_C, PET, PET_E), 'tampa do motor')
d(f'M{CX - 14} 880 L{CX + 14} 880 L{CX + 9} 1500 L{CX - 9} 1500Z', CREME, 'faixa central')

# cockpit: abertura, capacete e halo
d(f'M{CX - 66} 610 Q{CX} 530 {CX + 66} 610 L{CX + 68} 860 Q{CX} 920 {CX - 68} 860Z', grad((CX, 540), (CX, 900), '#020203', '#14161c'), 'cockpit')
call('draw_shape', {'shape': 'ellipse', 'x': CX - 50, 'y': 660, 'width': 100, 'height': 120, 'fill': grad((CX - 18, 695), (CX + 54, 770), '#fff27a', '#f5c518', '#a96d00', kind='radial'), 'stroke': '#1a1a1a', 'strokeWidth': 3, 'name': 'capacete'})
call('draw_shape', {'shape': 'ellipse', 'x': CX - 28, 'y': 676, 'width': 26, 'height': 16, 'fill': '#ffffff', 'stroke': 'none', 'opacity': 0.75, 'name': 'brilho'})
call('draw_path', {'d': f'M{CX} 545 L{CX} 650 M{CX - 82} 815 Q{CX - 86} 610 {CX} 625 Q{CX + 86} 610 {CX + 82} 815', 'closed': False, 'fill': 'none', 'stroke': CARB_C, 'strokeWidth': 15, 'cap': 'round', 'name': 'halo'})

# asa traseira
d(f'M{CX - 256} 1520 L{CX + 256} 1520 L{CX + 256} 1612 L{CX - 256} 1612Z', grad((CX, 1520), (CX, 1612), PET_C, PET_E), 'asa traseira')
d(f'M{CX - 256} 1552 L{CX + 256} 1552 L{CX + 256} 1578 L{CX - 256} 1578Z', CORAL, 'faixa da asa')
for s in (1, -1):
    d(f'M{X(s, 246)} 1495 L{X(s, 276)} 1495 L{X(s, 276)} 1635 L{X(s, 246)} 1635Z', lateral(X(s, 246), X(s, 276), 0, CARB_C, PRETO), 'placa traseira')
d(f'M{CX - 256} 1612 L{CX + 256} 1612 L{CX + 238} 1630 L{CX - 238} 1630Z', PRETO, 'sombra da asa')
d(f'M{CX - 16} 1630 L{CX + 16} 1630 L{CX + 16} 1652 L{CX - 16} 1652Z', '#ff2d20', 'luz', ef=[{'effect': 'stylize.outerGlow', 'params': {'blur': 30, 'opacity': 0.9, 'color': '#ff2d20'}}])

call('save_file', {'path': str(saida / f'{NOME}.vectorcraft')})
call('export', {'path': str(saida / f'{NOME}.png'), 'format': 'png', 'scale': 1})
call('export', {'path': str(saida / f'{NOME}.svg'), 'format': 'svg'})
print('ok', n[0])
p.kill()
