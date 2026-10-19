# Instalação e recuperação (formatar o PC e voltar de onde parou)

O **código** está no GitHub (`github.com/lipeseven/guia-runeterra-studio`, privado). Os **dados** NÃO estão no Git
(são grandes e pessoais) — por isso o passo 1 é o backup.

## 1. Antes de formatar: o que copiar para um HD externo / nuvem

| O quê | Onde | Por quê |
|---|---|---|
| `.env` | raiz do projeto | chaves (Fish Audio, Freesound, Hugging Face) — não estão no Git |
| `dados/` | raiz do projeto | bancos (`studio.db`, `acervo.db`, `canais/`), miniaturas, índices de busca (CLIP), efeitos sonoros (`sfx/`), modelos (`modelos/`), análises das referências, backups |
| `projetos/` e `projetos_pokemon/` | raiz do projeto | os vídeos em andamento (direção, storyboard, gravações, renders) |
| `catálogo sequencial LOL` | `Downloads` | acervo do Guia de Runeterra (inclui `_oficial_riot/`) |
| `catálogo sequencial POKEMON` | `Downloads` | acervo do canal Pokémon (inclui `_oficial/`) |
| `recursos de vídeo para aprender*` | raiz do projeto | vídeos de referência (dá para baixar de novo) |

Dica: `dados/cache_voz`, `dados/backups` e `dados/analise_referencias` são recriáveis — dispensáveis se faltar espaço.
Os renders de rascunho dentro de `projetos/*/trabalho/` também (o sistema refaz).

## 2. Programas (Windows)

Instale, nesta ordem (todos grátis):

1. **Driver NVIDIA** atualizado (RTX 4060; CUDA vem junto com o PyTorch).
2. **Git**: `winget install Git.Git`
3. **GitHub CLI**: `winget install GitHub.cli` → `gh auth login` (conta lipeseven)
4. **Python 3.12**: `winget install Python.Python.3.12`
5. **Node.js 24**: `winget install OpenJS.NodeJS`
6. **FFmpeg** (com NVENC): `winget install Gyan.FFmpeg`
7. **Claude Code** (o diretor/roteirista usam `claude -p` com o plano Pro): `npm install -g @anthropic-ai/claude-code`
   → rodar `claude` uma vez e fazer login com a conta do plano Pro.

## 3. Código e dependências

```bat
cd %USERPROFILE%\Downloads
gh repo clone lipeseven/guia-runeterra-studio "exclusive Claude"
cd "exclusive Claude"

py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128

cd app\video  && npm install && cd ..\..
cd app\painel && npm install && npm run build && cd ..\..
```

`requirements.txt` tem as versões exatas que estavam funcionando (torch 2.11 + CUDA 12.8).
Se o `pip` reclamar do torch, instale ele antes:
`.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128`.

## 4. Devolver os dados

- Copie de volta `.env`, `dados/`, `projetos/`, `projetos_pokemon/` para a raiz do projeto.
- Copie as pastas `catálogo sequencial LOL` e `catálogo sequencial POKEMON` para `Downloads`.
  (Se a pasta for parar em outro lugar, ajuste `canais/runeterra/canal.toml` e `canais/pokemon/canal.toml` → `[pastas] acervo`.)
- Sem `.env`? Copie `.env.example` para `.env` e preencha as chaves (links dentro do arquivo).

Os modelos que se baixam sozinhos na primeira vez (precisam de internet): CLIP (busca de imagens), Whisper
(transcrição), CLAP (efeitos sonoros), sentence-transformers (conferência do roteiro). A voz local de reserva (Piper)
fica em `dados/modelos/` — vem junto com o backup de `dados/`.

## 5. Ligar

- Guia de Runeterra: `iniciar.bat` → http://127.0.0.1:8765
- Pokémon: `iniciar_pokemon.bat` → http://127.0.0.1:8766

Conferência rápida: o quadro abre com os cards de antes, "Atualizar acervo" termina com "0 arquivos novos" e um
storyboard antigo abre com as miniaturas.

## 6. Reabrir a conversa com o Claude Code

O histórico da conversa fica em `%USERPROFILE%\.claude\projects\` (inclui a memória do assistente:
`...\memory\`). Copie essa pasta também se quiser manter a mesma sessão e as preferências. Sem ela, o `CLAUDE.md`
do projeto e os documentos de `docs/` já bastam para retomar o trabalho.
