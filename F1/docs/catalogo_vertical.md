# Cenas prontas do vertical (lido pelo diretor)

Cenas do vídeo de regras, com parâmetros. Use "tipo" no lugar de "codigo" só quando a cena mostra exatamente a fala; dentro
do código, c.tipo(nome, {parâmetros}) desenha uma delas como base. O resto do vídeo é escrito com a API (api_cenas.md).
Cada plano começa numa palavra do roteiro e dura até o próximo. Troque de plano a cada 2 a 6 s, quase sempre no começo de
uma frase. O mundo (cenário e luz) muda com o assunto.

Campos comuns a todos os planos:
- `em`: trecho EXATO do roteiro (2 a 5 palavras seguidas) onde o plano começa. O primeiro plano começa na primeira palavra.
- `tipo`: um dos tipos abaixo (ou `codigo`, ver api_cenas.md).
- `clima` (opcional, troca a luz): tarde, manha, sol, noite, brasa, chumbo, vazio (estúdio escuro), claro (estúdio claro, para comparações).
- `equipe` (0 a 10): pintura do carro. 0 vermelho, 1 laranja, 2 verde-água, 3 azul, 4 roxo, 5 amarelo, 6 prata, 7 preto e verde-limão,
  8 preto e dourado, 9 verde, 10 branco e azul.
- `marcas`: {nome: "trecho exato"} = momentos dentro do plano (cada tipo diz os nomes que usa).

Sobreposições (opcionais, só o que a fala diz; nunca invente número):
- `placas`: [{texto, unidade?, em?: "trecho", cor?: branco|amarelo|vermelho|verde|azul|laranja|ouro, pos?: baixo|meio|esquerda|direita|alto}]
  Texto curto (até 18 letras). Duas placas lado a lado = esquerda e direita.
- `contador`: {de, ate, unidade?, casas?, formato?: "numero"|"tempo" (segundos → h:mm:ss), em?: "trecho", ate_em?: "trecho", cor_final?}
  Número que conta enquanto a coisa acontece.
- `chips`: {itens: ["SEX","SÁB","DOM"], ativo?: índice, em?: "trecho"} fichas lado a lado (fases, dias, etapas).
- `selo`: {texto: "SC", em?} letreiro de LED amarelo (SC, VSC, DRS…).
- `riscado`: {texto: "DRS", em: "trecho"} palavra que leva um risco vermelho (algo que acabou).
- `medidor`: {texto: "50/50", sub?, em?} anel meio laranja, meio azul.
- `gota`: {texto} gota verde com texto (combustível, sustentável).
- `chuva`: true

## Tipos
| tipo | cena | parâmetros | marcas |
|---|---|---|---|
| voo_grid | abertura: câmera voa rasante pelo grid até a pole | n (carros, padrão 22) | — |
| grid_topo | vista de cima, carros aparecendo um a um em fila | n | aparece |
| dupla | dois carros da mesma equipe lado a lado, câmera baixa girando | equipe | — |
| grid_recua | câmera sobe e recua mostrando o grid inteiro | n | — |
| destaque | um carro sozinho com auréola de luz, câmera girando | equipe, cor da auréola | destaque |
| circuito | circuito visto do alto; um traço laranja percorre de `de` a `ate` (0 a 1 da volta) | de, ate, angulo: "girado" | — |
| perseguicao | um carro andando; câmera conforme `angulo` | equipe, angulo: lateral, traseira, frontal, rasante, topo | — |
| pelotao | todos os carros andando juntos, câmera à frente | n | — |
| eliminacao | grid visto do alto; os `sai` últimos ficam cinza com auréola vermelha e saem | n, sai | sai, saiu |
| fila | fila de carros correndo, câmera baixa | n | — |
| pole | carro da pole com auréola dourada | — | destaque |
| luzes | pórtico das 5 luzes vermelhas | angulo: "perto" | acende, acesas, apaga |
| largada | largada: o grid arranca | — | — |
| pneus | 1 a 3 pneus; com 1, câmera gira em volta | cores: [macio, medio, duro, intermediario, chuva], modo: "queda" (caem quicando), chuva | gasta (soltam migalhas) |
| pit | box: modo chegada, troca (vista de cima, rodas saem e voltam), passagem (passa sem parar), parada (para e sai) | equipe, modo | — |
| barras | barras 3D com valores (até 10), da maior para a menor | valores | b0, b1, b2… (quando cada uma sobe) |
| trofeu | troféu dourado girando | — | confete |
| bandeiras | fileira de bandeiras no muro | cores: [verde, amarela, azul, vermelha, preta, quadriculada] | — |
| bandeira | uma bandeira tremulando na pista | cor, acao: passam, batida, ultrapassagem, param, desclassificado, chegada | chegada |
| batida | carro batido fora da pista, fumaça, câmera tremida | — | — |
| safety_car | Safety Car (superesportivo com luzes) | modo: entra, lidera (com o pelotão atrás) | — |
| espacados | carros vistos do alto andando com espaço igual entre eles | — | — |
| aproxima | vista de cima: um carro chega perto do da frente | equipe | — |
| ultrapassagem | carro ganha um empurrão azul e passa o outro | equipe | boost |
| asa | asa traseira: abre e fecha, ar passando | — | abre, fecha |
| moedas | pilhas de moedas crescendo até um teto vermelho (estúdio claro) | — | teto |
