# PLANEJAMENTO — F1 horizontal

Registro de tudo que for decidido sobre o projeto horizontal. Criado em 2026-11-26, reorganizado em 2026-11-27.

Fontes: conversa do Felipe com o orquestrador e prints de uma conversa dele com outra sessão.

**Como ler:** o que vale está nas seções 1 a 3. A seção 4 é o que ainda falta decidir. A seção 5 é só contexto e histórico.
A seção 6 reúne informações importantes de trabalhos anteriores (análise das referências e testes de 3D).

**Fase atual: discussão de ideias.** Nada de execução nem de vídeo nesta semana (também pela cota). Não oferecer execução a cada resposta.

## 1. Decisões

### 1.1 Canal e idiomas

- Canal só sobre Fórmula 1, para o público de internet e redes sociais (não o de TV).
- **Três idiomas: PT-BR, alemão e italiano.** Inglês fora (mercado lotado).
- Critério: maior pagamento, mas só em país com público.
- **Um canal por idioma, todos no mesmo Gmail** que já roda os Shorts (sem Gmail novo). O canal atual vira o PT-BR; alemão e italiano são canais novos (Brand Accounts) dentro dele.
- O PT-BR sai na frente nos inscritos (~800); falta fazer as 4.000 horas. Os outros dois começam do zero.
- Risco aceito: mesmo Gmail e AdSense; violação grave em um canal pode pesar nos outros.

### 1.2 Formato e linguagem

- Documentário, vídeos longos de **9 a 20 minutos**.
- No fundo é um **motion graphic estilizado e bonito**, com estilo bem definido e fluido.
- Recursos: telemetria; trechos fotorrealistas de carros e peças; 3D; muitos gráficos; HyperFrames e Remotion; transições; blur e foco.
- Transições de cena sem cortes; anotações "à mão", em fonte que parece cursiva.
- Trechos fotorrealistas: **Blender junto com as ferramentas ArtCraft** (ver `docs/hub_ferramentas.md`).
- Referência de modelo: Formula Addict. Há muitos outros canais de referência (a enviar): juntar o melhor de cada um num estilo próprio e forte. Inspiração, não cópia.
- **O 3D entra nos momentos-chave ou de grande impacto.**
- **60 fps é regra do canal**, daqui para frente (o que já foi feito em 30 fica como está).
- **O carro precisa fazer o traçado que o piloto fez.** O capricho é visual: erro de ±0,2 s no delta é aceitável. O OpenF1 não mede posição lateral (ver A-9).
- **Movimento sem pulos nem degraus:** temos a malha 3D inteira, é só fazer certo (interpolar os dados e conferir quadro a quadro).
- **Carro:** vale o exterior. Se o exterior é o carro atual, é ele que se usa; nomes de peça dentro do `.glb` não importam (modders reaproveitam peças de outros carros).

### 1.3 Roteiro

- É prioridade. Ordem de importância: **RETENÇÃO > HOOKS/REHOOKS > CONTEÚDO DE ALTA QUALIDADE > FACILIDADE DE TRADUÇÃO.**
- **Elementos locais são bem-vindos:** gíria, expressão e jeito de falar de cada idioma dão imersão. A tradução pode flutuar, não precisa ser literal.
- **Nada de apontar tudo para um "grande vilão"** nem de expor situação super arriscada a cada momento. Envolver com a história: fisgar e fazer a pessoa querer, naturalmente, assistir até o fim.
- Entendimento do orquestrador: a tensão vem de curiosidade, de gente tentando resolver um problema e de respostas aos poucos; risco e conflito só quando os fatos trazem.

### 1.4 Miniatura

- A miniatura **pode ser a mesma nos três, mudando só o idioma** do texto (ex.: "slow", "devagar").

### 1.5 Processo de produção

1. **Primeiro só o PT-BR**, até ficar 100% arrumado, praticamente pronto para postar.
2. Depois os outros idiomas, usando o PT-BR como **molde**. Motivo: não encher o disco, não gastar render em três vídeos juntos e garantir versões idênticas ao original.

- O vídeo é montado por completo com a **voz guia** (como no Runeterra). As partes 3D entram primeiro como **blocking**: mockup simples, storyboard dentro do storyboard ou slides mostrando como a cena vai se comportar. O 3D de verdade vem depois da voz final.
- Cenas divididas por **trechos que fazem sentido** (como no Runeterra); cada idioma liga a sua fala ao trecho.
- O Felipe revisa quase quadro a quadro e refaz cenas à mão.
- Há um **agente diretor de arte** com liberdade para inventar cenas. A mesma informação ganha roupagem diferente a cada vídeo.

