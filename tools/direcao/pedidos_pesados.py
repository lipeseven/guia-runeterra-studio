r"""Pedidos pesados: pedidos de cena que exigem capacidade nova ou julgamento visual vão para o ORQUESTRADOR (o chat do
Felipe no Claude Code, que lê o código, edita a biblioteca e olha os quadros) em vez de o diretor (`claude -p`) tentar e
falhar. Mesmo padrão do documentário (`F1/horizontal/diretor/painel.py` / `motor.aguardar_orquestrador`): cada pedido
vira um arquivo em `<projeto>/orquestrador/` e uma pendência `orq_pedido_pesado` no card.

Como um pedido vira pesado:
  - o Felipe clica "enviar ao orquestrador" no painel Animação (vertical/horizontal animado) ou no storyboard (Runeterra);
  - AUTOMÁTICO (vertical): o diretor devolve o pedido em `nao_feitos` com `"capacidade": true` (falta real de capacidade).

Arquivos (por projeto):
  orquestrador/pedidos_pesados.json     fila (abertos e resolvidos: id, cena, texto, motivo, status, nota)
  orquestrador/pedido_pesado_<id>.md    o que o orquestrador precisa (texto, cena e fala, código da cena, motivo, quadro)
Vertical: o pedido continua em direcao/pedidos_vertical.json com `"pesado": <id>` (o diretor não o recebe) até ser
resolvido; ao resolver sai de lá e vai para direcao/historico_pedidos_vertical.json com `"via": "orquestrador"`.
Storyboard (Runeterra): o ajuste da cena ganha `comentario_pesado: <id>` (o diretor não o recebe); ao resolver vira
`comentario_aplicado`.

CLI (para o orquestrador; canal pelo GRS_CANAL, ex. `$env:GRS_CANAL='f1'`):
    .venv\Scripts\python.exe tools\direcao\pedidos_pesados.py listar [--todos]
    .venv\Scripts\python.exe tools\direcao\pedidos_pesados.py mostrar <id>
    .venv\Scripts\python.exe tools\direcao\pedidos_pesados.py resolver <id> --nota "o que foi feito" [--renderizar] [--porta 8766]
(`--renderizar`: pede ao painel do canal "Só renderizar de novo" do card — vertical — ou um novo rascunho — Runeterra —
quando não sobra outro pedido pesado aberto no card.)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI.parent) not in sys.path:
    sys.path.insert(0, str(AQUI.parent))
from canal import CANAL, RAIZ, caminho  # noqa: E402

CHAVE = "orq_pedido_pesado"   # pendência do card (uma por card, o texto conta quantos estão abertos)
FILA = "pedidos_pesados.json"
AO_CRIAR = None              # callback (vid, item): o servidor liga aqui o orquestrador automático (motor.iniciar)
LINHAS_CODIGO = 120           # trecho do código da cena no .md (o orquestrador lê o vertical.json inteiro se precisar)


def _agora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _ler_json(arq: Path, padrao):
    try:
        return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else padrao
    except (OSError, json.JSONDecodeError):
        return padrao


def _gravar_json(arq: Path, dados) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def pasta_orq(projeto: Path) -> Path:
    return projeto / "orquestrador"


def ler(projeto: Path) -> list[dict]:
    return _ler_json(pasta_orq(projeto) / FILA, [])


def abertos(projeto: Path) -> list[dict]:
    return [p for p in ler(projeto) if p.get("status") == "aberto"]


def _gravar(projeto: Path, lista: list[dict]) -> None:
    _gravar_json(pasta_orq(projeto) / FILA, lista)


# ---------------------------------------------------------------- contexto da cena
def contexto_vertical(projeto: Path, plano: str | None) -> dict:
    """Cena (número, fala, código, tipo) a partir de direcao/vertical.json; quadro de conferência se houver."""
    dirc = projeto / "direcao"
    arq = dirc / "vertical.json"
    ctx = {"vertical_json": str(arq) if arq.exists() else None}
    d = _ler_json(arq, {})
    planos = d.get("planos") or []
    pos = next((n for n, p in enumerate(planos) if p.get("id") == plano), None) if plano else None
    if pos is None:
        return ctx
    p = planos[pos]
    pal = _ler_json(dirc / "tempos_voz.json", [])
    fala = p.get("em", "")
    if pal and isinstance(p.get("i"), int):
        fim = planos[pos + 1]["i"] if pos + 1 < len(planos) and isinstance(planos[pos + 1].get("i"), int) else len(pal)
        fala = " ".join(w.get("t", "") for w in pal[p["i"]:fim]) or fala
    codigo = p.get("codigo") or ""
    if not codigo:   # cena por tipo (sem código próprio): mostra os parâmetros
        codigo = json.dumps({k: v for k, v in p.items() if k not in ("i", "marcas", "marcas_texto")}, ensure_ascii=False, indent=1)
    quadro = projeto / "trabalho" / "conferencia_cenas" / f"{pos:03d}.jpg"
    ctx.update({"n": pos + 1, "fala": fala, "codigo": codigo, "tipo": p.get("tipo") or f"cena própria ({p.get('set', '?')})",
                "quadro": str(quadro) if quadro.exists() else None})
    return ctx


def _md(item: dict, ctx: dict) -> str:
    cena = f"cena {ctx['n']} (id {item['plano']})" if ctx.get("n") else (f"cena {item['plano']}" if item.get("plano") else "pedido geral (vídeo todo)")
    linhas = [f"# Pedido pesado {item['id']} — {item.get('titulo') or item['slug']}", "",
              f"- card: {item.get('titulo') or ''} (id {item['video']}, pasta `{item['slug']}`, formato {item['formato']})",
              f"- cena: {cena}", f"- criado: {item['criado_em']} · origem: "
              + ("o diretor devolveu por falta de capacidade" if item["origem"] == "diretor" else "o Felipe mandou ao orquestrador"),
              "", "## Pedido do Felipe", "", item["texto"], ""]
    if ctx.get("fala"):
        linhas += ["## Fala da cena", "", f"“{ctx['fala']}”", ""]
    if item.get("motivo"):
        linhas += ["## Motivo do diretor", "", item["motivo"], ""]
    if ctx.get("codigo"):
        cod = ctx["codigo"].splitlines()
        trecho = "\n".join(cod[:LINHAS_CODIGO]) + (f"\n// … (+{len(cod) - LINHAS_CODIGO} linhas no vertical.json)" if len(cod) > LINHAS_CODIGO else "")
        linhas += [f"## Código atual da cena ({ctx.get('tipo', '')})", "", "```js", trecho, "```", ""]
    if item.get("quadro"):
        linhas += ["## Quadro de conferência (da última rodada do diretor)", "", f"`{item['quadro']}`", ""]
    linhas += ["## Arquivos", ""]
    if ctx.get("vertical_json"):
        linhas.append(f"- direção: `{ctx['vertical_json']}`")
    for k, v in (ctx.get("extras") or {}).items():
        linhas.append(f"- {k}: `{v}`")
    linhas += [f"- projeto: `{item['projeto']}`", "",
               "## Ao terminar", "",
               f"    .venv\\Scripts\\python.exe tools\\direcao\\pedidos_pesados.py resolver {item['id']} --nota \"o que foi feito\" --renderizar",
               ""]
    return "\n".join(linhas)


# ---------------------------------------------------------------- pendência e atividade (mesmas tabelas do painel)
def _registrar(con, vid: int, texto: str, tipo: str = "info") -> None:
    con.execute("INSERT INTO atividade (video_id, texto, tipo, quando) VALUES (?,?,?,?)", (vid, texto, tipo, _agora()))


def atualizar_pendencia(con, vid: int, projeto: Path) -> int:
    """Abre/atualiza a pendência `orq_pedido_pesado` com os pedidos abertos do card; sem nenhum, fecha. Devolve quantos."""
    lista = abertos(projeto)
    if not lista:
        con.execute("UPDATE pendencias SET resolvida=1 WHERE video_id=? AND chave=? AND resolvida=0", (vid, CHAVE))
        return 0
    titulo = f"Aguardando o orquestrador: {len(lista)} pedido(s) pesado(s)"
    texto = ("Para o chat/orquestrador (o diretor não tem capacidade para estes pedidos): "
             + " · ".join(f"[{p['id']}] {('cena ' + str(p['n'])) if p.get('n') else 'geral'}: {p['texto'][:80]}" for p in lista)
             + f" — arquivos em {pasta_orq(projeto)}; `tools/direcao/pedidos_pesados.py listar`.")
    if con.execute("SELECT 1 FROM pendencias WHERE video_id=? AND chave=? AND resolvida=0", (vid, CHAVE)).fetchone():
        con.execute("UPDATE pendencias SET titulo=?, texto=? WHERE video_id=? AND chave=? AND resolvida=0", (titulo, texto, vid, CHAVE))
    else:
        con.execute("INSERT INTO pendencias (video_id, etapa, chave, titulo, texto, criada_em) VALUES (?,?,?,?,?,?)",
                    (vid, "direcao", CHAVE, titulo, texto, _agora()))
    return len(lista)


# ---------------------------------------------------------------- criar
def criar(con, vid: int, projeto: Path, texto: str, plano: str | None = None, motivo: str = "", origem: str = "felipe",
          formato: str = "vertical", titulo: str = "", contexto: dict | None = None) -> dict:
    """Um pedido pesado: arquivo .md + entrada na fila + pendência. NÃO mexe na fila de pedidos do diretor (quem chama
    marca o pedido lá com `pesado: id`). `contexto` (storyboard) substitui o contexto lido do vertical.json."""
    ctx = contexto if contexto is not None else contexto_vertical(projeto, plano)
    pid = uuid.uuid4().hex[:8]
    orq = pasta_orq(projeto)
    orq.mkdir(parents=True, exist_ok=True)
    quadro = None
    if ctx.get("quadro") and Path(ctx["quadro"]).exists():   # a pasta de conferência é refeita a cada rodada: guarda uma cópia
        quadro = orq / f"pedido_pesado_{pid}_quadro{Path(ctx['quadro']).suffix}"
        shutil.copy2(ctx["quadro"], quadro)
    item = {"id": pid, "video": vid, "slug": projeto.name, "titulo": titulo, "formato": formato, "plano": plano,
            "n": ctx.get("n"), "fala": ctx.get("fala", ""), "texto": texto.strip(), "motivo": motivo.strip(), "origem": origem,
            "status": "aberto", "criado_em": _agora(), "projeto": str(projeto),
            "quadro": str(quadro) if quadro else None, "arquivo": str(orq / f"pedido_pesado_{pid}.md")}
    Path(item["arquivo"]).write_text(_md(item, ctx), encoding="utf-8")
    _gravar(projeto, ler(projeto) + [item])
    atualizar_pendencia(con, vid, projeto)
    onde = f"cena {item['n']}" if item.get("n") else ("cena " + plano if plano else "geral")
    _registrar(con, vid, f"Pedido pesado [{pid}] ({onde}) enviado ao orquestrador"
               + (f": o diretor não tem capacidade ({item['motivo'][:120]})" if origem == "diretor" else ""), "alerta" if origem == "diretor" else "info")
    if AO_CRIAR:
        try:
            AO_CRIAR(vid, item)
        except Exception:  # acordar o orquestrador nunca pode impedir o pedido de existir
            pass
    return item


def promover_nao_feitos(con, vid: int, projeto: Path, pesados: list[dict], titulo: str = "") -> list[dict]:
    """Vertical: os `nao_feitos` com `capacidade: true` que o diretor devolveu (já casados com o pedido do Felipe em
    `vertical.revisar`) viram pedidos pesados; os pedidos correspondentes em pedidos_vertical.json ganham `pesado: id`.
    Devolve os pedidos (da fila do diretor) promovidos."""
    if not pesados:
        return []
    arq = projeto / "direcao" / "pedidos_vertical.json"
    fila = _ler_json(arq, [])
    promovidos = []
    for ps in pesados:
        ped = ps.get("pedido") or {}
        alvo = next((p for p in fila if not p.get("pesado") and p.get("texto") == ped.get("texto")
                     and p.get("plano") == ped.get("plano") and p.get("quando") == ped.get("quando")), None)
        if alvo is None:
            continue
        item = criar(con, vid, projeto, alvo["texto"], alvo.get("plano"), ps.get("motivo", ""), "diretor", "vertical", titulo)
        alvo["pesado"] = item["id"]
        promovidos.append(alvo)
    _gravar_json(arq, fila)
    return promovidos


def marcar_pedido_vertical(con, vid: int, projeto: Path, n: int, titulo: str = "", motivo: str = "") -> dict:
    """O Felipe manda o pedido nº n da fila do diretor (pedidos_vertical.json) ao orquestrador."""
    arq = projeto / "direcao" / "pedidos_vertical.json"
    fila = _ler_json(arq, [])
    if not 0 <= n < len(fila):
        raise ValueError("pedido não existe mais: recarregue")
    if fila[n].get("pesado"):
        raise ValueError("este pedido já está com o orquestrador")
    item = criar(con, vid, projeto, fila[n]["texto"], fila[n].get("plano"), motivo, "felipe", "vertical", titulo)
    fila[n]["pesado"] = item["id"]
    _gravar_json(arq, fila)
    return item


# ---------------------------------------------------------------- resolver / descartar
def _fechar(projeto: Path, pid: str, status: str, nota: str, via: str) -> dict:
    lista = ler(projeto)
    item = next((p for p in lista if p["id"] == pid), None)
    if item is None:
        raise KeyError(pid)
    if item.get("status") != "aberto":
        raise ValueError(f"o pedido {pid} já está {item.get('status')}")
    item.update({"status": status, "nota": nota.strip(), "via": via, "fechado_em": _agora()})
    _gravar(projeto, lista)
    md = Path(item["arquivo"])
    if md.exists():
        md.write_text(md.read_text(encoding="utf-8") + f"\n---\n**{status.upper()}** em {item['fechado_em']} (via {via})"
                      + (f": {item['nota']}" if item["nota"] else "") + "\n", encoding="utf-8")
    return item


def _tirar_da_fila_vertical(projeto: Path, pid: str) -> dict | None:
    arq = projeto / "direcao" / "pedidos_vertical.json"
    fila = _ler_json(arq, [])
    ped = next((p for p in fila if p.get("pesado") == pid), None)
    if ped is not None:
        _gravar_json(arq, [p for p in fila if p is not ped])
    return ped


def _historico_vertical(projeto: Path, item: dict, ped: dict | None, via: str) -> None:
    """Igual ao `motor.guardar_pedidos_vertical`, uma rodada própria, marcada com a via (o aprendizado lê na publicação)."""
    arq = projeto / "direcao" / "historico_pedidos_vertical.json"
    hist = _ler_json(arq, [])
    rodada = max((h.get("rodada", 0) for h in hist), default=0) + 1
    hist.append({"rodada": rodada, "texto": item["texto"], "plano": item.get("plano"), "fala": item.get("fala", ""),
                 "quando": (ped or {}).get("quando") or item["criado_em"], "via": via, "nota": item.get("nota", ""),
                 "pedido_pesado": item["id"]})
    _gravar_json(arq, hist)


def _ajustes_storyboard(projeto: Path, pid: str, aplicado: bool) -> None:
    arq = projeto / "direcao" / "ajustes.json"
    aj = _ler_json(arq, {})
    for a in aj.values():
        if isinstance(a, dict) and a.get("comentario_pesado") == pid:
            a.pop("comentario_pesado")
            if aplicado:
                a["comentario_aplicado"] = True
    if arq.exists():
        _gravar_json(arq, aj)


def resolver(con, vid: int, projeto: Path, pid: str, nota: str = "", via: str = "orquestrador") -> dict:
    """Fecha o pedido: sai da fila do diretor, vai para o histórico (`via`), a pendência do card é atualizada/fechada."""
    item = _fechar(projeto, pid, "resolvido", nota, via)
    if item["formato"] == "storyboard":
        _ajustes_storyboard(projeto, pid, aplicado=True)
    else:
        ped = _tirar_da_fila_vertical(projeto, pid)
        _historico_vertical(projeto, item, ped, via)
    restantes = atualizar_pendencia(con, vid, projeto)
    _registrar(con, vid, f"Orquestrador resolveu o pedido pesado [{pid}]" + (f": {item['nota'][:160]}" if item["nota"] else ""), "ok")
    return {**item, "restantes": restantes}


def descartar(con, vid: int, projeto: Path, pid: str) -> dict:
    """O Felipe desistiu do pedido (descartar no painel): sai da fila sem ir para o histórico."""
    item = _fechar(projeto, pid, "descartado", "", "painel")
    if item["formato"] == "storyboard":
        _ajustes_storyboard(projeto, pid, aplicado=False)
    else:
        _tirar_da_fila_vertical(projeto, pid)
    atualizar_pendencia(con, vid, projeto)
    _registrar(con, vid, f"Pedido pesado [{pid}] descartado", "info")
    return item


# ---------------------------------------------------------------- todos os cards do canal
def conectar_banco() -> sqlite3.Connection:
    banco = caminho("studio")
    if not banco.exists():   # não cria banco vazio (ex.: rodando numa worktree sem os dados do canal)
        raise KeyError(f"banco do canal {CANAL['chave']} não existe: {banco}")
    con = sqlite3.connect(banco)
    con.row_factory = sqlite3.Row
    return con


def todos(con, so_abertos: bool = True) -> list[dict]:
    """Pedidos pesados de todos os cards do canal (abertos, ou todos), do mais antigo ao mais novo."""
    projetos = caminho("projetos")
    saida = []
    for v in con.execute("SELECT id, slug, titulo, coluna FROM videos ORDER BY id"):
        for p in ler(projetos / v["slug"]):
            if not so_abertos or p.get("status") == "aberto":
                saida.append({**p, "video": v["id"], "titulo": v["titulo"], "coluna": v["coluna"]})
    return sorted(saida, key=lambda p: p.get("criado_em", ""))


def achar(con, pid: str) -> tuple[dict, Path, dict]:
    projetos = caminho("projetos")
    for v in con.execute("SELECT id, slug, titulo, formato FROM videos"):
        for p in ler(projetos / v["slug"]):
            if p["id"] == pid or (len(pid) >= 4 and p["id"].startswith(pid)):
                return dict(v), projetos / v["slug"], p
    raise KeyError(f"pedido pesado {pid} não encontrado no canal {CANAL['chave']}")


# ---------------------------------------------------------------- CLI
def _linha(p: dict) -> str:
    cena = f"cena {p['n']}" if p.get("n") else ("cena " + str(p["plano"]) if p.get("plano") else "geral")
    motivo = f"\n    motivo: {p['motivo'][:160]}" if p.get("motivo") else ""
    st = "" if p.get("status") == "aberto" else f" [{p.get('status')}]"
    return f"{p['id']}{st}  card {p['video']} {p.get('titulo', '')[:40]} · {cena}\n    {p['texto'][:200]}{motivo}"


def _renderizar(vid: int, formato: str, porta: int) -> str:
    rota, corpo = ((f"/api/videos/{vid}/rascunho/refazer", {}) if formato == "storyboard"
                   else (f"/api/videos/{vid}/animacao/refazer", {"so_render": True}))
    req = urllib.request.Request(f"http://127.0.0.1:{porta}{rota}", data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return f"render pedido ao painel (porta {porta}): {r.status}"
    except urllib.error.HTTPError as e:
        return f"o painel recusou o render ({e.code}): {e.read().decode('utf-8', 'replace')[:300]}"
    except OSError as e:
        return f"painel da porta {porta} fora do ar ({e}); renderize pelo painel depois"


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("listar", "mostrar", "resolver"):
        print(__doc__)
        return 2
    with __import__("contextlib").suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        con = conectar_banco()
    except KeyError as e:
        print(e.args[0] if e.args else e)
        return 1
    try:
        if argv[0] == "listar":
            lista = todos(con, so_abertos="--todos" not in argv)
            print(f"{len(lista)} pedido(s) pesado(s) {'' if '--todos' in argv else 'aberto(s) '}no canal {CANAL['chave']}")
            for p in lista:
                print(_linha(p))
            return 0
        if len(argv) < 2:
            print("falta o id")
            return 2
        v, projeto, p = achar(con, argv[1])
        if argv[0] == "mostrar":
            arq = Path(p["arquivo"])
            print(arq.read_text(encoding="utf-8") if arq.exists() else json.dumps(p, ensure_ascii=False, indent=1))
            print(f"\n(arquivo: {arq})")
            return 0
        nota = argv[argv.index("--nota") + 1] if "--nota" in argv else ""
        item = resolver(con, v["id"], projeto, p["id"], nota, "orquestrador")
        con.commit()
        print(f"resolvido {item['id']} (card {v['id']}); pedidos pesados abertos no card: {item['restantes']}")
        if "--renderizar" in argv:
            if item["restantes"]:
                print("não renderizei: ainda há pedido pesado aberto neste card (resolva todos e use --renderizar no último)")
            else:
                porta = int(argv[argv.index("--porta") + 1]) if "--porta" in argv else int(CANAL["porta"])
                print(_renderizar(v["id"], item["formato"], porta))
        return 0
    except (KeyError, ValueError) as e:
        print(e.args[0] if e.args else e)
        return 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
