# Estado: Explicando F1 (vertical e horizontal)

Saído do CLAUDE.md (2026-11-08). Ao terminar um recurso desta área, registre AQUI, não no CLAUDE.md.

- **Explicando F1 (2026-11-01, em construção)**: `F1/` (porta 8766, `F1/Iniciar F1.bat`, fatos na Wikipedia em inglês, acervo em `Downloads\canais\catálogo F1`). Card nasce com `videos.formato` (seletor no quadro quando `canal.toml` tem `formatos`). Horizontal = fluxo do Runeterra. Vertical (`etapas.ETAPAS_VERTICAL`): roteiro → voz pronta (`/voz`, `motor.tarefa_voz_ia` padroniza e mede tempos) → animação → render → publicação; sem gravação nem capa. Animação ✅ (2026-11-02, refeita no mesmo dia: "cada vídeo é um projeto novo"): com roteiro aprovado + voz pronta, `motor.tarefa_animacao` chama `tools/direcao/vertical.py`: o Opus ESCREVE o código JavaScript de cada cena para aquele texto (API em `<docs>/api_cenas.md` = modelos da biblioteca + câmera + efeitos; cena pronta do `catalogo_vertical.md` só quando mostra exatamente a fala), citando TRECHOS → índices de palavra; o código passa pelo `tsc` (`F1/vertical/video/tsconfig.cenas.json`, arquivo temporário `src/_conferir_cenas.ts`; erros voltam ao Sonnet, 2 rodadas, o que não compila vira cena pronta) e por 1 rodada em que o Opus vê um quadro de cada cena (`F1/comum/remotion/quadros.mjs`, folhas numeradas em `trabalho/conferencia_cenas/`) e refaz o que não mostra a fala. O código roda no `Vertical.tsx` via `new Function` com os nomes do bloco `// API:inicio … // API:fim`; cena que quebra cai numa cena pronta. Nada do código de um vídeo fica no projeto Remotion: só no `direcao/vertical.json` dele (versões em `vertical_versoes/`) e renderiza a composição do canal (`canal.toml [vertical]`: projeto, composição, catálogo; `--public-dir trabalho/` com voz.wav) → `saida/final_vN.mp4`, pendência `ver_final`. Painel “Animação” (`PainelAnimacao.tsx`): pedido por plano ou geral (`direcao/pedidos_vertical.json`) → “Refazer com os pedidos” (tarefa `rascunho` → `vertical.revisar`: só os planos pedidos vão completos ao Opus, os outros resumidos sem código, e só os alterados voltam; pedido geral manda todos completos), “Refazer do zero” ou “Só renderizar de novo” (sem Claude). Ponte com a internet nos pedidos (2026-11-07, `tools/direcao/anexos.py`, roda antes do diretor, que segue sem ferramentas): link de imagem no pedido é baixado (sem cota; SVG da Wikimedia pela miniatura PNG) e vai ao Opus como imagem anexa (máx. 4); "pesquise" ou link de página = 1 chamada Sonnet com WebSearch/WebFetch (`claude_cli.chamar(ferramentas=...)`), fatos com fonte entram no pedido como confirmados (cache em `direcao/pesquisas_pedidos.json`). O diretor devolve `nao_feitos` e cada pedido não feito vira aviso no painel (nunca ignorar em silêncio). Render por blocos com cache (2026-11-03, `vertical.blocos`/`renderizar` + `F1/comum/remotion/render_blocos.mjs`): ~3 planos por bloco, corte decidido pelo id do plano; impressão = planos do bloco + quadros + palavras + código de `F1/vertical/video/src`; cache em `<projeto>/blocos_vertical/` (versão atual + anterior); voz entra no FFmpeg concat sem recomprimir. `enquadrar()` na API = câmera que mostra o objeto inteiro (regra na folha de estilos, aprovada v3). Briefing (2026-11-02, `tools/direcao/briefing.py`, vale para os dois canais): .txt com seções entre linhas de "=" — só a seção ROTEIRO é narrada; o resto vai para `direcao/briefing.json` (fica até chegar outro briefing; editar o roteiro não apaga). O diretor vertical recebe o briefing menos fontes e "pontos para decidir"; a conferência usa as linhas de FATOS e EVITAR como "fato do briefing" (acima da wiki; briefing com fatos novos apaga o cache da conferência). Painel: bloco "Briefing do vídeo" no Roteiro. Formato de exemplo: `Downloads\roteiro com briefing.txt` (Antonelli). F1: `F1/vertical/video/src/Vertical.tsx` = cenas do piloto com parâmetros (`TIPOS`) + sobreposições (placas, contador, chips, selo, riscado, medidor, gota, chuva); placa nova na mesma posição substitui a anterior. Modelos reaproveitáveis em `F1/comum/remotion/modelos/` (`Carro3D`, `Vantage` = Safety Car, `mundo.tsx` = cenários 3D e ajudantes de câmera/cena, saídos do piloto publicado; `extras.ts` = piloto sem rosto com capacete/boné e tom de pele, kart, pódio, escada de categorias, mapa real de país pelo ISO com alfinete de cidade [Natural Earth 1:50m, `paises.json`], número no carro; `desmonte.ts` = explodir/isolar/raioX/cortar com peças marcadas por `peca()`, técnicas do skill Teardown [MIT] reescritas, `restaurar()` a cada quadro; `pneus/` = pneu Pirelli 2026 [`pneu.ts`: marcações da lateral extraídas das fotos oficiais em `F1/dados/modelos3d/<composto>*.jpg` para `lateral.ts`, sulcos do intermediário/chuva, roda de liga leve vazada de 10 raios em Y; usado nas rodas do carro e no pneu do estúdio]; `volante.ts` = volante genérico de 2026 sem equipe, comandos principais como peças [apertar/girar/puxar/luzesDeTroca/telaDoVolante], resto da face só aparência, nome do canal no topo da borda; `geografia.ts` = mapa do Brasil com estados/cidade [IBGE] e circuito com traçado real em metros [bacinger/f1-circuits, MIT; traçados antigos `monaco_1984` e `donington_1993` tirados das imagens da Wikimedia em `F1/dados/modelos3d/`; dados em `modelos/geo/`; altitude SRTM 30 m em `alt`], set "real", `cenario.ts` = cidade, muros, arquibancadas e boxes com `criarCircuito(nome, {cenario: true})`, `filmar` = câmera que transita em volta do carro; gráficos que interagem com a cena em `src/InfograficosDinamicos.tsx`; trilha ligada por padrão no vertical, efeitos swoosh/pop/alerta, sem som de carro; composição "Modelos" = vitrine); o código de cada vídeo não fica guardado, só os modelos. Estilo em definição: `F1/vertical/docs/folha_de_estilos.md` (a revisar pelo Felipe) e `F1/vertical/docs/analise_reels.md`, lidos com as ferramentas gratuitas do Hypit (projeto em `F1/vertical/dados/estilo`, programas em `C:\\Users\\Felipe\\hypit`, porque o `AppData` deste app estoura o limite de caminho). Cada vídeo tem um mundo próprio: nunca uma peça segurando o vídeo inteiro. Motor de produção do Hypit não usado; a montagem é com as nossas ferramentas. **Motor único, projetos por formato (2026-11-20, fase 2 da organização do F1): `node_modules` e `package.json` ÚNICOS na raiz do repositório (Remotion 4.0.539, React, three; sem cópia por canal nem junção). Biblioteca compartilhada pelos dois formatos em `F1/comum/remotion/` (`modelos/` = Carro3D, pneus, volante, desmonte…, `kit.tsx`, e os scripts `quadros.mjs`/`render_blocos.mjs`, que rodam com cwd = o projeto). Projeto do VERTICAL em `F1/vertical/video/` (`src/Vertical.tsx`, Infográficos, `Root.tsx` com Vertical, Carro3D e Modelos); projeto do HORIZONTAL v1 em `F1/horizontal/v1/` (`src/`: Horizontal, cenas 3D, cartões, testes; render: `npx remotion render src/index.ts <Composição>` com cwd na pasta do projeto, GL `angle`); motor documental em `F1/horizontal/` (kits, HyperFrames, `remotion/`). Cada formato importa a biblioteca por caminho relativo (`../../../comum/remotion/...`). `canal.toml`: `[vertical].projeto`/`biblioteca`, `[horizontal].projeto`. Nunca importar código de canal em `app/video`, nem o contrário: os canais só compartilham o motor.**
- **Horizontal do F1 (2026-11-06, padrão v1)**: `F1/horizontal/docs/folha_horizontal.md` (Formula Addict + Documentsui, regras próprias) e `F1/horizontal/v1/src/` (composição `Horizontal`, plano JSON em segundos: cenas estudio [claro/cheio/escuro/tecnico, palavra gigante atrás do carro com decodificação, anotações à mão], pista [Interlagos .glb, carro apoiado no asfalto: helicoptero/drone/lado/passagem com rastro/pov], pessoa, capitulo "PARTE 0N", solta; transições corte/empurrar/glitch/cortina/cor em `linha.tsx`; demo `DEMO_HORIZONTAL`). Diretor ✅ (`tools/direcao/horizontal.py`, `F1/horizontal/docs/api_horizontal.md`, `[horizontal]` no canal.toml, modelo sonnet): roteiro em blocos de ~220 palavras com cache por conteúdo (`direcao/horizontal_blocos/`), trechos → palavras → segundos; render por blocos (`vertical.renderizar` com `composicao`/`props`, cache `blocos_horizontal/`, .glb por link na pasta pública). Card horizontal NOVO do F1 = fluxo animado (`etapas.ETAPAS_HORIZONTAL_ANIMADO`: roteiro → narração [gravação do Felipe, `limpar_gravacao` + tempos] → direção → render → publicação); motor reconhece o fluxo animado pela etapa `voz_ia` (`motor._animado`, `_diretor`); direção fica em `direcao/vertical.json` como no vertical (painel Animação serve aos dois). Card horizontal antigo continua no fluxo do Runeterra.
- **Pit stop coreografado ✅ (2026-11-09)**: `F1/comum/remotion/modelos/pitstop.ts` (`criarPitStop`, `pitStop`, `noPit`, `PAPEIS`; API em `api_cenas.md` "Pit stop"), coreografia e IK portados do teste livre do Blender (`C:\Users\Felipe\opus-livre-teste\pit-stop\scripts\cena.py`). Motivo: sem modelo na API o Opus tentava desenhar 22 mecânicos à mão e a direção passava de 15 min. Ajustes do Felipe no v2 (2026-11-09, v3): painel de luzes pendurado num braço preso à parede do box (sem poste no chão; some no estúdio); faixa do ombro e tronco dividiam a face de cima (z-fighting + sombra = cor "piscando"): tronco termina dentro da faixa; `foco` deixa os outros translúcidos (material fantasma único, sem profundidade nem sombra, para não piscar) ou `outros: "some"`; rodas do carro rolam na chegada (`rolarRodas`). v5 (2026-11-09): "rodas ao contrário" era serrilhado (wagon-wheel), não sinal: o sentido estava certo em câmera lenta, mas a 30 q/s o pneu girava 60–80° por quadro e o desenho lia como ré; o giro visto agora fica limitado a ~4,5 m/s (`rolagem` no `pitStop`, `rolarRodas(carro, metros, velocidade)`); efeito sonoro com `"obrigatorio": true` passa por fora do teto de 1 a cada 12 s (`vertical.sons`).
- **Rodas: giro + esterço juntos (2026-11-11)**: causa de "dianteiras não giram / não esterçam": `rolarRodas` e `estercar` usavam `girarPeca` (absoluto, os 3 eixos) no MESMO grupo da roda, então a última chamada apagava a outra (o `AND` dos planos fazia poeNoCircuito→rolarRodas→estercar: dianteiras só esterçavam; quem rolava depois do poeNoCircuito perdia o esterço). Agora `girarPecaEixo` (desmonte.ts) mexe num eixo só e a roda tem `rotation.order = "YXZ"` (esterço no carro, rolagem no eixo virado); `rolarRodas`/`V_RODA` moram em efeitos3d.ts (pitstop.ts reexporta). `poeNoCircuito`/`poePinturaNoCircuito`/`transito` já rolam as 4 rodas pela distância de f (`v` real em m/s, padrão 80). Esterço de `noCircuito` refeito: curvatura média em ~28 m, 4 m à frente, Ackermann com curva de visibilidade (lenta ~20-25°, rápida 5-10°, reta 0, sem tremer). "Calota não gira com a borracha" era serrilhado: 10 raios = 36°, e a ~37°/quadro (V_RODA 4,5 com `v` menor que a real) os raios pareciam parados; `V_RODA` = 2,5 m/s (13°/quadro).
- **Boneco articulado e mapa por região (2026-11-12, v2 do "transporte dos carros")**: Felipe reprovou bonecos "pedaço de pau" deslizando e continente cinza. `criarPiloto` ganhou coluna/pescoço/pulso/tornozelo (em repouso igual ao antigo; `userData.juntas`, `userData.corpo` = raiz girada, o kart continua igual); poses em `modelos/boneco.ts` (andar com `faseDoPasso`, carregar, agachar, abaixar, apontar, acenar, empurrar, `maos`, `olhar`). `criarMapaRegiao` (extras.ts) = países com cor e fronteira, oceano azul. Tudo na API do Vertical.tsx e em `api_cenas.md`.
- **Mapa dos EUA, Caesars Palace, rótulo ancorado e tabela de classificação (2026-11-21, feedback do Felipe no "GP de Las
  Vegas 2026", branch f1-mapa-eua-caesars-tabela)**: `modelos/eua.ts` (`criarMapaEUA`, `zoomNoMapa`; dados us-atlas 3.0.1 =
  Census Bureau, domínio público, em `geo/eua.json` gerado por `geo/preparar_eua.py`: 48 estados + DC em Albers, 4 cores
  sóbrias por vizinhança, condados de Nevada, nomes, cidades). `modelos/caesars.ts` (`criarCaesarsPalace` "atual"/"1981",
  conferido em fotos do Commons e na Wikipedia; `criarEstacionamentoCaesars` + `revelarEstacionamento` = o circuito do
  plano do vídeo levado para a biblioteca; `rotuloEm` + `conferirRotulos` = rótulo ancorado com checagem automática
  `ERRO_ROTULO`, chamada no Vertical antes de desenhar). Gráfico `classificacao` (InfograficosDinamicos, sem seta).
  Causa da tag "ESTACIONAMENTO" fora do centro: posição escrita à mão no MUNDO (25, 3, 6) com o estacionamento num grupo
  escalado a 0,3 (centro ≈ (-1, 0, 2)). Pendente: modelo de referência do estacionamento do Felipe (nenhum arquivo em
  `F1/dados/modelos3d` nem `F1/dados/mapas` com caesars/estacionamento/parking/1981/1982 em 2026-11-21); o traçado do
  estacionamento ainda é o do plano (não o oficial de 1981, que é um zigue-zague anti-horário de 14 curvas, 3,65 km).
