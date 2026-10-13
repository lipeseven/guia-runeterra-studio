# Arquitetura — Guia de Runeterra Studio

Assistente de edição local para o canal **Guia de Runeterra** (lore de League of Legends, PT-BR).
Não é uma fábrica de vídeos: o sistema faz o trabalho braçal, e as decisões criativas
(roteiro final, humor, aprovação de cenas, narração) são do Felipe.

Documentos relacionados: [guia_de_estilo.md](guia_de_estilo.md).

---

## 1. Princípios (não negociáveis)

1. **Tudo local e gratuito**, exceto o Claude (plano Pro, via `claude -p`). Sem nuvem, sem RunPod.
2. **Nunca parecer produção em massa**: voz real do Felipe, pontos de controle humanos,
   variação controlada, memória de uso de mídias, cortes com "imperfeição humana".
3. **Inspiração, não cópia**: do canal de referência saem fatos e temas, nunca frases.
   Detector de semelhança obrigatório antes de gravar.
4. **Voz de IA nunca vai para o vídeo publicado.** A voz guia só serve para o rascunho.
5. **Direção ancorada em palavras, não em segundos**: trocar a narração ressincroniza tudo.
6. **Econômico com a cota do Claude**: miniaturas em vez de imagens grandes, chamadas em lote,
   resultados salvos (nada é pedido duas vezes), pausa e retomada se a cota acabar.
7. **Arquivos do Felipe nunca são movidos ou alterados**; o sistema só lê e cataloga.

---

## 2. Fluxo de um vídeo

```
 1. TEMA ─────────────► Felipe escolhe o tema (ou o sistema sugere).
 2. PESQUISA ─────────► Vídeo(s) do canal de referência → transcrição → MAPA DE FATOS (Claude).
                        Fontes primárias (Universe, wiki, contos, HQs) → conferir e ampliar fatos.
 3. ÂNGULO ───────────► Claude sugere estruturas/ganchos que a referência não explorou.
                        ★ Felipe escolhe o ângulo e a ordem das seções.
 4. ROTEIRO ──────────► Claude escreve rascunho no estilo do Felipe.
                        Detector de semelhança marca trechos próximos demais da referência.
                        ★ Felipe reescreve/aprova (é o texto que ele vai ler).
 5. VOZ GUIA ─────────► Fish Audio (reserva: Edge TTS) lê o roteiro na velocidade do Felipe.
 6. TEMPOS ───────────► faster-whisper: tempo de cada palavra + correção pelo roteiro/glossário.
 7. MÍDIAS ───────────► Para cada trecho: acervo local (CLIP + etiquetas) e internet
                        (Riot, wiki, Reddit, entrada manual), meta 50/50. IA só para lacunas.
 8. DIREÇÃO ──────────► Claude escolhe tipo de cena + mídias + legendas + palavras em vermelho,
                        ancorado em palavras. Variação controlada aplicada.
 9. RASCUNHO ─────────► Remotion Player no painel: vídeo completo com a voz guia.
                        ★ Felipe revisa: troca mídias, legendas, memes; ajusta o roteiro.
10. GRAVAÇÃO ─────────► Felipe grava lendo o roteiro final.
11. LIMPEZA DE ÁUDIO ─► Ruído (DeepFilterNet), silêncios longos, regravações (fica a última),
                        volume. faster-whisper de novo → ressincronização da direção.
12. RENDER ───────────► Remotion (cartões) + FFmpeg/NVENC (tela cheia, clipes, mix, final).
                        ★ Felipe assiste o resultado final.
13. PUBLICAÇÃO ───────► Título, descrição (com créditos automáticos), thumbnail — escritos com Felipe.
                        Upload manual por enquanto.
```

★ = ponto de controle humano obrigatório.

---

## 3. Componentes

