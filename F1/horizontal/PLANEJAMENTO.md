# PLANEJAMENTO — F1 horizontal

Registro de tudo que for decidido sobre o projeto horizontal. Criado em 2026-11-26.

Fontes: conversa do Felipe com o orquestrador e prints de uma conversa dele com outra sessão.

## Decisões

- Intenção do Felipe: canal só sobre Fórmula 1, em PT-BR (padrão) e em um segundo idioma estrangeiro.
- Inglês descartado como segundo idioma (mercado lotado de canais gigantes).
- Público-alvo: internet e redes sociais (não o público de TV).
- Formato: documentário, vídeos longos de 9 a 20 minutos.
- Recursos do vídeo: telemetria; trechos fotorrealistas de carros e peças; imagens 3D; muitos gráficos com motion graphics; HyperFrames e Remotion; transições; blur e foco.
- Linguagem: transições de cena sem cortes; anotações "à mão", em fonte que parece cursiva.
- Critério do segundo idioma: maior pagamento, mas só em país que tenha público.
- Canal de referência para o modelo: Formula Addict (inglês americano). Vale o princípio do projeto: inspiração, não cópia.
- Localização completa: não só o áudio; os textos na tela também são adaptados por idioma (como em Toy Story).
- **Segundo idioma: alemão** (decidido em 2026-11-27). Idiomas do projeto: PT-BR e alemão.
- **São três idiomas: PT-BR, alemão e italiano** (2026-11-27; substitui a decisão anterior de ficar só com dois). Um canal por idioma, no mesmo Gmail dos Shorts.

### Processo contra "AI slop" (parte 5)

- Felipe revisa os vídeos praticamente quadro a quadro e refaz cenas à mão depois que a IA entrega o produto completo.
- Há um **agente diretor de arte** com liberdade para inventar cenas: segue o padrão do canal e também cria novas.
- A mesma informação ganha roupagem diferente a cada vídeo (ex.: tabela de pilotos desenhada à mão em um, como placa de metal em outro).

Sugestões da outra sessão (sem OK): manter a identidade (paleta, fonte cursiva, tipo de transição) variando a execução; guardar projetos, rascunhos e versões como evidência do processo.

### Ritmo e contas (parte 6)

- **Fase atual: só discussão de ideias.** Nada de execução nem de vídeo nesta semana (também por causa da cota). Não oferecer execução a cada resposta.
- Há outros canais que vão entrar como referência; o Felipe ainda vai mandar.
- **PT-BR fica no canal que já roda** (Shorts de F1, quase 800 inscritos, "Trust Score" alto).
- **Um Gmail só, sem Gmail novo** (correção da parte 7): o que já roda os Shorts. O canal atual vira o PT-BR; o alemão (e, na conversa do print, o italiano) entra como **canal novo (Brand Account) dentro dele**. A verificação por telefone já feita vale para eles.
- Inscritos: o PT-BR sai na frente (~800); depois é fazer as 4.000 horas. Os canais novos começam do zero em inscritos, horas e histórico.
- Risco aceito até aqui: mesmo Gmail e AdSense; violação grave em um canal pode pesar nos outros.
- Mesmo vídeo para cada idioma, com os textos adaptados (estilo Toy Story).

Pontos levantados pela outra sessão (**não verificados aqui**):

- Para monetizar não bastam 1.000 inscritos: também 4.000 horas de vídeo longo em 12 meses ou 10 milhões de views em Shorts em 90 dias. Conferir na página do Programa de Parcerias.
- Inscrito de Shorts nem sempre assiste vídeo longo; conferir no YouTube Studio depois do primeiro.
- "Trust Score" não é métrica oficial; verificação por telefone libera recursos. Para canal novo, preferir conta limpa e verificada às antigas sem verificação.
- ~~Cuidados com várias contas e novo número~~: não se aplicam, já que não haverá Gmail novo (parte 7).

Nota sobre o italiano: os prints ainda contam com ele. Nesta conversa o Felipe fechou em dois idiomas (2026-11-27) e avisou que o assunto muda até o final dos prints. Revisar quando chegar a parte final.

### Texto desacoplado (parte 8)

- **Requisito do Felipe:** na construção do vídeo, todo texto inserido fica guardado em separado (desacoplado), para ser traduzido depois. Todo o resto do vídeo, que não depende de tradução, é reaproveitado (Remotion e HyperFrames).
- Os vídeos longos vão começar no canal PT-BR que já funciona. No print são 3 canais no mesmo Gmail (PT, italiano, alemão).

