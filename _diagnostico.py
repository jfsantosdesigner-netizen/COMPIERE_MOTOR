# -*- coding: utf-8 -*-
import os, sys, json, re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
print(f'=== MOTOR: {AQUI} ===\n')

# 1) Arquivos que existem
print('--- ARQUIVOS NA PASTA ---')
for f in sorted(AQUI.iterdir()):
    if f.is_file():
        print(f'  {f.name}  ({f.stat().st_size} bytes)')

print('\n--- PASTAS NA PASTA ---')
for d in sorted(AQUI.iterdir()):
    if d.is_dir() and d.name not in ('__pycache__',):
        print(f'  [DIR] {d.name}')

# 2) padrao.json
print('\n--- padrao.json ---')
p = AQUI / 'padrao.json'
if p.exists():
    print(p.read_text(encoding='utf-8'))
else:
    print('  (nao existe)')

# 3) assets/
print('\n--- assets/ ---')
a = AQUI / 'assets'
if a.exists():
    for f in sorted(a.iterdir()):
        print(f'  {f.name}  ({f.stat().st_size} bytes)')
else:
    print('  (nao existe)')

# 4) novo_ambiente.py - trecho do _ASSETS e cfg
print('\n--- novo_ambiente.py (topo 60 linhas) ---')
na = AQUI / 'novo_ambiente.py'
if na.exists():
    for i, ln in enumerate(na.read_text(encoding='utf-8', errors='replace').splitlines()[:60], 1):
        print(f'  L{i:03d}: {ln}')
else:
    print('  (nao existe)')

# 5) gerar_caderno.py - procura COTAS_SEM_PAREDE, PAREDE_COR, show_pdf_page, lay
print('\n--- gerar_caderno.py: tokens criticos ---')
gc = AQUI / 'gerar_caderno.py'
if gc.exists():
    src = gc.read_text(encoding='utf-8', errors='replace')
    linhas = src.splitlines()
    for i, ln in enumerate(linhas, 1):
        if re.search(r'COTAS_SEM_PAREDE|PAREDE_COR|show_pdf_page|LAYOUT_FIXO|wf\.append\(\s*\(\s*1e9', ln):
            print(f'  L{i:04d}: {ln.strip()[:130]}')
else:
    print('  (nao existe)')

# 6) PROJETOS - quais ambientes estao la
print('\n--- PROJETOS ---')
for nome_proj in ('PROJETOS', 'PROJETOS MOTOR', 'PROJETOS TESTE'):
    pr = AQUI / nome_proj
    if pr.exists():
        print(f'  [{nome_proj}] existe')
        for cli in sorted(pr.iterdir()):
            if cli.is_dir():
                print(f'    {cli.name}/')
                for amb in sorted(cli.iterdir()):
                    if amb.is_dir():
                        xml = list(amb.glob('*.xml'))
                        dxf = list(amb.glob('*.dxf'))
                        cfg = list(amb.glob('_config.json'))
                        print(f'      {amb.name}  xml={len(xml)} dxf={len(dxf)} cfg={len(cfg)}')

# 7) Python importa o que?
print('\n--- IMPORTS ---')
if gc.exists():
    for i, ln in enumerate(linhas, 1):
        m = re.match(r'^\s*(?:from|import)\s+([\w\.]+)', ln)
        if m:
            print(f'  L{i:04d}: {ln.strip()[:100]}')