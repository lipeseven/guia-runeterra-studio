# REVIEW — Ferrari SF-26 (HyperFrames 0.9.20)

Entrega: `ferrari_hyperframes.mp4` — 1920x1080, 30 fps, 43,0 s (1290 quadros), narração original, render local `--quality delivery` em 1 min 11 s (76 s de relógio), GPU (RTX 4060 via ANGLE/D3D11), 4 workers, 59,9 MB.

## Escolhas criativas
- Linha de história A, "Uma volta pelo carro": o objeto é a explicação, uma tomada contínua no estúdio claro que sai para dois mundos (pilotos, Interlagos 3D) e volta. Não construídas: B "O resultado primeiro" (brigaria com a ordem da voz) e C "A palavra carrega" (viraria lista de palavras). Ver `STORYLINES.md`.
- A aba superior da asa traseira foi recortada da malha oficial na carga (triângulos acima de y 0,875 e atrás de z -2,40, entre as placas laterais) e gira 28° no bordo de fuga aos 12,8 s: o mecanismo que a voz descreve acontece de verdade no carro oficial.
- O traçado branco sobre o vermelho é a linha central real projetada pela mesma câmera que abre Interlagos: o corte da cor para o 3D é casado.
- Sem trilha nem efeitos: não há música local nem login HeyGen, e o canal proíbe som de motor. A voz é a única faixa.

## Catálogo
Instalados com `add` e usados como base, reescritos: `product-turntable` (estúdio Three.js: tiras de luz no RoomEnvironment, sombra de contato assada, `buildReady`), `scramble-reveal` (tabela de quadros com semente fixa, aqui em ordem sorteada a 0,52 letra/quadro com 3 iscas, como pede o canal), `hw-arrow` (seta à mão por hash determinístico). `hw-underline` e `directional-wipe` foram instalados, testados contra a regra do canal e removidos (o empurrão e a cortina do canal foram escritos à mão). Fotos P&B pelo `media-treatment` (saturação -1, contraste +0,12), sem filtro CSS.

## O que o check pegou e o que mudou
- 2 erros `text_occluded` (a "2026" atrás do carro): é a regra do canal, palavra gigante atrás do carro → `data-layout-allow-occlusion` no canvas.
- `content_overlap` nas letras da decodificação (as iscas são mais largas que a letra final) → `data-layout-allow-overlap` só nos contêineres das palavras gigantes.
- Ficaram de propósito: 37 `line_unread` (o check lê cada letra da decodificação como uma "palavra"; cada palavra gigante fica inteira 1,0–2,3 s); `composition_file_too_large`/`timeline_track_too_dense` no `studio.html` (uma tomada contínua só, câmera e anotações presas ao mesmo relógio); `canvas_content_at_edge` aos 7,2 s (carro cortado durante a viagem da câmera); aviso de precisão do shader do Three.js (inofensivo). Check final: `ok: true`, 0 erros.

## O que a revisão (snapshot --review + quadros avulsos) pegou
- P0 · 19,5 s · cena dos pilotos tinha fundo opaco e cobria a saída do estúdio: o empurrão não aparecia (quadro vazio) → fundo do `pilotos` transparente; agora o estúdio sai borrado para a esquerda e Leclerc entra 9 quadros depois.
- P0 · 4,6 s · "menos vermelho?" saía da tela e depois caía em cima do "O" de BRANCO → mão embaixo à direita, seta subindo até a tampa do motor.
- P1 · 9,0 s · câmera longe demais da asa dianteira e a mão por cima de AGRESSIVO → câmera mais baixa e perto; "olha o ângulo" no canto livre.
- P1 · 13,8 s · aba girando pequena demais para ler → câmera traseira 0,5 m mais perto; legenda "ASA TRASEIRA" movida para o vazio à direita.
- P1 · 15,5 s · linhas de ar quase invisíveis → mais grossas (22 mm) e 50% de opacidade.
- P1 · 27–30 s · reta dos boxes encostada na borda e legendas fora da tela; "pé embaixo!" em cima de "RETA OPOSTA" → câmera aérea mais alta e aberta, legendas viradas para dentro do miolo, mão acima.
- P1 · 25,9 s · "INTERLAGOS" mal terminava de decodificar e o vermelho já abria → vermelho segura até 26,63 (palavra inteira por 0,5 s); traçado mais fino (6 px, 70%).
- P1 · 42,9 s · fim com o carro cortado à esquerda → câmera recua e `setViewOffset` desloca o carro para a esquerda, terço direito livre para a tela final.

## Medido x só olhado
- Medido: check, duração (ffprobe 43,000 s), som presente (`audio`: voz, -18 LUFS integrado, pico -4,1 dBTP, sem clipping). O som não foi ouvido. A narração não foi normalizada (a voz é do canal e não foi trocada).
- Olhado: as folhas do `snapshot --review`, os quadros de QA do SPEC e 5 quadros do .mp4 final.
- Não conferido: o ponto exato da "mini asa" no modelo (o .glb não separa a beam wing; o anel envolve a região logo abaixo do escapamento); o desenho exato do DRS 2026 (a aba gira no bordo de fuga, é ilustrativo).

## Mais fraco e o que eu mudaria
- Plano mais fraco: Interlagos 3D. A malha da pista é de jogo, com textura de chão borrada nas bordas; com mais tempo, uma Ferrari andando na reta oposta com a câmera baixa em vez da vista aérea.
- Os pilotos: dois retratos lado a lado lembram "painéis lado a lado"; com mais tempo, recorte de fundo (`remove-background`) para os dois ficarem na frente do TÍTULO.

## v2 (2026-11-12) — giro completo da aba
- Pivô no centro geométrico da aba (0; 0,932; -2,518), eixo lateral x (era o bordo de fuga, 0,99/-2,63).
- Giro de 180° (era 28°): abre 12,80–14,05 s, segura invertida até 15,10 s, fecha até 16,30 s (ease quadrático). A aba sobe até 13 cm durante o giro (0,13·sin^0,75 do ângulo) para não atravessar o plano principal (folga mínima medida na malha: 9 mm); invertida cabe no vão.
- Recorte: |x| < 0,545 e triângulo com vértice além de 0,56 fica no carro (só os do miolo, |x| < 0,5, vão junto) — tira as lascas das placas laterais.
- Seta "abre!" virou arco no próprio plano do giro (da frente, por cima, até a traseira). Narração, câmera e o resto sem mudança; depois de 16,3 s a aba fica fechada (antes ficava aberta 28° até 31 s).
- Medido: check ok (0 erros), 43,000 s, PSNR contra o original ≥ 40 dB fora de 12,83–17,37 s. Folhas em `_verif/`.
