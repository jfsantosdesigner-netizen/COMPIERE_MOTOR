# -*- coding: utf-8 -*-
"""
LAUNCHER LIVRE - motor_t6
Arrasta QUALQUER pasta de ambiente (com XML + DXF dentro) sobre esse arquivo.
Ele roda o motor_t6 nessa pasta.

Uso:
  1) Arrasta a pasta do ambiente pra cima do LAUNCHER.bat  (jeito facil)
  2) Ou roda:  python launcher.py "C:\caminho\da\pasta"

Se rodar sem argumento, abre uma janelinha pra escolher a pasta.
"""
import sys, os, subprocess, tkinter as tk
from tkinter import filedialog
from pathlib import Path

# === CONFIGURACAO ===
MOTOR = Path(__file__).parent  # BLINDADO: motor roda do próprio diretório (05/10/2026)
# ====================

def escolher_pasta():
    """Abre dialogo do Windows pra escolher a pasta do ambiente."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    pasta = filedialog.askdirectory(
        title='Escolha a pasta do ambiente (com XML + DXF dentro)',
        mustexist=True,
    )
    root.destroy()
    return pasta

def rodar(pasta):
    pasta = Path(pasta).resolve()
    if not pasta.is_dir():
        print(f'ERRO: "{pasta}" nao e uma pasta valida.')
        return 1

    # checa se a pasta tem XML + DXF (é um ambiente de verdade)
    xmls = [f for f in pasta.glob('*.xml') if not f.name.lower().startswith('xplod')]
    dxfs = list(pasta.glob('*.dxf'))
    if not xmls or not dxfs:
        print(f'ATENCAO: "{pasta}" nao tem XML+DXF direto nela.')
        print(f'  XMLs encontrados: {len(xmls)}')
        print(f'  DXFs encontrados: {len(dxfs)}')
        print('  Tentando assim mesmo (pode ser pasta-mae com subpastas)...')

    if not MOTOR.exists():
        print(f'ERRO: motor nao existe em {MOTOR}')
        return 1
    if not (MOTOR / 'novo_ambiente.py').exists():
        print(f'ERRO: novo_ambiente.py nao existe em {MOTOR}')
        return 1

    print('=' * 60)
    print(f'  LAUNCHER LIVRE - motor_t6')
    print('=' * 60)
    print(f'  Motor   : {MOTOR}')
    print(f'  Ambiente: {pasta}')
    print('=' * 60)
    print()

    r = subprocess.run(
        [sys.executable, str(MOTOR / 'novo_ambiente.py'), str(pasta)],
        cwd=str(MOTOR),
    )

    print()
    print('=' * 60)
    print(f'  codigo de saida: {r.returncode}')
    pdfs = sorted(pasta.glob('CADERNO*.pdf'),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if pdfs:
        print(f'  PDF gerado: {pdfs[0]}')
        print(f'  tamanho   : {pdfs[0].stat().st_size} bytes')
    print('=' * 60)

    if len(sys.argv) >= 2:
        input('\nPressione ENTER para fechar...')
    return r.returncode

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        pasta = sys.argv[1].strip('"')
    else:
        print('Nenhuma pasta passada por argumento.')
        print('Abrindo janela pra escolher a pasta do ambiente...')
        pasta = escolher_pasta()
        if not pasta:
            print('Cancelado.')
            sys.exit(0)
    sys.exit(rodar(pasta))