Termos: **blocking** = ensaio da cena com formas simples; **blockout** = modelo cinza; **previs** = pré-visualização 3D; **animatic** = storyboard em vídeo com tempos e áudio.

### 1.6 Revisão de idioma

- **Um subagente exclusivo por idioma: SUBAGENTE ALEMÃO e SUBAGENTE ITALIANO.**
- Eles **só conferem**, não fazem mais nada.

### 1.6b Modelos dos agentes

| Agente | Modelo | Esforço |
|---|---|---|
| Todos os que mexem com o vídeo em si: edição, ArtCraft, Blender, Remotion, HyperFrames, FFmpeg e o que mais envolver o vídeo | Opus 5.5 | médio |
| Conferência de tradução (subagentes alemão e italiano) | Sonnet 5.5 | médio |

### 1.7 Voz

- O Felipe sintetiza a própria voz no **VoiceStudio**; ela é usada nos outros idiomas e **vai para o vídeo publicado**. É exceção à regra "voz de IA nunca é publicada", só para a voz dele neste projeto.
- O card tem **campo para subir o áudio de cada idioma**.

### 1.8 Reuso e arquivos

- Vídeo **desacoplado**: reaproveitar tudo o que puder.
- **Os trechos 3D são os mesmos em qualquer idioma.**
- **Todo texto local fica em camada separada**, guardado à parte para tradução; nunca dentro da cena 3D.
- Diferença de duração entre idiomas: **medir primeiro**; muitas vezes basta acelerar ou desacelerar um pouco, e isso pode virar recurso de imagem, com aviso na tela ("0,9×").
- Um novo render **aproveita o que já existe e só complementa**.
- **Nada é excluído até a publicação dos 3 vídeos.** O card recebe **3 links do YouTube**; os três idiomas ficam na mesma pasta e a limpeza atual (Lixeira) leva tudo de uma vez.

### 1.9 Música e SFX

- Preocupação importante.
- Fica bom quando a música acompanha o roteiro ou o diretor trabalha sobre a batida. Música de fundo em alguns momentos; **não é regra**.
- **Editar em cima da batida é exceção, um "super trunfo"** para momentos especiais.

### 1.9b Motores e arquivos de teste

- **O Studio trabalha com os dois motores (Remotion e HyperFrames).** O HyperFrames não ganha tempo renderizando em paralelo; aceito.
- **Vídeos de teste e arquivos `.blend` nossos ficam dentro do projeto.** Antes de uma limpeza, listar por nome o que vai sumir e esperar o OK.

### 1.10 Qualidade antes de mostrar

- Cada cena é avaliada de 0 a 100; **só passa acima de 75**.
- Conferir todo plano em quadro de tamanho original.
- Objeto novo e complexo é testado isolado, contra a referência, antes de entrar no vídeo.
- Manter a lista do que o Felipe mandou tirar e conferir a cada entrega.
- Mudar só o que foi pedido e provar com diff de pixels.

## 2. Testes de viabilidade

Tudo o que for para testar entra aqui, como casos de teste. **Todos os casos serão testados.**

Status: `pendente`, `passou`, `falhou`.

