# -*- coding: utf-8 -*-
"""Testes deterministicos de ambiente.py (pecas sinteticas, sem DXF/XML/PDF). Rodar: python teste_ambiente.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ambiente as A


def peca(i, bb, layer='L'):
    x0, y0, z0, x1, y1, z1 = bb
    f = [[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    return dict(i=i, layer=layer, bb=list(bb), dim=[x1 - x0, y1 - y0, z1 - z0], faces=[[list(v) for v in fc] for fc in f])


def cena():
    return [peca(0, [0, 0, 0, 600, 500, 700]),              # movel do XML
            peca(1, [0, 0, 5, 4000, 3000, 5]),               # piso: placa fina grande no chao (nao e pedra: z0=5)
            peca(2, [0, 0, 850, 1500, 600, 880]),            # pedra: placa 30 mm a 850 mm
            peca(3, [-150, 0, 0, 0, 3000, 2600]),            # parede 150 mm, 2,6 m
            peca(4, [0, 0, 0, 600, 500, 700])]              # copia do movel (duplicada)


def rodar():
    P = cena(); P[1]['bb'] = [0, 0, 0, 4000, 3000, 5]; P[1]['dim'] = [4000, 3000, 5]
    return P, A.construir(P, {0}, [P[0]['bb']])


P, amb = rodar()
assert 4 in amb['duplicadas'] and 0 not in amb['duplicadas']
assert [p['i'] for p in amb['pedra']] == [2]
assert 3 in [p['i'] for p in amb['paredes_pecas']]
assert amb['piso_z'] == 5
assert all('ft' in p for p in amb['pedra'])

# contrato: ida e volta pelo JSON devolve o mesmo ambiente
j = json.loads(json.dumps(A.para_json(amb)))
P2 = cena(); P2[1]['bb'] = [0, 0, 0, 4000, 3000, 5]; P2[1]['dim'] = [4000, 3000, 5]
amb2 = A.de_json(j, P2)
assert A.para_json(amb2) == A.para_json(amb)
assert amb2['duplicadas'] == amb['duplicadas'] and amb2['piso_z'] == amb['piso_z']

# reprodutibilidade: mesma entrada, mesma saida
assert json.dumps(A.para_json(rodar()[1]), sort_keys=True) == json.dumps(A.para_json(rodar()[1]), sort_keys=True)

# versao errada e rejeitada
try:
    A.de_json({'versao': 99}, P2); raise SystemExit('deveria recusar')
except ValueError:
    pass
print('OK: 5 testes de ambiente')
