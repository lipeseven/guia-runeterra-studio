# Observações gerais do vídeo (voz ou texto)

Painel **"Observações gerais"** na página de qualquer card (Runeterra, F1 vertical, horizontal animado, documentário),
na coluna da direita, acima de Recursos.

## Como usar
- **Microfone**: clicar para gravar e clicar no quadrado para parar, ou segurar o botão enquanto fala e soltar.
  O navegador grava (MediaRecorder, webm/opus), envia ao servidor, e aparece "transcrevendo…". O texto cai no campo,
  **editável**: corrija e clique em "Salvar observação". Ditar de novo acrescenta ao que já está no campo.
- **Digitar**: escrever direto no campo e salvar.
- **"áudio"**: transcreve um arquivo já gravado (wav, mp3, m4a, ogg, webm, flac).
- Cada observação mostra a hora (mic = ditada; "editada" quando mudou); lápis edita, lixeira apaga (pergunta antes).

Microfone só funciona em **localhost/127.0.0.1 ou https** (regra do navegador). Pelo IP do Wi-Fi (celular) aparece o
aviso: digite ou envie um áudio. Permissão negada → mensagem com o caminho (cadeado → Microfone → Permitir).

## Onde fica
- Banco do canal: tabela `observacoes` (sai junto com o card excluído). Espelho: `<projeto>/observacoes.json`.
- Áudio do ditado: `<projeto>/observacoes_audio/`, apagado assim que transcreve (fica só o texto).
- **Documentário F1**: a cada leitura do card, o painel copia para `horizontal/observacoes.txt`, que entra nos prompts
  da **História**, da **SPEC** e do **pedido por cena** como "Observações gerais do Felipe" (valem como pedido explícito).
  Mudar uma observação muda o prompt (o cache por prompt não reaproveita a resposta antiga). Nos outros formatos as
  observações só ficam gravadas e visíveis (ainda não entram no diretor).

## Transcrição
`tools/audio/ditado.py <áudio>` → JSON. FFmpeg decodifica para 16 kHz; faster-whisper `large-v3-turbo` (o mesmo da
limpeza da gravação), PT-BR, VAD. Tenta a GPU (float16) e cai para a CPU (int8) se a CUDA falhar (ex.: VRAM ocupada
por um render). O servidor roda o script num processo à parte numa thread, um ditado por vez; a tela pergunta
`GET /api/transcricoes/{id}` a cada segundo.

## API (`app/servidor/observacoes.py`)
| Rota | Faz |
|---|---|
| `GET /api/videos/{id}/observacoes` | lista |
| `POST /api/videos/{id}/observacoes` `{texto, origem: voz\|texto}` | salva |
| `PUT /api/videos/{id}/observacoes/{oid}` `{texto}` | edita (`editada_em`) |
| `DELETE /api/videos/{id}/observacoes/{oid}` | apaga |
| `POST /api/videos/{id}/observacoes/transcrever` (arquivo) | inicia ditado → `{tarefa}` |
| `GET /api/transcricoes/{tarefa}` | `na_fila` / `transcrevendo` / `pronto` (texto) / `falhou` (erro) |

## Teste
`.venv\Scripts\python.exe F1\horizontal\testes\painel\testar_observacoes.py [-v]` (~10 s com GPU): fala gerada pela voz
pt-BR do Windows (wav e webm/opus) → Whisper → texto; salvar/editar/apagar; recusas; prompts da História e SPEC com as
observações; vertical/horizontal intactos; card excluído leva as observações.
