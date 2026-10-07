# -*- coding: utf-8 -*-
"""
ambiente.py — o AMBIENTE (alvenaria/estrutura) separado do gerar_caderno.

Funcao pura: construir(P, usadas, bbs_moveis) -> dict   (ver CONTRATO_AMBIENTE.md)
  P            lista de pecas do DXF (cada uma com i, layer, bb, dim, faces, mat opcional)
  usadas       conjunto de indices de P que pertencem a itens do XML (movel/componente)
  bbs_moveis   caixas [x0,y0,z0,x1,y1,z1] dos itens do XML
Tudo que NAO e movel do XML e e arquitetura/objeto de apoio sai daqui: pedra, paredes (malha e pecas),
eletros/objetos, piso, duplicadas e as faces das paredes reais. O gerar_caderno so CONSOME este resultado.
Nao le arquivo, nao escreve arquivo, nao guarda estado entre chamadas.
(Movido do gerar_caderno.py sem alterar a logica.)
"""
import math
import geo

PEDRA_COR = (0.16, 0.16, 0.17)

# REGRA (v33, João): parede e piso têm que LER como parede e piso - não podem se perder dentro do
# móvel. O móvel branco e (0.97,0.97,0.97); a parede era (0.94,0.94,0.94), quase o mesmo tom.
# REGRA (João, 2026-09-28): parede "gelo" — cinza-branco levemente quente (R e G acima de B),
# nem cinza puro/frio nem branco puro. Reaplicado após reversão (edição perdida em backup anterior).
PAREDE_COR = (0.95, 0.94, 0.91)
PISO_COR = (0.78, 0.78, 0.80)
ELETRO_COR = (0.72, 0.73, 0.76)

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