- **Las Vegas noturna em NEON (2026-11-21, pedido do Felipe: v1 do "GP de Las Vegas 2026" "muito escuro e sem vida")**:
  padrão de `criarCircuito("lasvegas", { cenario: true, noite: true })` (`neon: false` volta ao antigo). Peças fixas em
  `modelos/neon_vegas.ts` (arestas/aro/quinas/letreiros de neon nos prédios do OSM, 4 grades de janelas, Sphere de LED,
  cones e poças de luz nos postes, névoa roxa no horizonte, pulso) ligadas em `cenario.ts`/`geografia.ts` (tubo de neon
  no alambrado e na base do muro, traçado rosa nas margens com pulso de luz, asfalto fosco um pouco mais escuro).
  Por quadro em `modelos/pos_neon.ts` (`desenhar(w, t)` no lugar de `w.r.render` no `Vertical.tsx`): só com o circuito
  em neon visível liga céu/névoa/luz ambiente arroxeados, traçado acendendo com a altura da câmera, luzes traseiras de LED
  dos carros (luz de chuva + LEDs das placas da asa traseira, referência: short do Felipe; filete da cor da equipe; sem
  farol/seta) e EffectComposer (UnrealBloom limiar 1 + OutputPass + correção de cor), desfazendo tudo depois. Sem o
  circuito em neon o desenho é a mesma chamada de antes (diff de pixels 0 em 7 cenas não-neon, incl. cenas prontas noturnas
  de outro vídeo). `minimapa` de Las Vegas em neon. Asfalto espelhado foi rejeitado pelo Felipe: nunca reflexo.
