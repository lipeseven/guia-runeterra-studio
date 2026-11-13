# Explicando F1 — projeto HORIZONTAL (documentário)

Tudo do vídeo horizontal novo fica aqui. O vertical tem a própria pasta (`F1/vertical/`). Os dois pertencem ao mesmo canal
(`F1/canal.toml`), mas código, docs e testes de cada formato não se misturam.

- `ARQUITETURA.md` — desenho do motor documental e do painel.
- `PLANO.md` — fases, estado e regras de retomada autônoma (leia primeiro ao voltar ao trabalho).
- `kit/` — módulos independentes de motor (GPS, SFX, anotações, gráficos, imagens reais, foco).
- `remotion/` e `hyperframes/` — adaptadores de cada motor sobre o mesmo kit.
- `montador/` — junta os trechos de cada motor e faz a mixagem única.
- `diretor/` — história (storyline), SPEC por palavra, preparação de ativos e verificação.
- `docs/` — folha de estilo, regras e estado do horizontal.
- `testes/` — folhas de teste de cada componente (aprovadas pelo Felipe antes de entrar em vídeo).

Dados de cada vídeo (fora do Git): `F1/dados/projetos/<slug>/horizontal/`.
Código legado do horizontal v1 (Remotion, vocabulário fixo): `F1/video/src/horizontal/` (continua funcionando; não mexer).
