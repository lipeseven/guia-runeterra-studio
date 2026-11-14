# kit/sfx — banco único de efeitos sonoros do horizontal (independente de motor)

Junta num lugar só o melhor dos SFX dos dois testes (`C:\Users\Felipe\teste-motores\remotion` e `\hyperframes`), os sons
livres que o sistema já tinha baixado (`dados/comum/sfx`, Freesound CC0/CC BY e Stable Audio Open) e sons sintetizados
aqui mesmo. O diretor pede **categoria + palavra-âncora + intensidade**; o kit escolhe a variação, alinha o pico do som
na palavra e entrega o mesmo resultado para numpy, ffmpeg, Remotion e HyperFrames.

## Arquivos
| Arquivo | O que é |
|---|---|
| `gerar.py` | gera/regera `banco/<categoria>/<id>.wav` e `catalogo.json` (cortes, normalização, medidas) |
| `sintese.py` | síntese procedural (numpy) dos 23 sons próprios, com sementes fixas |
| `freesound.py` | amplia o banco pela API do Freesound: `buscar` (busca, filtra, mede, escolhe → `freesound.json`), `baixar`, `folhas` (espectrogramas) |
| `freesound.json` | sons escolhidos da API: id, autor, licença (+url da licença), url, url da prévia, medidas e relatório de rejeições; `gerar.py` regera por ele **sem busca e sem chave** |
| `medir.py` | leitura/gravação, BS.1770-4 (LUFS integrado e momentâneo máx.), pico verdadeiro 4x, limitador |
| `sfx.py` | API Python: `Banco.para`, `para_palavra`, `capitulo`, `de_pedidos`, `creditos`; `mixar` (numpy), `mixar_ffmpeg`, `para_hyperframes`, `para_json` |
| `sfx.ts` | a mesma API em TypeScript sem dependências (Remotion, scripts Node) — mesmas escolhas que o Python |
| `catalogo.json` | o que existe no banco: arquivo, categoria, duração, pico, LUFS, pico verdadeiro, origem, licença, autor/url |
| `testes.py` | teste automático (loudness, clipping, estéreo, formato, âncora, paridade Python×TS, mixagem) |
| `exemplo/` | trilho de 20 s (`palavras.json` + `pedidos.json`), runner `exemplo_20s.py`, `eventos.ts`, `remotion/` |

O **banco (≈72 MB de WAV, 236 sons) fica fora do Git** (`.gitignore`): passa do limite de 5 MB e a licença Pixabay não permite
redistribuir os arquivos soltos. Para recriar (≈40 s; na 1ª vez baixa as 170 prévias do Freesound para
`dados/comum/freesound_cache/`, sem chave):

```
.venv\Scripts\python.exe F1\horizontal\kit\sfx\gerar.py
.venv\Scripts\python.exe F1\horizontal\kit\sfx\testes.py
```

`gerar.py` procura as fontes em `dados/comum/sfx/` e na biblioteca de SFX do HyperFrames
(`~/teste-motores/hyperframes/assets/audio`, `~/hyperframes-teste/_fonte/skills/media-use/audio/assets/sfx` ou o cache do
`npx hyperframes`). Se alguma faltar, o catálogo ganha a lista `faltando` e o teste falha. Os sons sintetizados saem
iguais sempre.

## Categorias (no catálogo: `categorias`)
Loudness medida como **LUFS-M máx** (momentânea máxima, janela de 400 ms), que serve melhor para efeito curto do que o
integrado. Todos com pico verdadeiro ≤ −1 dBTP.