| Componente | Tecnologia | Papel |
|---|---|---|
| **Painel** | React 19 + TypeScript + Vite + Tailwind + Radix + dnd-kit | Quadro de vídeos (Ideia → Roteiro → Gravação → Montagem → Revisão → Publicado), editor de roteiro, revisão de cenas com Remotion Player, acervo |
| **Servidor** | Python 3.12 + FastAPI | API do painel, fila de tarefas, orquestra as etapas. Escuta só em `127.0.0.1` |
| **Banco** | SQLite (`dados/`) | Vídeos, roteiros, cenas, mídias, histórico de uso, créditos |
| **Diretor / roteirista** | Claude Code headless (`claude -p`) | Mapa de fatos, ângulos, roteiro, direção de cenas, títulos |
| **Transcrição** | faster-whisper `large-v3-turbo` (GPU) | Tempo por palavra; glossário de nomes de LoL |
| **Voz guia** | Fish Audio `s2.1-pro-free` → reserva Edge TTS | Só para rascunho |
| **Áudio** | DeepFilterNet / RNNoise + FFmpeg | Limpeza, cortes, normalização (-14 LUFS), ducking dos efeitos |
| **Busca no acervo** | CLIP ViT-L-14 (GPU) + etiquetas | Busca por significado e por personagem/uso |
| **Coleta na internet** | APIs: Data Dragon/CommunityDragon, wiki (MediaWiki), Reddit, museus; `yt-dlp` | Imagens, HQs, cinemáticas, transcrições da referência |
| **Imagens por IA** | Z-Image-Turbo no ComfyUI local | Só lacunas |
| **Efeitos sonoros** | Stable Audio Open (catálogo gerado uma vez) | Whooshes, impactos, ambiências por etiqueta |
| **Cartões animados** | Remotion | Grade de ícones, cartão emoldurado, diálogo, citação, título, colagem, gameplay |
| **Render final** | FFmpeg + NVENC | Arte em tela cheia (Ken Burns), clipes, mixagem, codificação |
| **Recortes/ícones** | rembg (local) + Pillow | Remover fundo, gerar ícones redondos |

Iniciar tudo: `iniciar.bat` (um clique) ou pedir ao Claude Code nesta pasta.

---

## 4. Modelo de dados (resumo)

- **video**: tema, status (coluna do quadro), ângulo, referências usadas, datas.
- **fato**: texto, fonte (URL/obra), verificado (sim/não), vídeo.
- **roteiro**: versões; cada versão com seções → frases → palavras.
- **cena**: vídeo, tipo (do vocabulário do guia de estilo), âncora (frase/palavra inicial e final),
  mídias, legenda, palavras em destaque, parâmetros de movimento, aprovada (sim/não).
- **midia**: já existe em `dados/acervo.db` — origem, autor, URL, licença, categoria,
  personagens, descrição, uso, tags.
- **uso_midia**: mídia × vídeo × data → evita repetição entre vídeos.
- **credito**: gerado a partir das mídias usadas → descrição do vídeo e marca na tela (fan art).

---

## 5. Estrutura de pastas

```
exclusive Claude/
├─ docs/                     arquitetura, guia de estilo
├─ app/
│  ├─ servidor/              FastAPI (Python)
│  ├─ painel/                React + Vite
│  └─ video/                 projeto Remotion (modelos de cena)
├─ tools/                    scripts de linha de comando (análise, acervo, ...)
├─ dados/                    (fora do Git) bancos, miniaturas, índices
├─ projetos/                 (fora do Git) uma pasta por vídeo: roteiro, áudio, cenas, render
├─ projeto.toml              configuração
├─ .env                      (fora do Git) chaves
└─ iniciar.bat
```

---

## 6. Ordem de construção

| Fase | Entrega | Como valida |
|---|---|---|
| **0. Base** ✅ | Ambiente, guia de estilo, acervo catalogado + busca | Feito |
| **1. Prova do Remotion** | 2–3 modelos de cartão (grade de ícones, cartão emoldurado, diálogo com palavras em vermelho) sincronizados com tempos do Whisper | Medir tempo de render na RTX 4060; Felipe aprova o visual |
| **2. Áudio** | Voz guia (Fish/Edge), limpeza da gravação, detecção de regravações, ressincronização | Gravação real do Felipe |
| **3. Diretor** | Claude transforma roteiro + tempos em lista de cenas (JSON) usando o acervo | Rascunho de um trecho do vídeo dos Demônios refeito |
| **4. Render completo** | Remotion + FFmpeg montando um vídeo inteiro | Vídeo de 5 min de ponta a ponta |
| **5. Painel** | Quadro, revisão de cenas com Player, troca de mídias | Felipe usa sem terminal |
| **6. Pesquisa e roteiro** | Referência → mapa de fatos → fontes → roteiro → detector de semelhança | Roteiro de um vídeo novo |
| **7. Internet** | Coletores (Riot, wiki, Reddit, entrada manual) alimentando o acervo, créditos | Vídeo com proporção ~50/50 |
| **8. Extras** | Efeitos sonoros (catálogo), imagens IA, thumbnail, títulos | — |

Cada fase gera algo utilizável sozinho; nenhuma depende de todas as outras estarem prontas.