- **Velocidade, tráfego e câmeras (2026-11-21, feedback do Felipe no "GP de Las Vegas 2026"; branch f1-velocidade-trafego-cameras)**:
  `modelos/velocidade.ts` liga sozinho em plano com carro/câmera de pista (poeNoCircuito, poePinturaNoCircuito, transito,
  pelotao, filmar, perseguir, filmarVariado) e câmera abaixo de ~90 m: película de asfalto (grão, trincas seladas, manchas;
  a malha da pista com UV), juntas e remendos, postes do alambrado a cada 3 m, painéis vermelho/branco de 2 m no pé do muro
  (sem cenário: balizas), lente +7° e tremor leve perto do carro, e borrão de movimento por acúmulo (o `Vertical.tsx`
  redesenha o plano em 4 instantes num obturador de 180° e tira a média: `quadroEm(t)` + `borrarMovimento`). Opt-out
  `semVelocidade(w)` / `{ velocidade: false }`; ajuste `velocidade(w, {...})`. Cenas sem pista: mesma chamada de antes
  (diff 0). `pelotao` (até 22 carros, formas pelotao/fila/duelo/espalhado, sem sobreposição), câmeras novas em `filmar`
  (rodaFrente, tresQuartos, travelling, nariz, halo, helicoptero, drone, grua, passagem), `filmarVariado` (+ `c.n`) e
  `TIPO_CAMERA`. Causa da "luz saindo do pneu" aos 5 s: código do plano fe741a8f do vídeo (freava e chamava `aquecer` nos
  freios dianteiros), não a biblioteca; regra nova no regras_de_direcao.md. Medidas e custo: `api_cenas.md`, "Velocidade".