| Categoria | Variações | Alvo | Faixa aceita | Dur. máx | volume_db | Uso |
|---|---|---|---|---|---|---|
| impacto | 17 | −12 | −13 a −11 | 2,5 s | 0 | peso de revelação: número grande, frase-tese |
| riser | 17 | −15 | −16 a −14 | 3,2 s | −2 | crescendo antes de capítulo/algo grandioso (o pico/fim cai na palavra) |
| whoosh | 17 | −16 | −17 a −15 | 3,0 s | −3 | troca de cena, câmera voando, cartão atravessando |
| sino | 17 | −18 | −19 a −17 | 2,6 s | −4 | fecho, nome do canal, confirmação |
| alerta | 17 | −18 | −19 a −17 | 1,8 s | −5 | erro, penalidade, bandeira, rádio |
| pop | 17 | −20 | −25 a −19 | 0,8 s | −5 | etiqueta/tag aparecendo |
| clique | 17 | −22 | −27 a −21 | 0,45 s | −6 | informação entrando ("clique, clique") |
| tecla | 17 | −24 | −30 a −23 | 0,35 s | −7 | tecla antes do texto; em sequência = digitação |
| motor | 10 | −16 | −17 a −15 | 4,0 s | −6 | carro passando/acelerando ao longe (o pico = passagem) |
| pneu | 10 | −16 | −17 a −15 | 2,5 s | −5 | freada, pneu cantando, travada, saída de pista |
| radio | 10 | −20 | −21 a −19 | 1,5 s | −6 | estática/chiado/bipe de rádio da equipe (sem voz) |
| cronometro | 10 | −24 | −30 a −23 | 0,6 s | −7 | tique de relógio/cronômetro: tempo de volta, contagem |
| grafico | 10 | −18 | −19 a −17 | 1,2 s | −5 | swoosh curto de interface: linha/barra do gráfico entrando |
| obturador | 10 | −22 | −27 a −21 | 0,6 s | −6 | câmera fotográfica: foto entrando, quadro congelado |
| whoosh_grave | 10 | −15 | −16 a −14 | 3,0 s | −3 | whoosh grave de cinema: virada de capítulo |
| boom | 10 | −14 | −15 a −13 | 3,0 s | −2 | boom subgrave por baixo de uma revelação |
| box | 10 | −20 | −21 a −19 | 4,0 s | −8 | pit/box: pistola de roda, ferramentas |
| multidao | 10 | −24 | −25 a −23 | 6,0 s | −10 | torcida ao longe (ambiente: âncora no INÍCIO, entra suave) |

Faixas largas em pop/clique/tecla: são sons de 20–150 ms; o LUFS-M deles só sobe esmagando o ataque, então o
limitador corta no máximo 6 dB e o resto fica abaixo do alvo (o que soa natural para um clique).

### De onde veio cada som (236 no total: 66 locais + 170 do Freesound pela API)
- **Elogiados nos testes** (anotados em `nota` no catálogo): `impacto_remotion_14s` (impacto de ~14 s do Remotion),
  `whoosh_capitulo_remotion` + `riser_trilha_remotion` (o "crescente + impacto" de ~16–17 s e ~47–48 s do Remotion era
  esse whoosh épico sobre o riser de ruído da trilha sintetizada; o riser foi refeito em `sintese.py` igual ao de
  `tools/trilha.py`), `impacto_hf_grave` (~13 s do HyperFrames), `clique_hf_suave` (os "clique, clique"),
  `tecla_hf` + fatias de `typing.mp3` (família da tecla antes do texto), `whoosh_hf_troca_cena` (troca de cena da
  parte 3), `sino_hf_ping_final` (sininho com o nome do canal).
- **Freesound** (23, já baixados pelo sistema em 2026-10; 17 CC0 e 6 CC BY 4.0 que exigem crédito: `Banco.creditos(eventos)` gera as linhas para a descrição).
- **Pixabay** (17, biblioteca do HyperFrames; uso livre em vídeo, sem crédito obrigatório, sem redistribuir solto).
- **Stable Audio Open** (3, gerados localmente antes; licença Stability Community).
- **Síntese própria** (23): risers (trilha, varredura, tonal, Shepard, prato reverso), impactos sub, cliques, teclas
  mecânicas, sinos FM, pops, whooshes de banda estreita, bipes de rádio/alerta.
- **Excluído de propósito**: `seletor/fs669142.wav` (= `mecanico.wav`, o som da asa abrindo do Remotion, reprovado).
  `gerar.py` recusa o arquivo e o teste confere.
- **Freesound pela API** (170, 2026-11-14; 104 CC0, 62 CC BY 4.0, 4 CC BY 3.0; nunca NC/Sampling+): `freesound.py buscar`
  (chave `FREESOUND_API_KEY` do `.env`, ~1 requisição/1,1 s) busca por categoria, baixa a prévia hq para
  `dados/comum/freesound_cache/` (fora do Git), corta/normaliza como o resto e rejeita automaticamente: texto com
  voz/música/marca, clipping, silêncio demais, ruído de fundo, banda estreita (espectro), loudness inalcançável, estéreo
  torto, riser sem crescendo, e o CLAP local (fala/canto/música) + Whisper (fala). Entre os aprovados ganha o mais
  parecido com a descrição da categoria (CLAP), no máximo 3 por autor. A lista fica em `freesound.json` (no Git, com o
  relatório de rejeições); `gerar.py` regera por ela sem chave. Os CC BY entram com `credito_obrigatorio` e saem em
  `Banco.creditos` / `creditos_sfx` do montador. **Ninguém ouviu os 170 um a um**: a escolha é automática (medidas,
  CLAP, Whisper, nome); reprovar um som = pôr o id em `REVISAO` no `freesound.py` e rodar `buscar` de novo.

