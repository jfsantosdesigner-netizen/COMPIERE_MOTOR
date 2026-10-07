# -*- coding: utf-8 -*-
"""Etapas 1 e 4: leitura blindada do DXF e casamento inicial XML x DXF."""
import json, os, subprocess, sys
import geo
from ambiente import validar_pecas


def ler_dxf(path, raiz=None):
    raiz = raiz or os.path.dirname(os.path.abspath(__file__))
    leitor = os.path.join(raiz, 'dxf_pecas(motor core).py')
    r = subprocess.run([sys.executable, '-B', leitor, path, '-'], capture_output=True)
    if r.returncode:
        raise RuntimeError('erro ao ler o DXF: ' + r.stderr.decode('utf-8', 'replace')[-1500:])
    P = json.loads(r.stdout.decode('utf-8'))
    for i, p in enumerate(P): p['i'] = i
    validar_pecas(P)
    return P


def casar(P, linhas_xml, quantidades):
    validar_pecas(P)
    return geo.casar(P, linhas_xml, quantidades)