- **Las Vegas com vida e logo na Sphere (2026-11-12, v3 do "transporte")**: chão de dia em asfalto/terreno (o bege claro parecia neve), `vidaDeVegas` em cenario.ts (postes, palmeiras, letreiros de neon instanciados, fora dos prédios reais), Sphere escura com o logo do canal em 4 calotas de projeção plana (sem distorcer de frente). Logo embutido em `modelos/logo_canal.ts` (data URL; cópia em `logo_canal.jpeg`, fonte `Downloads\logof1.jpeg`) porque o render usa a pasta do vídeo como pública; o `Vertical.tsx` espera a imagem decodificar antes do 1º quadro (`logoPronto`). Interlagos não muda (mesma escolha de cor do chão para listas de 3 cores).
- **Ajustes v5 do "transporte" (2026-11-12)**: logo da Sphere recortado em disco (canvas com clip circular e aro vermelho, fundo transparente); `logo_canal.ts` segura o render com `delayRender` no carregamento do módulo (a espera dentro do efeito do `Vertical.tsx` gerava quadro preto/velho no `quadros.mjs`). Letreiros de neon: painel 0,45 m à frente da moldura + polygonOffset (piscavam); texturas de janelas com anisotropia 16. `plano()` (Carro3D, marcações dos sets) com polygonOffset. Cartões centralizados: `riscado`, `selo` e `Placa` com `width: max-content` + `nowrap` (o "ÚNICO ESTOQUE" quebrava e ficava colado à esquerda); `palavra` com largura máxima.
- **Circuito de Las Vegas ✅ (2026-11-10)**: `criarCircuito("lasvegas", { cenario: true, noite? })` (API em `api_cenas.md`, "Las Vegas"). Traçado bacinger/f1-circuits us-2023 (MIT), 6.202 m (oficial 6.201: +1 m, +0,02%), conferido com o OpenStreetMap (raceway "Las Vegas Strip Circuit", ~0,5 m) e com o traço de uma volta do MultiViewer (circuito 152, RMS 4,6 m); f 0 = linha de chegada = início da volta cronometrada do MultiViewer (o ponto 0 do geojson ficava 147 m depois); 17 curvas do MultiViewer projetadas no traçado; ruas dos trechos conferidas no OSM ao longo da volta; sentido anti-horário (F1.com). Cenário de rua em `cenario.ts` (`rua`, `real`, `noite`): 1.100 prédios do OSM (ODbL) com altura real quando há, lago do Bellagio, pit lane, Sphere/High Roller/Torre Eiffel em volume simples, muro colado na pista; grade genérica só no horizonte. Dados em `modelos/geo/lasvegas.json`, gerados por `F1/dados/mapas/lasvegas/preparar.py` (fontes baixadas na mesma pasta; `conferencia_tracado.png` = traçado da lib sobre o desenho do Felipe). `minimapa` ganhou `circuito`; `TRECHOS` por circuito; `marcoNoCircuito`; `enquadrar`/`panorama` recuam a névoa com a câmera acima de 3,2 km (Interlagos não muda). Fica de fora: arquibancadas em posição exata (sem planta oficial), telões e marcas, linha de largada separada (~92 m antes da chegada), perfil de altitude.