Requisitos propostos pela outra sessão (sem OK):

- um arquivo de textos por idioma, cada texto com nome fixo (nunca pela posição);
- nada de texto "queimado" em render 3D ou fotorrealista; texto sempre em camada por cima;
- duração das cenas ligada ao áudio de cada idioma, com marcação de tempo própria;
- anotação à mão que se adapta ao tamanho do texto (revela o texto medido);
- números, datas e unidades no formato do idioma; nomes de pilotos e equipes iguais;
- teste automático de texto estourando a caixa em cada idioma.

Em aberto por ela: os gráficos de telemetria usam sempre os mesmos dados em todos os idiomas (aposta dela) ou há variação por mercado?

Anotações do orquestrador sobre o que já existe:

- A direção é ancorada em **trechos literais do roteiro em português** (cenas, SFX, ritmo de gráfico). Outro idioma precisa de um mapa dessas âncoras para as palavras traduzidas; `retemporizar` hoje só cobre narração nova no mesmo texto.
- O `kit/anotacao` já mede o texto e desenha por traço, mas os glifos cobertos foram conferidos para PT-BR; falta conferir ä, ö, ü e ß.
- O `kit/cartoes` e o `kit/graficos` calculam largura por tabela de caracteres: conferir o alemão neles também.

### Fluxo de produção e agente de idioma (parte 9)

- **Reaproveitar tudo o que puder.**
- Texto como **camada** por cima da cena 3D (nunca dentro dela), para ser editável.
- Um projeto, uma versão por idioma, feitas juntas, para o Felipe assistir e aprovar depois (no print, 3 idiomas).
- Haverá um **agente dedicado à revisão de idioma/dialeto**, já que o Felipe não fala os outros idiomas.

Propostas da outra sessão (sem OK):

- revisor nativo nos primeiros vídeos para calibrar o agente;
- glossário fixo por idioma (undercut, dirty air, box, pit stop, parc fermé...);
- revisar o roteiro traduzido como fala, não só como texto;
- testar a pronúncia da voz sintetizada com nomes de pilotos e pistas antes do render;
- idioma padrão (Hochdeutsch; italiano neutro), sem sotaque regional;
- o PT-BR sai primeiro e é a base de tempo e roteiro.

### Montagem com voz guia e blocking 3D (proposta do Felipe, 2026-11-27)

- O vídeo é **montado por completo com a voz guia** (como já é no Runeterra).
- As partes em 3D entram como **mockup bem simples (blocking)**: pode ser um storyboard dentro do storyboard, ou uma sequência de slides que indica como a cena vai se comportar depois de pronta.
- O 3D de verdade só é feito depois, com a voz final no vídeo.

Termos: **blocking** é o ensaio da cena com formas simples (posições, câmera e tempos); **blockout** é o modelo cinza simplificado; **previs** é a pré-visualização em 3D; **animatic** é o storyboard em vídeo, com os tempos e o áudio.

### Arquitetura de reuso (Felipe, 2026-11-27)

- Vídeo **desacoplado**, para reusar quase tudo.
- **Trechos 3D são os mesmos em qualquer idioma.**
- **Todo texto local** (do idioma) fica em camada separada, para ser traduzido.
- O vídeo é, no fundo, um **motion graphic estilizado e bonito**, com estilo bem definido e fluido.

Proposta do orquestrador para cumprir isso (sem OK ainda):

- A duração das cenas muda com o idioma (o alemão tende a ser mais longo). Renderizar cada plano 3D uma vez, **com sobra no começo e no fim**, e aparar ou segurar conforme a narração.
- O render 3D exporta, por quadro, a posição na tela dos pontos que recebem rótulo, para o texto de cada idioma acompanhar a peça.
- O 3D só é refeito se a diferença de tempo for maior que a sobra.

### Ajuste de duração entre idiomas (Felipe, 2026-11-27)

- Primeiro **medir quanto a duração passa** de um idioma para outro.
- Conforme o caso, **desacelerar (ou acelerar) um pouco já basta**.
- Pode virar recurso de imagem, com **aviso na tela** de que o trecho foi acelerado ou desacelerado em X vezes.

Anotações do orquestrador:

- O aviso é texto local: vai na camada traduzível. O `kit/gps` e o montador já escrevem "acelerado N×" no HUD.
- Vídeo a 60 fps desacelerado repete quadros. Em 3D feito no HyperFrames ou Remotion, renderizar de novo no tempo certo é barato; no Blender (~2,8 s por quadro) vale guardar sobra ou renderizar com mais quadros por segundo.
- O limite de desaceleração sem parecer travado ainda precisa ser testado.

Complemento de render (2026-11-27): um novo render por idioma **aproveita o que já existe e só complementa**. Para isso: guardar a cena (modelos, câmera, animação) e os quadros em sequência de imagens; a animação precisa dar o mesmo resultado a cada render. Esticar o começo ou o fim renderiza só os quadros novos; mudar o ritmo no meio do plano gera quadros novos daquele trecho (com a mesma cena).

### Retenção de arquivos (Felipe, 2026-11-27)

- **Nada é excluído até o card ser publicado**, e "publicado" quer dizer **os 3 vídeos** no ar. Assim qualquer alteração custa menos.

**Decidido:** o sistema de limpeza atual continua (publicar o card manda a pasta do projeto para a Lixeira). O card horizontal passa a **receber 3 links do YouTube**. Os três idiomas ficam dentro da mesma pasta do projeto, então a limpeza leva tudo de uma vez.

A implementar: três campos de link no card; a limpeza só roda com os três preenchidos.

Idiomas: confirmado em 2026-11-27 que são três (PT-BR, alemão e italiano). Onde este arquivo diz "dois idiomas" ou "italiano fora" em notas anteriores, vale esta decisão. Revisão e voz valem para alemão e italiano.

### Gargalos resolvidos (Felipe, 2026-11-27)

- **Voz:** o Felipe sintetiza a própria voz no **VoiceStudio**, e ela é usada nos outros idiomas e **vai para o vídeo publicado** (exceção à regra "voz de IA nunca é publicada", só para a voz dele sintetizada neste projeto). O card precisa de **campo para subir o áudio de cada idioma**.
- **Âncoras:** dividir como no Runeterra, quebrando as cenas por **trechos que fazem sentido**; cada idioma liga a sua fala ao trecho.
- **Ordem de produção:** primeiro **só o PT-BR**, até ficar 100% arrumado, praticamente pronto para postar. Depois os outros idiomas, usando o PT-BR como **molde**. Motivo: não encher o disco, não gastar horas de render em três vídeos juntos e garantir que as versões fiquem idênticas ao original. (Substitui a ideia de produzir os três ao mesmo tempo.)
- **Trechos fotorrealistas:** feitos no **Blender, junto com as ferramentas ArtCraft** (ver `docs/hub_ferramentas.md`).
- **Testes:** haverá testes antes (piloto curto pelo caminho inteiro).
- **Estilo:** o Felipe tem muitos outros canais de referência; a ideia é juntar o melhor de cada um num **estilo próprio e forte** (gráficos, imagens de carros e peças, telemetria etc.).
- **Roteiro é prioridade:** precisa de hooks, rehooks, stakes e payoffs bons. O Felipe tem um documento sobre roteiro (a enviar).

