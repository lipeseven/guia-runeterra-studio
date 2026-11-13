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

## Qualquer GP (fase 2b)
Nada é fixo de GP, piloto ou sessão: ano, lugar (`location`, `country_name`, `circuit_short_name`, `meeting_name`
sem " Grand Prix"), tipo de sessão, total de voltas (maior volta registrada no `/v1/laps`) e tempos de volta vêm do
OpenF1 da `session_key` pedida. O que muda por tipo de sessão:
- **Corrida e sprint:** a TV mostra `LAP C/N` (N = total da sessão, ex.: /71 em Interlagos 2026, /53 em Monza 2025).
  Validação pelo contador (abaixo).
- **Classificação e treinos:** não há contador. A volta é provada pelo **tempo dela escrito na tela** (o OpenF1 tem
  cada volta ao milésimo: `1:19.007` = volta 16 do Leclerc na classificação de Monza 2025), com três travas, porque
  a torre e os gráficos "BEST LAP" continuam mostrando o tempo minutos depois:
  1. só vale se o tempo **aparece** dentro do trecho (ausente num quadro e presente no seguinte, sem corte entre
     eles = fechamento da volta); presente desde o 1º quadro = `ambiguo` (não valida);
  2. tempo na tela de uma volta de **qualquer** piloto que terminou mais de 20 s depois da pedida = `reprovado`
     ("o trecho é de depois", pelo relógio da sessão);
  3. tempo de outra volta do mesmo piloto = `reprovado`. Nenhum tempo = `nao_verificado`.
  A busca lê o quadro inteiro (o tempo não fica no canto do contador) a cada 5 s e prefere o trecho em que o tempo
  aparece, com o nome do piloto, sem replay e sem tempo posterior.

## Como valida (corrida/sprint)
A transmissão mostra `LAP C/N`, que é a volta do **líder**, não a do piloto. Então:
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
   anterior à sessão e total do contador (`/N`) = total de voltas da sessão no OpenF1.
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
| `dados_teste/openf1_9908.json`, `openf1_9912.json` | fixtures da 2ª pista: Monza 2025, classificação e corrida |

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

### 2ª pista (2026-11-13, Monza 2025, classificação 9908): Leclerc (16), volta 16 = 1:19.007
| Versão | Resultado |
|---|---|
| 1ª (só "tempo na tela") | `validado` em Qualifying Highlights `XSK1zf4LMZQ` 05:04–05:09 — **ERRADO**: olhei o quadro e era o carro do Verstappen com o gráfico "BEST LAP" VER × LEC (o tempo do LEC estava no gráfico). Daí as travas 1 e 2 acima. |
| final | `nao_validado` (`NAO_VALIDADO_s9908_c16_v16.mp4`, 04:13–04:18): sessão ok ("2025 Italian", Qualifying), piloto ok (LECLERC na tela), volta `ambiguo` — o tempo já está na tela desde o 1º quadro. Olhando o quadro, é o momento certo (carro do LEC logo depois da linha, caixa "LECLERC −0.049" e torre com LEC 1:19.007), mas o kit não consegue provar sozinho: fica para o Felipe conferir. O trecho 05:04 agora é descartado pela trava 2 (1:18.923 do VER terminou depois). Vídeos de outros GPs de 2025 descartados pela data. |

`testes.py`: 81 checagens offline (57 de Interlagos + 24 de Monza 2025: tempo que aparece × já na tela × depois de corte,
tempo de volta posterior de outro piloto (o erro do gráfico BEST LAP), outra volta do mesmo piloto, replay, título de
outra sessão/ano/país, pole como volta mais rápida, total /53 do OpenF1, contador fora da volta), 0 falhas.
(`--rede`: 62 em Interlagos na fase 2; não rodado de novo na 2b.)

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
  Classificação e treinos não têm contador: a volta só é provada se o tempo dela aparecer escrito (a TV mostra o
  tempo ao fechar a volta, por poucos segundos; volta lenta, de saída ou sem tempo no OpenF1 fica `nao_verificado`).
  Risco que sobra: a torre/gráfico ENTRAR na tela no mesmo plano (sem corte) minutos depois, sem nenhum tempo novo
  visível, passaria pela trava 1. Na única busca real feita (Monza) o kit não validou nada (resultado `nao_validado`).
- Total de voltas = maior volta no `/v1/laps`. Numa corrida encurtada (bandeira vermelha sem retomada) a TV mostra o
  total PROGRAMADO e o kit reprovaria a sessão pelo `/N` lido: não testado, não há caso assim nas fixtures.
- O canto do contador (`REGIAO_CONTADOR`) é o do gráfico da TV de 2026; em outro gráfico a varredura cai para o quadro
  inteiro (mais lenta), sem garantia de leitura.
- Confiança 60% é um limiar escolhido aqui, não medido em muitos vídeos. A âncora por virada do contador depende da
  detecção de corte por histograma (pode errar em panorâmicas rápidas).
- O nome pela narração (legenda automática) é evidência fraca: o narrador pode citar alguém que não está na imagem.
- Trechos saem sem áudio (a narração é a voz do Felipe; o som ambiente fica para o `kit/sfx`/montador).