## API
```python
from sfx import Banco, mixar, mixar_ffmpeg, para_hyperframes, para_json
b = Banco(semente=0)
b.para("impacto", 13.0, intensidade=0.8)                       # pico do som em 13,0 s
b.para_palavra("clique", palavras, "Leclerc")                   # palavras.json do projeto: [{"t"|"p", "i", "f"}]
b.para_palavra("tecla", palavras, "diferença", ponto="f")       # no FIM da palavra (antes do texto seguinte)
b.capitulo(16.2)                                                # riser chegando ao pico em 16,2 + impacto em 16,2
evs = b.de_pedidos([{"categoria": "capitulo", "palavra": "Capítulo"}, {"categoria": "pop", "palavra": "Ferrari"}], palavras)
mixar(evs, 20.0, "trilho.wav");  mixar_ffmpeg(evs, 20.0, "trilho_ff.wav")
para_hyperframes(evs)   # tags <audio data-start data-duration data-media-start data-volume data-track-index>
para_json(evs)          # lista para o Remotion (exemplo/remotion/TrilhaSfx.tsx) e o montador
```
- **Âncora = pico** do som (`pico_s` do catálogo): início = t − pico_s. Impacto/clique batem na palavra, whoosh passa
  por ela, riser chega ao fim do crescendo nela (nos "riser hit" o pico é a batida). Se o início cairia antes de 0, o
  começo do arquivo é pulado (`corte_ini`).
- **Intensidade** 0..1 → −9..0 dB, somada ao `volume_db` da categoria. **Duração** cortada no `dur_max` (ou `dur`), saída de 30 ms.
- **Variação**: hash FNV-1a de `semente:categoria:contagem`, sem repetir as 2 últimas da categoria; `variacao="id"` força um arquivo.
- `mixar` passa um limitador a −1,5 dBFS só se a soma estourar.

TS (`sfx.ts`): `new Banco(catalogo, semente).para(...) / paraPalavra / capitulo / dePedidos`, `volume(evento)`.

## Exemplo de 20 s e resultados (2026-11-13)
`exemplo_20s.py --motores` monta 13 SFX em 12 palavras-âncora e gera o mesmo trilho por 4 caminhos:

| Caminho | Atraso | Nível vs numpy | Diferença de envelope (p95) | LUFS integrado |
|---|---|---|---|---|
| numpy (`mixar`) | — | — | — | −18,51 (pico −1,49 dBTP) |
| ffmpeg (`mixar_ffmpeg`) | 0 ms | 0,00 dB | 0,00 dB (resíduo da onda −81,5 dB) | −18,49 |
| HyperFrames 0.9.20 (`para_hyperframes`, render real) | 0 ms | −0,01 dB | 0,08 dB (resíduo −39,5 dB, AAC) | −18,51 |
| Remotion 4.0.539 (`sfx.ts` + `TrilhaSfx.tsx`, render real) | 0 ms | −0,03 dB | 3,32 dB (golpes até 20 ms deslocados) | −18,57 |

O Remotion só posiciona áudio em quadro inteiro (1/60 s): cada som pode sair até 8,3 ms deslocado, o que muda a forma da
onda somada (por isso a diferença de envelope maior), mas não o nível nem o ritmo. Paridade Python × TS: mesmos arquivos,
inícios e ganhos em 3 sementes.

`testes.py`: 1380 checagens, 0 falhas (formato, faixa de loudness por categoria, pico verdadeiro, clipping, canais,
duração, crescendo dos risers, BS.1770 próprio × `ebur128` do ffmpeg ≤ 0,3 LU, âncoras, paridade, mixagem).

## O que NÃO foi verificado
- **Ninguém ouviu o banco.** Tudo foi conferido por medida (loudness, pico, envelope, espectrograma), não por ouvido.
  Os sons sintetizados (sobretudo whoosh, pop, tecla e prato reverso) podem soar artificiais; o Felipe deve ouvir
  `exemplo/saida/trilho_numpy.wav` e reprovar o que não servir (basta tirar a receita/entrada e rodar `gerar.py`).
- No teste HyperFrames o riser tocava a partir de 8,6 s de `riser.mp3`, mas esse arquivo só tem som até ~4,1 s: o
  "riser" de ~10–11,7 s provavelmente foi silencioso e o que se ouviu foi o impacto. Aqui o recorte usa o trecho com som.
