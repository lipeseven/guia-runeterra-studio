# Feedback do Felipe sobre ferrari_fable.mp4 (versão da rodada 3, nota interna 82)

Estes itens são PEDIDOS DIRETOS do Felipe e valem mais que o placar e que regras pré-setadas. A rodada 4 parte daqui. Registrado em 2026-11-12 (texto dele, resumido por item).

## Manter (ele gostou; não mexer, no máximo refinar)
- **Jogo de câmera na asa dianteira:** mesmo plano 3D, só gira, afasta e aproxima o modelo, sem take novo. "Interessantíssimo". Regra geral: com modelo 3D, mudar o ângulo girando o carro e movendo a câmera (zoom in/out), sem cortar para novo take.
- **Seta com texto "olha o ângulo"** e o **antes/depois** (comparativo da asa): muito bons.
- **Passar muito ar:** a câmera afasta um pouco e desenha o fluxo de ar. Bom.
- **Escapamento:** câmera nos detalhes com blur no fundo e escapamento focado. Muito bom para prender a atenção. Blur nas partes não destacadas é legal, desde que sem exagero.
- **Fotos; fundo vermelho com branco (cores da Ferrari); fonte dos dados (OpenF1) embaixo; gráfico de linha de velocidade; setas para baixo no downforce; fontes que contrastam e mudam:** todos gostou.

## Consertar (inaceitável ou errado)
1. **Círculos feitos à mão (o defeito mais grave).** Cena do carro branco: círculo completamente torto, sem focar nada. Asa traseira, quando vai girar: círculo torto, mal feito. Mini asa: círculo pontiagudo e feio. Ele NÃO quer círculo perfeito: oval serve, traço aberto sem fechar serve, fechar com "perninha" serve. O que não serve é traço de quem tem problema na mão: torto, pontiagudo, rabo sobrando. O círculo tem que focar a peça citada.
2. **Texto picotado/cortado (defeito crônico em TODOS os textos).** No "piscar", o final do texto sai cortado e a exclamação picotada, como se a caixa cortasse abrupto. Texto à mão da "velocidade final" também cortado/picotado. Corrigir na raiz (máscara/caixa de recorte das animações de texto).
3. **Asa traseira girando:** o movimento está errado (sentido). Corrigir o sentido/curso do giro da aba (DRS).
4. **Seta vermelha sem alvo** na parte que fala de girar a asa: aponta para lugar nenhum. Remover ou apontar para a peça.
5. **Continuidade da mini asa do escapamento:** no segundo 13 é uma, no segundo 14 é outra. Inaceitável. A mesma peça, no mesmo lugar, em todos os planos.
6. **Blur inicial exagerado:** no começo a traseira do carro fica sob blur muito forte. Manter o blur de profundidade, mas sem exagerar.
7. **Ritmo:** na parte do "agressivo" as coisas acontecem rápido demais; mais lento (é só jogo de câmera). Em geral o vídeo está acelerado e não dá tempo de ler a informação.

## Dados
- Usar SEMPRE dados de 2026 (o vídeo usou 2025 com selo de fonte). Verificar se é limitação da API (OpenF1 2026).
- Verificar se a API tem dados de GPS/posição (x, y, z). Se tiver, colocar o carro 3D na pista de Interlagos 3D exatamente onde esteve na pista real.
- O uso do modelo de Interlagos no vídeo foi pouco intuitivo; preferir o carro na pista (temos pista 3D e carros 3D).

## Ideias e diretrizes
- Raio-X com o pistão que gira a asa: seria interessante, mas não há modelo com interior. Só se conseguirmos um modelo adequado.
- O modelo do carro precisa de refinamento em muita coisa; vai ser trabalhado.
- Peças separadas "feitas pelo Fable" (aba, rodas, mini asa) são aproximadas; o movimento da aba não é o real.

## Movimento correto da asa "Macarena" da Ferrari (pesquisado em 2026-11-12; o Felipe mandou o short https://youtube.com/shorts/AGbS_msQwVs, gameplay do F1 26)
- O elemento superior (flap) NÃO abre como um DRS comum (inclinação de poucos graus). Ele GIRA mais de 180° e fica de cabeça para baixo na reta (reduz arrasto); fechado = posição normal de downforce.
- Giro por eixo lateral (de ponta a ponta de asa) perto do bordo de ataque do elemento superior (Autosport); dois atuadores escondidos nas placas laterais (f1technical: mais de 200°). Fontes divergem: 180°, "mais de 200°" e 270° (RacingNews365). Usar ~180° como padrão e anotar a incerteza.
- O modelo do Fable gira só -26° em `FH_aba_pivo`: mecanismo errado. Corrigir para o giro de ~180° (passando pela vertical) com os atuadores nas placas laterais como detalhe opcional.
- Fontes: Autosport (how-ferrari-180-degree-rear-wing-works), F1.com Tech Weekly (Macarena rear wings used in Miami), F1technical (news/28460), PlanetF1.
- Short de referência 2 (RacingNews365, "All Macarena Wings Compared", https://youtube.com/shorts/ddLZPfz-NSI, 10 s; vista por trás/de cima, flap em verde): na linha da Ferrari o flap sai da posição fechada (deitado sobre o plano principal), levanta e gira para cima e por cima em um movimento grande e contínuo (não um tilt pequeno), e volta; McLaren (H-wing) e Red Bull aparecem em linhas abaixo. Conferido por 5 quadros (1,5 s, 3,2 s, 5,2 s, 7,2 s, 9 s); a rotação completa e o ângulo exato não dá para ler só desses quadros.
