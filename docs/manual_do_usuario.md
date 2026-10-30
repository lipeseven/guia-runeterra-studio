# Manual do usuário — Guia de Runeterra Studio

Este manual explica **o que cada parte da ferramenta faz e como usar**, sem detalhes de programação.
Para instalar em um computador novo, veja `docs/instalacao.md`.

---

## 1. O que é a ferramenta

É um assistente de edição que roda **no próprio computador** e ajuda a produzir vídeos longos (~20 min) para o
YouTube. Ela faz o trabalho braçal — escolher imagens, montar cenas, sincronizar com a narração, renderizar — e
deixa as decisões criativas com a pessoa: o roteiro final, a voz (gravada por um humano), a aprovação de cada
etapa e os ajustes cena a cena.

Algumas regras que a ferramenta segue sempre:

- **A voz publicada é sempre humana.** A ferramenta gera uma "voz guia" de IA só para o rascunho; ela nunca vai
  para o vídeo final.
- **Os arquivos da pasta de imagens (o "acervo") nunca são movidos nem alterados.** A ferramenta só lê e cataloga.
- **O que você ajusta à mão vale sempre.** Nenhuma regra automática passa por cima de um ajuste manual.
- **Tudo é ancorado nas palavras do roteiro**, não em segundos: se a narração mudar, as cenas se reajustam sozinhas.
- O único serviço pago é o Claude (a IA que escreve e dirige). Ela é usada com economia: o que já foi feito é
  reaproveitado e não é pedido de novo.

---

## 2. Ligando a ferramenta

- Dê dois cliques em **`iniciar.bat`** (canal Guia de Runeterra) ou **`iniciar_pokemon.bat`** (canal Pokémon).
- Abre uma janela preta (o "servidor") e o navegador no endereço do painel:
  - Guia de Runeterra: **http://127.0.0.1:8765**
  - Pokémon: **http://127.0.0.1:8766**
- **Não feche a janela preta** enquanto estiver usando. Fechar a janela desliga a ferramenta.
- Os dois canais podem ficar ligados ao mesmo tempo. Eles **não se enxergam**: cada um tem os próprios vídeos,
  imagens e regras. A máquina faz **uma tarefa pesada por vez** (ex.: um render), mesmo com os dois ligados.
- Se o servidor for desligado no meio de uma tarefa, ao ligar de novo ele **retoma sozinho** o que ficou pela
  metade (recomeçando aquela tarefa).

---

## 3. O Quadro (tela inicial)

É um quadro de cards, um card por vídeo, em colunas que representam as etapas:

| Coluna | O que significa |
|---|---|
| **Ideia** | Temas anotados. Nada acontece ainda. |
| **Roteiro** | O texto está sendo escrito/conferido; depois vêm voz guia, capa e direção automática. |
| **Gravação** | O rascunho foi aceito; falta a narração gravada pela pessoa. |
| **Montagem** | A ferramenta está montando o vídeo com a voz real. |
| **Revisão** | Vídeo final pronto para assistir e aprovar. |
| **Publicado** | Vídeo no ar. Definitivo: o card não sai mais dessa coluna. |

No topo do quadro:

- **Seletor de canal** (no título): troca para o painel do outro canal.
- **Nova ideia de vídeo…**: cria um card na coluna Ideia.
- **Atualizar acervo**: procura imagens/vídeos novos na pasta do acervo e cataloga (sem custo). Também roda
  sozinho quando um card novo é criado.
- **Aprendizado**: regras que a ferramenta propõe a partir dos ajustes feitos nos vídeos já publicados. Cada
  regra só passa a valer se for **aprovada** aqui.
- **Vídeo já publicado**: cria um card direto em Publicado para um vídeo feito fora da ferramenta (capa, link e
  roteiro), só para registro.
- Indicadores de **GPU / VRAM / Disco**: uso da placa de vídeo e espaço livre.
- **Barra de progresso**: aparece no card (e na página do vídeo) quando algo está rodando, com o tempo restante.

Os cards podem ser **arrastados** entre colunas; cada movimento importante pede confirmação. Um card **travado**
não pode ser excluído por engano (botão **Travar/Destravar**).

---

## 4. A página do vídeo

Clique em um card para abrir. A página mostra as **etapas** do vídeo, cada uma com seu estado
(Aguardando · Em andamento · Precisa de você · Concluído) e os avisos que precisam de atenção.
A ordem natural é a seguinte.

