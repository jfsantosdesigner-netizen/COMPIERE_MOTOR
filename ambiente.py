# -*- coding: utf-8 -*-
"""
ambiente.py — ETAPA 2: o AMBIENTE (parede, piso, janela/abertura) lido SÓ do DXF. Não conhece XML nem móvel.

  construir(P) -> dict    (P = peças do DXF: i, layer, bb, dim, faces)
    malha_par     indices: parede/casca em peça única (altura>=1800, comprimento>=1000, espessura>400)
    fontes_parede indices: malha_par + paredes finas altas (espessura 60-400, altura>=1800, comprimento>=1000)
    par_dxf       indices: candidatas a parede em peça (espessura 60-400, altura>=100, comprimento<20000)
    paredes_pecas indices: paredes altas (altura>=2000, espessura 80-400, comprimento>=1000)
    piso          indices: placa(s) de piso (placa fina grande no chao)
    piso_z        altura do piso (mm)
São CANDIDATAS: sem o XML não dá para saber se uma peça alta é parede ou móvel. A Unificação (unificacao.py) descarta as
que casam com o XML. Pura: não lê/escreve arquivo, não guarda estado.
"""
import math

PEDRA_COR = (0.16, 0.16, 0.17)

# REGRA (v33, João): parede e piso têm que LER como parede e piso - não podem se perder dentro do
# móvel. O móvel branco e (0.97,0.97,0.97); a parede era (0.94,0.94,0.94), quase o mesmo tom.
# REGRA (João, 2026-09-28): parede "gelo" — cinza-branco levemente quente (R e G acima de B),
# nem cinza puro/frio nem branco puro. Reaplicado após reversão (edição perdida em backup anterior).
PAREDE_COR = (0.95, 0.94, 0.91)
PISO_COR = (0.78, 0.78, 0.80)
ELETRO_COR = (0.72, 0.73, 0.76)

CHAVES_PECA = ('i', 'layer', 'bb', 'dim', 'faces')


def numero_finito(v):
    return type(v) in (int, float) and math.isfinite(v)


def validar_caixa(b, nome='bb'):
    if not isinstance(b, (list, tuple)) or len(b) != 6 or not all(numero_finito(v) for v in b):
        raise ValueError(f'{nome} deve conter 6 números finitos')
    if any(b[k + 3] < b[k] for k in range(3)):
        raise ValueError(f'{nome} possui limites invertidos')


def validar_pecas(P):
    """Valida o contrato comum do DXF antes de qualquer classificação."""
    if not isinstance(P, list):
        raise TypeError('P deve ser uma lista de peças do DXF')
    for pos, p_ in enumerate(P):
        if not isinstance(p_, dict):
            raise TypeError(f'P[{pos}] deve ser um dicionário')
        faltam = [k for k in CHAVES_PECA if k not in p_]
        if faltam:
            raise ValueError(f'P[{pos}] sem chaves obrigatórias: {", ".join(faltam)}')
        if type(p_['i']) is not int or p_['i'] != pos:
            raise ValueError(f'P[{pos}].i={p_["i"]}; o índice deve coincidir com a posição')
        if not isinstance(p_['layer'], str):
            raise TypeError(f'P[{pos}].layer deve ser texto')
        if not isinstance(p_['bb'], (list, tuple)) or len(p_['bb']) != 6:
            raise ValueError(f'P[{pos}].bb deve ter 6 números')
        if not isinstance(p_['dim'], (list, tuple)) or len(p_['dim']) != 3:
            raise ValueError(f'P[{pos}].dim deve ter 3 números')
        if not all(numero_finito(v) for v in list(p_['bb']) + list(p_['dim'])):
            raise ValueError(f'P[{pos}].bb/dim devem conter apenas números finitos')
        if any(p_['bb'][k + 3] < p_['bb'][k] for k in range(3)) or any(v < 0 for v in p_['dim']):
            raise ValueError(f'P[{pos}] possui limites ou dimensões inválidos')
        if not isinstance(p_['faces'], list):
            raise TypeError(f'P[{pos}].faces deve ser uma lista')
        for face in p_['faces']:
            if not isinstance(face, (list, tuple)) or len(face) < 3:
                raise ValueError(f'P[{pos}] possui face inválida')
            for vertice in face:
                if not isinstance(vertice, (list, tuple)) or len(vertice) != 3 or not all(numero_finito(v) for v in vertice):
                    raise ValueError(f'P[{pos}] possui vértice inválido')
    return P

