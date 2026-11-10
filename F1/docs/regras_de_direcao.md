# Regras de direção — Explicando F1

Este arquivo entra no prompt do diretor. Todo ajuste fino do Felipe entra aqui.

## Ajustes do Felipe (GP do Brasil, 2026-11-04)
- **Cartões empilhados (`etapas`) cansam.** No máximo 1 por vídeo, e de preferência com `foco` (fundo escuro e desfocado).
  `foco` também é tempero: 1 ou 2 por vídeo. Para o resto, gráfico que interage com a cena: `linhatempo`, `minimapa`,
  `perfil`, `torre`, `relogio`, `ano`, `sentido`, ou a lista falada em cortes rápidos com `palavra`.
- **A abertura pode ser a própria pergunta escrita na tela** (`frase`, com `sem_legenda`), não precisa ser carro na pista.
- **O gráfico pertence à cena.** Falou de um trecho do circuito: o carro PASSA por ele, com o `minimapa` mostrando onde
  está. Falou de um vencedor: o carro na pintura dele, na vista panorâmica.
- **Vista de um circuito real usa `criarCircuito(nome, { cenario: true })`**, nunca a reta genérica (`set: "pista"`).
- **Carro parado fora do box parece acidente.** "Parada" é sempre no set `pit`, na marca, com a equipe em volta.
- **Plano só no carro, sem nada acontecendo, é fraco.** Toda cena mostra o que a fala diz.
- **Som:** nada de barulho de carro. Swoosh em troca forte de cena, pop quando algo aparece, alerta quando algo dá errado.
  **Efeito só em momento-chave, ligado a algo que muda na tela naquela palavra** (a cor do carro troca, um número aparece, o
  alerta da perda de posições). Sem isso, não leva som: efeito em toda cena vira "goteira" e não destaca nada. O efeito bate numa
  palavra-chave falada, nunca numa pausa. No máximo uma lista por vídeo com um efeito por item; ~9 efeitos em 2 min 20 s é a medida.
- **O autódromo fica na cidade**, não numa floresta nem numa rodovia: muros, arquibancadas e prédios em volta da pista, poucas árvores só no miolo.
- **Câmera transita.** Plano com carro usa `filmar` com 2 ou 3 posições, nunca uma posição só do começo ao fim.
- **Velocidade do carro é constante no plano e parecida entre planos** (~0,015 da volta por segundo; reta rápida ~0,021).
- **O próprio cenário é o infográfico (aprovado, "Por que a chuva vira um problema em Interlagos?", 2026-11-08).** Em vez de
  cartão/seletor `etapas` por cima da imagem, cada palavra da lista marca algo DENTRO da cena, entrando seca na palavra:
  "curvas" = placa 3D da curva no traçado (`numerarCurvas`/`nomearTrechos`); "pontos de frenagem" = zona de frenagem acesa
  em vermelho no asfalto (`destacarTrecho`); "outros carros" = brilho âmbar nos carros (`brilho`). Só numerar a curva que
  aparece no quadro. Cuidado com o halo do brilho (forte demais) e com a placa colada na legenda.
- **Carro seguindo outro carro com spray: câmera panorâmica alta e de longe, acompanhando os dois.** Referência aprovada:
  `filmar` com 3 posições, ~70 m atrás, 31–35 m de altura, lente 30, mirando ~30 m à frente do ponto entre os carros;
  carros a ~19 m um do outro e spray curto (~12 m) para não cobrir o de trás. Câmera baixa/grudada atrás do carro foi
  reprovada: "levantar um pouco e ficar panorâmica, acompanhando de longe". Mundo tem só 140 partículas (`w.parts`):
  `solta` acima disso quebra a cena e cai na cena de reserva.

