# -*- coding: utf-8 -*-
"""
unificacao.py — ETAPA 4: onde o XML encontra o DXF. Recebe os CANDIDATOS de ambiente.py e ambientemodu.py e fecha o
ambiente final, descartando o que o XML reconhece como móvel e aplicando o que depende dos móveis.

  fechar(P, amb, modu, usadas, bbs_moveis) -> dict   (mesmo dict que o gerar_caderno sempre consumiu)
    usadas      conjunto de indices de P que pertencem a itens do XML
    bbs_moveis  caixas [x0,y0,z0,x1,y1,z1] dos itens do XML
Pura. Lógica movida do antigo ambiente.construir(P, usadas, bbs) sem alteração.
"""
import geo
from ambiente import caixa_faces_, _arestas


def _tup(p_): p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]


def fechar(P, amb, modu, usadas, bbs_moveis):
    _usadas = usadas; _inst_bb = bbs_moveis
    def _vol(b): return max(0, b[3] - b[0]) * max(0, b[4] - b[1]) * max(0, b[5] - b[2])
    def _vol_int(A, B): return _vol([max(A[0], B[0]), max(A[1], B[1]), max(A[2], B[2]), min(A[3], B[3]), min(A[4], B[4]), min(A[5], B[5])]) if all(min(A[k + 3], B[k + 3]) > max(A[k], B[k]) for k in range(3)) else 0
    _bb_list = [P[pi]['bb'] for pi in _usadas]
    DUP_I = {p_['i'] for p_ in P if p_['i'] not in _usadas and _vol(p_['bb']) > 0 and sorted(p_['dim'])[1] >= 50
             and any(_vol_int(p_["bb"], b_) >= 0.8 * max(_vol(p_["bb"]), _vol(b_)) for b_ in _bb_list)}
    AMB = [P[i] for i in modu['pedra'] if i not in _usadas]
    AMB_I = {p_['i'] for p_ in AMB}
    MALHA_PAR = [P[i] for i in amb['malha_par'] if i not in _usadas and i not in AMB_I]
    MALHA_I = {p_['i'] for p_ in MALHA_PAR}
    for p_ in MALHA_PAR: _tup(p_)
    def _faces_parede_real():
        out = []   # (eixo 'x'|'y', coordenada, a0, a1)
        malha_cand = set(amb['malha_par'])
        for i_ in amb['fontes_parede']:
            p_ = P[i_]
            if i_ in malha_cand:
                if i_ not in MALHA_I: continue      # parede-malha que o XML reconheceu como móvel
            elif i_ in _usadas: continue            # parede fina que o XML reconheceu como móvel
            fcs = p_['faces'] if i_ in MALHA_I else caixa_faces_(p_['bb'])
            for fc in fcs:
                xs = [v[0] for v in fc]; ys = [v[1] for v in fc]; zs = [v[2] for v in fc]
                if max(zs) - min(zs) < 1500: continue
                if max(xs) - min(xs) <= 1 and max(ys) - min(ys) >= 300: out.append(('x', sum(xs) / len(xs), min(ys), max(ys)))
                elif max(ys) - min(ys) <= 1 and max(xs) - min(xs) >= 300: out.append(('y', sum(ys) / len(ys), min(xs), max(xs)))
        # faces no MESMO plano (±10 mm) = uma parede só, de ponta a ponta: o vão de porta/janela não quebra a parede
        lin = []
        for e, c, a0, a1 in sorted(out):
            o = next((l for l in lin if l[0] == e and abs(l[1] - c) <= 10), None)
            if o is None: lin.append([e, c, a0, a1])
            else: o[2] = min(o[2], a0); o[3] = max(o[3], a1)
        return [tuple(l) for l in lin]
    _FR = _faces_parede_real()
    ELETROS = [P[i] for i in modu['eletro_a'] if i not in _usadas and i not in AMB_I and i not in MALHA_I]
    # REGRA (João): blocos QUADRADOS (caixa simples, 12 faces) não entram — atrapalham a imagem. Fica objeto com forma
    # real (> 12 faces); em cima da pedra, só o que for baixo (cuba, cooktop: até 300 mm acima da pedra).
    _topo_pedra = [p_['bb'][5] for p_ in AMB]
    def _eletro_ok(p_):
        if len(p_['faces']) <= 12: return False
        if p_['bb'][2] < 50 and p_['bb'][5] < 250: return False   # base/rodapé solto no chão não é eletro
        for t_ in _topo_pedra:
            if p_['bb'][2] <= t_ + 15 and p_['bb'][5] > t_ - 60: return p_['bb'][5] <= t_ + 300
        return True
    ELETROS = [p_ for p_ in ELETROS if _eletro_ok(p_)]
    _ja_e = {q['i'] for q in ELETROS}
    ELETROS += [P[i] for i in modu['eletro_b'] if i not in _usadas and i not in AMB_I and i not in MALHA_I and i not in _ja_e
                and any(geo.dist_caixas(P[i]['bb'], b_) <= 20 for b_ in _inst_bb)]
    ELETRO_I = {p_['i'] for p_ in ELETROS}
    for p_ in ELETROS: _tup(p_)
    for p_ in AMB + ELETROS + MALHA_PAR:
        _tup(p_); p_['ft'] = _arestas(p_['faces'])
    PAR_DXF = [P[i] for i in amb['par_dxf'] if i not in _usadas and i not in AMB_I and i not in ELETRO_I]
    for p_ in AMB: _tup(p_)
    PAREDES_PECAS = [P[i] for i in amb['paredes_pecas']]
    return dict(duplicadas=DUP_I, pedra=AMB, malha_par=MALHA_PAR, eletros=ELETROS, par_dxf=PAR_DXF,
                paredes_pecas=PAREDES_PECAS, piso_z=amb['piso_z'], faces_parede_real=_FR)


# ---- Contrato (JSON) do resultado final: so indices e numeros --------------------------------------------------
VERSAO = 1
PAPEIS = ('duplicadas', 'pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas')


def para_json(res):
    d = {'versao': VERSAO, 'piso_z': res['piso_z'], 'faces_parede_real': [list(f) for f in res['faces_parede_real']]}
    d['duplicadas'] = sorted(res['duplicadas'])
    for k in PAPEIS[1:]:
        d[k] = [p['i'] for p in res[k]]
    return d


def de_json(d, P):
    if d.get('versao') != VERSAO:
        raise ValueError(f"contrato de ambiente versao {d.get('versao')} != {VERSAO}")
    res = {k: [P[i] for i in d[k]] for k in PAPEIS[1:]}
    res['duplicadas'] = set(d['duplicadas']); res['piso_z'] = d['piso_z']
    res['faces_parede_real'] = [tuple(f) for f in d['faces_parede_real']]
    for p_ in res['pedra'] + res['eletros'] + res['malha_par']:
        _tup(p_); p_['ft'] = _arestas(p_['faces'])
    return res
