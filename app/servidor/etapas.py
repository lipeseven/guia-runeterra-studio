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
EM_BREVE_VERTICAL = {"direcao", "render", "publicacao"}  # dependem do estilo de animação


def etapas_do_formato(formato: str) -> list[dict]:
    return ETAPAS_VERTICAL if formato == "vertical" else ETAPAS


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
