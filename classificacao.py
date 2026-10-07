# -*- coding: utf-8 -*-
"""
classificacao.py — Fase 1 da reorganizacao do motor Compiere.

Funcao pura: classificar_peca(peca, contexto) -> tipo (str)

Tipos possiveis:
    MODULO_COMUM, CANTO_L_ESQ, CANTO_L_DIR, CANTO_RETO,
    NICHO, PAINEL_OCULTO, RODAPE_OCULTO
"""

import geo  # reaproveita geo.uniao -- sem duplicar logica que ja existe e e pura

NICHO_MIN_RATIO  = 0.4
NICHO_LARG_MAX   = 2000.0
NICHO_ALT_MAX    = 1200.0
NICHO_MIN_PECAS  = 3
NICHO_MIN_HORIZ  = 2

CANTO_TOL_PAREDE  = 50.0
CANTO_EXT_MIN     = 300.0
CANTO_CONCAVIDADE = 0.80

RODAPE_ALT_MAX    = 250.0
OCLUSAO_MIN_RATIO = 0.6

TIPOS = ('MODULO_COMUM', 'CANTO_L_ESQ', 'CANTO_L_DIR', 'CANTO_RETO',
         'NICHO', 'PAINEL_OCULTO', 'RODAPE_OCULTO')

FACE_NORMAL = {'x-': (1, 0), 'x+': (-1, 0), 'y-': (0, 1), 'y+': (0, -1)}


def classificar_peca(peca, contexto):
    if peca.get('tipo') == 'grupo' or 'itens' in peca:
        if _eh_nicho_conjunto(peca['itens']):
            return 'NICHO'
        return 'MODULO_COMUM'

    if peca.get('tipo') == 'mod':
        canto = _classificar_canto(peca, contexto)
        if canto is not None:
            return canto
        if _eh_nicho_modulo(peca, contexto):
            return 'NICHO'
        return 'MODULO_COMUM'

    if peca.get('tipo') == 'comp':
        if _eh_oculto(peca, contexto):
            b = peca['bb']
            return 'RODAPE_OCULTO' if (b[5] - b[2]) <= RODAPE_ALT_MAX else 'PAINEL_OCULTO'
        return 'MODULO_COMUM'

    return 'MODULO_COMUM'


def _canto_do_ambiente(peca, contexto):
    lim = contexto['lim']
    existentes = contexto.get('paredes_existentes') or {'x-', 'x+', 'y-', 'y+'}
    b = peca['bb']
    pares = (('x-', 'y-'), ('x+', 'y-'), ('x-', 'y+'), ('x+', 'y+'))
    for wa, wb in pares:
        if wa not in existentes or wb not in existentes:
            continue
        dist_a = abs(b[0] - lim[0]) if wa == 'x-' else abs(lim[2] - b[3])
        dist_b = abs(b[1] - lim[1]) if wb == 'y-' else abs(lim[3] - b[4])
        if dist_a > CANTO_TOL_PAREDE or dist_b > CANTO_TOL_PAREDE:
            continue
        if (b[3] - b[0]) < CANTO_EXT_MIN or (b[4] - b[1]) < CANTO_EXT_MIN:
            continue
        return wa, wb
    return None


def _lado_canto(wa, wb, peca):
    na, nb = FACE_NORMAL[wa], FACE_NORMAL[wb]
    cruz = na[0] * nb[1] - na[1] * nb[0]
    b = peca['bb']
    asa_a = (b[3] - b[0]) if wa in ('x-', 'x+') else (b[4] - b[1])
    asa_b = (b[3] - b[0]) if wb in ('x-', 'x+') else (b[4] - b[1])
    a_mais_longa = asa_a >= asa_b
    esquerda_longa = a_mais_longa if cruz > 0 else (not a_mais_longa)
    return 'ESQ' if esquerda_longa else 'DIR'


def _area_uniao_footprint(bboxes):
    if not bboxes:
        return 0.0
    xs = sorted(set([bb[0] for bb in bboxes] + [bb[3] for bb in bboxes]))
    ys = sorted(set([bb[1] for bb in bboxes] + [bb[4] for bb in bboxes]))
    area = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx = (xs[i] + xs[i + 1]) / 2.0
            cy = (ys[j] + ys[j + 1]) / 2.0
            if any(bb[0] <= cx <= bb[3] and bb[1] <= cy <= bb[4] for bb in bboxes):
                area += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return area