## Vertical a 60 fps (2026-11-12)
Ordem do Felipe. `Root.tsx` (`VERTICAL_FPS = 60`), `F1/canal.toml [vertical] fps = 60`, `vertical.py` `FPS` lido do canal.toml e passado como `fps` a `blocos`/`renderizar`/`remixar` (fps na chave dos blocos: cache de 30 não é reaproveitado). Horizontal continua 30 (`horizontal.py` `FPS` próprio, `[horizontal] fps`). Cenas já usam segundos; `V_RODA` é m/s (mesmo giro no tempo). Falta testar: render curto 60 vs 30 e um card com "Só renderizar de novo" (reiniciar o servidor do F1 antes).

## Freio de F1 na biblioteca (2026-11-12, vídeo "pq os freios de um F1 ficam incandescentes?")
`modelos/freio.ts` (`criarFreio` f1/rua, `freioDoCarro`, `girarDisco`, `apertarFreio`, `corDoCalor`, `calorNosDiscos`) e `modelos/freio_cena.ts` (`aquecer` com halo, `fluxo`, `ventilar`, `criarTermometro`/`medirTemperatura`, `criarMedidorTermico`/`ponteiro`, `criarPlacaCarbono`, `poeHibrido`/`caminhoDaEnergia`, `noFreio`, `tomadaDeAr`, `escurecer`). Medidas da Brembo (disco 328/280 mm, 32 mm, ~1.050 furos radiais na borda, pinça 6 pistões). O `carro()` ganhou os 4 conjuntos de freio (peças `freio_<eixo>_<lado>`, irmãos das rodas: no pit stop a roda sai e o freio fica) com a tomada de ar do lado de dentro; `estercar` vira o conjunto dianteiro e `rolarRodas` gira só o disco. Calor: material próprio por disco na 1ª vez (carros da mesma equipe são clones) e `aoRestaurar` esfria tudo a cada quadro. Nada de Object3D no userData (vira JSON no clone): rotor e pastilhas achados pelo nome. API no `Vertical.tsx` e em `api_cenas.md` ("Freio").
Vídeo "pq os freios de um F1 ficam incandescentes?" (card 12, 2026-11-12): direção escrita à mão pelo motor (34 planos, `direcao/vertical.json`; fonte em `trabalho/teste/planos.py` + `gerar.py`/`conferir.py`/`render.py`), `saida/final_v1.mp4` a 60 fps. `palavra` encolhe a fonte em palavra longa ("INCANDESCÊNCIA" saía cortada). v2 (2026-11-13, pedidos do Felipe: "coisas pulando e travando"): medido no final_v1 (diferença média entre quadros
consecutivos): sem quadros duplicados nem emendas ruins entre blocos (12 blocos, quadros inteiros, emendas = cortes), mas
saltos PERIÓDICOS nos planos com câmera presa ao carro (a cada 12–34 quadros, conforme a velocidade). Causa: `noCircuito`
calculava o giro (e o esterço) só no ponto inteiro do traçado (degrau a cada ponto); `filmar` media a distância ao muro
em pontos de 2 em 2 a partir do ponto do carro (degrau na câmera baixa). Agora tudo é interpolado. `rolarRodas` com `v`
mudando a cada quadro saltava (distância TOTAL × V_RODA/v): acima de V_RODA o giro vem do tempo do vídeo
(`definirTempo`, posto pelo Vertical.tsx a cada quadro; estado do quadro anterior não serve porque o Remotion desenha fora
de ordem, em 3 abas). Pedais/piloto no cockpit: `poePedais`, `poePilotoNoCarro`, `linhaDoFreio` (freio_cena.ts).

