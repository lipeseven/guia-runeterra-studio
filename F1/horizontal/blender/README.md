# F1/horizontal/blender — Blender como motor de cena de pista (teste)

Teste do Blender 5.3 (Cycles/EEVEE) com o mod de AC `vhe_interlagos` completo + carro do acervo, no traçado do
`kit/gps`. Relatório: `../docs/teste_blender_senna.md`.

- `senna.py` — roda DENTRO do Blender, sobre a cópia da cena do Felipe (`F1/dados/testes_vhe/interlagos_vhe_full.blend`):
  acerta materiais do mod (ksMultilayer, borracha, colisores), importa e prepara o carro (rodas separadas, giro e esterço),
  anima pelo relógio s(t) do kit, apoia o carro por raios nas malhas de física, monta céu/sol/câmeras/compositor e
  renderiza quadros PNG. Opções no cabeçalho do arquivo.
- `folhas.py` — Python da `.venv` + FFmpeg: correção de cor/grão (igual em vídeo e stills), vídeo (com/sem aviso),
  folha de comparação com a referência e folha de sequência de 12 quadros.

```
B=C:\Users\Felipe\opus-livre-teste\blender-5.3-portatil\blender.exe      # cópia do Blender da Microsoft Store (o .exe da loja nega acesso pela linha de comando)
%B% -b F1\dados\testes_vhe\interlagos_vhe_full.blend --python F1\horizontal\blender\senna.py -- --motor cycles --amostras 32 --pct 100 --quadros todos --dados --versao final
python F1\horizontal\blender\folhas.py video F1\dados\testes_vhe\blender_senna\final F1\dados\testes_vhe\hamilton_senna_blender.mp4 --aviso
python F1\horizontal\blender\folhas.py sequencia F1\dados\testes_vhe\blender_senna\final 281 --saida F1\horizontal\testes\blender\folha_zebra.jpg
```
