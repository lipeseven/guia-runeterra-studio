# Pedido: vídeo da Ferrari 2026 feito do jeito do HyperFrames

Você vai fazer um vídeo horizontal (1920×1080, 30 fps) de ~40 s para o canal **Explicando F1**, usando o
**HyperFrames** e o fluxo dele, do zero. É um teste de comparação: faça o melhor vídeo que o HyperFrames consegue, sem
copiar nada de fora deste pedido.

## Onde trabalhar
- Tudo dentro de `C:\Users\Felipe\hyperframes-teste\comparacao\` (crie o projeto em `comparacao\video\`).
- Não leia nem altere nada fora de `C:\Users\Felipe\hyperframes-teste\`.
- Rode o CLI com a telemetria desligada: `HYPERFRAMES_NO_TELEMETRY=1` e `DO_NOT_TRACK=1`, versão
  `npx --yes hyperframes@0.9.20 ...`. Não instale plugin nem skill global.

## Instruções do HyperFrames (leia antes de tudo)
As skills oficiais estão em `C:\Users\Felipe\hyperframes-teste\_fonte\skills\` (leia como arquivos):
- `hyperframes\SKILL.md` e as referências que ela indica, em especial `references\types\explainer.md`,
  `references\types\3d.md`, `references\story.md`, `references\spec.md`, `references\motion.md`,
  `references\runtimes.md`, `references\review.md`;
- `hyperframes-registry\SKILL.md`: procure blocos prontos antes de escrever à mão;
- `hyperframes-cli\SKILL.md`: comandos (`init`, `add`, `check`, `snapshot`, `render`).

Siga o fluxo dele: escolha uma das três linhas de história (escolha você, sem perguntar), escreva o `SPEC.md`, monte,
rode `check` até zerar os erros, faça a revisão por `snapshot --review` com `REVIEW.md` e renderize.

## Matéria-prima (`materia_prima\`)
- `assets\narracao.mp3`: a narração (é a voz do vídeo, não troque).
- `transcricao_palavras.json`: cada palavra com início e fim em segundos.
- `roteiro.txt`: o texto falado.
- `estilo_do_canal.md`: as regras de estilo do canal (valem para este vídeo).
- `assets\ferrari_sf26.glb`: a Ferrari 2026 oficial em 3D (carro do estúdio).
- `assets\interlagos_sao_paulo.glb` e `assets\alinhamento_interlagos.json`: a pista de Interlagos em 3D e a linha
  central dela (x, altura, z a cada ~3,6 m; começa na linha de chegada);
  `assets\interlagos_tracado_lonlat.json`: o traçado em longitude/latitude, para mapa 2D.
- `assets\charles-leclerc.jpg` e `assets\lewis-hamilton.jpg`: fotos dos pilotos.

## Entrega
- `comparacao\video\ferrari_hyperframes.mp4` (com a narração) e, ao lado, `SPEC.md` e `REVIEW.md`.
- Ao terminar, responda em português, em poucas linhas: a linha de história escolhida, os blocos do catálogo usados, o
  que o `check` e a revisão pegaram, e o tempo de render.
