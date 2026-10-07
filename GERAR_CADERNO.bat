@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Arraste a pasta de UM ambiente (XML + DXF) sobre este arquivo.
rem ATENCAO: tudo na pasta e apagado, menos o XML e o DXF. Saem so o PDF e o relatorio.
python -B launcher.py %*
pause
