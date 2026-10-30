@echo off
rem Canal Pokémon — liga o painel DESTE canal em http://127.0.0.1:8766 (servidor próprio: não enxerga o Runeterra).
rem Os dois canais podem ficar ligados juntos; o motor faz uma tarefa por vez na máquina.
cd /d "%~dp0"
title Pokémon Studio
set GRS_CANAL=pokemon

if not exist "app\painel\dist\index.html" (
  pushd app\painel
  call npm run build
  popd
)

".venv\Scripts\python.exe" tools\pokemon\preparar_canal.py
start "" http://127.0.0.1:8766
".venv\Scripts\python.exe" -m uvicorn app.servidor.main:app --host 127.0.0.1 --port 8766
pause
