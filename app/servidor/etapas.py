"""Etapas do fluxo de um vídeo (os cards do topo da tela do vídeo). Ordem = ordem de exibição."""

ETAPAS = [
    {"chave": "pesquisa", "titulo": "Pesquisa", "descricao": "Referências, fatos levantados e conferidos"},
    {"chave": "roteiro", "titulo": "Roteiro", "descricao": "Texto final + detector de semelhança"},
    {"chave": "voz_guia", "titulo": "Voz guia", "descricao": "Leitura provisória para o rascunho"},
    {"chave": "direcao", "titulo": "Direção", "descricao": "Cenas, legendas e destaques"},
    {"chave": "midias", "titulo": "Mídias", "descricao": "Acervo, internet e IA"},
    {"chave": "rascunho", "titulo": "Rascunho", "descricao": "Animatic com a voz guia"},
    {"chave": "gravacao", "titulo": "Gravação", "descricao": "Sua narração limpa"},
    {"chave": "ressincronizacao", "titulo": "Ressincronização", "descricao": "Cenas realinhadas à sua voz"},
    {"chave": "render", "titulo": "Render", "descricao": "Vídeo final"},
    {"chave": "publicacao", "titulo": "Publicação", "descricao": "Título, descrição, créditos e limpeza"},
]

# Etapas cujo código ainda não existe aparecem como "em breve".
EM_BREVE = {"pesquisa", "midias"}

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