def construir(P, usadas, bbs_moveis):
    _usadas = usadas
    _inst_bb = bbs_moveis
    def _vol(b): return max(0, b[3] - b[0]) * max(0, b[4] - b[1]) * max(0, b[5] - b[2])
    def _vol_int(A, B): return _vol([max(A[0], B[0]), max(A[1], B[1]), max(A[2], B[2]), min(A[3], B[3]), min(A[4], B[4]), min(A[5], B[5])]) if all(min(A[k + 3], B[k + 3]) > max(A[k], B[k]) for k in range(3)) else 0
    _bb_list = [P[pi]['bb'] for pi in _usadas]
    DUP_I = {p_['i'] for p_ in P if p_['i'] not in _usadas and _vol(p_['bb']) > 0 and sorted(p_['dim'])[1] >= 50
             and any(_vol_int(p_["bb"], b_) >= 0.8 * max(_vol(p_["bb"]), _vol(b_)) for b_ in _bb_list)}
    AMB = [p_ for p_ in P if p_['i'] not in _usadas and p_['faces'] and 15 <= p_['dim'][2] <= 100
           and max(p_['dim'][0], p_['dim'][1]) >= 500 and min(p_['dim'][0], p_['dim'][1]) >= 250 and 700 <= p_['bb'][2] <= 1100]
    AMB_I = {p_['i'] for p_ in AMB}
    # PAREDES REAIS do DXF (com vãos de janela/porta quando vierem): peça vertical, espessura 60–400 mm, não casada com móvel.
    # PAREDES EM PEÇA ÚNICA (alguns DXF trazem a sala inteira numa camada): usa as FACES reais, nunca a caixa.
    MALHA_PAR = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['faces'] and p_['dim'][2] >= 1800
                 and max(p_['dim'][0], p_['dim'][1]) >= 1000 and min(p_['dim'][0], p_['dim'][1]) > 400]
    MALHA_I = {p_['i'] for p_ in MALHA_PAR}
    for p_ in MALHA_PAR: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
    def _faces_parede_real():
        out = []   # (eixo 'x'|'y', coordenada, a0, a1)
        fontes = list(MALHA_PAR) + [p_ for p_ in P if p_['i'] not in _usadas and p_['dim'][2] >= 1800
                                    and 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
        for p_ in fontes:
            fcs = p_['faces'] if p_['i'] in MALHA_I else caixa_faces_(p_['bb'])
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
    ELETROS = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['i'] not in MALHA_I and p_['faces']
               and len(p_['faces']) >= 10 and sorted(p_['dim'])[0] >= 40 and sorted(p_['dim'])[1] >= 150 and max(p_['dim']) <= 2200 and p_['dim'][2] >= 100
               and p_['bb'][5] <= 2300 and not (60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and p_['dim'][2] >= 1800)]
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
    ELETROS += [p_ for p_ in P if not p_.get('mat') and p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['i'] not in MALHA_I and p_['i'] not in _ja_e and p_['faces']
                and sorted(p_['dim'])[0] >= 15 and sorted(p_['dim'])[1] >= 100 and p_['bb'][5] <= 1300 and p_['bb'][2] >= -5
                and not (p_['dim'][2] < 60 and min(p_['dim'][0], p_['dim'][1]) > 1000) and not (p_['bb'][2] < 50 and p_['bb'][5] < 250)
                and any(geo.dist_caixas(p_['bb'], b_) <= 20 for b_ in _inst_bb)]
    ELETRO_I = {p_['i'] for p_ in ELETROS}
    for p_ in ELETROS: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
    for p_ in AMB + ELETROS + MALHA_PAR:
        p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]; p_['ft'] = _arestas(p_['faces'])
    PAR_DXF = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in {q['i'] for q in AMB} and p_['i'] not in ELETRO_I and 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400
               and max(p_['dim'][0], p_['dim'][1]) >= 100 and p_['dim'][2] >= 100 and max(p_['dim'][0], p_['dim'][1]) < 20000
               and not (p_['bb'][2] < 50 and p_['dim'][2] < 1000)]   # peça baixa no chão (rodapé solto) não é parede
    for p_ in AMB: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
    PAREDES_PECAS = [p_ for p_ in P if p_['dim'][2] >= 2000 and 80 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
    ZP = max([p_['bb'][5] for p_ in P if min(p_['dim'][0], p_['dim'][1]) > 1500 and p_['dim'][2] <= 60 and p_['bb'][2] <= 1] or [0])
    return dict(duplicadas=DUP_I, pedra=AMB, malha_par=MALHA_PAR, eletros=ELETROS, par_dxf=PAR_DXF,
                paredes_pecas=PAREDES_PECAS, piso_z=ZP, faces_parede_real=_FR)


# ---- Contrato (JSON) -------------------------------------------------------------------------------------------
# Quem produzir o ambiente (este modulo, hoje; um motor proprio, amanha) entrega o MESMO conteudo. Versao 1 aponta
# as pecas do DXF por indice; ver CONTRATO_AMBIENTE.md.
VERSAO = 1
PAPEIS = ('duplicadas', 'pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas')


def para_json(amb):
    """Resultado de construir() -> dict serializavel (so indices e numeros). Ordem das listas preservada."""
    d = {'versao': VERSAO, 'piso_z': amb['piso_z'],
         'faces_parede_real': [list(f) for f in amb['faces_parede_real']]}
    d['duplicadas'] = sorted(amb['duplicadas'])
    for k in PAPEIS[1:]:
        d[k] = [p['i'] for p in amb[k]]
    return d


def de_json(d, P):
    """dict do contrato + pecas do DXF -> o mesmo dict que construir() devolve (faces em tuplas, arestas 'ft')."""
    if d.get('versao') != VERSAO:
        raise ValueError(f"contrato de ambiente versao {d.get('versao')} != {VERSAO}")
    amb = {k: [P[i] for i in d[k]] for k in PAPEIS[1:]}
    amb['duplicadas'] = set(d['duplicadas'])
    amb['piso_z'] = d['piso_z']
    amb['faces_parede_real'] = [tuple(f) for f in d['faces_parede_real']]
    for p_ in amb['pedra'] + amb['eletros'] + amb['malha_par']:
        p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]; p_['ft'] = _arestas(p_['faces'])
    return amb