Cockpit em proporção real (2026-11-17, branch f1-cockpit-proporcoes, para o vídeo da visão interna; Felipe: "sem espaço
para os braços nem para o volante"): o monocoque ganhou abertura de verdade (`casco(..., cava)` afunda os vértices da
elipse da abertura; borda acolchoada e apoio de cabeça), halo refeito (pilar preso à frente da abertura, arco na altura
da testa), piloto simples dentro (capacete menor, ombros, volante). `poePilotoNoCarro`: reclinado ~52°, ombros mais
juntos (0,33 m), mãos nas empunhaduras por IK, volante real na coluna (`poeVolanteNoCarro`). Câmeras prontas
`cameraNoCockpit` (piloto, ombro, rosto, lado, cima) e `alvoDoCockpit`. Medidas em `COCKPIT` (Carro3D.tsx). Capacete do
`criarPiloto` de 0,28 x 0,33 x 0,30 m para 0,26 x 0,30 x 0,28 m. O exterior do carro e as câmeras externas não mudaram
(quadros conferidos antes/depois).

## Pedido pesado → orquestrador (2026-11-21, branch f1-pedido-pesado)
Pedido que exige capacidade nova ou julgamento visual vai para o chat (orquestrador) em vez de o diretor tentar e falhar:
botão "Ao orquestrador"/"enviar ao orquestrador" no painel Animação, ou sozinho quando `revisar` recebe `nao_feitos` com
`capacidade: true`. Detalhes, arquivos e comandos em `docs/estado/sistema.md` (Pedidos pesados).

## Capacidades do vertical pedidas pelo Felipe (2026-11-14, branch f1-capacidades-vertical)
O diretor devolvia "pedidos não feitos" por falta de capacidade ou por regra. Agora (testes em `tools/direcao/testar_vertical.py`):
- **Pedido do Felipe vence a regra**: `vertical.sistema()`, o prompt de `revisar` e `regras_de_direcao.md` dizem que o pedido
  explícito dele sempre é cumprido; `nao_feitos` só por falta real de capacidade, com o arquivo exato que falta.
- **Números na tela**: checagem nova `vertical.checar_regras` (no fim de `conferir`, só avisos no card, sem Claude):
  `avisos_numeros` compara os números escritos na tela (placas, contador, gráficos, título/selo/medidor, `rotulo`/`texto:`
  do código) com os da fala (algarismos e por extenso: "seis vírgula duzentos e um" = 6201). Exceções: seção do briefing
  `NÚMEROS NA TELA (pedido do Felipe)` (`numeros_liberados`) e os números escritos nos pedidos do card
  (`liberar_dos_pedidos` → `direcao["numeros_liberados"]`; "cena 5" não conta). Só aqueles números são liberados.
- **Som por arquivo**: `som.arquivo` (+ `volume`, `duracao`): `achar_som` (absoluto, `dados/comum/`, pasta do projeto,
  raiz, `dados/comum/freesound_cache`, `F1/horizontal/kit/sfx/banco`, `dados/comum/sfx`), `som_de_arquivo` normaliza como o
  catálogo (cópia em `trabalho/sons_arquivo/`), `avisos_sons` avisa o que não existe; o render segue sem ele. A chave do
  cache `sons_vertical.json` dos sons do catálogo é a mesma de antes (vídeos antigos não trocam de som).
- **Legenda**: `legenda` {fundo, opacidade, raio, margem, branca} no plano ou na raiz da direção (`_props` → `legenda`);
  `Legenda` do `kit.tsx` desenha a caixa numa camada separada. Sem estilo, nada muda (nem a impressão dos blocos).
- **Logos de arquivo**: `F1/comum/arte/logos/<chave>.png` (`canal.toml [vertical] logos`), `modelos/logos.ts` (`logo`,
  `aplicarLogo`, `criarPainelLogo`, `criarLivro`); o Python copia os citados (`logo:fia`) para `trabalho/logos/` e passa o
  mapa nas props; o `Vertical.tsx` só desenha depois de decodificar. Lista dos disponíveis no prompt; logo que falta =
  aviso "falta o logo ... coloque o arquivo F1/comum/arte/logos/fia.png". A pasta está vazia: o logo da FIA o Felipe fornece.