| ID | O que testar | Passa quando | Status |
|---|---|---|---|
| TV-01 | Tradução falsa: esticar os textos para achar estouro de caixa | nenhum texto estoura ou se sobrepõe | pendente |
| TV-02 | Fonte cursiva, cartões e gráficos com ä, ö, ü, ß e acentos do italiano | todos os caracteres desenhados e dentro das caixas | pendente |
| TV-03 | VoiceStudio no nível **padrão** (o teste lento foi no máximo): tempo e qualidade | tempo aceitável para 15 min e voz reconhecível como a do Felipe | pendente |
| TV-04 | Licença do modelo de voz para canal monetizado (e marca d'água) | licença permite uso comercial | pendente |
| TV-05 | Pronúncia em alemão e italiano de pilotos, pistas e termos técnicos | sem erro apontado na conferência | pendente |
| TV-06 | Subagentes revisores com erros plantados de propósito | pegam os erros e não "corrigem" o que está certo | pendente |
| TV-07 | Diferença de duração PT-BR × alemão × italiano no mesmo roteiro | diferença medida por trecho | pendente |
| TV-08 | Quanto dá para desacelerar ou acelerar a 60 fps | limite sem parecer travado definido | pendente |
| TV-09 | Cenas por trecho ancorando em outro idioma | cenas, textos e SFX caem no momento certo | pendente |
| TV-10 | Render complementar de um plano 3D (esticar começo ou fim) | emenda invisível | pendente |
| TV-11 | Rótulo traduzido seguindo a peça 3D (depende do item aberto A-3) | rótulo acompanha a peça em todos os quadros | pendente |
| TV-12 | Troca do blocking pelo 3D final | tempos e textos continuam no lugar | pendente |
| TV-13 | Peça fotorrealista no Blender com as ferramentas ArtCraft | comparável à referência real | pendente |
| TV-14 | Detectar a batida e encaixar corte ou movimento | efeito percebido no momento escolhido | pendente |
| TV-15 | Triagem de ouvido do banco de SFX | sons ruins reprovados | pendente |
| TV-16 | Card com 3 áudios e 3 links; limpeza só com os 3 | não apaga nada antes do terceiro link | pendente |
| TV-17 | Piloto de 60 a 90 s pelo caminho inteiro nos três idiomas | os três saem sem refazer o visual | pendente |
| TV-18 | Gráficos no horizontal: poucos cartões empilhados e gráfico interagindo com a cena (regra do vertical) | aprovado pelo Felipe | pendente |

## 3. Anotações técnicas (do orquestrador)

- A direção atual ancora cenas, SFX e gráficos em **trechos literais do roteiro em português**; outro idioma precisa de um mapa dessas âncoras.
- `kit/anotacao`, `kit/cartoes` e `kit/graficos` foram conferidos para PT-BR; falta o alemão e o italiano.
- Números, datas e unidades no formato de cada idioma; nomes de pilotos e equipes iguais.
- Vídeo a 60 fps desacelerado repete quadros. No HyperFrames ou Remotion, renderizar de novo no tempo certo é barato; no Blender (~2,8 s por quadro) vale guardar sobra.
- Para o render complementar: guardar cena, quadros em sequência de imagens e animação que dê o mesmo resultado a cada render.
- VoiceStudio: o teste anterior foi desinstalado em 2026-11-22 (cerca de 10 min por minuto de áudio, no máximo; pesos do OmniVoice não comerciais). Reinstalar quando for testar.
- A criar no card: 3 campos de link e envio de áudio por idioma.
- A criar no sistema: arquivo de textos por idioma, com nome fixo para cada texto.

## 4. Em aberto

- **A-1** Objetivo principal: receita de AdSense, crescimento de inscritos ou os dois?
- **A-2** Qual modelo de voz, e se a licença permite (ver TV-03 e TV-04).
- **A-3** Proposta do orquestrador, sem OK: render 3D com sobra no começo e no fim, exportando a posição na tela das peças que recebem rótulo.
- **A-4** Telemetria e gráficos: os mesmos dados nos três idiomas ou variação por mercado?
- **A-5** Temas do primeiro lote de vídeos.
- **A-6** Raio-X: provavelmente será necessário, mas fica para o futuro. Os `.glb` não têm interior (radiador, dutos, motor, câmbio); caminhos: modelos com interior, raio-X estilizado ou corte só na casca.
- **A-7** SFX: conversar a fundo. Diretriz já aceita: bancos grátis (Freesound CC0, Pixabay, Mixkit, Sonniss) em vez de gerar com IA local.
- **A-8** Telemetria: comparar depois OpenF1 e FastF1 (o FastF1 retornou 401 porque exige autenticação).
- **A-9** Fonte para o traçado real do piloto: no teste de 2026-11-14 (`docs/teste_vhe_interlagos.md`), as voltas de pilotos diferentes do OpenF1 caem sobre a mesma linha, então a posição lateral foi inferida (linha ideal do mod do Assetto Corsa, no ritmo do piloto).
- **A-10** Montador: o código ainda recusa `imagens`, `modelo3d`, `pessoa` e `tag` (`montador/README.md`). O Felipe lembra de um teste com isso funcionando; falta identificar qual.

Propostas sem OK (da outra sessão e do orquestrador):

- Glossário fixo por idioma (undercut, dirty air, box, pit stop, parc fermé...).
- Revisor nativo humano nos primeiros vídeos para calibrar os subagentes.
- Idioma padrão, sem sotaque regional.
- Título e descrição próprios por idioma.
- Mapa musical por trecho no roteiro; a música se ajusta à voz; licença conferida por faixa.
- Manter identidade (paleta, fonte, transição) variando a execução; guardar projetos e versões como prova do processo.

## 5. Contexto e histórico

Números **não verificados aqui**, salvo a conferência de 5.4.

### 5.1 Como se chegou aos idiomas

A outra sessão começou recomendando italiano (audiência de TV), passou a alemão (receita por view no YouTube). O Felipe escolheu alemão, depois considerou três, voltou a dois e fechou em **três** em 2026-11-27.

### 5.2 Pesquisa de audiência e YouTube

| | PT-BR | Italiano | Alemão |
|---|---|---|---|
| CPM estimado | US$ 0,80–3 | € 2,50–5,00 | € 5–9,80 |
| Buscas por "f1" no país | 519 mil | 53 mil | 112 mil |
| Receita por 1.000 views, vídeo longo | ~US$ 0,55–0,60 | ~US$ 0,95 | ~US$ 1,55 |
| Maiores canais independentes | GP EM CASA (210 mil), Clube da F1 (101 mil), Canal Enerto (66 mil) | Alberto Naska (1,17 mi, motorsport), Matteo Bobbi (75 mil), Rastrelli (74 mil) | Motorsport-Magazin (294 mil), FormelFranz (52 mil), Lumi F1 (55 mil) |
| Maior vídeo longo recente | 76 mil | 229 mil (16 min) | 80 mil (51 min) |

- TV em 2026: forte alta no Brasil e na Itália; estagnada e paga na Alemanha.
- Anúncios no meio do vídeo a partir de 8 minutos.
- Vaga: não foi achado, nos três idiomas, canal de F1 com documentário de 9 a 20 min, motion graphics pesado e transições sem corte.
- PT-BR já tem concorrente grande (RessacaMotor, 329 mil). Alemão: formato livre; ganchos Audi, Mercedes, Schumacher, Hockenheim. Italiano: quase livre; ganchos Antonelli, Ferrari, Monza.
- Limites: volumes do vidIQ sem unidade clara; amostra de ~20 canais por idioma; sem Google Trends.

### 5.3 Formula Addict

648 mil inscritos; 23 vídeos longos em um ano, ~780 mil views por vídeo; os que mais rendem têm 10 a 15 min e título em pergunta; temas de regulamento, montadora e "por que isso acontece". Receita estimada ~US$ 3,3 mil/mês (vidIQ). Fora do inglês, esperar cerca de uma ordem de grandeza a menos.

### 5.4 Documento de retenção do Felipe (conferido em 2026-11-27)

Arquivo: `Retenção de Audiência em Vídeos Longos.docx` (na pasta Downloads). Referências quase todas de blogs e ferramentas de IA; nem tudo foi checado.

- **Usar como técnica:** gancho sem cumprimento que entrega o título; stakes como "por que isso interessa"; roadmap sem entregar o final; cada seção responde à dúvida anterior; rehooks; open loops; payoff; sem "em conclusão"; CTA curto para o próximo vídeo; frases curtas; pausas antes de virada; imagem mostra o que a voz diz; título e miniatura sem o mesmo texto.
- **Errado ou sem base:** "imagem 60.000 vezes mais rápida que texto"; Zeigarnik como memória superior (meta-análise de 2025, DOI 10.1057/s41599-025-05000-w); título com efeito "exponencial" no CTR; "reupar" vídeo mantendo o link; CTR de 8 a 12% como meta (YouTube: metade fica entre 2% e 10%).
- **Não confirmado:** números do Retention Rabbit e metas por duração; +18% de CTR na miniatura; quebra de padrão a cada 15 a 40 s.
- Medir de verdade pela curva de retenção do YouTube Studio.

### 5.5 Regras do YouTube citadas pela outra sessão (não verificadas)

- Monetização: 1.000 inscritos e mais 4.000 horas em 12 meses ou 10 milhões de views em Shorts em 90 dias.
- Até 100 canais por conta Google.
- Clonar a própria voz não exigiria marcar conteúdo sintético; vídeo próprio traduzido não pareceria "conteúdo reutilizado" (sem regra explícita).
- Risco de "conteúdo repetitivo ou de template": variar estrutura e gancho.
- "Trust Score" não é métrica oficial.

## 6. INFORMAÇÕES IMPORTANTES

Do trabalho de 2026-11-05 e 06 (antes da reorganização de 20/11), ainda válido.

### 6.1 Análise das referências

- 10 vídeos analisados por inteiro (9 Formula Addict, 1 Documentsui): cortes, fala, som, ~7 mil miniaturas, 144 transições quadro a quadro.
  Em `F1/horizontal/dados/estilo/referencias_horizontais/` (`analise_horizontal.md`, `transicoes_quadro_a_quadro.md`, `sons_resumo.json`).
- Formula Addict: quase 100% 3D e motion graphics; palavra gigante atrás do carro (25 a 35 vezes por vídeo, entra com letras
  embaralhadas); uma cor de destaque por vídeo, a da equipe do tema; modo claro e modo técnico escuro; notas à mão que comentam
  a fala; respiros de 7 a 40 s sem texto (~35–40% do tempo); 145 a 190 palavras/min; algo muda na tela a cada 2 a 3 s; trilha
  16 a 26 dB abaixo da voz.
- Transições medidas (24 fps): só ~36% são corte seco; empurrão sai em 8 quadros com desfoque de até 8% da largura e entra em
  12; glitch de 4 a 6 quadros; cortina sempre de baixo para cima em 14; fade de 14 a 22; letras embaralhadas a ~0,65 letra por quadro.
- Documentsui: ~60% filmagem de TV; dele só servem a abertura de capítulo com o traçado, a tabela de pontos e a palavra solta em tela escura.

### 6.2 Decisões do Felipe nessa época

- Mesclar Formula Addict e Documentsui, com regras próprias (nada das regras do Runeterra).
- Carros sempre oficiais e o mais atuais possível, em `.glb` (base para o Blender).
- Estúdio alterna dois modos pelo clima do trecho: claro (fundo claro, palavra na cor de destaque) e cor cheia (fundo na cor, palavra branca).
- Zebras verde/amarela fazem parte da assinatura de Interlagos.

### 6.2b Feedback do teste Ferrari (Fable + HyperFrames)

- Aprovado: câmera girando no mesmo plano 3D e blur de foco.
- Reprovado: círculos feitos à mão, texto picotado, continuidade e ritmo. Cuidado ao fazer as anotações "à mão" da seção 1.2.

### 6.2c Onde estão os testes de motor (e o que se perdeu em 2026-11-20)

- Guardado: textos em `docs/testes_hyperframes/`; scripts, dados, `ferrari_fable_v5.mp4` e `hamilton_senna_blender_limpo.mp4` em `dados/arquivo_testes/`.
- Apagado na limpeza: `sf26_pecas.blend` (mapeamento parcial do SF26), `interlagos_vhe_full.blend` e o vídeo do traçado `hamilton_melhor_volta_vhe.mp4`.
- O vídeo do traçado pode ser refeito: cena em `hyperframes/vhe_interlagos/`, entradas conferidas no projeto, render ainda não testado. Descrição em `docs/teste_vhe_interlagos.md`.

### 6.3 Testes feitos e o que se aprendeu

Código em `F1/horizontal/v1/src/` (`TesteEstudio.tsx`, `TestePista.tsx`, `TesteCorrida.tsx`).

- **Leitor de `.glb` de carro:** ajusta para 5,4 m, acha a frente pela asa traseira (a ponta mais alta é a de trás) e separa as
  4 rodas pela posição, mesmo quando o arquivo junta as quatro numa peça. Asas, halo e suspensão grudados na carroceria exigem
  corte por região ou o Blender ("separar por partes soltas").
- `ferrari_sf26.glb` é uma SF-25 com a pintura de 2026 (carroceria de 2025); `ferrari_sf26_v2.glb` é a F1-75 de 2022.
- **Pista `.glb` de Interlagos:** está em metros e bate com o traçado real (escala 1, erro mediano ~0,9 m); largura medida
  13 a 14 m; relevo de 43 m. Só a superfície (`surface_2`) basta; asfalto = `mesh2_7`/`mesh2_11`, zebras verde/amarela/branca =
  `mesh2_8`/`mesh2_9`, linhas brancas `mesh2_6`, amarelas `mesh2_17`.
- **Alinhamento:** `F1/dados/modelos3d/pistas/alinhamento_interlagos.json` = trajetória da volta (x, altura, z a cada 3,5 m,
  f 0 = chegada) recentralizada no asfalto do `.glb`. O nosso traçado estava ~2,5 m fora do centro (até 8 m).
- **Câmera que segue carro:** usar a direção média da pista em ±25 m e a volta fechada com pontos espaçados por igual; sem isso
  a imagem treme (a variação entre quadros caiu de 5,15 para 0,41).
- Estilo que funcionou: asfalto bem escuro, só zebras e faixas com textura original, o resto na cor de fundo e sumindo na névoa.
