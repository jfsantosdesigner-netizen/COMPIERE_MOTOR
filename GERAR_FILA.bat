@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Uso: arraste uma ou mais pastas (ambiente ou pasta-mae) sobre este arquivo.
rem Sem argumento: gera todos os ambientes de PROJETOS TESTES.
python fila.py %*
echo.
echo Relatorio: %~dp0FILA_RELATORIO.txt
pause