Anotação do orquestrador sobre o VoiceStudio: o teste local foi encerrado e desinstalado em 2026-11-22 (cerca de 10 min para gerar 1 min de áudio; pesos do OmniVoice com licença não comercial; marca d'água AudioSeal ligada por padrão). Antes de publicar, confirmar a licença do modelo usado, porque os canais serão monetizados. Reinstalar quando for a hora.

### Documento de roteiro e retenção (conferido em 2026-11-27)

Arquivo do Felipe: `C:\Users\Felipe\Downloads\Retenção de Audiência em Vídeos Longos.docx` (compilação com referências quase todas de blogs e ferramentas de IA). Conferência por busca na web; nem tudo foi checado.

**Usar como técnica de roteiro (bom senso de escrita, sem número como prova):** gancho sem cumprimento, entregando o que o título promete; stakes (erro, custo, consequência, promessa); roadmap que não entrega o final; cada seção responde à dúvida que a anterior criou; rehooks; open loops encadeados; payoff fechando todos; sem "em conclusão"; CTA curto para o próximo vídeo; frases curtas; pausas antes de virada e capítulo; imagem mostra o que a voz diz; título e miniatura sem repetir o mesmo texto.

**Errado ou sem base (não usar):**

- "Cérebro processa imagem 60.000 vezes mais rápido que texto": sem fonte científica.
- Efeito Zeigarnik como memória superior de tarefa inacabada: meta-análise de 2025 (Ghibellini e Meier, DOI 10.1057/s41599-025-05000-w) não achou essa vantagem; achou tendência a retomar a tarefa. Open loop segue como técnica, sem essa justificativa.
- "Impacto de título no CTR é exponencial": o próprio exemplo é linear (CTR 1,6 vez = cliques 1,6 vez).
- "Reupar e sobregravar vídeo publicado": o YouTube não deixa trocar o arquivo mantendo o link; só edições como cortar trecho.
- "Canais bons têm CTR de 8% a 12%" como meta: o YouTube informa que metade dos canais e vídeos fica entre 2% e 10%.

**Não confirmado (tratar como palpite):** números do relatório Retention Rabbit (23,7% de retenção média, 55% de perda no 1º minuto, 68% e +58%, tabela de metas por duração), cujo original não foi achado; +18% de CTR com miniatura de 2 a 3 elementos; interrupção de padrão a cada 15 a 40 s (as fontes vão de 3 a 45 s).

**Não checado:** "35% dos canais" com desalinhamento de nicho, janela de 8 s, 2 a 5 vezes em telas finais, prazos de produção do LEMMiNO, valores de RPM.

Como medir de verdade: usar a curva de retenção do YouTube Studio dos próprios vídeos.

VoiceStudio: o Felipe informa que o teste lento foi com tudo no máximo; o nível padrão não foi testado. Refazer o teste no padrão.

### Tom do roteiro (regra do Felipe, 2026-11-27)

- **Nada de apontar tudo para um "grande vilão".**
- **Nada de expor uma situação super arriscada a cada momento.**
- O objetivo é **envolver com a história**: chamar a atenção, fisgar e fazer a pessoa querer, naturalmente, assistir até o fim.

Como o orquestrador entende (vale sobre o "stakes" do documento de retenção): a tensão vem de **curiosidade** (uma pergunta que vale a pena responder, uma peça que não encaixa, um detalhe que muda o que se pensava), de gente tentando resolver um problema e de respostas entregues aos poucos. Risco e conflito só quando os fatos trazem, sem inflar. Evitar a fórmula "a maioria erra → custo oculto → isso te destrói".

### Música e SFX (Felipe, 2026-11-27)

- É preocupação importante.
- Fica bom quando a **música acompanha o roteiro** ou quando o **diretor trabalha em cima da batida**.
- Pode haver música de fundo em alguns momentos; **não é regra** ter música o tempo todo.
- **Editar em cima da batida é exceção, um "super trunfo"**: reservado para momentos especiais (aberturas, viradas, revelações).

Propostas do orquestrador (sem OK):

- Mapa musical por trecho no roteiro: clima, intensidade, onde entra, onde para (silêncio também é escolha).
- Detectar as batidas da faixa localmente e permitir que cortes, textos e movimentos "encaixem" na batida mais próxima. A voz manda: quem se ajusta é a música e a imagem.
- Por idioma, os tempos mudam: reencaixar a música por trecho, sem esticar a voz.
- SFX: o banco do `kit/sfx` já tem 236 sons por categoria, mas ninguém ouviu um a um; fazer uma triagem de ouvido antes.
- Conferir a licença de cada faixa para canal monetizado (inclusive música gerada localmente).

## Em discussão

- ~~Segundo idioma: alemão ou italiano.~~ Decidido: alemão. O histórico abaixo fica como registro.
- Parte 1 (superada): a outra sessão recomendava italiano, com base em audiência de TV.
- Parte 2, com foco no YouTube: PT-BR segue como base; segundo idioma vira quase empate. Palpite dela (confiança baixa a média, sem OK do Felipe): **alemão** se o objetivo é receita por vídeo, **italiano** se é crescimento e engajamento mais rápidos; se fosse um só, alemão.
- Sugestão técnica dela: cada idioma exige render próprio, então externalizar todos os textos no Remotion desde o início.
- Parte 3 (com a localização de texto): ela recomenda **alemão** como segundo idioma. Sem OK registrado do Felipe.
  - Argumento: escolher errado custa pouco se a animação for parametrizada; testar alemão com 3 a 5 vídeos e trocar por italiano se não render.
- Checklist de localização proposto por ela (sem OK):
  - todo texto em arquivos de tradução por idioma (JSON), inclusive anotações à mão e rótulos de gráfico;
  - fonte cursiva com ã, õ, ç, ä, ö, ü, ß e vogais acentuadas do italiano, testada antes de escolher;
  - folga nas caixas de texto (o alemão ocupa bem mais espaço que o inglês);
  - um canal separado por idioma (como o texto na tela muda, trilha de áudio extra não resolve).
- Próximo passo oferecido por ela: documento com números, concorrentes e checklist, ou lista de 10 temas do primeiro lote.

### Três idiomas e voz sintetizada (parte 4)

Ideia levantada pelo Felipe como pergunta, **ainda não decidida**:

- Três idiomas (PT-BR, alemão e italiano), cada um em um canal próprio, todos no mesmo Gmail, reutilizando o mesmo vídeo com idioma e textos trocados.
- Felipe grava a voz em português; a IA traduz e sintetiza a voz dele nos outros idiomas.

Resposta da outra sessão (pesquisa de regras **não verificada aqui**):

- Até 100 canais por conta Google; cada um com inscritos, monetização e algoritmo próprios.
- Clonar a própria voz para narração ou dublagem não exige marcar como conteúdo sintético.
- Vídeo próprio traduzido: não achou regra explícita; leitura dela é que não é "conteúdo reutilizado" (não é garantia).
- Riscos: conteúdo repetitivo ou de template (variar estrutura e gancho); mesma conta e mesmo AdSense compartilham punição (Gmail separado por canal isola o risco).
- Custos: revisor nativo para alemão e italiano; testar sotaque e ritmo da voz com nativo; três comunidades; começo lento.
- Ordem sugerida: vídeo 1 em PT-BR e alemão no mesmo dia, italiano uma semana depois; em 3 a 5 vídeos decidir se corta um canal.

Pontos do projeto que a ideia toca (anotados pelo orquestrador):

- O `CLAUDE.md` diz que voz de IA nunca vai para vídeo publicado (única exceção registrada: verticais do F1). Publicar voz sintetizada no horizontal exige o Felipe registrar nova exceção.
- O teste de clonagem local (VoiceStudio) foi encerrado e desinstalado em 2026-11-22: lento demais, e os pesos do OmniVoice têm licença não comercial. A ferramenta de voz está em aberto.

### Plano resumido na parte 5

A outra sessão fechou a parte 5 com "PT-BR, alemão e italiano, com a voz clonada e telas traduzidas". O italiano foi descartado depois, nesta conversa (2026-11-27), e a decisão mais recente vale.

## Dúvidas abertas

Parte 4:

- ~~Dois ou três idiomas?~~ Respondida: dois (PT-BR e alemão).
- A voz em alemão será a voz do Felipe sintetizada? Se sim, é preciso registrar exceção à regra "voz de IA nunca é publicada".
- Com qual ferramenta a voz seria sintetizada?
- ~~Um Gmail ou um por canal?~~ Respondida: um só, o que já roda os Shorts.
- Quem revisa o alemão?

Perguntas feitas pela outra sessão (parte 1):

Perguntas da parte 1:

- ~~Formato: Shorts ou longos?~~ Respondida: longos, 9 a 20 minutos.
- Idioma: voz gerada com roteiro traduzido, ou alguém que domine o idioma para revisar? (aberta)
- Objetivo: receita de AdSense, crescimento de inscritos ou os dois? (aberta)

Perguntas da parte 2:

1. ~~Economia por vídeo ou crescimento rápido?~~ Respondida: maior pagamento, com público (alemão).
2. Quem revisa o roteiro e a narração no outro idioma?
3. Fazer o teste direto (2 ou 3 temas pesquisados no YouTube em cada idioma) ou um documento com a pesquisa?

## Contexto: pesquisa de audiência (parte 1)

Números relatados pela outra sessão. **Não verificados aqui.**

| | Brasil (PT-BR) | Itália | Alemanha |
|---|---|---|---|
| TV em 2026 | forte alta | forte alta | estagnada, fragmentada |
| Herói local | Bortoleto e Rafa Câmara | Antonelli, campeão mundial | nenhum |
| Acesso | TV aberta (Globo) | Sky + TV8 aberta | quase tudo pago |
| CPM estimado | US$ 0,80–3 | € 2,50–5,00 | € 5–9,80 |

- **Brasil:** base de 71 milhões de fãs. Alcance de 52,8 milhões entre fevereiro e julho de 2026 (39,3 milhões em toda a temporada de 2025). Câmara na Haas em 2027.
- **Itália:** Monza com mais de 4,4 milhões de espectadores médios e 39% de share. Sky +27% sobre 2025, direitos até o fim de 2032. Cautela: parte da alta vem do efeito Antonelli.
- **Alemanha:** RTL com só quatro corridas em TV aberta em 2026; Sky exclusiva até o fim de 2027. Canais locais pequenos (Sky Sport Formel 1 ~266 mil, Motorsport-Magazin ~226 mil, Formel1.de ~82 mil, ams.f1 ~19,7 mil). Uma fonte coloca o RPM em só US$ 2,30.
- **Concorrência (parte fraca da pesquisa):** PT-BR tem Sprint Race Brasil, Boteco F1, Fórmula Brumnh; italiano tem The Race Italia, Motorsport.com Italia, Formulatok e quase nenhum explicativo curto. Sem números confiáveis de inscritos e views dos canais independentes.
- **Fontes de CPM:** fluxnote.io e dynamoi.com (estimativas de terceiros).
- **Próxima rodada proposta:** tendência de buscas, amostra de views dos canais menores por idioma e temas que mais viralizam em cada mercado.

## Contexto: pesquisa no YouTube (parte 2, nov/2026)

Números relatados pela outra sessão. **Não verificados aqui.**

| | PT-BR | Italiano | Alemão |
|---|---|---|---|
| Buscas por "f1" no país | 519 mil | 53 mil | 112 mil |
| Receita por 1.000 views, vídeo longo (cálculo dela, a partir do vidIQ) | ~US$ 0,55–0,60 | ~US$ 0,95 | ~US$ 1,55 |
| Maiores canais independentes | GP EM CASA (210 mil), Clube da F1 (101 mil), Canal Enerto (66 mil) | Alberto Naska (1,17 mi, motorsport em geral), Matteo Bobbi (75 mil), Rastrelli (74 mil) | Motorsport-Magazin (294 mil), FormelFranz (52 mil), Lumi F1 (55 mil) |
| Maior vídeo longo recente encontrado | 76 mil (GP EM CASA) | 229 mil (Naska, 16 min) | 80 mil (sport auto, 51 min) |

- **Potencial total (busca × valor por view):** PT-BR em primeiro, alemão com cerca de metade, italiano com cerca de um sexto.
- **Anúncios no meio do vídeo:** disponíveis a partir de 8 minutos.
- **Vaga:** não achou, nos três idiomas, canal de F1 com documentário de 9 a 20 min, motion graphics pesado e transições sem corte.
  - PT-BR: Botequim GP se diz documentário (41 mil, ~3,5 mil views por vídeo).
  - Italiano: explicativos de engenharia funcionam (138 mil views em vídeo de 12 min sobre o câmbio).
  - Alemão: canais pequenos de nicho com médias altas (Fahrer Goat ~170 mil, Hungary599 ~131 mil), publicando pouco.
- **Limites:** unidade do volume de busca do vidIQ não explicitada; "f1" inclui jogo e mods; amostra de ~20 canais por idioma; sem Instagram/TikTok por país; sem Google Trends.

## Contexto: Formula Addict e vaga por idioma (parte 3)

Números relatados pela outra sessão. **Não verificados aqui.**

- **Formula Addict:** 648 mil inscritos; 23 vídeos longos em um ano (~2 por mês), 18 milhões de views (~780 mil por vídeo). Receita estimada ~US$ 3,3 mil/mês (vidIQ, pode estar baixa); patrocínio e membros pesariam tanto quanto AdSense.
- **O que mais rende nele:** 10 a 15 min e título em pergunta ("What's REALLY Changing?" 2,4 mi; "Why Is Lamborghini NOT in F1?" 1,7 mi; "Why is Audi Joining F1?" 1,5 mi). Temas de regulamento, montadora e "por que isso acontece".
- **Escala esperada fora do inglês:** uma ordem de grandeza menor; melhores canais fazem 60 a 130 mil views de média.
- **Alemão:** formato não ocupado (só notícia e análise). NaBravoo (história, 7,7 mil). Berlin Channel (história, não F1): 245 mil inscritos, 654 mil views por vídeo. Ganchos: Audi, Mercedes, Schumacher, Hockenheim.
- **Italiano:** quase não ocupado. Racing Hub (2 mil, +32% em 30 dias). Ganchos: Antonelli, Ferrari, Monza.
- **PT-BR:** já há concorrente grande. RessacaMotor (329 mil); Cortes do Motor (7,6 mil, +61% em 30 dias).
