@echo off
rem Explicando F1 — liga o painel DESTE canal em http://127.0.0.1:8766 e abre o navegador.
rem Feche esta janela para desligar.
cd /d "%~dp0.."
title Explicando F1
set GRS_CANAL=f1

if not exist "app\painel\dist\index.html" (
  echo Compilando a tela pela primeira vez...
  pushd app\painel
  call npm run build
  popd
)

start "" http://127.0.0.1:8766
".venv\Scripts\python.exe" -m uvicorn app.servidor.main:app --host 0.0.0.0 --port 8766
pause