- **Circuitos**: `silverstone` com `TRECHOS_SILVERSTONE` (nomes conferidos na Wikipedia: 1 Abbey … 14 Chapel, 15 Stowe,
  16 Vale, 17-18 Club); `monaco` atual documentado (vs `monaco_1984`), `TRECHOS_MONACO` vazio (numeração não conferida).

## Documentário: correções do 1º uso real (2026-11-14, card 20 "Nove milésimos")
Detalhes em `F1/horizontal/docs/painel.md` ("Correções do 1º uso real"). Card novo saindo com "Narração" (`voz_ia`) e
sem voz guia NÃO era bug do código: a pasta principal estava no PR #108 (antes da 7a) com #109–#111 já no GitHub, e o
painel tinha subido desse código. Agora `app/servidor/versao.py` avisa no quadro (pasta atrás do origin/main ou código
mudado sem reiniciar). Markdown (`**`, `#`, `_x_`) sai da narração ao receber o roteiro (todos os canais; roteiro sem
Markdown sai idêntico); conferência F1 lê a sessão do texto (GP/ano/sessão em PT) e confere setor; "sem fonte" nunca
aparece como conferido; verificação aceita cronômetro na tela (1:16.514 = 76.514) e cartão "PARTE 02".

## Visão do piloto v4 (2026-11-18, pedidos do Felipe sobre a v3)
Biblioteca: suspensão do `carro()` presa NA superfície do bico/chassi (`superficie` em Carro3D.tsx, mesma interpolação do
`casco`; antes o ponto de dentro ficava fixo em x 0,14–0,18 e os braços de cima passavam do topo do bico, "voando"),
montante dentro de cada roda unindo os braços, barra de direção e pushrod; boca do sidepod virou moldura arredondada com
fundo recuado (a placa preta chapada parecia erro); retrovisores, banco (novo, concha sob o piloto) e apoio de cabeça
viraram peças próprias; nomes `halo_arco`, `halo_pilar`, `borda_cockpit`. `realcar` (a peça acende: emissivo + contorno)
e `campoDeVisao` (leque com degradê, bordas e volume) em efeitos3d.ts. Direção da v4: `trabalho/v4/planos_v4.py` +
`gerar_v4.py` (parte da v3 guardada em `direcao/vertical_versoes/vertical_v3.json`), POV real nos trechos "e mesmo assim
precisa enxergar tudo" e na combinação final (sem `etapas`).

v5 (2026-11-18, "imundice no primeiro frame"): a causa era o desmonte, não a malha: `raioX`/`isolar` com k = 0 (o
começo de qualquer plano que "acende" o raio-X numa palavra) já trocava o material pelo fantasma com opacidade 1 e SEM
gravar profundidade; com as cascas DoubleSide, as faces de dentro do cockpit/sidepod saíam por cima das de fora (lascas
brancas e serrilhadas). Agora k <= 0,01 não mexe em nada e o fantasma quase opaco (> 0,6) grava profundidade
(desmonte.ts). De quebra o sidepod não atravessa mais o cockpit: sem a cava "todo" (que esticava triângulos até o
fundo), o lado de dentro para numa parede lisa (`limiteX` em `casco`, `meiaLargura`). Conferido em folha de 30 em 30°
em volta do carro, por baixo, de cima e em raio-X 0,3/0,85.

v6 (2026-11-18): apoio de cabeça virou encosto fino atrás do capacete (as cápsulas em volta do pescoço pareciam
"almofadinha de avião"); banco refeito atrás das costas (o encosto estava inclinado ao contrário e atravessava o peito)
e cinza-azulado; interior do cockpit grafite azulado + forro liso por dentro da borda (`forroDoCockpit`: escondia os
"dentes" brancos da cava vistos do POV); cinto em X (`cintoEmX`, dentro de `poePilotoNoCarro`); volante com `giro` e mãos
presas às empunhaduras; `cockpitNaPista`/`marchaDe`; tomada "pov"; `espelhoReal` (Reflector) e cabeça do retrovisor
virada para o piloto, haste por fora (cruzava o vidro na visão do piloto).

v7 (2026-11-18): regra do Felipe: iterar só no que foi pedido (blocos). Biblioteca: tomada "olhos" (POV na altura real
dos olhos), `rodasRapidas` (opt-in), arnês preso ao tronco do boneco passando por cima dos ombros (`criarArnes`, substitui
o X), retrovisor com pilar nascendo do sidepod, borda na cor do carro na tomada de ar sobre a cabeça (a "bola preta").
Direção: `trabalho/v7/gerar_v7.py` (parte da v6 e muda só os planos pedidos; `mudou.json`), prova em `diff_v6_v7.txt`.

