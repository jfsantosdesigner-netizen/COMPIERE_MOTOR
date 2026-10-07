# -*- coding: utf-8 -*-
"""Testes deterministicos de classificacao.py (casos sinteticos, sem DXF/XML/PDF). Rodar: python teste_classificacao.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classificacao as C

F = (0, 1)   # olhar para +y: a frente do modulo fica no y minimo, a parede em y maximo


def P_(i, bb):
    return dict(i=i, bb=bb, dim=[bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]])


def modulo(desc, bb, pecas, **kw):
    return dict(tipo='mod', desc=desc, dim='x', bb=bb, pecas=pecas, **kw)


def ctx(P, itens):
    return dict(P=P, lim=[0, 0, 5000, 3000], moveis={p['i'] for p in P}, soltas=itens, eixo_vista=F)


# modulo 600 x 500 (prof) x 700 (alt), sem frente: lateral, lateral, base
caixa = [P_(0, [0, 0, 0, 18, 500, 700]), P_(1, [582, 0, 0, 600, 500, 700]), P_(2, [18, 0, 0, 582, 500, 18])]
bb = [0, 0, 0, 600, 500, 700]

# 1) sem porta e sem frente => NICHO
m = modulo('Balcao Inferior', bb, [0, 1, 2])
assert C.classificar_peca(m, ctx(caixa, [m])) == 'NICHO'

# 2) com frente de gaveta (chapa fina na frente, y 0..18) => MODULO_COMUM
frente = P_(3, [2, -2, 0, 598, 16, 150])
m = modulo('Balcao Inferior', bb, [0, 1, 2, 3])
assert C.classificar_peca(m, ctx(caixa + [frente], [m])) == 'MODULO_COMUM'

# 3) nome com Gaveta / Porta => nunca NICHO, mesmo sem chapa no DXF
for nome in ('Gaveteiro 3 Gavetas', 'Armario 2 Portas', 'Armario 1 Portas Basculantes'):
    m = modulo(nome, bb, [0, 1, 2])
    assert C.classificar_peca(m, ctx(caixa, [m])) == 'MODULO_COMUM', nome

# 4) porta de vidro (fora do DXF): XML diz que tem porta => MODULO_COMUM
m = modulo('Armario Superior', bb, [0, 1, 2], xml_tem_porta=True)
assert C.classificar_peca(m, ctx(caixa, [m])) == 'MODULO_COMUM'

# 5) reprodutibilidade: mesma entrada, mesma saida
m = modulo('Balcao Inferior', bb, [0, 1, 2])
assert [C.classificar_peca(m, ctx(caixa, [m])) for _ in range(3)] == ['NICHO'] * 3
print('OK: 5 testes')
