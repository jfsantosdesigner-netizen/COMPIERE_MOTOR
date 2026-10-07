# -*- coding: utf-8 -*-
"""
LAUNCHER BLINDADO - motor Compiere
Arraste a pasta de UM ambiente (com XML + DXF dentro) sobre o GERAR_CADERNO.bat.

ATENCAO: antes de gerar, TUDO que esta direto na pasta e apagado, menos o .xml e o .dxf.
Na saida ficam so: CADERNO - <AMBIENTE>.pdf e CADERNO - <AMBIENTE>_QUALIDADE.md (relatorio).
Sem cache, sem arquivos intermediarios, sem __pycache__.

Uso:
  1) Arraste a pasta do ambiente sobre GERAR_CADERNO.bat
  2) Ou:  python launcher.py "C:\\caminho\\da\\pasta"
  3) Sem argumento: abre uma janelinha para escolher a pasta.
"""
import sys, os, subprocess
from pathlib import Path

sys.dont_write_bytecode = True
MOTOR = Path(__file__).parent   # o motor roda do proprio diretorio


def escolher_pasta():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    pasta = filedialog.askdirectory(title='Escolha a pasta do ambiente (com XML + DXF dentro)', mustexist=True)
    root.destroy()
    return pasta


def rodar(pasta):
    pasta = Path(pasta).resolve()
    if not pasta.is_dir():
        print(f'ERRO: "{pasta}" nao e uma pasta valida.')
        return 1
    if not (MOTOR / 'novo_ambiente.py').exists():
        print(f'ERRO: novo_ambiente.py nao existe em {MOTOR}')
        return 1
    print('=' * 60)
    print('  LAUNCHER BLINDADO - motor Compiere')
    print('=' * 60)
    print(f'  Motor   : {MOTOR}')
    print(f'  Ambiente: {pasta}')
    print('  A pasta sera LIMPA: fica so XML + DXF; sai so PDF + relatorio.')
    print('=' * 60)
    print()
    r = subprocess.run([sys.executable, '-B', str(MOTOR / 'novo_ambiente.py'), str(pasta)], cwd=str(MOTOR),
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    print()
    print('=' * 60)
    print(f'  codigo de saida: {r.returncode}')
    for p in sorted(pasta.glob('CADERNO*')):
        print(f'  saida: {p.name}  ({p.stat().st_size} bytes)')
    print('=' * 60)
    if len(sys.argv) >= 2:
        input('\nPressione ENTER para fechar...')
    return r.returncode


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        pasta = sys.argv[1].strip('"')
    else:
        print('Nenhuma pasta passada por argumento. Abrindo janela para escolher a pasta do ambiente...')
        pasta = escolher_pasta()
        if not pasta:
            print('Cancelado.')
            sys.exit(0)
    sys.exit(rodar(pasta))
