# Explicando F1 — projeto VERTICAL (curto animado)

Organização das pastas do F1 (2026-11-20, fase 1): cada formato tem a sua pasta; o que os dois usam fica em `F1/comum/` e `F1/dados/`.
- `F1/vertical/docs/`: `api_cenas.md`, `catalogo_vertical.md`, `folha_de_estilos.md`, `analise_reels.md`.
- `F1/vertical/dados/estilo/`: referências verticais analisadas (fora do Git).
- `F1/horizontal/`: docs (`api_horizontal.md`, `folha_horizontal.md`), `dados/estilo/referencias_horizontais`, `dados/arquivo_testes`, `testes/`.
- `F1/comum/docs/`: `regras_de_direcao.md`, `guia_de_estilo.md`, `estilo_roteiro.md`, `estado_f1.md`. `F1/comum/arte/`: logos e carro de cima.
- `F1/dados/`: dados do canal compartilhados (bancos, acervo, projetos, `modelos3d`, `mapas`).
- O `canal.toml` aponta cada pasta (`[vertical].docs`, `[horizontal].docs`, `[pastas].docs`); `vertical.py`/`horizontal.py` procuram o documento primeiro na pasta do formato e depois na comum.

Fase 2 (pendente): dividir o projeto Remotion `F1/video` (composições Vertical e Horizontal v1 + biblioteca `src/modelos` em comum).
Hoje o código do vertical continua onde está, para não quebrar o painel e o render:
- Projeto Remotion: `F1/video/` (composição `Vertical`, `src/Vertical.tsx`, `src/modelos/`, 60 fps).
- Diretor: `tools/direcao/vertical.py` e docs em `F1/vertical/docs/` e `F1/comum/docs/` (`regras_de_direcao.md`).
- Estado: `F1/comum/docs/estado_f1.md`.
