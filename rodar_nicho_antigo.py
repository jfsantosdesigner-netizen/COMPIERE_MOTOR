# -*- coding: utf-8 -*-
"""Roda o motor ATUAL (gerar_caderno.py) em modo COMPIERE_TESTE_NICHO nos projetos de PROJETOS TESTES
e grava saida_nicho_antigo.tsv (projeto, parede, tipo, desc, dim). Nao gera PDF."""
import os, sys, json, subprocess, tempfile
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, 'PROJETOS TESTES')
linhas = ['projeto\tparede\ttipo\tdesc\tdim']
for dp, dn, fn in sorted(os.walk(RAIZ)):
    if '_pecas_dxf.json' not in fn or '_config.json' not in fn:
        continue
    xmls = sorted(f for f in fn if f.lower().endswith('.xml') and not f.lower().startswith('xplod'))
    if not xmls:
        continue
    cfg = json.load(open(os.path.join(dp, '_config.json'), encoding='utf-8'))
    cfg['xml'] = os.path.join(dp, xmls[0])
    cfg['pecas_json'] = os.path.join(dp, '_pecas_dxf.json')
    cfg['dxf'] = ''
    cfg['layout'] = os.path.join(AQUI, 'assets', 'LAYOUT_FIXO.pdf')
    cfg['contrato_fonte'] = os.path.join(AQUI, 'assets', 'CONTRATO.pdf')
    cfg['logo'] = os.path.join(AQUI, 'assets', 'LOGO.png')
    cfg['saida'] = os.path.join(tempfile.gettempdir(), 'nicho_teste.pdf')
    tmp = os.path.join(tempfile.gettempdir(), 'cfg_nicho_teste.json')
    json.dump(cfg, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    env = dict(os.environ, COMPIERE_TESTE_NICHO='1', PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, os.path.join(AQUI, 'gerar_caderno.py'), tmp], capture_output=True, env=env, cwd=AQUI)
    nome = os.path.relpath(dp, RAIZ)
    out = r.stdout.decode('utf-8', 'replace').splitlines()
    n = 0
    for l in out:
        if l.startswith('NICHO_ANTIGO\t'):
            linhas.append(nome + '\t' + l.split('\t', 1)[1]); n += 1
    print(f"{nome}: rc={r.returncode} nicho_antigo={n}", ('' if r.returncode == 0 else r.stderr.decode('utf-8', 'replace')[-300:]))
open(os.path.join(AQUI, 'saida_nicho_antigo.tsv'), 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
print('salvo saida_nicho_antigo.tsv')
