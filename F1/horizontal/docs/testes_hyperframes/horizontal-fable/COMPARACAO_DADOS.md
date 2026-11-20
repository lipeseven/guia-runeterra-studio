# Comparação de fontes de dados de F1 (etapa 1)

Conferido em 2026-11-12 pelo `gh api` (estrelas, licença, último push) e por teste real nesta máquina.

## Tabela

| Fonte | O que é | Dado útil para o vídeo | Offline / cache | Licença | Manutenção |
|---|---|---|---|---|---|
| **theOehrly/Fast-F1** (v3.9.2) | Biblioteca Python oficial da comunidade | Tudo: velocidade, freio, marcha, acelerador, X/Y, distância pronta, curvas, comparação de pilotos | Cache próprio em disco, ótimo | MIT | Ativa: 5.555 estrelas, push 2026-11-03, versão de 2026-11-02 |
| **br-g/openf1** (API openf1.org) | API HTTP gratuita com os mesmos dados do live timing | Velocidade, freio, marcha, acelerador, RPM, DRS (~4 Hz), X/Y/Z, voltas e setores | Sem cache próprio; JSON simples, fácil de guardar | CC BY-NC-SA 4.0 (código); dados históricos sem login | Ativa: 1.871 estrelas, push 2026-11-09 |
| Vucko95/Fast-F1 (fork) | Cópia do FastF1 | Igual ao original, mas parado em 2023 | igual | MIT | Parado (push 2023-10-21), 0 estrelas |
| Vucko95/openf1 (fork) | Cópia do openf1 | Nada além do original | igual | CC BY-NC-SA | Push 2026-05-10, 0 estrelas |
| Vucko95/f1-race-replay (fork de IAmTomShaw, 6.993 estrelas) | Aplicativo de replay de corrida em janela (usa FastF1 por baixo) | Posição dos carros na pista ao longo da corrida; não exporta dado pronto para nós | Usa o cache do FastF1 | MIT (README do original) | Fork parado (2026-01-29); original ativo (2026-10-24) |
| Vucko95/F1RaceTelemetry | Ingestão do OpenF1 para MongoDB (Docker) | Nada novo: `car_data` ainda está na lista de pendências dele | Precisa de Docker + Mongo | sem licença | Push 2025-10-19, 0 estrelas |
| Vucko95/F1DataLab | Site (FastAPI + Next + MySQL) de dados históricos | Resultados e tempos de volta; sem telemetria. README avisa que foi descontinuado | Precisa de Docker + MySQL | MIT | Descontinuado (push 2026-05-03) |
| Vucko95/F1StatsHub | Site de estatísticas (banco local + Ergast) | Só estatística histórica; a API Ergast foi desligada | Docker + MySQL | sem licença | Parado (2025-01-26), "em construção" |
| Vucko95/F1_telemetry_base | Um `main.py` de 2023, README vazio | Nada | - | sem licença | Parado (2023-10-21) |
| Vucko95/Formula1TelemetryStreaming | Recebe pacotes UDP do **jogo** F1 24 (Kafka, Grafana) | Dado de videogame, não de corrida real | - | sem licença | Parado (2024-10-25), 5 estrelas |

## Achado importante: FastF1 agora pede login

No teste real, o FastF1 3.9.2 não baixou nada: o servidor `livetiming.formula1.com` responde **401** e a biblioteca pede e-mail e senha de conta da F1 (variáveis `F1_USERNAME` e `F1_PASSWORD`). Não coloquei credenciais (regra: senha só o Felipe digita). Sem login, sessão, voltas e telemetria vêm vazias.

A API OpenF1 entregou os mesmos dados sem login.

## Decisão

**Usar a API OpenF1 direto, com cache nosso em disco.** Motivos:
- Tem tudo o que o vídeo precisa (velocidade, freio, marcha, acelerador, traçado X/Y, tempo de volta e setores de dois pilotos).
- Sem login, sem dependência pesada (só `numpy`), e depois da primeira carga roda sem internet (0,4 s).
- O perfil Vucko95 não acrescenta nada: são forks parados ou aplicativos que dependem de Docker e das mesmas duas fontes. Único item diferente é telemetria de videogame, que não serve.
- As curvas (número e posição) vêm da API MultiViewer, a mesma que o FastF1 usa.

O FastF1 fica instalado no venv como reserva: se o Felipe quiser, basta ele definir `F1_USERNAME` e `F1_PASSWORD` no próprio terminal e rodar `tools\extrair_telemetria_fastf1.py` (não testado com login). Vantagem dele: distância e curvas prontas e amostragem fundida de carro + posição.

Licença: FastF1 é MIT. O código do OpenF1 é CC BY-NC-SA, mas nós só consumimos a API. Os dados em si são da F1 (uso não oficial); no vídeo, mostrar como gráfico próprio, sem marca da F1.

## Como usar

```
cd C:\Users\Felipe\hyperframes-teste\horizontal-fable
.venv-f1\Scripts\python.exe tools\extrair_telemetria.py
.venv-f1\Scripts\python.exe tools\extrair_telemetria.py 2026 dados\telemetria_interlagos_2026.json
```
Argumentos (todos opcionais): `ano saida.json sessao pais numeros` (padrão `2025 dados\telemetria_interlagos.json Qualifying Brazil 16,44`). Outras sessões: `Race`, `Sprint`, `Practice 1`.

Cache: `cache_f1\openf1\` (0,5 MB). Apagar a pasta força baixar de novo.

## Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `dados\telemetria_interlagos.json` (26 kB) | Classificação do GP de São Paulo 2025 (2025-11-08). LEC 1:09.801 (volta 15), HAM 1:10.016 (volta 8) |
| `dados\telemetria_interlagos_2026.json` (26 kB) | Classificação de 2026 (2026-11-07), carro SF-26. LEC 1:28.082, HAM 1:30.001; máxima ~296 km/h |

Formato (um ponto a cada 10 m de pista):
- `pilotos.LEC` / `pilotos.HAM`: `tempo_volta_s`, `setores_s`, `vel_max`, `vel_min`, `vel_radar_kmh`, `cor_equipe`, e as listas alinhadas `dist` (m), `tempo_s`, `vel` (km/h), `acel` (%), `freio` (0/1), `marcha`.
- `tracado.x` / `tracado.y`: traçado da volta do Leclerc, em décimos de metro, mesmo índice de `dist`.
- `curvas`: número, `dist` (m) e posição X/Y das 15 curvas. `rotacao_graus`: giro sugerido para desenhar o mapa.

Comparar pilotos: os dois têm a mesma grade de distância, então `vel[i]` de um contra `vel[i]` do outro é o mesmo ponto da pista; diferença de tempo = `tempo_s[i]` de um menos o do outro.

## Limites conhecidos

- Amostragem original ~4 Hz (277 amostras por volta), interpolada para 10 m. Bom para gráfico; freio é só ligado/desligado (sem pressão).
- Distância é a integral da velocidade: deu 4.245 m contra 4.309 m oficiais (1,5 % a menos). A posição das curvas foi calculada no mesmo traçado, então fica coerente.
- Os tempos de 2026 são ~18 s mais lentos que os de 2025, com máxima 40 km/h menor. Parece pista molhada, mas **não conferi o clima**. Conferir antes de citar esses números na tela.
- Os tempos de volta vêm da API; não cruzei com o resultado oficial.
