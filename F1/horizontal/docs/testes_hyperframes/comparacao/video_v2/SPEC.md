# SPEC — Ferrari SF-26 (Explicando F1)

GOAL:    o espectador sai sabendo apontar no carro as quatro coisas que a voz cita (pintura mais branca, asa dianteira, asa traseira que gira, mini asa perto do escapamento) e por que a Ferrari anda nas duas retas de Interlagos.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    43,0 s x 30 = 1290 quadros. Narração 0–40,05 s (relógio); 40,1–43,0 = 3D em movimento com espaço livre à direita para a tela final. Sem trilha.
LOOK:    chão #E9E9E6 liso (fundo claro = base do canal), sem grão, sem vinheta.
         tinta #151515; destaque vermelho Ferrari #D40000 só em: traços à mão, retas acesas em Interlagos, mergulho de cor, palavra "TÍTULO".
         palavra gigante: League Gothic, caixa-alta, 440 px de altura de corpo (41% da altura), tracking 0, atrás do carro.
         microlegenda: Inter 800, 30 px, caixa-alta, tracking +4%, seca (entra num quadro, sem animação), fio-guia 2 px até a peça.
         anotação à mão: Caveat 700, 64 px, vermelho; traço 6 px.
         meio: estúdio 3D (Three.js 0.184) com o .glb oficial; luz chave quente à esquerda, contorno frio atrás, ambiente RoomEnvironment 0,5; sombra de contato radial 0,5 de opacidade.
         fotos de pessoas: P&B (media-treatment, saturação -1), recorte retangular 640 x 820, sem moldura.
OBJECTS: SF-26 (.glb oficial, não redesenhado); a aba superior da asa traseira separada da malha e girando no eixo do bordo de fuga;
         linhas de ar (fitas finas #151515 a 35%) passando por cima do carro e pela fenda da asa;
         Interlagos (.glb) com a linha central real; reta dos boxes = pontos 1140→1221→0→65; reta oposta = pontos 205→375.
MOTION:  câmera: power2.inOut, viagens de 1,2–1,6 s, deriva de 3–5°/s nas paradas.
         palavra gigante: decodificação 0,52 letra/quadro em ordem sorteada (semente fixa), 3 iscas por letra, sai ao contrário em 12 quadros.
         traço à mão 105 px/quadro; letra à mão 52 px/quadro (revelação por recorte da esquerda para a direita).
         empurrar: sai em 10 quadros power3.in com borrão horizontal 16 px e escala X 1,2; a nova entra 9 quadros depois, em 15 quadros expo.out, sem rebote; o fundo não se mexe.
         cor: 8 quadros para o vermelho, segura, 8 quadros para abrir. cortina: de baixo para cima, 15 quadros, power3.inOut.
SHOTS:
  1  0,00–5,10  estúdio: frente-3/4, câmera desliza para a direita. "2026" decodifica aos 1,45; vira "BRANCO" aos 3,60. Mão: "menos vermelho?" apontando a tampa do motor aos 4,20. → câmera continua.
  2  5,10–10,50 câmera desce até a asa dianteira (5,1–6,5). Legenda "ASA DIANTEIRA" aos 5,66. "AGRESSIVO" gigante aos 7,85. Mão: seta + "olha o ângulo" aos 8,6. → câmera continua.
  3  10,50–19,50 câmera viaja à traseira alta (10,5–12,0). Legenda "ASA TRASEIRA" aos 11,10. A aba gira 0→28° em 12,80–13,45 (seta curva à mão). Ar atravessa 14,50–19,5. Recuo para vista lateral 16,8–18,0; "VELOCIDADE" gigante aos 17,45. → empurrar para a esquerda aos 19,50.
  4  19,80–25,00 pilotos: Leclerc entra (empurrar) aos 19,80, nome seco aos 20,34; Hamilton entra aos 22,08, nome seco; "TÍTULO" gigante vermelho atrás deles aos 23,70. → cor.
  5  25,00–31,90 mergulho no vermelho 25,00–25,27; "INTERLAGOS" decodifica em branco aos 25,38 e o traçado (a linha central projetada na câmera de abertura) se desenha; segura até 26,63 e abre em 8 quadros em Interlagos 3D vista aérea, órbita lenta. Reta dos boxes acende aos 27,54 + legenda; reta oposta aos 28,82 + legenda; mão "pé embaixo!" aos 29,9. → cortina aos 31,40.
  6  31,40–40,10 estúdio, traseira: empurra até o escapamento (32,2–35,0). Legenda "ESCAPAMENTO" aos 35,48. Anel à mão na mini asa aos 37,14 + legenda "MINI ASA". Três setas para baixo aos 38,70 e "DOWNFORCE" gigante. → câmera continua.
  7  40,10–43,00 câmera recua e gira; carro à esquerda, terço direito livre. Sem texto.
BANNED:  cena nova com fundo opaco por cima de um empurrão (escondia a saída do estúdio); texto à mão sobre a palavra gigante; fundo escuro com coisas pequenas flutuando; brilho, bloom, partículas; gradientes roxo/azul; papel creme + serifa + rótulo mono; tudo centralizado; tudo entrando com fade + subir; texto que se mexe enquanto é lido; cantoneiras, HUD, molduras; três cartões em fila; logo no canto; janelas ".EXE"; "CHAPTER N"; rosto em 3D; citação inventada; números ou nomes que a voz não diz; som de motor.
QA:      1,0 (carro + câmera em movimento, quadro 0 não vazio); 4,5 ("BRANCO" atrás do carro, mão legível); 8,9 (asa dianteira + legenda + seta); 13,6 (aba aberta); 15,5 (linhas de ar); 18,3 ("VELOCIDADE" visível atrás do carro); 19,6 (empurrão); 24,2 (dois pilotos P&B + "TÍTULO"); 25,6 (vermelho + traçado); 29,6 (duas retas acesas); 31,6 (cortina); 36,0 (escapamento); 39,2 (mini asa + setas); 42,5 (espaço livre).