def _eh_convexo(peca, contexto):
    P = contexto['P']
    b = peca['bb']
    area_bbox = max(1.0, (b[3] - b[0]) * (b[4] - b[1]))
    pecas_do_corpo = [P[i]['bb'] for i in peca.get('pecas', []) if 0 <= i < len(P)]
    if not pecas_do_corpo:
        return True
    footprint = _area_uniao_footprint(pecas_do_corpo)
    return (footprint / area_bbox) >= CANTO_CONCAVIDADE


def _classificar_canto(peca, contexto):
    info = _canto_do_ambiente(peca, contexto)
    if info is None:
        return None
    wa, wb = info
    if _eh_convexo(peca, contexto):
        return 'CANTO_RETO'
    lado = _lado_canto(wa, wb, peca)
    return 'CANTO_L_ESQ' if lado == 'ESQ' else 'CANTO_L_DIR'


def _area_frontal_por_lado(peca, P, excluir):
    U = peca['bb']
    area = {'x-': 0.0, 'x+': 0.0, 'y-': 0.0, 'y+': 0.0}
    for p in P:
        if p['i'] in excluir:
            continue
        b = p['bb']; dx, dy, dz = p['dim']
        oz = max(0.0, min(b[5], U[5]) - max(b[2], U[2]))
        if dz <= 0 or oz < 0.5 * dz:
            continue
        if dx <= 26:
            oy = max(0.0, min(b[4], U[4]) - max(b[1], U[1]))
            if dy > 0 and oy >= 0.5 * dy:
                if abs(b[3] - U[0]) <= 35: area['x-'] += oy * oz
                if abs(b[0] - U[3]) <= 35: area['x+'] += oy * oz
        if dy <= 26:
            ox = max(0.0, min(b[3], U[3]) - max(b[0], U[0]))
            if dx > 0 and ox >= 0.5 * dx:
                if abs(b[4] - U[1]) <= 35: area['y-'] += ox * oz
                if abs(b[1] - U[4]) <= 35: area['y+'] += ox * oz
    return area


def _cobertura_frontal_max(peca, P):
    b = peca['bb']
    area = _area_frontal_por_lado(peca, P, excluir=set(peca.get('pecas', [])))
    ext_x, ext_y, alt = b[3] - b[0], b[4] - b[1], b[5] - b[2]
    denom = {'x-': ext_y * alt, 'x+': ext_y * alt, 'y-': ext_x * alt, 'y+': ext_x * alt}
    fracoes = [area[k] / denom[k] for k in area if denom[k] > 0]
    return max(fracoes) if fracoes else 0.0


def _eh_nicho_modulo(peca, contexto):
    b = peca['bb']
    if max(b[3] - b[0], b[4] - b[1]) > NICHO_LARG_MAX or (b[5] - b[2]) > NICHO_ALT_MAX:
        return False
    if peca.get('xml_tem_porta'):
        return False
    return _cobertura_frontal_max(peca, contexto['P']) < NICHO_MIN_RATIO


def _eh_nicho_conjunto(itens):
    if len(itens) < NICHO_MIN_PECAS:
        return False
    horizontais = sum(1 for i in itens if (i['bb'][5] - i['bb'][2]) <= 30)
    if horizontais < NICHO_MIN_HORIZ:
        return False
    U = list(itens[0]['bb'])
    for i in itens[1:]:
        U = geo.uniao(U, i['bb'])
    largura = max(U[3] - U[0], U[4] - U[1])
    altura = U[5] - U[2]
    return largura <= NICHO_LARG_MAX and altura <= NICHO_ALT_MAX


def _eh_oculto(peca, contexto):
    eixo = contexto.get('eixo_vista')
    if eixo is None:
        return False
    ad = 0 if eixo[0] else 1
    al = 1 - ad
    sinal = eixo[ad]
    b = peca['bb']
    # lado da peca voltado para a camera: se sinal>0, camera esta do lado '-', entao
    # a face visivel e a de menor coordenada (b[ad]); se sinal<0, e a de maior (b[ad+3]).
    face = b[ad] if sinal > 0 else b[ad + 3]
    area_face = max(1.0, (b[al + 3] - b[al]) * (b[5] - b[2]))
    excluir = set(peca.get('pecas', []))
    cobertura = 0.0
    for o in contexto['P']:
        if o['i'] in excluir:
            continue
        ob = o['bb']
        frente_o = ob[ad] if sinal > 0 else ob[ad + 3]
        if (face - frente_o) * sinal <= 5:   # 'o' precisa estar MAIS perto da camera que a face
            continue
        ov_al = max(0.0, min(ob[al + 3], b[al + 3]) - max(ob[al], b[al]))
        ov_z = max(0.0, min(ob[5], b[5]) - max(ob[2], b[2]))
        cobertura += ov_al * ov_z
    return (cobertura / area_face) >= OCLUSAO_MIN_RATIO