## Aprendizados aprovados pelo Felipe (retrospectivas automáticas)
- Lista de nomes de lugares (curvas, trechos) na abertura vira tipografia grande sobre o mapa da pista, com o lugar citado aceso na palavra; nunca carro de perto, que não mostra onde o lugar fica. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Toda cena sobre uma curva ou trecho de circuito leva o minimapa com o trecho aceso (e o ponto do carro), para o espectador se localizar. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- A mesma linguagem de câmera não se repete em sequência: aproximar/afastar no carro no máximo 1 ou 2 vezes no vídeo; cada curva ganha um enquadramento próprio (câmera fixa na beira, visão do piloto, de cima, lateral, contra a luz). Câmera em movimento sempre por interpolação suave, nunca seguindo pontos com tranco. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Fala sobre o passado de um lugar mostra como ele era (traçado antigo desenhado sobre o atual, trechos que sumiram em vermelho) e traz informação concreta (ano, motivo); número de distância é contador com o traçado sendo desenhado, nunca barras de velocidade. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Fala com pessoas fazendo algo (tomar café, comemorar, trabalhar) mostra bonecos fazendo a ação no lugar citado; objeto sozinho parado na tela não serve. Câmera "no carro" mostra parte do carro no quadro para se entender onde ela está. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Quando o tema for o pneu (compostos, degradação, pressão, desgaste), o pneu é o protagonista: usar o pneu em destaque (close, vista explodida ou lado a lado por composto), nunca o carro inteiro como ilustração. O carro só aparece quando a fala é sobre a pista ou a corrida. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Todo objeto desenhado deve estar completo e com detalhe característico: pneu com aro/roda visível, banda lateral e cor do composto, nunca o miolo preto liso. Rodas giram sempre que o carro está em movimento na pista. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Câmera nunca fica travada nem entra no chão ou perto demais: usar movimento suave e contínuo entre 2-3 posições, com distância mínima que mantenha o objeto inteiro e sem cortar o solo. Para explicar partes do carro, usar visão panorâmica e destacar (brilho) a parte relacionada à fala. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Curvas do carro devem ser suaves, com trajetória em arco e velocidade angular contínua, sem pausa nem 'travadas' na entrada ou saída da curva. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Caixas de texto não podem se sobrepor: antes de fechar a cena, checar que blocos simultâneos têm áreas separadas, com no máximo 2 textos ao mesmo tempo, ou escalonar a entrada e saída de cada um. Frases curtas de destaque podem ser quebradas em duas linhas hierárquicas (ex.: 'pneu mais' em cima, 'rápido' embaixo). _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Carro, capacete, macacão e boné de um piloto real seguem a identidade da época citada na fala (equipe, ano, modelo, cores). O diretor pesquisa antes de desenhar, e a cor correta vale para todas as cenas do mesmo ano. Não usar cor genérica nem de outra temporada. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Fala sobre chuva leva pneu de chuva (sulcado, cor correta), pista molhada e respingos. Condição do tempo citada na fala precisa aparecer no carro e no cenário. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Quando a fala cita um GP/circuito com data, usar o traçado real do circuito da época (da biblioteca/Wikimedia, nunca desenhado de memória) com a data em texto na tela, em vez de mapa-múndi ou mapa genérico. Mapa de país só quando o país é o lugar físico do evento, não quando é a nação como tema. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Números de estatísticas de carreira (títulos, vitórias, poles) viram infográfico próprio (cartão com número grande, troféu, bandeira ou ícone), nunca contador que parece gráfico de velocidade nem carro rodando como ilustração. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Texto em tela fica sempre alinhado (centralizado ou na mesma margem), com tamanho que caiba no take. Frase longa se divide em vários takes ou linhas, e o texto sobre cena de fundo ganha destaque com o fundo desfocado. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Objetos fixos do cenário (indicador/farol, poste, placa, luz) ficam sempre ancorados a uma estrutura real da cena (parede do box, chão, teto), nunca flutuando solto no espaço. Antes de fechar a cena, checar que cada objeto tem apoio físico visível. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Evitar cores piscando (z-fighting): nunca sobrepor superfícies coplanares (cor de macacão, faixa, marcação, decalque); dar deslocamento mínimo entre camadas ou usar um único material. Vale para todos os personagens e objetos coloridos. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Quando a fala citar uma função ou pessoa específica dentre várias (ex.: um mecânico), destacar só ela: os demais ficam translúcidos ou saem da cena. Em cenas com poucos personagens para o que a fala descreve (ex.: 'segurança'), completar o elenco da equipe. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Cena de ação (troca de pneus, pitstop, trabalho em equipe) nunca fica com personagens parados: a ação descrita deve acontecer em todas as cenas, desde o primeiro quadro. Pitstop completo = carro chega, é atendido e sai; ao repetir uma ação, variar o ângulo. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Sentido de giro das rodas deve corresponder ao sentido de movimento do carro, na chegada e na saída (rotação para frente, sem parecer marcha à ré). Verificar o sinal da rotação na biblioteca, não com inversão manual por plano. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
