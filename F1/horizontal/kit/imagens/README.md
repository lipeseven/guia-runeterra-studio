# kit/imagens: trechos reais da corrida, com validação (independente de motor)

Resolve o defeito 1 do teste HyperFrames (`C:\Users\Felipe\teste-motores\hyperframes\APONTAMENTOS_FELIPE.md`): o texto
falava da volta 55 e a imagem era da volta 1. Aqui um trecho só entra como **validado** se a volta, o piloto, a sessão
(e o evento, quando pedido) batem com a afirmação, conferidos contra o OpenF1. Se não der para provar, ele sai marcado
`NAO_VALIDADO_*` (ou nem sai), e nunca é usado sem aviso.

## API
```python
import sys; sys.path.insert(0, r"F1\horizontal\kit\imagens")
from imagens import achar, validar_arquivo
r = achar({"sessao": 11412, "piloto": 44, "volta": 62, "evento": "bandeira_amarela"})
r["arquivo"], r["quadro"], r["validado"], r["status"], r["evidencia"], r["credito"]
validar_arquivo(r"...\rh_20.mp4", {"sessao": 11412, "piloto": 16, "volta": 55},
                "https://www.youtube.com/watch?v=lkb5kqDJYXk", ini_na_fonte=20)   # trecho já baixado
```
- `achar(afirmacao, destino=None, fontes=None, duracao=5.0, canais=("FORMULA 1",), passo=10.0)`.
  `fontes` = URLs a usar; sem elas, busca no YouTube só nos canais oficiais (vídeos de até 25 min cujo título não
  contradiz a sessão). `destino` padrão: `F1/dados/imagens/<slug>/` (no projeto: `F1/dados/projetos/<slug>/horizontal/ativos/imagens`).
- `status`: `validado` | `nao_validado` (não deu para provar: arquivo `NAO_VALIDADO_*.mp4`) | `reprovado` (a imagem
  contradiz a afirmação: o recorte é apagado) | `nao_encontrado` (nenhuma fonte mostra aquela volta; `arquivo = None`).
- Saída na pasta: `<slug>.mp4` (trecho de `duracao` s, 1080p, H.264, **sem áudio**), `<slug>.png` (quadro de
  referência), `<slug>.json` (resultado com toda a evidência), `FONTES.txt` (crédito por arquivo; os não validados
  saem marcados).
- `evento` com checagem automática: `pit`, `ultrapassagem`, `bandeira_amarela` (= `incidente`, `rodada`),
  `volta_mais_rapida`. Qualquer outro texto vira "não verificado" (e o trecho não fica validado).

## Como valida
A transmissão mostra `LAP C/71`, que é a volta do **líder**, não a do piloto. Então:
1. **Relógio da sessão (OpenF1 `/v1/laps`, `/v1/sessions`):** a volta N do piloto vira uma janela UTC
   (`date_start` .. `+ lap_duration`). Cada valor C do contador vira outra janela (primeiro carro a abrir a volta C ..
   primeiro a abrir a C+1). Ex.: volta 55 do Leclerc = 18:16:09–18:17:24 → contador esperado **55 ou 56**.
2. **Contador lido no trecho (OCR local, RapidOCR):** um contador fora do esperado = **reprovado**, com os horários
   na evidência ("contador 1 = 17:03:21–17:04:54 UTC, fora da volta 55..."). Quadros com `REPLAY` não contam.
3. **Confiança:** fração do tempo do contador visto que cai dentro da volta pedida. Abaixo de 60% = `ambiguo`
   (pode ser a volta vizinha; ex.: contador 55 sozinho para a volta 55 do Leclerc dá 45%, porque ele estava ~40 s atrás
   do líder).
4. **Âncora:** se o contador vira de C para C+1 no mesmo plano (sem corte de câmera), o tempo do vídeo passa a ser o
   relógio da sessão (a virada = primeiro carro abrindo a volta C+1); o trecho inteiro tem de cair dentro da volta.
5. **Piloto:** sobrenome completo escrito na tela (a sigla de 3 letras da torre não conta, todos estão nela) ou citado
   na narração (legendas automáticas do YouTube no intervalo; marcado `forca: narracao`).
6. **Sessão:** ano, lugar e tipo no título (título de Qualifying/Sprint/outro ano reprova), data de publicação não
   anterior à sessão e total do contador (`/71`) = total de voltas da sessão.
7. **Evento:** `/v1/pit`, `/v1/overtakes`, `/v1/race_control` dentro da janela da volta.

Busca barata: um quadro a cada 10 s por busca HTTP no fluxo (o vídeo nunca é baixado inteiro), OCR só do canto do
contador (o quadro inteiro se o vídeo não tem contador ali, como nos onboards); refino a cada 1 s perto dos acertos;
recorte só do trecho escolhido; a validação final roda de novo no **arquivo recortado**, a cada 0,5 s.
Cache (OpenF1, metadados, varreduras, legendas) em `F1/dados/imagens/cache/`. `KIT_IMAGENS_DADOS` muda a pasta.

