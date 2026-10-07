# -*- coding: utf-8 -*-
"""Testes deterministicos de ambiente.py (pecas sinteticas, sem DXF/XML/PDF). Rodar: python teste_ambiente.py"""
import os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ambiente, ambientemodu, unificacao as A


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
    antes = copy.deepcopy(P)
    res = A.fechar(P, ambiente.construir(P), ambientemodu.construir(P, ambiente.construir(P)), {0}, [P[0]['bb']])
    assert P == antes, 'unificacao.fechar modificou a entrada P'
    return P, res


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

# ambiente e ambientemodu sao DXF-only: nao dependem de usadas; o movel 0 e candidato a pedra? (nao: 600x500x700, z0=0)
assert 3 in [P[i]['i'] for i in ambiente.construir(P)['paredes_pecas']]
_a = ambiente.construir(P); _m = ambientemodu.construir(P, _a)
assert _m['pedra'] == [2]
assert _m['moveis'] == [0, 2, 3, 4]   # só piso sai; parede ainda é candidata até a unificação
assert ambiente.construir(P)['piso'] == [1]

# reprodutibilidade: mesma entrada, mesma saida
assert json.dumps(A.para_json(rodar()[1]), sort_keys=True) == json.dumps(A.para_json(rodar()[1]), sort_keys=True)

# versao errada e rejeitada
try:
    A.de_json({'versao': 99}, P2); raise SystemExit('deveria recusar')
except ValueError:
    pass

# Armário alto com geometria de parede: a etapa 2 o considera candidato, mas o XML vence na unificação.
P3 = cena() + [peca(5, [2000, 0, 0, 2150, 1200, 2400])]
P3[1]['bb'] = [0, 0, 0, 4000, 3000, 5]; P3[1]['dim'] = [4000, 3000, 5]
a3 = ambiente.construir(P3); m3 = ambientemodu.construir(P3, a3)
assert 5 in a3['paredes_pecas'] and 5 in m3['moveis']
r3 = A.fechar(P3, a3, m3, {0, 5}, [P3[0]['bb'], P3[5]['bb']])
assert 5 not in [p['i'] for p in r3['paredes_pecas']]

# O contrato serializado só pode ser restaurado sobre as mesmas peças do mesmo DXF.
P_errado = copy.deepcopy(P2); P_errado[0]['bb'][0] += 1
try:
    A.de_json(j, P_errado); raise SystemExit('deveria recusar contrato de outro DXF')
except ValueError:
    pass

# Entradas fora do esquema falham cedo e de forma explícita.
try:
    ambiente.construir([{'i': 0}]); raise SystemExit('deveria recusar peça incompleta')
except ValueError:
    pass
print('OK: testes de ambiente/ambientemodu/unificacao')