### 4.1 Roteiro

- **Enviar roteiro**: cole o texto (parágrafos separados por uma linha em branco) ou envie um `.txt`.
- **Gerar com o Claude**: a IA escreve o roteiro no estilo do canal. Dá para dar **orientações** (foco, ordem das
  seções, personagens obrigatórios, tom, piadas) e, opcionalmente, colar um **roteiro base** (ex.: transcrição de
  um vídeo gringo) — ele serve só de inspiração; nada é copiado.
- **Conversa com o roteirista**: peça mudanças ("encurte a parte do Varus", "mais humor no começo"). Só os
  parágrafos alterados são reescritos; o resto fica intacto.
- Dá para **editar à mão** e **Salvar como nova versão**. Em **Versões** é possível voltar para uma versão antiga.
- **Conferência do roteiro** (roda sozinha a cada versão nova):
  - **Semelhança**: compara com o roteiro base e aponta trechos parecidos demais (para não virar cópia).
  - **Fatos**: confere as afirmações do roteiro nas wikis do assunto e marca cada uma como *confere*, *a fonte diz
    diferente* ou *sem fonte*, mostrando o trecho da fonte. É uma ajuda — a decisão final é humana.
  - **Conferir de novo**: refaz só os parágrafos que mudaram.
- Quando o texto estiver pronto, **aprove o roteiro**.

### 4.2 Voz guia

Gerada automaticamente depois do roteiro aprovado. É uma leitura de IA usada **só** para montar o rascunho e
acertar os tempos. Nunca vai para o vídeo publicado.

### 4.3 Capa

- Envie a **capa** do vídeo (a imagem com os círculos/ícones dos personagens de cada capítulo).
- A ferramenta detecta os círculos e o nome de cada um. Essa capa vira:
  - a **abertura** do vídeo;
  - a **transição de capítulo** (a "câmera" passeia pela capa e fecha no personagem do próximo capítulo);
  - o **selo redondo** no canto superior esquerdo das cenas de cada capítulo.
- **Aprove a capa** para seguir.

### 4.4 Direção automática

Começa sozinha quando roteiro, voz guia e capa estão aprovados. A IA "diretora":

1. divide o roteiro em **blocos** (introdução + um bloco por capítulo);
2. planeja as **cenas** de cada frase (tipo de tela, legenda, o que mostrar);
3. **busca** imagens e clipes no acervo e **escolhe** os melhores;
4. **monta** e **renderiza** o **rascunho** (com a voz guia).

O progresso aparece passo a passo. Se algo falhar, aparece um aviso com **Tentar de novo**. O trabalho já feito
não é refeito (economia de cota).

### 4.5 Rascunho e Storyboard

O rascunho aparece no player da página. Para ajustar, abra o **Storyboard** (seção 5). Cada novo rascunho só
renderiza de novo os **blocos (capítulos) que mudaram** — o resto é reaproveitado, por isso é rápido.

Quando o rascunho estiver bom, arraste o card para **Gravação** (isso aceita o rascunho).

### 4.6 Gravação

- Envie a narração gravada (upload com barra de progresso) **ou** coloque o(s) arquivo(s) na pasta `entrada/`
  do projeto e clique em "Já coloquei na pasta". Se gravou **por capítulos**, coloque vários arquivos: eles são
  juntados na ordem dos nomes (ex.: `01.wav`, `02.wav`…).
- A ferramenta **limpa** a gravação: tira regravações (quando você repete uma frase), falas fora do roteiro,
  pausas longas demais, e ajusta o volume. O timbre da voz não é alterado.
- A limpeza **para e espera você conferir**:
  - player **Original** × **Limpa (vai para o vídeo)**;
  - **Linha do tempo da gravação**: mostra cada trecho mantido/cortado; dá para **ouvir** cada trecho e trocar
    o que entra ou sai (**Escolher o que limpar**), e então refazer a limpeza sem regravar.
- Ao aprovar, a ferramenta **realinha** todas as cenas à sua voz e renderiza o **vídeo final**.

### 4.7 Revisão e Publicação

- Assista ao vídeo final. Se estiver certo, clique em **Vídeo aprovado**.
- A ferramenta prepara a **publicação**: 5 sugestões de título, descrição com capítulos (minutagem real) e
  créditos, tags, **comentário fixado** e a **thumbnail** (feita a partir da capa).
