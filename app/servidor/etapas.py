"""Etapas do fluxo de um vídeo (os cards do topo da tela do vídeo). Ordem = ordem de exibição."""

ETAPAS = [
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final, fatos conferidos e detector de semelhança"},
    {"chave": "voz_guia", "titulo": "Voz guia", "descricao": "Leitura provisória para o rascunho"},
    {"chave": "direcao", "titulo": "Direção", "descricao": "Cenas, legendas e destaques"},
    {"chave": "midias", "titulo": "Mídias", "descricao": "Acervo, internet e IA"},
    {"chave": "rascunho", "titulo": "Rascunho", "descricao": "Animatic com a voz guia"},
    {"chave": "gravacao", "titulo": "Gravação", "descricao": "Sua narração limpa"},
    {"chave": "ressincronizacao", "titulo": "Ressincronização", "descricao": "Cenas realinhadas à sua voz"},
    {"chave": "render", "titulo": "Render", "descricao": "Vídeo final"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição, créditos e limpeza"},
]

# Vídeo vertical (curto animado): a voz de IA vem pronta, então não há voz guia, rascunho, gravação nem ressincronização.
ETAPAS_VERTICAL = [
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final e fatos conferidos"},
    {"chave": "voz_ia", "titulo": "Voz", "descricao": "Áudio gerado no seu programa"},
    {"chave": "direcao", "titulo": "Animação", "descricao": "Cenas animadas no estilo do canal"},
    {"chave": "render", "titulo": "Render", "descricao": "Vídeo final em 1080×1920"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição e créditos"},
]
EM_BREVE_VERTICAL: set[str] = set()  # animação ligada em 2026-11-02 (diretor + projeto Remotion do canal)


# Horizontal animado (canal com `[horizontal]` no canal.toml, ex.: Explicando F1): mesmo fluxo do vertical, mas a voz é a
# gravação do Felipe (limpa no motor) e o diretor é o do horizontal. O painel e o motor reconhecem o fluxo animado
# pela etapa "voz_ia".
ETAPAS_HORIZONTAL_ANIMADO = [
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final e fatos conferidos"},
    {"chave": "voz_ia", "titulo": "Narração", "descricao": "Sua gravação, limpa e medida"},
    {"chave": "direcao", "titulo": "Direção", "descricao": "Cenas no estilo do horizontal"},
    {"chave": "render", "titulo": "Render", "descricao": "Vídeo final em 1920×1080"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição e créditos"},
]


# Horizontal DOCUMENTAL (canal com `[horizontal_doc]` no canal.toml): o fluxo do diretor documental
# (F1/horizontal/diretor/etapas.py, estado.json da pasta <projeto>/horizontal/) espelhado nos cards; ver horizontal_doc.py.
# Fase 7a (2026-11-14): Roteiro, Voz guia, Gravação e Ressincronização como no Runeterra (voz guia Fish Audio só para
# dosar e montar; a voz real do Felipe grava por cima e as cenas, presas às palavras, são retemporizadas). ★ = aprovação.
ETAPAS_HORIZONTAL_DOC = [
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final, pesquisa e fatos conferidos (OpenF1)"},
    {"chave": "voz_guia", "titulo": "Voz guia", "descricao": "Leitura provisória (Fish Audio) para medir e montar"},
    {"chave": "historia", "titulo": "História ★", "descricao": "Capítulos e afirmações presos ao roteiro"},
    {"chave": "spec", "titulo": "SPEC ★", "descricao": "Cenas por palavra, motor e kits"},
    {"chave": "ativos", "titulo": "Ativos", "descricao": "Dados OpenF1, imagens validadas, 3D, SFX"},
    {"chave": "verificacao", "titulo": "Verificação", "descricao": "Checagens automáticas da SPEC"},
    {"chave": "rascunho_doc", "titulo": "Rascunho ★", "descricao": "Montagem em baixa resolução"},
    {"chave": "gravacao", "titulo": "Gravação", "descricao": "Sua narração limpa"},
    {"chave": "ressincronizacao", "titulo": "Ressincronização", "descricao": "Cenas retemporizadas à sua voz"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição e créditos"},
]
# card documental criado antes da fase 7a (Narração = etapa "voz_ia", sua gravação já medida): continua como era
ETAPAS_HORIZONTAL_DOC_V1 = [
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final e fatos conferidos"},
    {"chave": "voz_ia", "titulo": "Narração", "descricao": "Sua gravação, limpa e medida"},
    {"chave": "historia", "titulo": "História ★", "descricao": "Capítulos e afirmações presos ao roteiro"},
    {"chave": "spec", "titulo": "SPEC ★", "descricao": "Cenas por palavra, motor e kits"},
    {"chave": "ativos", "titulo": "Ativos", "descricao": "Dados OpenF1, imagens validadas, 3D, SFX"},
    {"chave": "verificacao", "titulo": "Verificação", "descricao": "Checagens automáticas da SPEC"},
    {"chave": "rascunho_doc", "titulo": "Rascunho ★", "descricao": "Montagem em baixa resolução"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição e créditos"},
]


def etapas_do_formato(formato: str, chaves: set[str] | None = None) -> list[dict]:
    """`chaves` = etapas que o card já tem: card horizontal criado antes do fluxo animado continua no fluxo antigo."""
    if formato == "vertical":
        return ETAPAS_VERTICAL
    if formato == "horizontal_doc":
        return ETAPAS_HORIZONTAL_DOC_V1 if chaves is not None and "voz_ia" in chaves else ETAPAS_HORIZONTAL_DOC
    if chaves is not None and "voz_ia" not in chaves:
        return ETAPAS
    from canal import CANAL  # tools/ já está no caminho (banco.py)

    return ETAPAS_HORIZONTAL_ANIMADO if CANAL.get("horizontal") else ETAPAS


# Etapas cujo código ainda não existe aparecem como "em breve".
EM_BREVE = {"midias"}  # "pesquisa" saiu (2026-10-19): virou a conferência dentro do Roteiro

STATUS = ("pendente", "andamento", "concluido", "atencao", "em_breve")

# Colunas do quadro (tela inicial).
COLUNAS = [
    {"chave": "ideia", "titulo": "Ideia"},
    {"chave": "roteiro", "titulo": "Roteiro"},
    {"chave": "gravacao", "titulo": "Gravação"},
    {"chave": "montagem", "titulo": "Montagem"},
    {"chave": "revisao", "titulo": "Revisão"},
    {"chave": "publicado", "titulo": "Publicado"},
]