v8 (2026-11-18): biblioteca: argola da tomada de ar removida; `COCKPIT.volante` = [0, 0,585, -0,56], incl -0,12 (altura do
peito, face quase vertical; afeta todo carro com volante); tomada "olhos" centrada (x 0); arnês em fitas largas brancas
(geometria de fita na tangente do macacão). Direção: `trabalho/v8/gerar_v8.py` (só o plano do campo de visão: radar azul
na pista + contorno azul nos carros à frente + rótulo na cena); diff em `trabalho/v8/diff_v7_v8.txt`.

v9 (2026-11-18): luva com dedos para piloto de capacete (`luva` em extras.ts; boné continua com mão de pele); a segunda
coluna de direção de `poeVolanteNoCarro` saiu (o volante já tem a dele, peça "engate_rapido"; depois da v8 as duas saíam
em ângulos diferentes). Direção: plano "Ele não enxerga…" com a câmera centrada (tinha x 0,07 herdado da tomada torta) e
destaque do volante sem a coluna. `trabalho/v9/`.

v10 (2026-11-19): mãos refeitas pelas referências onboard: luva clara (#eceef2) com faixa no dorso e reforço dos nós nas
cores do macacão, punho fechado (falanges a 65° e 130°); em `poePilotoNoCarro` cada mão vai à empunhadura do volante
(centro da peça `empunhadura_*`, 1,2 cm para fora e 5,8 cm para o piloto; cotovelo para baixo), pulso orientado no espaço do volante (dorso para o
piloto, nós ao longo do cabo, antebraço vindo de baixo e de fora). Só mãos mudaram (`trabalho/v10/diff_v9_v10.txt`).

v11 (2026-11-19): `escavar` (Carro3D.tsx) afunda e escurece os vértices da face da frente da casca numa elipse = entrada de
ar de verdade; usada no sidepod (a moldura da v4 saía flutuando na frente do sidepod) e no airbox (o disco preto saía
acima da casca: era a "bola preta"). Mãos: `criarMaoNoVolante` (freio_cena.ts), filha do volante: 4 dedos com 3 falanges
cada encostadas na seção real do cabo (contorno `PEGA` exportado do volante.ts, z -0,0295 a 0,0115), polegar com 2
falanges entrando na janela do corpo do volante, dorso/palma em casca convexa, punho azul com faixa amarela orientado
pelo antebraço; a mão do boneco (`pulso`) fica oculta no piloto do cockpit. `trabalho/v11/`.
v12 (2026-11-19): `criarMaoNoVolante` refeita em medidas anatômicas (Felipe: "é só fazer uma mão normal"): dedos 0,062-0,084
(falanges 4:2,5:2, raio ~0,01), nós atrás da haste (t=284° na elipse folgada), dedos contornam por dentro e as pontas
param na frente da haste; palma em casca convexa no lado de fora indo até o pulso ~0,09 à frente; polegar 2 falanges
por cima do indicador; faixa amarela só no punho (a do dorso saiu). Sem polegar na fresta: a luva branca aparecia pela
janela como bolinha ao lado dos botões. `trabalho/v12/`.

**Acervo 3D em subpastas (2026-11-20):** `F1/dados/modelos3d/` é organizado pelo Felipe em `carros/`, `pistas/` e `pneus/` (e vai receber referências baixadas à mão). Tudo que lê essa pasta (montador `receitas.py`, `kit/gps/py/pista.py`, `diretor/ativos.py`, `tools/direcao/horizontal.py`, `remotion/preparar.mjs`, `hyperframes/preparar.mjs`, `blender/senna.py`, `hyperframes/vhe_interlagos/preparar.py`) procura o arquivo pelo **nome**, em qualquer subpasta. Nomes de arquivo devem ser únicos entre as subpastas; não mover arquivo exige nada no código.

**Polegar e DRS no vertical (2026-11-20):** `polegar(p, nome, k)` (freio_cena.ts) leva o polegar do piloto a um botão do volante e o afunda (FABRIK de 3 ossos; polegar de repouso = grupo `polegar_fixo`, o articulado = `polegar_mov`, trocados só quando k > 0). `drs(car, k)` (efeitos3d.ts) abre a aba móvel `aba_drs` da asa traseira de Carro3D (articula atrás; fechada fica na posição de sempre). Prova: 12 quadros de 4 planos antigos idênticos pixel a pixel antes/depois; cenas novas conferidas em sequência (polegar k 0→1, aba aberta/fechada de lado). Nota: o hash dos blocos de render inclui `F1/comum/remotion`, então o próximo render refaz todos os blocos uma vez. Limite conhecido: o polegar esticado é mais comprido que o de repouso (alcance real do botão OT, ~8 cm a partir da palma) e parece grosso em close; o dedo não usa o resto da mão (a mão não gira).