- Depois de subir no YouTube: **Salvar link** e **Marcar como publicado**. Isso:
  - registra quais imagens foram usadas;
  - guarda o aprendizado (legendas que você corrigiu e ajustes) para propor regras novas;
  - **arquiva** o projeto (pede confirmação): os arquivos de trabalho vão para a Lixeira e fica só a capa no card.

---

## 5. O Storyboard (ajuste cena a cena)

É onde se faz o ajuste fino. Cada cena tem um **número fixo** (se uma cena for dividida, vira 40.1, 40.2…),
uma **miniatura**, a frase do roteiro e os controles.

### 5.1 Topo do storyboard

- **Gerar novo rascunho**: aplica tudo o que foi mudado e renderiza de novo (só os capítulos alterados).
- **Ajustadas no total**: todas as cenas que você já mexeu neste vídeo.
- **Pendentes** (clique para ver a lista): o que mudou desde o último rascunho e vai entrar no próximo — "O que
  vai mudar no próximo rascunho".
- **Descartar**: desfaz as mudanças pendentes (volta ao que está no último rascunho).
- Lista de **faltas**: cenas que entraram só com texto porque o acervo não tinha imagem — serve de lista do que
  procurar para completar o acervo.

### 5.2 Tipos de cena (o "Tipo de cena" de cada uma)

| Tipo | Como fica na tela |
|---|---|
| **Cartão** | Imagem emoldurada no centro do fundo branco, com título do capítulo em cima e legenda embaixo. |
| **Tela cheia** | Imagem ocupando a tela toda (pode ter nome sobre a arte). |
| **Recorte** | Arte com fundo transparente direto no branco (o "estilo assinatura" do canal). |
| **Meio a meio** | Imagem de um lado, texto (ou outra imagem) do outro. |
| **Tela dividida** | 2 ou 3 imagens lado a lado em altura total, cada uma com seu texto embaixo. |
| **Lista** | Até 5 imagens em fileira, entrando uma a uma. |
| **Mosaico** | Imagens menores (até 7) por cima de uma imagem de fundo (ou fundo branco). |
| **Citação** | Uma fala em destaque com a imagem de quem falou. |
| **Clipe** | Trecho de vídeo (cinemática, trailer…). |
| **Só texto** | Texto na tela, sem imagem. |
| **Diálogo** | Conversa entre personagens com os retratos. |
| **Transição de seção** / **Capa** | Feitas a partir da capa (não precisam de ajuste). |

No canal Pokémon há também **Ficha** (dados da Pokédex desenhados: tipos, altura, peso, atributos) e **Rajada**
(sequência rápida de imagens com flash).

### 5.3 Controles de cada cena

- **Trocar imagem / Buscar imagem**: abre os candidatos que o diretor considerou e uma busca no acervo (por nome
  de arquivo, personagem ou descrição em português/inglês).
- **Buscar na internet**: procura imagens na web (em inglês costuma achar mais); a escolhida é baixada e
  catalogada na hora, com a página de origem guardada para os créditos.
- **Colar link de vídeo** (YouTube etc.): baixa o vídeo (até Full HD) e corta em tomadas. Os campos **de** e
  **até** (ex.: `1:23` e `1:41`) são opcionais: preenchidos, baixam **só aquele trecho**.
- **Escolher clipe / escolher o momento**: num clipe, abre o vídeo original para escolher **de onde** o clipe
  começa (ele segue até o fim do vídeo). Um clipe curto demais para a cena é tocado em câmera lenta — escolher um
  início resolve.
- **Legenda**: o texto da cena (edite à mão). **Quando o texto entra**: escolha a palavra em que ele aparece.
- **A cena começa em**: move o corte entre esta cena e a anterior para outra palavra.
- **Enquadrar**: clique no ponto da imagem que deve ficar no centro (e para onde o zoom vai).
- **Movimento**: aproximar, afastar, ← pan, pan →, subir, descer ou **nenhum**.
- **Entrada** (transição da cena inteira): automática, corte, empurrar ou sobrepor.
- **Remover fundo / Voltar o fundo**: tira o fundo da imagem para usar como recorte (o arquivo original não é
  alterado).
