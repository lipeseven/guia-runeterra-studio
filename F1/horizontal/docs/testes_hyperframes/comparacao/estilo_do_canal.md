# Estilo do canal Explicando F1 (vídeos horizontais)

## 1. Decisões
- Mescla da Formula Addict com a Documentsui, com regras próprias (Felipe, 2026-11-05).
- Carros sempre oficiais e o mais atuais possível (o .glb está em assets/).
- **Exceção ao "texto sem animação":** no horizontal do F1 a palavra-chave entra por decodificação, como assinatura.
  - Legenda e microlegenda continuam secas.
- Pessoas: a foto (em assets/) entra em P&B. Nunca rosto em 3D.
  - Nunca inventar citação de pessoa real. A citação só existe se a pessoa disse aquilo (fonte no briefing).
- Identidade própria:
  - O capítulo é "PARTE 0N" com o traçado do circuito, não "CHAPTER N".
  - Sem janelas ".EXE".
  - A cor de destaque vem da equipe ou do tema do vídeo.


## 3. Medidas (das referências, convertidas para 30 fps)
- **Palavra gigante:** 1–3 palavras-chave da frase, nunca a frase inteira.
  - Tamanho: 25–60% da altura (440 px por padrão), condensada ultra-bold, caixa-alta.
  - Entra 0–1 s depois da palavra falada.
  - Decodificação: 0,52 letra por quadro, em ordem aleatória, com 2–4 letras-isca. Sai ao contrário em ~12 quadros.
- **Anotação à mão:** comenta a fala, sem repeti-la ("Por quê?", "Não!", "Dominou").
  - Traço a ~105 px por quadro; a letra à mão vai na metade disso.
  - Cor: preta, ou na cor de destaque.
- **Ritmo:**
  - Alterna planos contínuos de 6–16 s com rajadas de cortes de 0,1–0,3 s.
  - Nos blocos de análise entra algo novo a cada 2–3 s.
  - Ciclo: gancho → bloco denso de 30–60 s → respiro de 7–40 s → bloco denso…
- **Transições**, mistura alvo a cada 16 momentos: 3–4 cortes, 3–4 empurrões, 3–4 câmeras contínuas,
  2–3 entradas de texto, 1 cor e 0–1 glitch ou cortina.
  - `corte`: 0 quadros. A cena nova já começa com a câmera em movimento.
  - `empurrar`: a antiga sai em 10 quadros (ease-in), com borrão na direção e esticada 1,2×. A nova entra 9 quadros
    depois, em 15 quadros (ease-out), sem rebote. O fundo não se mexe. Esquerda ou direita em 70% dos casos.
  - `glitch`: 5 quadros, só horizontal, sem cor. Raro.
  - `cortina`: sempre de baixo para cima, 15 quadros.
  - `cor`: mergulho em cor lisa (8 + 6 + 8 quadros), para capítulo ou virada.
- **Contadores e tabelas:** ficam 5–7 s na tela.
- **Trilha:** contínua, 16–26 dB abaixo da voz. Pausa de 3–11 s na narração antes de cada capítulo.
- **Abertura e fim:** abre direto no gancho, sem logo. Fecha com 15–20 s de 3D em movimento e espaço livre para o vídeo
  sugerido da tela final.


## 4. Fatos e números
- Só números que a fala diz.
- Dado de exemplo leva "(EXEMPLO)" e nunca vai para vídeo publicado.
- Fontes no briefing, conferidas antes da voz, com a mesma regra do vertical.


## Conteúdo
- Números e nomes na tela só os que a fala diz.
- Sem som de motor; trilha e efeitos discretos são permitidos.
- Fundo claro é a base; escuro só em momentos especiais.
