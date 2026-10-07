# -*- coding: utf-8 -*-
"""
ambientemodu.py — ETAPA 3: pedra e objetos (eletros) lidos SÓ do DXF. Não conhece XML.

  construir(P, amb) -> dict      (amb = resultado de ambiente.construir(P))
    moveis    índices candidatos: toda peça com faces, exceto piso. Inclui temporariamente paredes candidatas,
              pois um armário alto pode ter a mesma geometria; a Unificação decide com o XML.
    pedra     indices: placa 15-100 mm, >=500x250, base entre 700 e 1100 mm
    eletro_a  indices: objeto com forma (>=10 faces), tamanho de eletro, ate 2300 mm de altura
    eletro_b  indices: objeto baixo (ate 1300 mm), sem material, que precisa estar encostado num movel
São CANDIDATOS. Sem o XML, peças de MDF (prateleira/tamponamento 18 mm, tampo 45 mm) passam no critério de pedra.
A Unificação (unificacao.py) descarta as que casam com o XML e aplica o que depende de móvel (encostado, sobre a pedra).
"""


def construir(P, amb):
    from ambiente import validar_pecas
    validar_pecas(P)
    obrig = {'piso', 'malha_par', 'fontes_parede', 'par_dxf', 'paredes_pecas', 'piso_z'}
    if not isinstance(amb, dict) or not obrig.issubset(amb):
        raise ValueError('amb não obedece ao contrato da etapa 2')
    # Parede/malha ainda é candidata nesta etapa: pode ser um armário alto.
    # Só o piso é retirado; a Unificação decide definitivamente com o XML.
    fora = set(amb['piso'])
    moveis = [p_['i'] for p_ in P if p_['i'] not in fora and p_['faces']]
    pedra = [p_ for p_ in P if p_['faces'] and 15 <= p_['dim'][2] <= 100
             and max(p_['dim'][0], p_['dim'][1]) >= 500 and min(p_['dim'][0], p_['dim'][1]) >= 250 and 700 <= p_['bb'][2] <= 1100]
    ea = [p_ for p_ in P if p_['faces'] and len(p_['faces']) >= 10 and sorted(p_['dim'])[0] >= 40 and sorted(p_['dim'])[1] >= 150
          and max(p_['dim']) <= 2200 and p_['dim'][2] >= 100 and p_['bb'][5] <= 2300
          and not (60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and p_['dim'][2] >= 1800)]
    eb = [p_ for p_ in P if not p_.get('mat') and p_['faces']
          and sorted(p_['dim'])[0] >= 15 and sorted(p_['dim'])[1] >= 100 and p_['bb'][5] <= 1300 and p_['bb'][2] >= -5
          and not (p_['dim'][2] < 60 and min(p_['dim'][0], p_['dim'][1]) > 1000) and not (p_['bb'][2] < 50 and p_['bb'][5] < 250)]
    return dict(moveis=moveis, pedra=[p_['i'] for p_ in pedra], eletro_a=[p_['i'] for p_ in ea], eletro_b=[p_['i'] for p_ in eb])
