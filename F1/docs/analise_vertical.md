# Análise dos reels de referência — Explicando F1

Leitura com o método do Hypit (`hypit media tiles` com fala e imagem lado a lado) dos 6 reels de "Fórmula a fondo" (2026-11-01).
Evidências em `F1/dados/hypit/evidence`. Medidas convertidas para a tela de 1080×1920.

## Por que funciona
Um objeto ocupa a tela e muda de estado conforme a fala. O espectador entende vendo a peça reagir: a pergunta mostra a peça em
estado extremo, a explicação desmonta, a comparação sai do mundo da F1 e o fim volta à abertura.

## Sistemas visuais
- **Objeto principal:** ocupa cerca de 90% da largura (disco com raio de cerca de 480 px, centro perto de y 1110). Desenho 2D chapado,
  com gradientes e textura. Não é 3D: o volume vem de uma segunda cópia deslocada para a direita, que vira a borda com furos.
- **Estado no material:** a mesma peça passa de azul-cinza com veios a brasa e dourado. Calor, faíscas e brilho mudam na palavra certa.
- **Câmera:** começa colada na peça e abre em cerca de 1,4 s com desaceleração. Depois, corte seco só para mudar de explicação;
  dentro da explicação, aproxima e desliza.
- **Fundo:** quase preto. Linhas horizontais finas de velocidade com ponta luminosa dão movimento. Zebra vermelha e branca semitransparente
  perto de y 1560 e asfalto escuro embaixo.
- **Números vivos:** placa de vidro escuro com número grande em negrito e unidade pequena, em cima da própria peça, contando junto
  com a cena. Duas placas podem conviver (velocidade cai enquanto a temperatura sobe).
- **Legenda:** em y 360, tamanho 66, peso médio. Só aparecem as palavras já faladas; a atual em branco e negrito, as anteriores em cinza.
  Um termo-chave por frase ganha uma caixa fina. Nada de amarelo ou letra gigante.
- **Corte técnico:** vista chapada e simétrica; a câmara atrás dos pistões acende em laranja em "apertam", a faísca entra em "pastilhas".
- **Comparação:** cena com outra paleta, por poucos segundos, com objeto do dia a dia desenhado com a mesma qualidade.
- **Som:** só voz, com uma ou duas pontuações.

## O que estava errado no primeiro piloto
Peça pequena, disco chapado de cor única, legenda grande e amarela com palavras futuras, bolinhas desfocadas em vez de linhas de
velocidade, placas soltas, desenhos simples demais e números que não acompanhavam o estado da peça.

## O que precisa ser nosso
Texto, comparações (mãos, anilhas) e detalhes de desenho. A caixa do termo-chave é laranja e sem as alças de seleção da referência.