## Arquivos
| Arquivo | O que é |
|---|---|
| `imagens.py` | `achar`, `validar_arquivo`, varredura, refino, escolha do trecho, FONTES.txt |
| `validar.py` | validação pura (sem rede e sem OCR): sessão, volta, piloto, evento |
| `relogio.py` | janelas da volta do piloto e do contador da TV no relógio da sessão |
| `leitura.py` | OCR e leitura do contador (`LAP1I71`, `LAP3171`, `LAP 11 171` ...), nomes, marcas (REPLAY, YELLOW FLAG) |
| `fonte_video.py` | yt-dlp (metadados, busca, fluxo, legendas) e ffmpeg (quadro solto, recorte) |
| `openf1.py` | OpenF1 com cache |
| `testes.py` | testes (offline; `--rede` acrescenta o caso real) |
| `exemplo.py` | o exemplo do critério de pronto |
| `dados_teste/openf1_11412.json` | fixture do OpenF1 (GP de São Paulo 2026, corrida) para os testes offline |

Dependências (no `.venv` do projeto): `yt-dlp`, `opencv-python-headless`, `onnxruntime` e **`rapidocr-onnxruntime`**
(instalado nesta tarefa: `.venv\Scripts\python.exe -m pip install rapidocr-onnxruntime`); `ffmpeg` no PATH.

```
.venv\Scripts\python.exe F1\horizontal\kit\imagens\testes.py           (offline, ~1 s)
.venv\Scripts\python.exe F1\horizontal\kit\imagens\testes.py --rede    (rede + OCR, ~5 min na 1ª vez; depois usa o cache)
.venv\Scripts\python.exe F1\horizontal\kit\imagens\exemplo.py
```

## Resultado do exemplo (2026-11-13, GP de São Paulo 2026, session_key 11412)
| Pedido | Resultado |
|---|---|
| Leclerc (16), volta 55 | `nao_encontrado`, `arquivo = None`. Janela 18:16:09–18:17:24 UTC → contador esperado 55/56. Vistos: Race Highlights 1, 4–8, 10, 17–18, 20–21, 24, 35, 38, 63–64, 66, 70–71; Top 10 Onboards 1, 63, 66, 70; Nine Minutes Of Max Verstappen 1, 4, 17, 24, 38; Radio Rewind 1–2, 4, 7–8, 10, 14, 16, 18, 24, 37, 45, 49, 60, 65. **Não devolve a volta 1** (nem a 64, a mais próxima nos highlights). ~5 min na 1ª vez. |
| `rh_20.mp4` do HyperFrames contra a volta 55 do Leclerc | `reprovado`: "contador 1 = 17:03:21–17:04:54 UTC, fora da volta 55 do carro 16 = 18:16:09–18:17:24 UTC (esperado [55, 56])" |
| Hamilton (44), volta 62, `bandeira_amarela` | `validado`: Race Highlights 05:22–05:27 (pit lane no 1º s, depois onboard do Hamilton com YELLOW FLAG / TRACK HAZARD). Sessão ok (ano, lugar, "Race"); volta ok (contador 63, 81% dentro da volta 62 dele, 18:25:08–18:27:04); piloto ok ("HAMILTON" na tela em 2,5–4,5 s); evento ok (race_control 18:26:44 "DOUBLE YELLOW IN TRACK SECTOR 15"). 7,8 MB de mp4 + png. |

`testes.py`: 57 checagens offline e 62 com `--rede`, 0 falhas.

## Limites (o que NÃO foi verificado)
- **A volta 55 do Leclerc não existe em vídeo oficial** encontrado: os highlights pulam da volta 38 para a 63, e os
  outros vídeos oficiais da corrida não mostram aquela volta. O kit responde `nao_encontrado`, que é a resposta certa,
  mas o caso positivo do exemplo é outra volta (Hamilton, volta 62, incidente com bandeira amarela).
- **Ninguém assistiu aos recortes além de mim por quadros soltos.** O trecho do Hamilton tem um corte de câmera no
  primeiro segundo (pit lane com outros carros, mesma volta do contador): a evidência avisa dos cortes; quem monta a cena
  decide se usa o trecho todo.
- Só canais oficiais por padrão. Reenvios da corrida inteira por terceiros (que existem no YouTube) **não** são usados.
  Direito de uso: o crédito vai em `FONTES.txt`; antes de publicar, o Felipe confere a política do canal.
- Contador da TV legível só em transmissão com o gráfico padrão de 2026 (o OCR leu 41 de 49 quadros dos highlights).
  Classificação e treinos não têm contador de volta: a volta fica `nao_verificado`.
- Confiança 60% é um limiar escolhido aqui, não medido em muitos vídeos. A âncora por virada do contador depende da
  detecção de corte por histograma (pode errar em panorâmicas rápidas).
- O nome pela narração (legenda automática) é evidência fraca: o narrador pode citar alguém que não está na imagem.
- Trechos saem sem áudio (a narração é a voz do Felipe; o som ambiente fica para o `kit/sfx`/montador).