def _n(a, b, c):
    if len(set((a, b, c))) < 3: return (0, 0, 1)
    e1 = [b[k] - a[k] for k in range(3)]; e2 = [c[k] - a[k] for k in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]); m = math.sqrt(sum(x * x for x in n)) or 1
    return tuple(x / m for x in n)
def caixa_faces_(b):
    x0, y0, z0, x1, y1, z1 = b
    return [[(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]]
def _arestas(faces):
    # contorno nítido: aresta de borda ou quina (normais diferentes); diagonal de triangulação não aparece
    # só arestas RETAS de verdade (alinhadas a um eixo): quina de parede, vão de janela, borda da pedra.
    # Aresta inclinada = triangulação -> nunca aparece (evita riscos diagonais no desenho).
    reta = lambda a_, b_: sum(1 for k_ in range(3) if abs(a_[k_] - b_[k_]) > 1) <= 1
    ed = {}; nrm = [_n(fc[0], fc[1], fc[2]) for fc in faces]
    kk = lambda v: tuple(round(c, 0) for c in v)
    for i_, fc in enumerate(faces):
        for j_ in range(len(fc)):
            a_, b_ = kk(fc[j_]), kk(fc[(j_ + 1) % len(fc)])
            if a_ == b_: continue
            ed.setdefault(frozenset((a_, b_)), []).append(i_)
    out = []
    for i_, fc in enumerate(faces):
        fl = []
        for j_ in range(len(fc)):
            a_, b_ = kk(fc[j_]), kk(fc[(j_ + 1) % len(fc)])
            fs2 = ed.get(frozenset((a_, b_)), [])
            if a_ == b_ or not reta(a_, b_): fl.append(False); continue
            if len(fs2) < 2: fl.append(True); continue
            n1, n2 = nrm[fs2[0]], nrm[fs2[1]]
            fl.append(abs(sum(x * y for x, y in zip(n1, n2))) < 0.94)
        out.append(fl)
    return out


def construir(P):
    validar_pecas(P)
    malha = [p_ for p_ in P if p_['faces'] and p_['dim'][2] >= 1800
             and max(p_['dim'][0], p_['dim'][1]) >= 1000 and min(p_['dim'][0], p_['dim'][1]) > 400]
    mi = {p_['i'] for p_ in malha}
    finas = [p_ for p_ in P if p_['dim'][2] >= 1800 and 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
    par = [p_ for p_ in P if 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400
           and max(p_['dim'][0], p_['dim'][1]) >= 100 and p_['dim'][2] >= 100 and max(p_['dim'][0], p_['dim'][1]) < 20000
           and not (p_['bb'][2] < 50 and p_['dim'][2] < 1000)]   # peça baixa no chão (rodapé solto) não é parede
    paredes_pecas = [p_ for p_ in P if p_['dim'][2] >= 2000 and 80 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
    pisos = [p_ for p_ in P if min(p_['dim'][0], p_['dim'][1]) > 1500 and p_['dim'][2] <= 60 and p_['bb'][2] <= 1]
    zp = max([p_['bb'][5] for p_ in pisos] or [0])
    return dict(piso=[p_['i'] for p_ in pisos], malha_par=[p_['i'] for p_ in malha], fontes_parede=[p_['i'] for p_ in malha + finas],
                par_dxf=[p_['i'] for p_ in par], paredes_pecas=[p_['i'] for p_ in paredes_pecas], piso_z=zp)
