@echo off
rem Guia de Runeterra Studio — liga o painel em http://127.0.0.1:8765 e abre o navegador.
rem Feche esta janela para desligar.
cd /d "%~dp0"
title Guia de Runeterra Studio

if not exist "app\painel\dist\index.html" (
  echo Compilando a tela pela primeira vez...
  pushd app\painel
  call npm run build
  popd
)

start "" http://127.0.0.1:8765
".venv\Scripts\python.exe" -m uvicorn app.servidor.main:app --host 127.0.0.1 --port 8765
pause