- **Pôr fundo / Trocar fundo** (lista e mosaico): imagem atrás dos itens.
- **Efeito sonoro**: ouvir ou **tirar** o efeito da cena.
- **Juntar com a próxima**: transforma esta cena e a seguinte numa **tela dividida** (dá para juntar até 4).
  **Desfazer** separa de novo.
- **Remover cena**: a cena sai e o tempo dela vai para a vizinha.
- **Desfazer ajustes**: volta a cena para a decisão automática.
- **Pedir ao diretor** (usa cota da IA): escreva o que quer ("aqui é metáfora, quero algo de destruição", "use um
  clipe da cinemática", "troque por um meme de choque", "use as imagens X, Y e Z"). O diretor vê o trecho inteiro
  e pode até **dividir** a cena em várias.

### 5.4 Itens (tela dividida, lista e mosaico)

Na aba de itens, cada item tem:

- **imagem própria** (candidatos + busca, inclusive na internet) e **enquadrar este item**;
- **texto na tela** (dividida e lista): campo editável — Enter para salvar, vazio para tirar;
- **entra**: junto com a cena ou numa palavra escolhida;
- **entrada**: automática, nenhuma, aparecer, deslizar, revelar ou pop;
- **remover item** e **+ adicionar item** (até 3 na dividida, 5 na lista, 7 no mosaico — no limite o botão some).

### 5.5 Dicas

- Tudo o que é mudado fica **pendente** até o próximo rascunho. Junte vários ajustes e gere um rascunho só.
- O selo "escolhida por você" indica escolha manual — ela vale sempre.
- Se uma imagem **sumir da pasta do acervo**, a cena que a usava pega outra automaticamente no próximo rascunho
  (e o capítulo dela é renderizado de novo).

---

## 6. O acervo (imagens e vídeos)

- É a pasta de imagens/vídeos do canal (ex.: `catálogo sequencial LOL`). **Nunca é alterada** pela ferramenta.
- **Nomes de arquivo importam**: o personagem é reconhecido pelo nome (`varus3.jpg` → Varus). Imagens de um
  personagem novo, sem nenhuma outra com o mesmo nome, podem ficar sem etiqueta — use nomes claros.
- **GIF animado** funciona em tela cheia, cartão e recorte. Atenção: um `.gif` com um quadro só é imagem parada.
- O que é baixado da internet fica em `dados\acervo_internet\` (imagens em `busca\`, vídeos em `clipes\`), fora
  da pasta do acervo.
- O botão **Atualizar acervo** cataloga o que foi adicionado à pasta.

---

## 7. Problemas comuns

| O que aparece | O que fazer |
|---|---|
| O painel não abre / "não foi possível conectar" | O servidor está desligado: abra o `iniciar.bat`. |
| Card parado em "Em andamento" e nada acontece | O servidor foi desligado no meio. Ligue de novo: ele retoma sozinho. |
| Mudança no código/correção "não pegou" | Feche a janela do servidor e abra o `iniciar.bat` de novo (nunca durante um render). |
| "Cena sem imagem boa" | O acervo não tinha imagem para aquela cena: escolha uma no storyboard ou busque na internet. |
| Um capítulo que ninguém mexeu foi renderizado de novo | Provavelmente um arquivo usado nele saiu da pasta do acervo. |
| Clipe em câmera lenta / "travando" | A tomada é mais curta que a cena: escolha o momento de início no clipe. |
| GIF não anima | O arquivo tem um quadro só; troque pela versão animada. |
| "Este tipo de cena comporta no máximo N itens" | Troque o tipo para lista ou mosaico para mais imagens. |

---

## 8. Glossário

- **Acervo**: o catálogo de imagens e vídeos que a ferramenta pode usar.
- **Bloco**: um capítulo do vídeo (a introdução também é um bloco). O render é feito por bloco.
- **Rascunho**: versão do vídeo com a voz guia, para ajustar antes de gravar.
- **Voz guia**: narração provisória de IA. Nunca publicada.
- **Diretor**: a IA que planeja as cenas e escolhe as imagens.
- **Tomada**: um trecho contínuo de um vídeo do acervo (os vídeos são cortados em tomadas).
- **Pendente**: ajuste feito no storyboard que ainda não entrou em um rascunho.
- **Cota**: o limite de uso do Claude no plano Pro. Pedidos ao diretor, roteiros e conferências gastam cota;
  ajustes manuais no storyboard não gastam.
