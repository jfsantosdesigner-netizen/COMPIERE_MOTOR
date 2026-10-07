# GERADOR DE CADERNO v2 — Compiere. Um comando: python gerar_caderno.py config.json
# XML/listagem -> DXF (posição real) -> vistas automáticas -> listagem por vista + balões -> elevações com cotas -> PDF + QUALIDADE
import sys as _sys0; _sys0.dont_write_bytecode = True   # BLINDAGEM: nao gera __pycache__
import sys, os, re, json, subprocess
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf as fz, geo, classificacao
import compatibilizacao


# BLINDAGEM: a configuracao chega como TEXTO JSON no argumento (sem arquivo _config.json). Arquivo ainda aceito p/ uso manual.
cfg = json.loads(sys.argv[1]) if sys.argv[1].lstrip().startswith('{') else json.load(open(sys.argv[1], encoding='utf-8'))
# REGRA (v27): PROIBIDO puxar listagem/imagens de PDF — tudo sai do XML + DXF
for _k in ('listagem_pdf', 'imagens', 'capa_img'): cfg.pop(_k, None)
AREA = fz.Rect(19, 142, 823, 577); IN = 7
RED = (0.545, 0, 0); CR = (0.9, 0, 0); PRETO = (0, 0, 0)
BRANCO = (1, 1, 1); MADEIRA = (0.80, 0.63, 0.42); CINZA = (0.93, 0.93, 0.93)
MM = 72 / 25.4
# REGRA (João, 28/09/2026): threshold "40%" que decide se uma face frontal esta COBERTA (=tem porta/frente,
# nao e nicho) ou ABERTA (=nicho). Usado em 2 lugares: tem_porta(), nichos().
# Ajustar aqui muda o comportamento das 3 regras de uma vez. Valor original era 0.4 hardcoded.
NICHO_MIN_RATIO = 0.4
ESC = [15, 20, 25, 30, 40, 50, 75, 100, 125, 150]
ESC_COTA = [10, 12.5, 15, 20, 25, 30, 40, 50, 75, 100]   # v15: elevação de cotas usa a maior escala que cabe   # 1:15 e 1:20 só para móvel/parede pequena (ver escala_para)
FV = {'x+': (1, 0), 'x-': (-1, 0), 'y+': (0, 1), 'y-': (0, -1)}
AREA_IN = fz.Rect(AREA.x0 + IN, AREA.y0 + IN, AREA.x1 - IN, AREA.y1 - IN)   # regra: nada encosta no quadro

def fmt(v):
    v = round(v * 2) / 2
    return str(int(round(v))) if abs(v - round(v)) < 0.01 else ('%.1f' % v).replace('.', ',')

# ---------------- entrada única ----------------
import entrada_xml
_XML=entrada_xml.ler(cfg['xml'])

import entrada_projeto
import unificacao, projeto_unificado
P = entrada_projeto.ler_dxf(cfg['dxf'])

import math
def preparar(P):
    # REGRA: imagem limpa - cada peça é desenhada como caixa reta (só as bordas, sem triangulação)
    for p_ in P:
        x0, y0, z0, x1, y1, z1 = p_['bb']
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
        N = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
        p_['fq'] = [[[c[i] for i in f_], n_, [True] * 4] for f_, n_ in zip(F, N)]
preparar(P)

# ===== ETAPA 5 ? MATERIAIS/CORES =====
import collections as _col
import cores as _cores
_norm = _cores.normalizar  # compatibilidade: normaliza??o textual tamb?m ? usada por regras legadas
try:
    from PIL import Image as _Im, ImageDraw as _ImD
    import numpy as _np
except Exception:
    _Im = None
_MD = os.path.dirname(os.path.abspath(__file__))
_BIB = _cores.Biblioteca(_MD, cfg, pixmap=fz, image=_Im)
_MAT = _BIB.pasta; _MC = _BIB.cache_path; _TXD = _BIB.reserva; _cc = _BIB.cache
def cor_material(nome): return _BIB.cor_material(nome)
def textura(nome): return _BIB.textura(nome)
def _gravar_biblioteca():
    n_ = _BIB.gravar_cache_cores()
    if n_: print(f"BIBLIOTECA: {n_} cor(es) nova(s) gravada(s) em materiais_cores.json")
_MATERIAIS_XML = unificacao.materiais_por_peca(P, _XML)
PROJETO = unificacao.construir(P, _XML, _MATERIAIS_XML)
_RES_CORES = _cores.aplicar(PROJETO, _BIB)
_nc = _RES_CORES['coloridas']; _usadas = _RES_CORES['usadas']
print('CORES: %d pecas coloridas pelo MATERIAIS (medidas no XML: %d)' % (_nc, len(_XML['materiais_dimensoes'])))
TEX_FALTA = [m_ for m_ in _usadas if _cc.get(m_) and not any(os.path.exists(os.path.join(d_, _cc[m_][1].replace(chr(92), '/').split('/')[-1].lower())) for d_ in (_TXD,))]
for nm_, q_ in _usadas.most_common(): print('   %-22s %4d pecas <- %s' % (nm_, q_, os.path.relpath(_cc[nm_][1], _MAT)))
_todas_mats = {r_ for c_ in _XML['materiais_dimensoes'].values() for r_ in c_}
for nm_ in [k for k, v in _cc.items() if not v and k in _todas_mats]: print('   SEM TEXTURA:', nm_)

inst = PROJETO['itens']; AMBIENTE = PROJETO['ambiente']
if not inst:
    raise SystemExit('UNIFICAÇÃO BLOQUEADA: nenhum item do XML foi localizado no DXF. Confira o par XML montado + DXF exportado.')
PORTAS_XML = PROJETO['portas']['pecas_xml']
linhas = PROJETO['xml']['linhas']; cores = PROJETO['xml']['cores']
puxs = PROJETO['xml']['puxadores']; ferrs = PROJETO['xml']['ferragens']
_ADOTADAS = PROJETO['diagnostico']['orfas_adotadas']
if _ADOTADAS: print(f"ORFAS ADOTADAS: {len(_ADOTADAS)} chapa(s) sem item no XML incorporada(s) ao módulo que a contém")
paredes = compatibilizacao.definir_paredes(inst, P, PORTAS_XML)
# REGRA: mesma parede com módulos de profundidades diferentes (ex.: armário raso 200 mm + balcão 600 mm)
# = UMA parede só. Junta paredes do mesmo lado com planos a até 600 mm e trechos que se tocam/sobrepõem.
def _juntar_paredes(paredes):
    mudou = True
    while mudou:
        mudou = False
        for a in paredes:
            for b in paredes:
                if a is b or a['key'] != b['key'] or abs(a['plano'] - b['plano']) > 600: continue
                ax = 1 if FV[a['key']][0] else 0
                ra = (min(i['bb'][ax] for i in a['itens']), max(i['bb'][ax + 3] for i in a['itens']))
                rb = (min(i['bb'][ax] for i in b['itens']), max(i['bb'][ax + 3] for i in b['itens']))
                if ra[1] < rb[0] - 100 or rb[1] < ra[0] - 100: continue
                sg = FV[a['key']][1 - ax]
                a['plano'] = max(a['plano'] * sg, b['plano'] * sg) * sg   # plano mais "no fundo"
                a['itens'] += b['itens']; paredes.remove(b); mudou = True; break
            if mudou: break
    for w in paredes:
        w['id'] = f"{w['key']}@{round(w['plano'])}"
        for it in w['itens']: it['parede'] = w['id']
    return paredes
paredes = _juntar_paredes(paredes)
# AMBIENTE (referência, NUNCA cotado): peças do DXF que não são móvel do XML nem parede/piso.
# Hoje: PEDRA / bancada / rodabanca = placa horizontal (15–100 mm) na altura da bancada (700–1100 mm).
# Desenhada com as faces reais do DXF (pedra em L sai em L).
# Planta conserva a projeção anterior: portas avulsas não entram como corpo.
_usadas = PROJETO['moveis'] - PORTAS_XML
# REGRA (v26): peça do DXF que NÃO está na listagem e ocupa o MESMO lugar de uma peça listada (cópia do painel,
# ex.: painel usinado 1580 sobre o painel 1530 da lista) = duplicada -> não é desenhada (cobria o painel de cinza).
# AMBIENTE = MÓDULOS À PARTE (contrato em CONTRATO_AMBIENTE.md): ambiente.py e ambientemodu.py leem SÓ o DXF e
# entregam candidatos; unificacao.py aplica o XML (peças usadas e caixas dos móveis) e fecha o resultado.
import ambiente
from ambiente import _n, PEDRA_COR, PAREDE_COR, PISO_COR, ELETRO_COR
DUP_I = AMBIENTE['duplicadas']; AMB = AMBIENTE['pedra']; MALHA_PAR = AMBIENTE['malha_par']; ELETROS = AMBIENTE['eletros']
PAR_DXF = AMBIENTE['par_dxf']; PAREDES_PECAS = AMBIENTE['paredes_pecas']; ZP = AMBIENTE['piso_z']
AMB_I = {p_['i'] for p_ in AMB}; MALHA_I = {p_['i'] for p_ in MALHA_PAR}; ELETRO_I = {p_['i'] for p_ in ELETROS}
_AMBIENTE_POR_I = {p_['i']: p_ for p_ in AMB + ELETROS + MALHA_PAR}
if DUP_I: print('PEÇAS DUPLICADAS NO DXF (não desenhadas):', len(DUP_I))
print('AMBIENTE (eletros/objetos):', len(ELETROS), 'peças')
print('AMBIENTE (pedra):', len(AMB), 'peças')
# REGRA (João, 28/09/2026 - skill V1, bloco VISTAS): a vista nasce da PAREDE REAL do ambiente (malha LAYER1 do DXF),
# não do plano das costas do móvel. Módulo cujas costas NÃO encostam em parede real (vista-fragmento, ex.: módulo de
# canto girado no closet em U) é levado para a parede real em que ele encosta; as peças soltas que ficaram sem módulo
# vão junto com o módulo mais próximo. Módulo que já está com as costas numa parede real não muda (canto L continua
# na parede do lado das portas - V3). Sem parede real atrás em nenhum lado = ilha/solto: não muda (P4).
# Sem malha de parede no DXF: nada muda (lógica anterior).
def _parede_real_atras(it, key, FR, tol=80):
    b = it['bb']; ax = 'x' if key[0] == 'x' else 'y'; back = geo.plano(key, b)
    a0, a1 = (b[1], b[4]) if ax == 'x' else (b[0], b[3])
    best = None
    for e, c, r0, r1 in FR:
        if e != ax or abs(c - back) > tol: continue
        if min(a1, r1) - max(a0, r0) < 0.5 * (a1 - a0): continue
        if best is None or abs(c - back) < abs(best - back): best = c
    return best
_FR = AMBIENTE['faces_parede_real']
if _FR:
    _movidos = []
    for w in list(paredes):
        for it in [i for i in w['itens'] if i['tipo'] == 'mod']:
            if _parede_real_atras(it, w['key'], _FR) is not None: continue      # já está numa parede real
            eixo = geo._ao_longo(it)
            pref = ('y-', 'y+') if eixo == 'x' else ('x-', 'x+')
            outros = tuple(k for k in ('x-', 'x+', 'y-', 'y+') if k not in pref)
            achou = None
            _b = it['bb']
            _quad = abs((_b[3] - _b[0]) - (_b[4] - _b[1])) <= 50   # módulo quadrado: o eixo do XML não decide o lado
            for grupo_ in ((pref, outros) if _quad else (pref,)):
                cands = [(abs(_parede_real_atras(it, k, _FR) - geo.plano(k, it['bb'])), k) for k in grupo_ if _parede_real_atras(it, k, _FR) is not None]
                if cands: achou = min(cands)[1]; break
            if achou is None: continue                                             # ilha / móvel solto
            w['itens'].remove(it); _movidos.append((it, achou))
    for it, k in _movidos:
        pl = geo.plano(k, it['bb'])
        alvo = next((o for o in paredes if o['key'] == k and not o.get('divisoria') and abs(o['plano'] - pl) <= 600), None)
        if alvo is None: alvo = dict(key=k, plano=pl, itens=[]); paredes.append(alvo)
        alvo['itens'].append(it); it['parede_key'] = k
        print(f"VISTA PELA PAREDE REAL: {it['desc']} {it['dim']} -> parede {k}")
    if _movidos:
        _mods_ = [i for w in paredes for i in w['itens'] if i['tipo'] == 'mod']
        for w in list(paredes):
            if any(i['tipo'] == 'mod' for i in w['itens']): continue
            if any(_parede_real_atras(i, w['key'], _FR) is not None for i in w['itens']): continue   # painel na parede real fica
            for it in list(w['itens']):
                m = min(_mods_, key=lambda m: geo.dist_caixas(it['bb'], m['bb']), default=None)
                if m is None or geo.dist_caixas(it['bb'], m['bb']) > 400: continue
                dono = next(o for o in paredes if m in o['itens'])
                w['itens'].remove(it); dono['itens'].append(it)
        paredes = [w for w in paredes if w['itens']]
        paredes = _juntar_paredes(paredes)
# ORDEM 005.B (v37.1): CÂMERA INDEPENDENTE — a parede REAL do ambiente decide a frente, independente
# de orientação do módulo no Promob. Para cada módulo, varre AS QUATRO direções (x-, x+, y-, y+) e
# verifica se há parede real do ambiente a até 80 mm. Se exatamente UMA direção tem, essa é a parede
# das costas, parede_key = essa direção, e a câmera (lado oposto) olha para a frente real.
# Se duas (módulo em canto) ou nenhuma (ilha) → mantém o parede_key atual (lado_frontal/parede_de decidem).
if _FR:
    _any_005b = False
    for _m in [i for i in inst if i['tipo'] == 'mod']:
        _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+') if _parede_real_atras(_m, _k, _FR) is not None]
        if len(_com_real) == 1 and _m.get('parede_key') != _com_real[0]:
            print(f"005.B: {_m['desc']} {_m['dim']}: {_m.get('parede_key')} -> {_com_real[0]}")
            _m['parede_key'] = _com_real[0]
            _m['frente'] = geo.OPOSTO[_com_real[0]]
            _any_005b = True
    if _any_005b:
        # Rebuild paredes dos módulos; componentes herdam do módulo mais próximo
        paredes = geo._montar([i for i in inst if i['tipo'] == 'mod'])
        _mods_ref = [i for i in inst if i['tipo'] == 'mod']
        for _it in inst:
            if _it['tipo'] == 'mod': continue
            _mp = min(_mods_ref, key=lambda m: geo.dist_caixas(_it['bb'], m['bb'])) if _mods_ref else None
            if _mp and geo.dist_caixas(_it['bb'], _mp['bb']) <= 400:
                _it['parede_key'] = _mp['parede_key']
                dono_ = next((o for o in paredes if _mp in o['itens']), None)
                if dono_ and _it not in dono_['itens']:
                    _it['parede'] = dono_['id']
                    dono_['itens'].append(_it)
        paredes = _juntar_paredes(paredes)
# Vistas e desenho consomem o projeto encerrado acima.
import cena_render
import compatibilizacao_camera
import renderizador
# REGRA (v28, João): móvel feito com GEOMETRIA no Promob (vem no DXF, não no XML) que ENCOSTA num móvel do projeto
# = referência na imagem (como a pedra): forma real, sem listagem/balão/cota.
# v29: peça com medida+cor do XML é PEÇA DE MÓVEL (porta/frente), nunca geometria.
# ===== REGRAS ESPECIAIS (v18) — só atuam quando o projeto tem esses móveis =====
def _sd(it): return sorted(parse_dim_(it['dim']))
def parse_dim_(dm):
    try: return [float(x) for x in re.findall(r'[\d.]+', dm.replace(',', '.'))[:3]]
    except Exception: return [0, 0, 0]
def _toca(a, b, tol=6): return geo.dist_caixas(a['bb'], b['bb']) <= tol
_comps = [i for i in inst if i['tipo'] == 'comp']
# 1) DIVISÓRIA RIPADA: 6+ ripas (espessura <= 30, largura 60-200, comprimento >= 500) na MESMA faixa de profundidade,
#    enfileiradas ao longo de um eixo. Vira um BLOCO PRÓPRIO (listagem + cotas só dela), fora das paredes.
DIVISORIAS = []
_rip = [i for i in _comps if (lambda d: d[0] <= 30 and 60 <= d[1] <= 200 and d[2] >= 500)(_sd(i))]
for axd in (0, 1):   # axd = eixo da profundidade (as ripas têm a largura de 150 nesse eixo)
    grp = {}
    for i in _rip:
        b = i['bb']
        if 60 <= b[axd + 3] - b[axd] <= 200: grp.setdefault((round(b[axd] / 10), round(b[axd + 3] / 10)), []).append(i)
    for key_, rs in grp.items():
        if len(rs) < 6 or any(i.get('_div') for i in rs): continue
        # REGRA (João, 28/09/2026 - bloco vistas): divisória ripada = 6+ ripas IGUAIS (mesmo comprimento ±20 mm, mesma
        # direção). Tiras de acabamento de 70 mm com comprimentos diferentes (moldura de painel na parede) NÃO são
        # divisória: continuam na vista da parede.
        _cmp = lambda i: (_sd(i)[2], 'z' if (i['bb'][5] - i['bb'][2]) >= _sd(i)[2] - 1 else 'h')
        _grp_ = {}
        for i in rs:
            L_, o_ = _cmp(i); k2 = next((k for k in _grp_ if k[1] == o_ and abs(k[0] - L_) <= 20), (L_, o_)); _grp_.setdefault(k2, []).append(i)
        _gm = max(_grp_.values(), key=len)
        if len(_gm) < 6: continue
        # ripado = ripas próximas umas das outras (vão mediano <= 150 mm); postes de moldura espaçados pelos módulos não são ripado
        # e ENFILEIRADAS lado a lado ao longo da divisória (6+ posições diferentes). Tiras empilhadas na frente de
        # módulos (mesma posição, alturas diferentes) não são ripado.
        _al = 1 - axd; _pos = sorted({round(i['bb'][_al] / 10) * 10: i for i in _gm}.values(), key=lambda i: i['bb'][_al])
        if len(_pos) < 6: continue
        _vaos = sorted(max(0, b_['bb'][_al] - a_['bb'][_al + 3]) for a_, b_ in zip(_pos, _pos[1:]))
        if _vaos[len(_vaos) // 2] > 150: continue
        d0, d1 = min(i['bb'][axd] for i in rs), max(i['bb'][axd + 3] for i in rs)
        conj = list(rs); topo = max(i['bb'][5] for i in rs)
        for i in rs: i['_div'] = True
        mudou = True
        while mudou:
            mudou = False
            for c in _comps:
                if c.get('_div'): continue
                b = c['bb']; dentro = b[axd] >= d0 - 30 and b[axd + 3] <= d1 + 30
                faixa = b[2] <= 100 or b[5] >= topo - 130 or (b[5] - b[2]) >= 0.8 * topo
                if (dentro or faixa) and any(_toca(c, o) for o in conj):
                    conj.append(c); c['_div'] = True; topo = max(topo, b[5]); mudou = True
        DIVISORIAS.append(dict(itens=conj, axd=axd, d0=d0, d1=d1))
# 2) DIVISOR DE GAVETA (joias/talheres): 4+ peças finas (<= 18) e baixas (<= 100) de até 450 mm, nos dois sentidos,
#    encostadas, acima do piso. Sai da listagem da parede e ganha uma PRANCHA PRÓPRIA (vista de cima com cotas).
DIVISORES = []
# REGRA (v26): divisor de TALHER de gaveta de cozinha tem peças até 750 mm (conjunto até 800 x 800);
#    as peças ficam DEITADAS (altura <= 100 mm de verdade no DXF) -> fechamento/tamponamento em pé não entra.
_dv = [i for i in _comps if not i.get('_div') and i['bb'][2] > 150 and i['bb'][5] - i['bb'][2] <= 100 and (lambda d: d[0] <= 18 and d[1] <= 100 and d[2] <= 750)(_sd(i))]
_vis = set()
for i in _dv:
    if id(i) in _vis: continue
    g_ = [i]; _vis.add(id(i)); k_ = 0
    while k_ < len(g_):
        for o in _dv:
            if id(o) not in _vis and _toca(g_[k_], o, 3): g_.append(o); _vis.add(id(o))
        k_ += 1
    ori = {0 if (o['bb'][3] - o['bb'][0]) > (o['bb'][4] - o['bb'][1]) else 1 for o in g_}
    U_ = [min(o['bb'][0] for o in g_), min(o['bb'][1] for o in g_), max(o['bb'][3] for o in g_), max(o['bb'][4] for o in g_)]
    if len(g_) >= 4 and len(ori) == 2 and U_[2] - U_[0] <= 800 and U_[3] - U_[1] <= 800:
        DIVISORES.append(g_)
# 3) GAVETA / MÓDULO MONTADO COM PAINÉIS (não é módulo do Promob): peça horizontal (fundo, >= 0,1 m²) acima de 300 mm
#    + peças do MESMO material encostadas, até 140 mm acima do fundo, 3+ em pé. Sai da parede -> prancha própria.
GAVETAS = []
_usad = {id(i) for g_ in DIVISORES for i in g_}
for fb in _comps:
    if fb.get('_div') or id(fb) in _usad or fb['bb'][2] <= 300: continue
    b = fb['bb']; dx_, dy_, dz_ = b[3] - b[0], b[4] - b[1], b[5] - b[2]
    if not (dz_ <= 30 and dx_ * dy_ >= 1e5 and max(dx_, dy_) <= 1000): continue
    mat_ = P[fb['pecas'][0]].get('mat')
    g_ = [fb]; k_ = 0
    while k_ < len(g_):
        for o in _comps:
            if o in g_ or o.get('_div') or id(o) in _usad: continue
            ob = o['bb']
            if P[o['pecas'][0]].get('mat') != mat_ or ob[2] < b[2] - 5 or ob[5] > b[2] + 140: continue
            if _toca(g_[k_], o, 3): g_.append(o)
        k_ += 1
    em_pe = [o for o in g_ if o['bb'][5] - o['bb'][2] >= 60]
    if len(g_) >= 4 and len(em_pe) >= 3:
        GAVETAS.append(g_); _usad |= {id(o) for o in g_}
_fora = {id(i) for d in DIVISORIAS for i in d['itens']} | {id(i) for g_ in DIVISORES for i in g_} | {id(i) for g_ in GAVETAS for i in g_}
if _fora:
    for w in paredes: w['itens'] = [i for i in w['itens'] if id(i) not in _fora]
    paredes = [w for w in paredes if w['itens']]
for d in DIVISORIAS:   # parede "virtual" da divisória: vista pelo lado do painel (peça larga e fina), senão pelo lado do ambiente
    axd = d['axd']; its = d['itens']
    lrg = [i for i in its if _sd(i)[1] > 300 and d['d0'] - 30 <= i['bb'][axd] and i['bb'][axd + 3] <= d['d1'] + 30]
    mid = (d['d0'] + d['d1']) / 2
    if lrg: menor = sum((i['bb'][axd] + i['bb'][axd + 3]) / 2 for i in lrg) / len(lrg) < mid
    else: menor = sum((i['bb'][axd] + i['bb'][axd + 3]) / 2 for i in inst) / len(inst) < mid
    key = ('x+' if menor else 'x-') if axd == 0 else ('y+' if menor else 'y-')
    pl = d['d1'] if menor else d['d0']
    w = dict(key=key, plano=pl, itens=its, id=f"DIVISORIA@{round(pl)}", divisoria=True)
    for i in its: i['parede'] = w['id']
    paredes.append(w); d['parede'] = w['id']
# 4) CONDIÇÃO (v22, planta do João): PERNA DO L dentro de uma parede (ex.: penteadeira em L) = VISTA PRÓPRIA.
#    Peças soltas da parede que vão bem mais fundo que os módulos (> 300 mm além da frente deles), formando um trecho de
#    600 mm+ na profundidade, viram outra "parede" vista de lado (pelo lado de dentro do L).
_novas = []
for w in [w for w in paredes if not w.get('divisoria')]:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    prof_ = lambda bb: max((w['plano'] - bb[ad]) * sg_, (w['plano'] - bb[ad + 3]) * sg_)
    mods_ = [i for i in w['itens'] if i['tipo'] == 'mod']
    if not mods_: continue
    D_ = max(prof_(m['bb']) for m in mods_)
    perna = [i for i in w['itens'] if i['tipo'] == 'comp' and prof_(i['bb']) > D_ + 300]
    if len(perna) < 2: continue
    p0 = min(min((w['plano'] - i['bb'][ad]) * sg_, (w['plano'] - i['bb'][ad + 3]) * sg_) for i in perna)
    if max(prof_(i['bb']) for i in perna) - max(p0, D_) < 600: continue
    c_perna = sum((i['bb'][al] + i['bb'][al + 3]) / 2 for i in perna) / len(perna)
    c_main = sum((i['bb'][al] + i['bb'][al + 3]) / 2 for i in mods_) / len(mods_)
    maior = c_perna > c_main       # câmera olha do lado de dentro do L (onde está o resto do móvel)
    key = ('x+' if maior else 'x-') if al == 0 else ('y+' if maior else 'y-')
    pl = max(i['bb'][al + 3] for i in perna) if maior else min(i['bb'][al] for i in perna)
    w['itens'] = [i for i in w['itens'] if i not in perna]
    nw = dict(key=key, plano=pl, itens=perna, id=f"{key}@{round(pl)}L", perna_l=True, pai=w['id'])
    for i in perna: i['parede'] = nw['id']
    _novas.append(nw)
paredes += _novas
# REGRA (v28): "parede" com até 2 peças soltas que ENCOSTAM (60 mm) em móvel de outra parede não vira vista: junta na outra
for w in [w for w in paredes if not (w.get('divisoria') or w.get('bloco') or w.get('perna_l'))]:
    if len(w['itens']) > 2 or any(i['tipo'] != 'comp' for i in w['itens']): continue
    alvo = None
    for o in paredes:
        if o is w or o.get('divisoria') or o.get('bloco') or len(o['itens']) <= 2: continue
        if all(any(geo.dist_caixas(i['bb'], j['bb']) <= 60 for j in o['itens']) for i in w['itens']): alvo = o; break
    if alvo:
        for i in w['itens']: i['parede'] = alvo['id']
        alvo['itens'] += w['itens']; w['itens'] = []
paredes = [w for w in paredes if w['itens']]
# 5) CONDIÇÃO (v26): PAREDE CORTADA POR PILAR / VÃO DE PASSAGEM. Os móveis de uma mesma parede ficam
#    dos dois lados de uma parede real que atravessa a faixa dos móveis (pilar, verga de vão de passagem) -> são DOIS
#    ambientes: cada lado vira uma parede (vista) própria, com listagem e cotas só dele (escala maior, leitura por lado).
def _faces_parede():
    for p_ in PAR_DXF + MALHA_PAR:
        for fc in p_['faces']: yield fc
_cortadas = []
for w in [w for w in paredes if not w.get('divisoria') and not w.get('perna_l')]:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]; pl = w['plano']
    mods_ = [i for i in w['itens'] if i['tipo'] == 'mod']
    if len(mods_) < 2: continue
    D_ = max(max((pl - m['bb'][ad]) * sg_, (pl - m['bb'][ad + 3]) * sg_) for m in mods_)
    a0, a1 = min(m['bb'][al] for m in mods_), max(m['bb'][al + 3] for m in mods_)
    cs = []
    for fc in _faces_parede():
        vs = [v[al] for v in fc]
        if max(vs) - min(vs) > 1: continue
        c = vs[0]
        if not a0 + 300 < c < a1 - 300: continue
        d0, d1 = sorted(((pl - min(v[ad] for v in fc)) * sg_, (pl - max(v[ad] for v in fc)) * sg_))
        if min(d1, D_) - max(d0, 0) >= 0.8 * D_: cs.append(c)
    cs.sort(); grp = []
    for c in cs:
        if grp and c - grp[-1][-1] <= 400: grp[-1].append(c)
        else: grp.append([c])
    partes = [w['itens']]
    for g in grp:
        c = (g[0] + g[-1]) / 2; nv = []
        for its_ in partes:
            e_ = [i for i in its_ if (i['bb'][al] + i['bb'][al + 3]) / 2 < c]; d_ = [i for i in its_ if i not in e_]
            le = sum(i['bb'][al + 3] - i['bb'][al] for i in e_ if i['tipo'] == 'mod'); ld = sum(i['bb'][al + 3] - i['bb'][al] for i in d_ if i['tipo'] == 'mod')
            nv += [e_, d_] if le >= 1000 and ld >= 1000 else [its_]
        partes = nv
    if len(partes) > 1: _cortadas.append((w, partes))
for w, partes in _cortadas:
    paredes.remove(w)
    for k_, its_ in enumerate(partes):
        nw = dict(key=w['key'], plano=w['plano'], itens=its_, id=f"{w['id']}{'abcdef'[k_]}", cortada=True)
        for i in its_: i['parede'] = nw['id']
        paredes.append(nw)
# 6) CONDIÇÃO (v26): CONJUNTO DE PAINÉIS SEM MÓDULO (painel com nichos na ponta da parede, painel
#    no teto, barrotes/cunhas, agastadores). Paredes só com painéis que se ENCOSTAM formam UM BLOCO PRÓPRIO no fim
#    (como a divisória): listagem com o móvel sozinho (3D frontal + 3D lateral reta) e cotas frontal + lateral.
_so = [w for w in paredes if not w.get('divisoria') and not any(i['tipo'] == 'mod' for i in w['itens'])]
_blocos = []
for w in _so:
    junto = [b for b in _blocos if any(_toca(i, j, 10) for o in b for i in o['itens'] for j in w['itens'])]
    novo_ = [w] + [o for b in junto for o in b]
    _blocos = [b for b in _blocos if b not in junto] + [novo_]
BLOCOS = []
for b in _blocos:
    its_ = [i for o in b for i in o['itens']]
    if len(b) < 2 or len(its_) < 4: continue
    # frente = parede do MAIOR painel em pé (visto de frente); plano = face da parede real logo atrás (até 150 mm)
    def _af(o):
        f_ = FV[o['key']]; ad = 0 if f_[0] else 1; al = 1 - ad
        return max([(i['bb'][al + 3] - i['bb'][al]) * (i['bb'][5] - i['bb'][2]) for i in o['itens'] if i['bb'][ad + 3] - i['bb'][ad] <= 30] or [0])
    fr_ = max(b, key=_af); f_ = FV[fr_['key']]; ad = 0 if f_[0] else 1; sg_ = f_[ad]; pl = fr_['plano']
    for fc in _faces_parede():
        vs = [v[ad] for v in fc]
        if max(vs) - min(vs) <= 1 and 0 < (vs[0] - pl) * sg_ <= 150: pl_ = vs[0]; break
    else: pl_ = pl
    for o in b: paredes.remove(o)
    nicho_ = any(re.match(r'tampon', i['desc'], re.I) for i in its_) and any(_sd(i)[0] <= 8 for i in its_)
    nw = dict(key=fr_['key'], plano=pl_, itens=its_, id=f"BLOCO@{round(pl_)}", divisoria=True, bloco='PAINEL COM NICHOS' if nicho_ else 'CONJUNTO DE PAINÉIS')
    for i in its_: i['parede'] = nw['id']
    paredes.append(nw); BLOCOS.append(nw)
PW = {w['id']: w for w in paredes}

# GANCHO DE TESTE (Fase 1 - classificacao.py) — nunca ativo em producao.
# So roda com a variavel de ambiente COMPIERE_TESTE_CLASSIFICACAO=1, e termina
# ANTES de qualquer codigo de desenho/render3d/PDF (nada abaixo desta linha e executado nesse modo).
if os.environ.get('COMPIERE_TESTE_CLASSIFICACAO'):
    import classificacao
    for _w in paredes:
        _ctx = dict(P=P, lim=geo.limites(inst),
                    moveis={_p for _i in inst for _p in _i.get('pecas', [])},
                    soltas=_w['itens'] + [_i for _i in inst if _i['tipo'] == 'mod'],
                    eixo_vista=geo.PAREDES.get(_w['key']))
        for _it in _w['itens']:
            _tipo = compatibilizacao.classificar(_it, _ctx)
            print(f"CLASSIFICACAO\t{_tipo}\t{_it['desc']}\t{_it['dim']}")
    sys.exit(0)

# 7) CONDIÇÃO (v26): PAINEL USINADO. Painel em pé na FRENTE de uma estrutura de nichos aberta (2 laterais + 3 ou mais
#    prateleiras logo atrás, até 150 mm) = painel com VÃOS usinados alinhados aos nichos (o DXF traz o painel inteiro).
#    Vão = largura livre entre as laterais x altura livre entre prateleiras (> 150 mm). O painel é desenhado com os vãos.
def _caixa_fq(b):
    x0, y0, z0, x1, y1, z1 = b
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
    N = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
    return [[[c[i] for i in f_], n_, [True] * 4] for f_, n_ in zip(F, N)]
USINADOS = {}
for w in paredes:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    cps = [i for i in w['itens'] if i['tipo'] == 'comp']
    for pn in cps:
        b = pn['bb']
        if b[ad + 3] - b[ad] > 25 or b[al + 3] - b[al] < 400 or b[5] - b[2] < 800: continue
        tras = b[ad + 3] if sg_ > 0 else b[ad]
        atr = [i for i in cps if i is not pn and i['bb'][al] >= b[al] - 5 and i['bb'][al + 3] <= b[al + 3] + 5 and i['bb'][2] >= b[2] - 5
               and i['bb'][5] <= b[5] + 5 and 0 <= ((i['bb'][ad] - tras) if sg_ > 0 else (tras - i['bb'][ad + 3])) <= 150]
        prs = sorted([i for i in atr if i['bb'][5] - i['bb'][2] <= 30 and i['bb'][al + 3] - i['bb'][al] >= 150], key=lambda i: i['bb'][2])
        lts = sorted([i for i in atr if i['bb'][al + 3] - i['bb'][al] <= 30 and i['bb'][5] - i['bb'][2] >= 300], key=lambda i: i['bb'][al])
        if len(prs) < 3 or len(lts) < 2: continue
        o0, o1 = lts[0]['bb'][al + 3], lts[-1]['bb'][al]
        vz = [(p0['bb'][5], p1['bb'][2]) for p0, p1 in zip(prs, prs[1:]) if p1['bb'][2] - p0['bb'][5] > 150]
        if not vz or o1 - o0 < 150: continue
        pi = pn['pecas'][0]; USINADOS[pi] = dict(u=(o0, o1), z=vz, al=al)
        cxs = []
        def sub(a0_, a1_, z0_, z1_):
            bb_ = list(b); bb_[al], bb_[al + 3], bb_[2], bb_[5] = a0_, a1_, z0_, z1_; cxs.append(bb_)
        sub(b[al], o0, b[2], b[5]); sub(o1, b[al + 3], b[2], b[5])
        zz = [b[2]] + [v for z_ in vz for v in z_] + [b[5]]
        for z0_, z1_ in zip(zz[0::2], zz[1::2]):
            if z1_ - z0_ > 0.5: sub(o0, o1, z0_, z1_)
        P[pi]['fq'] = [fq_ for c_ in cxs for fq_ in _caixa_fq(c_)]
        print('PAINEL USINADO:', pn['desc'], pn['dim'], '->', len(vz), 'vão(s)')
grupos = geo.agrupar_vistas2([w for w in paredes if not w.get('divisoria')])

# REGRA (ENGENHARIA seção 5): sequência espacial por tipo de ambiente. O caderno deve começar
# pelo grupo de parede que contém o elemento-âncora do ambiente (ex.: cozinha começa pela pia).
# Só rotaciona o PONTO DE PARTIDA da lista de grupos; a continuidade espacial entre eles
# continua vindo de geo.agrupar_vistas2 (não mexe na geometria nem no casamento XML x DXF).
_ANCORA_AMBIENTE = {
    'cozinha': r'\bpia\b|\bcuba\b',
    'varanda': r'\bpia\b|\bcuba\b',
    'gourmet': r'\bpia\b|\bcuba\b',
    'quarto': r'guarda[\s-]?roupa|roupeiro',
    'escritorio': r'bancada|mesa',
    'sala': r'\bpainel\b',
    # REGRA (João, 28/09/2026): banheiro e lavabo. Engenharia manda "leitura frontal" -- comeca
    # pelo elemento que ancora a parede frontal do sanitario (gabinete/cuba/pia). Cobre variacoes:
    # "banheiro", "banheiros", "wc", "bwc", "lavabo", "suite banheiro", "bh casal" etc.
    'banheiro': r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'lavabo':   r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'wc':       r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'bwc':      r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
}
def _ancora_regex(ambiente):
    amb_ = _norm(ambiente or '')
    return next((rx for chave, rx in _ANCORA_AMBIENTE.items() if chave in amb_), None)
_rx_ancora = _ancora_regex(cfg['dados'].get('ambiente'))
if _rx_ancora and grupos:
    _idx_ancora = next((k for k, g in enumerate(grupos)
                         if any(re.search(_rx_ancora, i['desc'], re.I) for w in g for i in PW[w]['itens'])), None)
    if _idx_ancora:   # já é 0 -> nada a fazer; None -> âncora não encontrada, mantém ordem atual
        grupos = grupos[_idx_ancora:] + grupos[:_idx_ancora]
        print(f"SEQUÊNCIA ESPACIAL: ambiente '{cfg['dados'].get('ambiente')}' -> início na parede com a âncora (grupo {_idx_ancora})")

_DIVW = [w['id'] for w in paredes if w.get('divisoria')]
nao_achados = [tuple(linha) for linha in PROJETO['diagnostico']['itens_nao_localizados']]

# REGRA (v35.3): itens que não são peças de mobiliário (ferragens, acessórios, kits) existem no XML
# mas NUNCA terão geometria no DXF. Filtrá-los antes da Regra 1 evita bloqueio falso.
# Critérios: (a) alguma dimensão ≤ 5mm (é acessório/ferragem); (b) nome indica acessório.
_RE_ACESS = re.compile(r'\bkit\b|\btapa[- ]?furo\b|\bcorredi[cç]a\b|\bmetalon\b|\bsuporte\s+fixa[cç][aã]o\b'
                        r'|\bdesliz\b|\bpuxador\b|\btrilho\b|\bdobradi[cç]a\b|\bparafuso\b'
                        r'|\bamortecedor\b|\bsapata\b|\bcantoneira\b|\brebite\b', re.I)
def _eh_acessorio(desc_, dim_):
    """True se o item é acessório/ferragem/fundo que não aparece no DXF."""
    if _RE_ACESS.search(desc_): return True
    try:
        vals = [float(v.replace(',', '.')) for v in dim_.split('x')]
        if any(v <= 5 for v in vals): return True              # dimensão ≤5mm = acessório
        # REGRA (João, 28/09/2026 - bloco 1): espessura <=25mm NÃO é critério de acessório.
        # Painel, tamponamento e frente têm 18/25mm; se não forem achados no DXF são FALTA real.
    except Exception: pass
    return False
_acessorios = [(d, dm) for d, dm in nao_achados if _eh_acessorio(d, dm)]
_faltando_real = [(d, dm) for d, dm in nao_achados if not _eh_acessorio(d, dm)]
if _acessorios:
    print(f'AVISO: {len(_acessorios)} acessório(s)/ferragem(ns) do XML sem geometria no DXF (normal, ignorados):')
    for _d, _dm in _acessorios: print(f'  - {_d}  {_dm}')

# REGRA 1 (v35.4): BLOQUEIO TOTAL apenas quando a incompatibilidade é significativa.
# Bloqueia somente quando AMBOS os limites são ultrapassados simultaneamente:
#   - mais de 3 peças reais faltando E mais de 10% do total.
# Isso evita falsos positivos em ambientes pequenos (poucos itens) e tolerará
# fundos/rodapés/tiras que o DXF frequentemente não exporta.
_REGRA1_MAX = 3; _REGRA1_PCT = 0.10
_pct = len(_faltando_real) / max(1, len(linhas))
if _faltando_real and (len(_faltando_real) > _REGRA1_MAX and _pct > _REGRA1_PCT):
    print('=' * 70, file=sys.stderr)
    print(f'ERRO CRITICO: {len(_faltando_real)} item(ns) do XML nao foram localizados no DXF.', file=sys.stderr)
    print(f'CADERNO NAO GERADO (Regra 1: Bloqueio Total).', file=sys.stderr)
    print(f'Ambiente: {cfg["dados"]["cliente"]} / {cfg["dados"]["ambiente"]}', file=sys.stderr)
    print('-' * 70, file=sys.stderr)
    print('ITENS FALTANDO NO DXF:', file=sys.stderr)
    for _d, _dm in _faltando_real:
        print(f'  - {_d}  {_dm}', file=sys.stderr)
    print('-' * 70, file=sys.stderr)
    print('Acao sugerida: reexportar XML+DXF do Promob, ou verificar se todas as pecas', file=sys.stderr)
    print('do XML foram exportadas no DXF (blocos aninhados / solidos 3D podem ter falhado).', file=sys.stderr)
    print('=' * 70, file=sys.stderr)
    raise SystemExit(2)
elif _faltando_real:
    print(f'AVISO: {len(_faltando_real)} peça(s) do XML não localizada(s) no DXF (abaixo do limiar de bloqueio):')
    for _d, _dm in _faltando_real: print(f'  - {_d}  {_dm}')

# vistas: liga cada grupo à imagem 3D do config pela peça de referência
V = []
livres = list(grupos)
for cv in cfg['vistas']:
    g = next((g for g in livres if any(cv['ref'] in f"{i['desc']} {i['dim']}" for w in g for i in PW[w]['itens'])), None)
    if g: livres.remove(g); V.append(dict(cv, paredes=sorted(g, key=lambda w: -len(PW[w]['itens']))))
letras = 'ABCDEFGHIJKL'
# REGRA (João): cada parede tem sua LETRA (A, B, C, D... em sequência; em cada L a parede maior primeiro).
# Parede PEQUENA (< PAREDE_PEQ ao longo da parede) vai junto com a parede grande do mesmo L:
#   listagem única com 3D angulado pegando as duas + cotas das duas lado a lado na mesma prancha.
# Paredes grandes = vista própria (3D frontal).
PAREDE_PEQ = 2500  # João: parede < 2,5 m vai junto com a vizinha do L (listagem na diagonal)
def _larg(w):
    ax = 1 if FV[PW[w]['key']][0] else 0
    return max(i['bb'][ax + 3] for i in PW[w]['itens']) - min(i['bb'][ax] for i in PW[w]['itens'])
_nl = len(V)
for g in livres:
    ws = sorted(g, key=lambda w: -_larg(w)); blocos = []
    for w in ws:
        if blocos and _larg(w) < PAREDE_PEQ and len(blocos[0]) < 2: blocos[0].append(w)
        else: blocos.append([w])
    for b in blocos:
        ls = [letras[_nl + k] for k in range(len(b))]; _nl += len(b)
        V.append(dict(letra=ls[0], letras=ls, img3d=None, paredes=b))
for wid in _DIVW:   # REGRA (v18): divisória ripada = bloco próprio no fim
    V.append(dict(letra=letras[_nl], letras=[letras[_nl]], img3d=None, paredes=[wid], divisoria=True)); _nl += 1
# REGRA (v22, planta do João): a vista da PERNA DO L vem logo DEPOIS da vista da parede dela (b -> c); letras em sequência
for v in [v for v in V if len(v['paredes']) == 1 and PW[v['paredes'][0]].get('perna_l')]:
    pai_ = PW[v['paredes'][0]]['pai']; V.remove(v)
    k_ = next((j for j, o in enumerate(V) if pai_ in o['paredes']), len(V) - 1)
    V.insert(k_ + 1, v)
_c = 0
for v in V:
    if v.get('img3d') is None and not v.get('ref'):
        v['letras'] = [letras[_c + k] for k in range(len(v['paredes']))]; v['letra'] = v['letras'][0]
    _c += len(v['paredes'])
for v in V:
    v.setdefault('letras', [v['letra'] + (str(j + 1) if len(v['paredes']) > 1 else '') for j in range(len(v['paredes']))])
    v['titulo'] = 'VISTA ' + v['letras'][0] if len(v['letras']) == 1 else 'VISTAS ' + ' E '.join(v['letras'])
    if v.get('divisoria'): v['titulo'] = PW[v['paredes'][0]].get('bloco') or 'DIVISÓRIA RIPADA'
    # REGRA (João): LISTAGEM sempre FRONTAL e POR PAREDE (só os móveis daquela parede); o bloco junta só as cotas.
    v['subs'] = [v] if len(v['paredes']) == 1 else [dict(letra=l_, letras=[l_], titulo='VISTA ' + l_, img3d=None, paredes=[w_]) for w_, l_ in zip(v['paredes'], v['letras'])]
VW = [s_ for v in V for s_ in v['subs']]

# REGRA (v33, João): SEM ASTERISCO. Item que o motor não localizou no DXF não é desenhado,
# logo não aparece na imagem frontal e, pela regra da peça escondida, não é listado.

# ---------------- geometria de elevação ----------------
def uu(x, y, f): return x * f[1] - y * f[0]

def area2(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2

def _tick(sh, x, y):
    sh.draw_line((x - 2.2, y + 2.2), (x + 2.2, y - 2.2))

def _txt(page, pos, s, fs, rotate=0, fundo=False):
    if fundo:
        tw = fz.get_text_length(s, 'helv', fs)
        r = fz.Rect(pos[0] - 0.8, pos[1] - fs * 0.8, pos[0] + tw + 0.8, pos[1] + 1) if not rotate else fz.Rect(pos[0] - fs * 0.8, pos[1] - tw - 0.8, pos[0] + 1, pos[1] + 0.8)
        page.draw_rect(r, color=None, fill=(1, 1, 1))
    page.insert_text(pos, s, fontname='helv', fontsize=fs, rotate=rotate)

def cadeia_h(page, us, yl, yobj, X, fs=6.5, fundo=False):
    us = _uniq(us)
    if len(us) < 2: return
    sh = page.new_shape()
    for u in us:
        sh.draw_line((X(u), yobj), (X(u), yl + (2.5 if yl < yobj else -2.5))); sh.finish(color=CR, width=0.25)
    sh.draw_line((X(us[0]), yl), (X(us[-1]), yl)); sh.finish(color=CR, width=0.5)
    for u in us: _tick(sh, X(u), yl)
    sh.finish(color=CR, width=0.6); sh.commit()
    # REGRA (ajuste, item 7 - João): linha cruzar linha é normal, NÃO mexe nisso. O que não pode é
    # o NÚMERO ficar em cima de uma linha (a própria ou outra cota cruzando ali) - por isso o
    # fundo=True é forçado (apaga a linha embaixo do texto) independente do que o chamador passar.
    # Mantém também o desvio se dois números vizinhos colidirem entre si (vão estreito).
    _oc_h = []
    for a, b in zip(us, us[1:]):
        s = fmt(b - a); tw = fz.get_text_length(s, 'helv', fs)
        cx = (X(a) + X(b)) / 2; ty = yl - 1.8
        for _tent in range(3):
            r = fz.Rect(cx - tw / 2 - 1, ty - fs, cx + tw / 2 + 1, ty + 1.5)
            if not any(r.intersects(o_) for o_ in _oc_h): break
            ty += (fs + 2.2) * (1 if yl < yobj else -1)
        _oc_h.append(r)
        _txt(page, (cx - tw / 2, ty), s, fs, fundo=True)

def cadeia_v(page, zs, xl, xobj, Y, fs=6.5, esquerda=True, fundo=False):
    zs = _uniq(zs)
    if len(zs) < 2: return
    sh = page.new_shape()
    for z in zs:
        if xobj is not None:
            sh.draw_line((xobj, Y(z)), (xl + (2.5 if xl > xobj else -2.5), Y(z))); sh.finish(color=CR, width=0.25)
    sh.draw_line((xl, Y(zs[0])), (xl, Y(zs[-1]))); sh.finish(color=CR, width=0.5)
    for z in zs: _tick(sh, xl, Y(z))
    sh.finish(color=CR, width=0.6); sh.commit()
    # REGRA (ajuste, item 7 - cruzamento de linhas/letras): mesma lógica do cadeia_h - texto de
    # cota vertical não pode invadir o texto vizinho; desloca lateralmente se colidir. A posição
    # das linhas/tracinhos das cotas não muda.
    _oc_v = []
    for a, b in zip(zs, zs[1:]):
        s = fmt(b - a); tw = fz.get_text_length(s, 'helv', fs)
        cy = (Y(a) + Y(b)) / 2; tx = xl - 1.8
        for _tent in range(3):
            r = fz.Rect(tx - fs, cy - tw / 2 - 1, tx + 1.5, cy + tw / 2 + 1)
            if not any(r.intersects(o_) for o_ in _oc_v): break
            tx += (fs + 2.2) * (1 if xobj is not None and xl > xobj else -1)
        _oc_v.append(r)
        _txt(page, (tx, cy + tw / 2), s, fs, rotate=90, fundo=True)   # ajuste item 7: fundo sempre ligado, apaga linha embaixo do número

def _uniq(vals, tol=2.0):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol: out.append(v)
    return out

# nível do piso pronto: placa de piso do DXF (grande, fina, no chão). Cotas de altura partem daqui.
CORTE = 1100
def _eh_ripa(it):
    try: d_ = sorted(float(x) for x in re.findall(r'[\d.]+', it['dim'].replace(',', '.'))[:3])
    except Exception: return False
    return len(d_) == 3 and d_[0] <= 30 and 60 <= d_[1] <= 200 and d_[2] >= 500

def cotar_divisoria(page, G, ox, fy, k):
    # REGRA (v18, PDF do João): divisória ripada NÃO cota ripa por ripa. Cota: largura total + peças laterais,
    # UMA ripa e UM vão (amostra), altura total e as alturas das partes (bases, painel, travessas).
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']; u0, u1 = G['umin'], G['umax']; ztop_ = max(b['z1'] for b in bx)
    rip = sorted([b for b in bx if _eh_ripa(b['it'])], key=lambda b: b['u0'])
    alt = [b for b in bx if not _eh_ripa(b['it']) and (b['z1'] - b['z0']) >= 0.8 * ztop_]
    cadeia_h(page, [u0, u1] + [v for b in alt for v in (b['u0'], b['u1'])], fy + 14, fy + 2, X)
    cadeia_h(page, [u0, u1], Y(ztop_) - 14, Y(ztop_) - 2, X)
    # REGRA (v18b): o montador precisa da distância entre as ripas -> cota TODOS os vãos, em cada faixa de ripas
    # (embaixo e em cima do painel), com as setas por dentro; a espessura da ripa sai uma vez só.
    faixas = sorted({(round(b['z0'] / 50), round(b['z1'] / 50)) for b in rip if b['z1'] - b['z0'] >= 300})
    feitas = []
    for f0, f1 in faixas:
        zc = (f0 + f1) * 25
        if any(abs(zc - z_) < 250 for z_ in feitas): continue
        estreitas = [b for b in bx if b['z0'] <= zc <= b['z1'] and (b['u1'] - b['u0']) <= 200]
        ed = _uniq(sorted(v for b in estreitas for v in (b['u0'], b['u1'])), 1.0)
        if len(ed) < 4: continue
        feitas.append(zc); yl = Y(zc)
        sh = page.new_shape(); sh.draw_line((X(ed[0]), yl), (X(ed[-1]), yl)); sh.finish(color=CR, width=0.4)
        for u_ in ed: _tick(sh, X(u_), yl)
        sh.finish(color=CR, width=0.5); sh.commit()
        ripa_ok = False
        for a_, c_ in zip(ed, ed[1:]):
            t_ = fmt(c_ - a_); tw = fz.get_text_length(t_, 'helv', 5)
            if (c_ - a_) >= 40 and (c_ - a_) * k >= tw + 1:
                _txt(page, ((X(a_) + X(c_)) / 2 - tw / 2, yl - 1.5), t_, 5, fundo=True)
            elif not ripa_ok and (c_ - a_) < 40:
                _txt(page, (X(c_) + 1, yl + 6), t_, 5, fundo=True); ripa_ok = True
    hor = [b for b in bx if not _eh_ripa(b['it']) and (b['u1'] - b['u0']) >= 0.4 * (u1 - u0)]
    zs = [ZP, ztop_] + [v for b in hor for v in (b['z0'], b['z1'])]
    cadeia_v(page, zs, X(u1) + 16, X(u1) + 2, Y)
    cadeia_v(page, [ZP, ztop_], X(u0) - 16, X(u0) - 2, Y)

def _u_de(G, c, al):   # coordenada do DXF (eixo al) -> coordenada u da elevação
    f = G['f']; return c * (f[1] if al == 0 else -f[0])

def cotar_bloco(page, G, ox, fy, k):
    # REGRA (v26): BLOCO DE PAINÉIS (painel com nichos). Cota: largura total, VÃOS USINADOS do painel (largura e altura
    # de cada vão e das faixas entre eles), altura do painel a partir do piso pronto e até o teto (painel do teto).
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']; f = G['f']; ad = 0 if f[0] else 1
    fin = [b for b in bx if b['it']['bb'][ad + 3] - b['it']['bb'][ad] <= 30]
    pn = max(fin or bx, key=lambda b: (b['u1'] - b['u0']) * (b['z1'] - b['z0']))
    zt = max(b['z1'] for b in bx); u0, u1 = G['umin'], G['umax']
    us_, zs_ = [pn['u0'], pn['u1']], [pn['z0'], pn['z1']]
    ui = USINADOS.get(pn['it']['pecas'][0])
    if ui:
        us_ += [_u_de(G, c, ui['al']) for c in ui['u']]; zs_ += [v for z_ in ui['z'] for v in z_]
    cadeia_h(page, us_, Y(pn['z0']) + 14, Y(pn['z0']) + 2, X, fundo=True)
    cadeia_h(page, [u0, u1], Y(zt) - 14, Y(zt) - 2, X)
    xr = X(max(pn['u1'], u1))
    cadeia_v(page, zs_, xr + 14, X(pn['u1']) + 2, Y)
    cadeia_v(page, [ZP, pn['z0'], pn['z1'], zt], xr + 30, xr + 2, Y)

def cotar(page, G, ox, fy, k):
    if G['w'].get('bloco'): return cotar_bloco(page, G, ox, fy, k)
    if G['w'].get('divisoria'): return cotar_divisoria(page, G, ox, fy, k)
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']
    mb = [b for b in bx if b['it']['tipo'] == 'mod'] or bx
    mu0, mu1 = min(b['u0'] for b in mb), max(b['u1'] for b in mb)
    cad = mb
    sup = [b for b in cad if b['z1'] > CORTE]
    inf = [b for b in cad if b['z0'] < CORTE]
    ytop = Y(G['zmax'])
    if sup:
        us = [v for b in sup for v in (b['u0'], b['u1'])]
        cadeia_h(page, us, ytop - 13, ytop - 2, X)
        if len(_uniq(us)) > 2: cadeia_h(page, [min(us), max(us)], ytop - 26, ytop - 2, X)
    if inf:
        us = [v for b in inf for v in (b['u0'], b['u1'])]
        cadeia_h(page, us, fy + 13, fy + 2, X)
        if len(_uniq(us)) > 2: cadeia_h(page, [min(us), max(us)], fy + 26, fy + 2, X)
    xr, xl = X(G['umax']), X(G['umin'])
    vr, vl = X(G.get('vmax', G['umax'])), X(G.get('vmin', G['umin']))   # REGRA (v15): cotas por FORA das paredes
    dir_ = [b for b in mb if b['u1'] >= G['umax'] - 700]
    esq = [b for b in mb if b['u0'] <= G['umin'] + 700]
    # móvel longe da parede lateral (> 600 mm): a cadeia fica encostada no móvel, não atravessa a parede vazia
    if vr - xr > 600 * k: vr = xr
    if xl - vl > 600 * k: vl = xl
    cadeia_v(page, [ZP] + [v for b in dir_ for v in (b['z0'], b['z1'])], vr + 14, xr + 2, Y)
    cadeia_v(page, [ZP] + [v for b in esq for v in (b['z0'], b['z1'])], vl - 14, xl - 2, Y)
    cadeia_v(page, [ZP, max(b['z1'] for b in mb)], vl - 28, xl - 2, Y)
    # REGRA (João): cotas INTERNAS dentro do móvel, vão por vão.
    #  - horizontal: largura livre entre lateral/divisória/divisória/lateral
    #  - vertical: altura livre entre prateleiras (de uma prateleira à outra, onde entram gavetas etc.)
    f_ = G['f']
    prof = lambda bb: (bb[3] - bb[0]) if f_[0] else (bb[4] - bb[1])
    for b in bx:
        it = b['it']
        if it['tipo'] != 'mod' or b['z1'] - b['z0'] < 350: continue
        vert, hor = [], []
        for pi in it['pecas']:
            bb = P[pi]['bb']; pu0, pz0, pu1, pz1 = geo.caixa_elev(bb, G['f'])
            if prof(bb) < 150: continue                      # portas, frentes, tamponamentos, ferragens
            if pu1 - pu0 <= 30 and pz1 - pz0 >= 300: vert.append((pu0, pu1))
            elif 12 <= pz1 - pz0 <= 30 and pu1 - pu0 >= 150: hor.append((pu0, pz0, pu1, pz1))
        vert = sorted(vert)
        vaos = [(a[1], c[0]) for a, c in zip(vert, vert[1:]) if c[0] - a[1] > 100]
        for cu0, cu1 in vaos:
            larg = cu1 - cu0
            niv = sorted((z0_, z1_) for u0_, z0_, u1_, z1_ in hor if u0_ <= cu0 + 10 and u1_ >= cu1 - 10)
            gaps = [(a[1], c[0]) for a, c in zip(niv, niv[1:]) if c[0] - a[1] > 40]
            xv = X(cu0 + larg * 0.5)
            for g0, g1 in gaps: cadeia_v(page, [g0, g1], xv, None, Y, fs=5.5, fundo=True)
            zt = (gaps[-1][1] if gaps else b['z1']) - 70
            cadeia_h(page, [cu0, cu1], Y(zt), Y(zt), X, fs=5.5, fundo=True)

def _desenho2d(page, faces, XY):
    """REGRA (v16, João): cotas 2D (frontal e lateral) com as MESMAS cores e TEXTURAS do 3D (madeirado com veio).
    Chapa 1830 x 2750 mm, veio no sentido do comprimento da peça. Sem Pillow/textura = cor lisa (vetor)."""
    its = []
    for f_ in faces:
        pts, cor, ft = f_[1], f_[2], f_[3]
        q = [XY(a, b) for a, b in pts]
        if area2(q) < 0.15: continue
        its.append((q, cor, ft, f_[4] if len(f_) > 4 else None, f_[5] if len(f_) > 5 else 0, pts))
    if not its: return
    if _Im is None or not cfg.get('textura', True) or not any(textura(m_) for _, _, _, m_, _, _ in its if m_):
        sh = page.new_shape()
        for q, cor, ft, _, _, _ in its:
            sh.draw_polyline(q + [q[0]]); sh.finish(color=cor, fill=cor, width=0.45, closePath=True)
            if any(ft):
                for (a_, b_), f_ in zip(zip(q, q[1:] + q[:1]), ft):
                    if f_: sh.draw_line(a_, b_)
                sh.finish(color=(0.2, 0.2, 0.2), width=0.3, closePath=False)
        sh.commit(); return
    R = fz.Rect(min(x for q in [i[0] for i in its] for x, _ in q), min(y for q in [i[0] for i in its] for _, y in q),
                max(x for q in [i[0] for i in its] for x, _ in q), max(y for q in [i[0] for i in its] for _, y in q)) & page.rect
    if R.is_empty: return
    s_ = 250 / 72.0; W_ = max(1, int(R.width * s_)); H_ = max(1, int(R.height * s_))
    img = _Im.new('RGBA', (W_, H_), (0, 0, 0, 0)); dr = _ImD.Draw(img)
    for q, cor, ft, mat, pc, pts in its:
        Q = [((x - R.x0) * s_, (y - R.y0) * s_) for x, y in q]
        tex = textura(mat) if mat else None
        x0_ = int(max(0, min(a for a, _ in Q))); y0_ = int(max(0, min(b for _, b in Q)))
        x1_ = int(min(W_, max(a for a, _ in Q) + 1)); y1_ = int(min(H_, max(b for _, b in Q) + 1))
        if tex is not None and x1_ - x0_ >= 3 and y1_ - y0_ >= 3:
            Lu = max(a for a, _ in pts) - min(a for a, _ in pts); Lz = max(b for _, b in pts) - min(b for _, b in pts)
            sx_, sy_ = tex.width / CHAPA_L, tex.height / CHAPA_A
            deit = Lu > Lz                                   # peça deitada: veio na horizontal
            Lw, Lh = (Lz, Lu) if deit else (Lu, Lz)
            pw = max(2, min(tex.width, int(Lw * sx_))); ph = max(2, min(tex.height, int(Lh * sy_)))
            ox_ = (pc * 137) % max(1, tex.width - pw + 1); oy_ = (pc * 71) % max(1, tex.height - ph + 1)
            tile = tex.crop((ox_, oy_, ox_ + pw, oy_ + ph))
            if deit: tile = tile.rotate(90, expand=True)
            tile = tile.resize((x1_ - x0_, y1_ - y0_)).convert('RGBA')
            mask = _Im.new('L', tile.size, 0); _ImD.Draw(mask).polygon([(a - x0_, b - y0_) for a, b in Q], fill=255)
            img.paste(tile, (x0_, y0_), mask)
        else:
            dr.polygon(Q, fill=tuple(int(255 * v) for v in cor) + (255,))
        for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
            if fl_: dr.line([a_, b_], fill=(50, 50, 50, 255), width=max(1, int(0.3 * s_)))
    import io as _io
    bio = _io.BytesIO(); img.save(bio, format='PNG', optimize=True)
    page.insert_image(R, stream=bio.getvalue())

# ---------------- pranchas ----------------
lay = fz.open(cfg['layout'])
def nova_prancha(doc, n, titulo):
    p = doc.new_page(width=lay[0].rect.width, height=lay[0].rect.height)
    p.show_pdf_page(p.rect, lay, 0)
    p.draw_rect(fz.Rect(300, 117, 540, 141), color=None, fill=BRANCO)
    p.draw_rect(fz.Rect(712, 52, 816, 96), color=None, fill=BRANCO)
    d = cfg['dados']
    for x, y, t in ((224, 33, d['cliente']), (234, 59, d['ambiente']), (285, 85, d['projetista']), (239, 111, d['arquiteta'])):
        p.insert_text((x, y), t, fontname='hebo', fontsize=10)
    p.insert_text((419.5 - fz.get_text_length(titulo, 'hebo', 16) / 2, 135), titulo, fontname='hebo', fontsize=16, color=RED)
    p.insert_text((764 - fz.get_text_length('PRANCHA', 'hebo', 18) / 2, 62), 'PRANCHA', fontname='hebo', fontsize=18)
    s = '%02d' % n
    p.insert_text((764 - fz.get_text_length(s, 'hebo', 18) / 2, 85), s, fontname='hebo', fontsize=18)
    return p

def tabela(p, linhas, x0, y0, largura=248, nums=None):
    fs, lh = 7.2, 10.5
    cols = [x0, x0 + 24, x0 + 168, x0 + largura]
    sh = p.new_shape()
    sh.draw_rect(fz.Rect(x0, y0, x0 + largura, y0 + lh)); sh.finish(color=PRETO, fill=(1, 1, 0), width=0.5)
    for i in range(len(linhas)):
        r = fz.Rect(x0, y0 + lh * (i + 1), x0 + largura, y0 + lh * (i + 2))
        sh.draw_rect(r); sh.finish(color=PRETO, fill=(0.85, 0.85, 0.85) if i % 2 else BRANCO, width=0.4)
    for c in cols[1:-1]:
        sh.draw_line((c, y0), (c, y0 + lh * (len(linhas) + 1))); sh.finish(color=PRETO, width=0.4)
    sh.commit()
    for t, a, b in (('Item', cols[0], cols[1]), ('Descrição', cols[1], cols[2]), ('Dimensão', cols[2], cols[3])):
        p.insert_text(((a + b) / 2 - fz.get_text_length(t, 'helv', fs) / 2, y0 + lh - 2.8), t, fontname='helv', fontsize=fs)
    for i, (d, dm, m) in enumerate(linhas, 1):
        y = y0 + lh * (i + 1) - 2.8
        s = str(nums[i - 1] if nums else i) + m
        p.insert_text(((cols[0] + cols[1]) / 2 - fz.get_text_length(s, 'helv', fs) / 2, y), s, fontname='helv', fontsize=fs)
        while fz.get_text_length(d, 'helv', fs) > cols[2] - cols[1] - 6: d = d[:-1]
        p.insert_text((cols[1] + 3, y), d, fontname='helv', fontsize=fs)
        p.insert_text(((cols[2] + cols[3]) / 2 - fz.get_text_length(dm, 'helv', fs) / 2, y), dm, fontname='helv', fontsize=fs)
    return y0 + lh * (len(linhas) + 1)

def escala_para(larg_mm, alt_mm, W, H, cheio=False):
    for S in (ESC_COTA if cheio else ESC):
        k = MM / S
        lim = 1.0 if cheio else 0.75 if S < 25 else 1.0   # cotas (v15): ocupa a prancha toda
        if larg_mm * k <= W * lim and alt_mm * k <= H * lim: return S, k
    return ESC[-1], MM / ESC[-1]

import math
def desenhar(page, G, ox, fy, k, baloes=None, letra=None):
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    _desenho2d(page, G['faces'], lambda u, z: (X(u), Y(z)))
    sh = page.new_shape()
    sh.draw_line((X(G.get('vmin', G['umin'])) - 6, fy), (X(G.get('vmax', G['umax'])) + 6, fy)); sh.finish(color=PRETO, width=0.9)
    sh.commit()


# ===== REGRAS FIXAS (João, 28/09/2026 - skill P1/P2): LISTAGEM = 3D FRONTAL, PORTAS FECHADAS, COM PAREDES (referência de localização)
#       | COTAS = 2D FRONTAL, MÓVEL ISOLADO (sem paredes, piso, pedra, eletros e móveis de outras paredes), SEM PORTAS, EM ESCALA, DENTRO DO QUADRO =====
def caixa_faces(b):
    x0, y0, z0, x1, y1, z1 = b
    V_ = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return [[V_[a] for a in fc] for fc in [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]]
def paredes_recorte(R):
    out = []
    for p_ in PAREDES_PECAS:
        b = p_['bb']; c = [max(b[k], R[k]) for k in range(3)] + [min(b[k + 3], R[k + 3]) for k in range(3)]
        if all(c[k + 3] - c[k] > 1 for k in range(3)): out.append(c)
    return out

def _vista_limites(w, f, umin_, umax_, zmax_):
    """REGRA (v15): limites da elevação 2D = parede a parede (face interna da parede lateral + espessura) e piso ao teto.
    Sem parede lateral a até 4 m: abre 300 mm além do móvel. Teto = maior altura das paredes reais (até 3,2 m)."""
    axd = 0 if f[0] else 1; sg = f[axd]; pl = w['plano']
    cx = []
    for p_ in PAREDES_PECAS + PAR_DXF: cx.append(p_['bb'])
    for p_ in MALHA_PAR:
        for fc in p_['faces']:
            cx.append([min(v[0] for v in fc), min(v[1] for v in fc), min(v[2] for v in fc), max(v[0] for v in fc), max(v[1] for v in fc), max(v[2] for v in fc)])
    esq, dir_, esp_e, esp_d, tetos = None, None, 150, 150, []; fundo_ = False
    for b in cx:
        if b[5] - b[2] < 1500: continue
        d0, d1 = sorted(((pl - b[axd]) * sg, (pl - b[axd + 3]) * sg))
        if d1 < -30 or d0 > 800: continue      # só paredes na faixa dos móveis (fundo até 800 mm à frente)
        u0, z0, u1, z1 = geo.caixa_elev(b, f)
        if u1 > umin_ + 20 and u0 < umax_ - 20: tetos.append(z1); fundo_ = True; continue
        if u0 >= umax_ - 20 and u0 - umax_ <= 4000 and (dir_ is None or u0 < dir_): dir_ = u0; esp_d = min(max(u1 - u0, 60), 250) if u1 - u0 > 1 else 150
        if u1 <= umin_ + 20 and umin_ - u1 <= 4000 and (esq is None or u1 > esq): esq = u1; esp_e = min(max(u1 - u0, 60), 250) if u1 - u0 > 1 else 150
        tetos.append(z1)
    vmin_ = esq - esp_e if esq is not None else umin_ - 300
    vmax_ = dir_ + esp_d if dir_ is not None else umax_ + 300
    ztop_ = min(max(tetos), 3200) if tetos else zmax_ + 150
    if not fundo_ and zmax_ <= 1200: ztop_ = zmax_ + 300   # REGRA (v31): ilha/península baixa sem parede atrás -> desenho grande
    return vmin_, vmax_, max(ztop_, zmax_ + 50)

def _eh_porta(b, mb, w):
    # REGRA (João, 28/09/2026 - bloco cotas): ÚNICA definição geométrica de porta/frente/basculante/porta de correr.
    # b = caixa da chapa, mb = caixa do módulo. Porta = chapa fina (<= 30 mm na profundidade) na FRENTE do módulo
    # (até 150 mm à frente, 80 mm para dentro - pega porta de correr no trilho interno), dentro da largura/altura do
    # módulo (folga 60 mm). NÃO é porta: chapa dentro da caixa que vai exatamente da base ao topo do módulo e ocupa
    # pelo menos metade da largura (lateral/fechamento do próprio módulo, ex.: braço do canto L).
    # Usada por tem_porta (nicho), _portas (3D sem portas) e _portas_cota (cotas).
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    perto = lambda bb: min(bb[ad] * sg_, bb[ad + 3] * sg_)
    fr = perto(mb)
    if b[ad + 3] - b[ad] > 30 or (b[al + 3] - b[al]) < 100 or (b[5] - b[2]) < 60: return False
    if not (fr - 150 <= perto(b) <= fr + 80): return False
    if b[al] < mb[al] - 60 or b[al + 3] > mb[al + 3] + 60 or b[2] < mb[2] - 60 or b[5] > mb[5] + 60: return False
    if perto(b) >= fr - 1 and abs(b[2] - mb[2]) <= 2 and abs(b[5] - mb[5]) <= 2 and (b[al + 3] - b[al]) >= 0.5 * (mb[al + 3] - mb[al]):
        return False
    return True

def _portas_cota(w):
    # REGRA (v31 + bloco cotas 28/09/2026): COTAS = SEM PORTAS. Usa a definição única _eh_porta.
    # Porta avulsa do XML (POR_) fica presa ao item mais próximo (às vezes um painel): sai também.
    out = {pi for it in w['itens'] for pi in it['pecas'] if pi in PORTAS_XML}
    for m in [i for i in w['itens'] if i['tipo'] == 'mod']:
        for pi in m['pecas']:
            if _eh_porta(P[pi]['bb'], m['bb'], w): out.add(pi)
    return out

def geom_parede(w):
    f = FV[w['key']]; faces = []; boxes = []
    dep = lambda vs: sum(v[0] * f[0] + v[1] * f[1] for v in vs) / len(vs)
    _pc = _portas_cota(w)
    for it in w['itens']:
        cor = MADEIRA if it['tipo'] == 'comp' else BRANCO
        for pi in it['pecas']:
            if pi in _pc: continue   # porta/frente não aparece nas cotas
            sd_ = sorted(P[pi]['dim'])
            if sd_[1] < 50 or sd_[0] > 60: continue  # REGRA: só MDF (sem dobradiças/suportes/cabideiros)
            for uq, nv, ft in P[pi]['fq']:
                faces.append((dep(uq), [(uu(v[0], v[1], f), v[2]) for v in uq], P[pi].get('rgb', cor), ft, P[pi].get('mat'), pi))
        u0, z0, u1, z1 = geo.caixa_elev(it['bb'], f)
        boxes.append(dict(it=it, u0=u0, z0=z0, u1=u1, z1=z1))
    # REGRA (João, 28/09/2026 - skill P2): cota = MÓVEL ISOLADO. Fica SÓ o conjunto de móveis listados da vista:
    # sem paredes, piso, janelas, portas do cômodo, pedra, eletros e móveis de outras paredes (substitui a v15
    # "a cota não elimina as paredes"). Enquadramento = o próprio conjunto + 100 mm de cada lado.
    umin_ = min(b['u0'] for b in boxes); umax_ = max(b['u1'] for b in boxes); zmax_ = max(b['z1'] for b in boxes)
    vmin_, vmax_, ztop_ = umin_ - 100, umax_ + 100, zmax_ + 50
    faces.sort(key=lambda t: -t[0])
    _cena = cena_render.construir(PROJETO, 'cota', w['itens'], [w['id']], portas_geometricas=_pc)
    return dict(w=w, f=f, faces=faces, boxes=boxes, umin=umin_, umax=umax_, zmax=zmax_, vmin=vmin_, vmax=vmax_, ztop=ztop_, cena=_cena)

def _ordem_pecas(fcs, bbs, cam):
    # Ordem de desenho POR PEÇA (pintor): A antes de B quando B está na frente de A.
    # Frente/trás pelo eixo de menor sobreposição das caixas (dobradiça/cabideiro atrás da porta fica atrás).
    import heapq
    fundo = sorted([f_ for f_ in fcs if f_[5] < 0], key=lambda t: -t[1])
    por = {}
    for f_ in fcs:
        if f_[5] >= 0: por.setdefault(f_[5], []).append(f_)
    ids = list(por)
    tela = {}
    for i_ in ids:
        xs_ = [x for f_ in por[i_] for x, _ in f_[2]]; ys_ = [y for f_ in por[i_] for _, y in f_[2]]
        tela[i_] = (min(xs_), min(ys_), max(xs_), max(ys_))
    ctr = {i_: [(bbs[i_][k] + bbs[i_][k + 3]) / 2 for k in range(3)] for i_ in ids}
    dist = {i_: math.dist(ctr[i_], cam) for i_ in ids}
    def frente(a, b):  # 1: a na frente de b | -1: b na frente de a | 0: indefinido
        A, B = bbs[a], bbs[b]
        ov = sorted((min(A[k + 3], B[k + 3]) - max(A[k], B[k]), k) for k in range(3))
        for o_, k in ov:
            ca, cb = ctr[a][k], ctr[b][k]
            if abs(ca - cb) < 1e-6: continue
            if cam[k] > max(ca, cb) or cam[k] < min(ca, cb):
                return 1 if abs(cam[k] - ca) < abs(cam[k] - cb) else -1
            if o_ > 0.5: break
        return 0
    depois = {i_: [] for i_ in ids}; grau = {i_: 0 for i_ in ids}
    for n_, a in enumerate(ids):
        ta = tela[a]
        for b in ids[n_ + 1:]:
            tb = tela[b]
            if ta[2] <= tb[0] or tb[2] <= ta[0] or ta[3] <= tb[1] or tb[3] <= ta[1]: continue
            r_ = frente(a, b)
            if r_ > 0: depois[b].append(a); grau[a] += 1
            elif r_ < 0: depois[a].append(b); grau[b] += 1
    hp = [(-dist[i_], i_) for i_ in ids if grau[i_] == 0]; heapq.heapify(hp)
    feito = set(); out = list(fundo)
    while len(feito) < len(ids):
        if not hp:
            i_ = max((j for j in ids if j not in feito), key=lambda j: dist[j]); grau[i_] = 0
        else: _, i_ = heapq.heappop(hp)
        if i_ in feito: continue
        feito.add(i_); out += sorted(por[i_], key=lambda t: -t[1])
        for j in depois[i_]:
            grau[j] -= 1
            if grau[j] == 0 and j not in feito: heapq.heappush(hp, (-dist[j], j))
    return out

# REGRA (João): a imagem da textura = UMA CHAPA de MDF de 1830 mm (largura) x 2750 mm (altura, sentido do veio).
# Cada peça usa o pedaço da chapa proporcional ao seu tamanho (peça maior que a chapa repete a chapa).
CHAPA_L, CHAPA_A = 1830.0, 2750.0
def _persp(dst, src_):
    # coeficientes PIL PERSPECTIVE: saída (dst) -> entrada (src_)
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src_):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return _np.linalg.solve(_np.array(A, float), _np.array(B, float)).tolist()

def _raster3d(page, rect, fcs, T, pmat, dpi=170):
    s_ = dpi / 72.0; W_ = max(1, int(rect.width * s_)); H_ = max(1, int(rect.height * s_))
    img = _Im.new('RGB', (W_, H_), (255, 255, 255)); dr = _ImD.Draw(img)
    px = lambda x, y: ((T(x, y)[0] - rect.x0) * s_, (T(x, y)[1] - rect.y0) * s_)
    for f_ in fcs:
        q, c_, ft, pc, vs, fs_ = f_[2], f_[3], f_[4], f_[5], f_[6], f_[7]
        Q = [px(x, y) for x, y in q]
        if area2(Q) < 0.5: continue
        tex = textura(pmat.get(pc)) if pc is not None and pc >= 0 and len(vs) == 4 else None
        x0_ = int(max(0, min(a for a, _ in Q))); y0_ = int(max(0, min(b for _, b in Q)))
        x1_ = int(min(W_, max(a for a, _ in Q) + 1)); y1_ = int(min(H_, max(b for _, b in Q) + 1))
        if tex is not None and x1_ - x0_ >= 3 and y1_ - y0_ >= 3:
            L1 = math.dist(vs[0], vs[1]); L2 = math.dist(vs[0], vs[3])
            sx_, sy_ = tex.width / CHAPA_L, tex.height / CHAPA_A   # px por mm da chapa
            # veio (altura da chapa) acompanha o lado mais comprido da peça
            if L1 >= L2: corners = [vs[0], vs[3], vs[2], vs[1]]; Lw, Lh = L2, L1
            else: corners = [vs[0], vs[1], vs[2], vs[3]]; Lw, Lh = L1, L2
            pw = max(2, int(Lw * sx_)); ph = max(2, int(Lh * sy_))
            if pw <= tex.width and ph <= tex.height:
                ox_ = (pc * 137) % max(1, tex.width - pw + 1); oy_ = (pc * 71) % max(1, tex.height - ph + 1)   # pedaço da chapa varia por peça
                tile = tex.crop((ox_, oy_, ox_ + pw, oy_ + ph))
            else:
                tile = _Im.new('RGB', (pw, ph))
                for ty in range(0, ph, tex.height):
                    for tx in range(0, pw, tex.width): tile.paste(tex, (tx, ty))
            if max(pw, ph) > 1400: tile = tile.resize((max(2, pw * 1400 // max(pw, ph)), max(2, ph * 1400 // max(pw, ph)))); pw, ph = tile.size
            if fs_ < 0.999: tile = tile.point(lambda v: int(v * fs_))
            iq = [q[vs.index(c3_)] for c3_ in corners]
            dst = [(px(*p2)[0] - x0_, px(*p2)[1] - y0_) for p2 in iq]
            try:
                co = _persp(dst, [(0, 0), (pw, 0), (pw, ph), (0, ph)])
                patch = tile.transform((x1_ - x0_, y1_ - y0_), _Im.PERSPECTIVE, co, _Im.BILINEAR)
                mask = _Im.new('L', patch.size, 0); _ImD.Draw(mask).polygon([(a - x0_, b - y0_) for a, b in Q], fill=255)
                img.paste(patch, (x0_, y0_), mask)
            except Exception:
                dr.polygon(Q, fill=tuple(int(255 * v) for v in c_))
        else:
            dr.polygon(Q, fill=tuple(int(255 * v) for v in c_))
        for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
            if fl_: dr.line([a_, b_], fill=(50, 50, 50), width=max(1, int(0.35 * s_)))
    import io as _io
    bio = _io.BytesIO(); img.save(bio, format='JPEG', quality=88)
    page.insert_image(rect, stream=bio.getvalue())






# ===== PUXADORES (v23, João): o DXF do Promob NÃO traz o puxador; o motor GERA pela regra =====
# Tipo/medida/cor = item "Puxador..." do XML (ex.: Linear Pino Champagne 200 x 15,8 x 37,5). Puxador de perfil/cava/aba = sem barra.
# Porta/frente = chapa fina na frente do módulo (geometria). Porta de giro: puxador VERTICAL do lado OPOSTO às dobradiças
# (dobradiças do DXF), 40 mm da borda; alto (armário) na altura da mão (~1,05 m), balcão perto do topo, aéreo perto de baixo.
# Gaveta/basculante (mais larga que alta): HORIZONTAL centrado, perto do topo (aéreo: perto de baixo).
PUX_TIPO = PROJETO['xml']['puxador_tipo']
_DOBR = [p_ for p_ in P if (lambda d: 12 <= d[0] <= 32 and 40 <= d[1] <= 65 and 65 <= d[2] <= 95)(sorted(p_['dim']))]
def _gerar_puxadores():
    out = []
    if not PUX_TIPO: return out
    L_ = PUX_TIPO['L']; ja = set()
    for w in paredes:
        f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
        perto = lambda bb: min(bb[ad] * sg_, bb[ad + 3] * sg_)
        for m in w['itens']:
            if m['tipo'] != 'mod': continue
            mb = m['bb']; fr = perto(mb)
            for p_ in P:
                b = p_['bb']
                if p_['i'] in ja or b[ad + 3] - b[ad] > 30 or (b[al + 3] - b[al]) < 100 or (b[5] - b[2]) < 100: continue
                if not (fr - 40 <= perto(b) <= fr + 5): continue
                if b[al] < mb[al] - 30 or b[al + 3] > mb[al + 3] + 30 or b[2] < mb[2] - 30 or b[5] > mb[5] + 30: continue
                ja.add(p_['i'])
                du, dz = b[al + 3] - b[al], b[5] - b[2]
                face = b[ad] if sg_ > 0 else b[ad + 3]; sai = -sg_     # lado de fora da porta
                if dz >= du:   # porta de giro
                    hs = [h for h in _DOBR if b[al] - 40 <= (h['bb'][al] + h['bb'][al + 3]) / 2 <= b[al + 3] + 40
                          and b[2] <= (h['bb'][2] + h['bb'][5]) / 2 <= b[5] and 0 <= (min(h['bb'][ad] * sg_, h['bb'][ad + 3] * sg_) - perto(b)) <= 160]
                    if not hs: continue
                    hc = sum((h['bb'][al] + h['bb'][al + 3]) / 2 for h in hs) / len(hs)
                    uc = b[al + 3] - 40 if abs(hc - b[al]) < abs(hc - b[al + 3]) else b[al] + 40
                    Lr = min(L_, dz - 120)
                    if dz >= 1200: zc = min(max(1050, b[2] + Lr / 2 + 80), b[5] - Lr / 2 - 80)
                    elif b[5] <= 1100: zc = b[5] - 60 - Lr / 2
                    elif b[2] >= 1200: zc = b[2] + 60 + Lr / 2
                    else: zc = (b[2] + b[5]) / 2
                    seg = dict(eixo='z', c_al=uc, z0=zc - Lr / 2, z1=zc + Lr / 2)
                else:          # gaveta / basculante
                    Lr = min(L_, du - 120); uc = (b[al] + b[al + 3]) / 2
                    zc = b[2] + 40 if b[2] >= 1200 else b[5] - 40
                    seg = dict(eixo='u', u0=uc - Lr / 2, u1=uc + Lr / 2, zc=zc)
                caixas = []
                def cx(a0, a1, dd0, dd1, z0, z1):
                    bb = [0.0] * 6; bb[al], bb[al + 3] = a0, a1; bb[2], bb[5] = z0, z1
                    p0, p1 = face + sai * dd0, face + sai * dd1; bb[ad], bb[ad + 3] = min(p0, p1), max(p0, p1); return bb
                if seg['eixo'] == 'z':
                    u = seg['c_al']
                    caixas.append(cx(u - 7.9, u + 7.9, 27, 37.5, seg['z0'], seg['z1']))                 # barra
                    for zz in (seg['z0'] + 6, seg['z1'] - 16): caixas.append(cx(u - 5, u + 5, 0, 27, zz, zz + 10))   # pés
                else:
                    z = seg['zc']
                    caixas.append(cx(seg['u0'], seg['u1'], 27, 37.5, z - 7.9, z + 7.9))
                    for uu_ in (seg['u0'] + 6, seg['u1'] - 16): caixas.append(cx(uu_, uu_ + 10, 0, 27, z - 5, z + 5))
                out.append(dict(porta=p_['i'], caixas=caixas))
    return out

_PT = None
def _portas():   # chapas finas na frente dos módulos (portas/frentes) - definição única: _eh_porta
    global _PT
    if _PT is None:
        _PT = set(PORTAS_XML)
        for w in paredes:
            for m in [i for i in w['itens'] if i['tipo'] == 'mod']:
                for p_ in P:
                    if _eh_porta(p_['bb'], m['bb'], w): _PT.add(p_['i'])
    return _PT

def tem_porta(m, w):
    # REGRA (v33, João): móvel com porta/frente nunca é nicho. Porta = _eh_porta (definição única, bloco cotas
    # 28/09/2026). Tem porta quando as portas cobrem >= NICHO_MIN_RATIO da face frontal do módulo.
    # REGRA (vidro, v35+): porta de vidro NÃO está no DXF; fallback no XML: módulo marcado xml_tem_porta = tem porta.
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad
    mb = m['bb']; area_ = (mb[al + 3] - mb[al]) * (mb[5] - mb[2]); cob = 0.0
    for p_ in P:
        b = p_['bb']
        if not _eh_porta(b, mb, w): continue
        cob += max(0, min(b[al + 3], mb[al + 3]) - max(b[al], mb[al])) * max(0, min(b[5], mb[5]) - max(b[2], mb[2]))
    if cob >= NICHO_MIN_RATIO * area_: return True
    # REGRA (João, 06/10/2026): frente = gaveta, porta = armário. Nome com Porta/Portas/Gaveta/Gavetas/Gaveteiro/Basculante = tem frente.
    return bool(m.get('xml_tem_porta')) or compatibilizacao.nome_tem_porta(m.get('desc', ''))

def _fundo_nicho_face(its, f):
    # REGRA (João, 06/10/2026): o nicho sem peça de fundo (aberto para a parede) é desenhado com FUNDO da cor
    # da madeira (MADEIRA), em vez de mostrar o vazio. Devolve o quadro (4 vértices) do fundo, ou None se o
    # grupo já tem peça de fundo (chapa fina no plano de trás cobrindo >= 60% do vão).
    U = list(its[0]['bb'])
    for i in its: U = geo.uniao(U, i['bb'])
    ad = 0 if f[0] else 1; al = 1 - ad
    xb = U[ad] if f[ad] < 0 else U[ad + 3]            # plano de trás = lado da parede (oposto ao da porta)
    larg = U[al + 3] - U[al]; alt = U[5] - U[2]
    if larg <= 0 or alt <= 0: return None
    cob = 0.0
    for i in its:
        for pi in i['pecas']:
            b = P[pi]['bb']
            if b[ad + 3] - b[ad] > 30 or min(abs(b[ad] - xb), abs(b[ad + 3] - xb)) > 40: continue
            cob += max(0, min(b[al + 3], U[al + 3]) - max(b[al], U[al])) * max(0, min(b[5], U[5]) - max(b[2], U[2]))
    if cob >= 0.6 * larg * alt: return None
    if ad == 0: return [(xb, U[1], U[2]), (xb, U[4], U[2]), (xb, U[4], U[5]), (xb, U[1], U[5])]
    return [(U[0], xb, U[2]), (U[3], xb, U[2]), (U[3], xb, U[5]), (U[0], xb, U[5])]

def _nichos_classificados(w):
    # REGRA (João, 06/10/2026): TODO nicho (estrutura SEM porta, módulo ou grupo de painéis soltos) vira subimagem.
    # A decisão é classificacao.classificar_peca (função pura); aqui só se monta o contexto e se agrupam as peças.
    ctx = dict(P=P, lim=geo.limites(inst), moveis={p_ for i_ in inst for p_ in i_.get('pecas', [])},
               soltas=w['itens'] + [i_ for i_ in inst if i_['tipo'] == 'mod'], eixo_vista=geo.PAREDES.get(w['key']))
    out = []
    for it in w['itens']:
        if compatibilizacao.classificar(it, ctx) != 'NICHO': continue
        out.append(compatibilizacao.grupo(it, ctx) if it['tipo'] == 'comp' else [it])
    return out

def detalhes(w):
    # nichos de painéis + módulos abertos; grupos que se encostam viram UM detalhe só
    # REGRA (João, 06/10/2026): módulo com porta de vidro/espelho (fora do DXF) continua ARMÁRIO: fica na vista
    # principal com a porta desenhada (face sintética) e o balão dele. Não vira subimagem.
    gs = [list(g) for g in nichos(w) + abertos(w) + _nichos_classificados(w)]
    toca = lambda A, B: all(min(A[k + 3], B[k + 3]) - max(A[k], B[k]) > -5 for k in range(3))
    mudou = True
    while mudou:
        mudou = False
        for i0 in range(len(gs)):
            for j0 in range(i0 + 1, len(gs)):
                if any(toca(a['bb'], b['bb']) for a in gs[i0] for b in gs[j0]):
                    gs[i0] += gs.pop(j0); mudou = True; break
            if mudou: break
    for k_ in range(len(gs)):   # mesma peça vinda das duas regras entra uma vez só
        vistos_ = set(); gs[k_] = [i for i in gs[k_] if not (id(i) in vistos_ or vistos_.add(id(i)))]
    return gs

def abertos(w):
    # REGRA (João): NICHO = estrutura ABERTA, SEM PORTA (sem porta/basculante/gaveta), com ou sem prateleira.
    # Módulo sem porta (até 2 m x 1,2 m) + tamponamentos/painéis encostados = DETALHE. Armário com porta NUNCA é nicho.
    f_ = FV[w['key']]; al = 1 if f_[0] else 0; out = []; ja = set()
    for g in nichos(w):
        for i in g: ja.add(id(i))
    for m in w['itens']:
        if m['tipo'] != 'mod' or id(m) in ja: continue
        mb = m['bb']
        if mb[al + 3] - mb[al] > 2000 or mb[5] - mb[2] > 1200 or tem_porta(m, w): continue
        g = [m] + [o for o in w['itens'] if o['tipo'] == 'comp' and id(o) not in ja
                   and all(min(o['bb'][k + 3], mb[k + 3]) - max(o['bb'][k], mb[k]) > -5 for k in range(3))
                   and (o['bb'][5] - o['bb'][2]) <= (mb[5] - mb[2]) + 150   # REGRA (v26): painel alto (tamponamento até o teto) não entra no detalhe do nicho
                   and o['bb'][al] >= mb[al] - 150 and o['bb'][al + 3] <= mb[al + 3] + 150]
        for i in g: ja.add(id(i))
        out.append(g)
    return out

def nichos(w):
    # REGRA (João): TODO NICHO ABERTO vira detalhe. Nicho = conjunto de painéis/tamponamentos encostados entre si
    # (peças "Vista" de acabamento não entram no agrupamento), com 3+ peças e 2+ horizontais, até 2 m de largura e 1,2 m de altura.
    cs = [i for i in w['itens'] if i['tipo'] == 'comp' and not re.match(r'vista\b', i['desc'], re.I)]; grupos_ = []
    toca = lambda A, B: all(min(A[k + 3], B[k + 3]) - max(A[k], B[k]) > -3 for k in range(3))
    for i in cs:
        junto = [g for g in grupos_ if any(toca(i['bb'], j['bb']) for j in g)]
        novo = [i] + [j for g in junto for j in g]
        grupos_ = [g for g in grupos_ if g not in junto] + [novo]
    out = []
    for g in grupos_:
        U_ = list(g[0]['bb'])
        for i in g: U_ = geo.uniao(U_, i['bb'])
        ext = [U_[k + 3] - U_[k] for k in range(3)]
        hz = sum(1 for i in g if i['bb'][5] - i['bb'][2] <= 30)
        ax_ = 1 if FV[w['key']][0] else 0
        if not (len(g) >= 3 and hz >= 2 and ext[ax_] <= 2000 and ext[2] <= 1200): continue
        # REGRA (v31): nicho tem a FRENTE ABERTA. Chapas do conjunto em pé de frente p/ a câmera, na face da frente,
        # cobrindo >= 40% da frente = caixa fechada -> não é nicho.
        ad_ = 1 - ax_; sg_ = FV[w['key']][ad_]; perto = lambda bb: min(bb[ad_] * sg_, bb[ad_ + 3] * sg_)
        fr_ = min(perto(i['bb']) for i in g); cob_ = 0.0
        for i in g:
            b = i['bb']
            if b[ad_ + 3] - b[ad_] <= 30 and perto(b) <= fr_ + 40 and b[5] - b[2] > 30: cob_ += (b[ax_ + 3] - b[ax_]) * (b[5] - b[2])
        if cob_ >= NICHO_MIN_RATIO * ext[ax_] * ext[2]: continue
        # REGRA (v33, João): MOVEL COM PORTA NAO E NICHO. Se qualquer modulo com porta ocupa o
        # mesmo espaco do conjunto, o conjunto inteiro deixa de ser nicho.
        if any(tem_porta(m, w) and all(min(U_[k + 3], m['bb'][k + 3]) - max(U_[k], m['bb'][k]) > -5 for k in range(3))
               for m in w['itens'] if m['tipo'] == 'mod'): continue
        out.append(g)
    return out

# --- GANCHO DE TESTE (Fase 2a): so com COMPIERE_TESTE_NICHO=1; imprime o nicho do motor ATUAL e termina antes de desenhar.
if os.environ.get('COMPIERE_TESTE_NICHO'):
    for _w in paredes:
        for _g in nichos(_w) + abertos(_w):
            for _i in _g:
                print(f"NICHO_ANTIGO\t{_w['id']}\t{_i['tipo']}\t{_i['desc']}\t{_i['dim']}")
    sys.exit(0)

def render3d(page, rect, pids, letra=None, itens=None, ang=None, dmin=4200, contexto=False, **kw):
    # contexto=True (REGRA João): mostra o AMBIENTE em volta (móveis e pedra das paredes vizinhas, perto desta parede)
    # para orientar; balões/listagem continuam só nos móveis da parede da vista.
    its = itens or [i for w in pids for i in PW[w]['itens']]
    U = list(its[0]['bb'])
    for i in its: U = geo.uniao(U, i['bb'])
    E = [U[0] - 80, U[1] - 80, U[2] - 80, U[3] + 80, U[4] + 80, U[5] + 80]
    f = FV[PW[pids[0]]['key']]; a = 0.0
    if len(pids) > 1:
        f2 = FV[PW[pids[1]]['key']]; a = math.radians(22 if f[0] * f2[1] - f[1] * f2[0] >= 0 else -22)
    if ang is not None: a = math.radians(ang)
    _cam = compatibilizacao_camera.calcular(f, U, len(pids), math.degrees(a), kw.get('elev'), dmin, contexto, bool(itens))
    fw, r, up = _cam['frente'], _cam['direita'], _cam['acima']
    dot = lambda a_, b_: a_[0] * b_[0] + a_[1] * b_[1] + a_[2] * b_[2]
    tc, D, cam = _cam['alvo'], _cam['distancia'], _cam['posicao']
    _finalidade = kw.get('finalidade', 'vista')
    _cena = cena_render.construir(PROJETO, _finalidade, its, pids, contexto=contexto,
                                  isolado=bool(kw.get('isolado')),
                                  camera={'posicao': cam, 'alvo': tc,
                                          'modo': 'perspectiva_interior' if _finalidade == 'visao_geral' else 'frontal',
                                          'altura_mm': cam[2], 'foco_altura_mm': tc[2]})
    cam = tuple(_cena['camera']['posicao']); tc = tuple(_cena['camera']['alvo'])
    ctx = contexto and not itens and len(pids) == 1
    if ctx:
        w0 = PW[pids[0]]; axd = 0 if f[0] else 1; axl = 1 - axd; sg = f[axd]
        prof_ = lambda bb: min((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg)
        # REGRA (v33, João): a vista e sempre frontal, entao a parede que fica NA FRENTE do móvel
        # nao e recortada: ela simplesmente NAO ENTRA. Assim a câmera pode se afastar ou aproximar
        # sem ninguem ter que acertar posicao de corte.
        _pf_mov = max((w0['plano'] - U[axd]) * sg, (w0['plano'] - U[axd + 3]) * sg)
        _na_frente = lambda bb: min((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg) > _pf_mov + 50
        _tg = {pi for i in its for pi in i['pecas']}
        def dentro_(bb, pi=None):
            if not (prof_(bb) <= 1000 and bb[axl + 3] >= U[axl] - 1800 and bb[axl] <= U[axl + 3] + 1800): return False
            if pi in _tg: return True
            # REGRA (v26, só parede cortada / bloco): o que fica todo ATRÁS do plano da vista (outro ambiente) não aparece
            if (w0.get('cortada') or w0.get('bloco')) and max((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg) < -100: return False
            cz = sum(((bb[k_] + bb[k_ + 3]) / 2 - cam[k_]) * fw[k_] for k_ in range(3))
            return cz > D * 0.8   # vizinho não fica entre a câmera e a parede
    cor = {}
    for i in inst:
        for pi in i['pecas']: cor[pi] = MADEIRA if i['tipo'] == 'comp' else (0.97, 0.97, 0.97)
    src = []; shell = []; _pmat = {}; _pidx = {}
    _iso = {pi for i in its for pi in i['pecas']} if kw.get('isolado') else None   # REGRA (v18): móvel complexo SOZINHO
    for p_ in P:
        # O contrato de ambiente é puro: faces preparadas e arestas ficam na saída.
        p_ = _AMBIENTE_POR_I.get(p_['i'], p_)
        b = p_['bb']
        sd_ = sorted(p_['dim'])
        if _iso is not None and p_['i'] not in _iso: continue
        if kw.get('sem_portas') and p_['i'] in _portas(): continue
        if p_['i'] in DUP_I: continue
        if p_['i'] in AMB_I or p_['i'] in ELETRO_I:
            if itens: continue   # detalhe (nicho/costas): só os móveis, sem pedra/eletros
            if (dentro_(b, p_['i']) if ctx else all(b[k] <= E[k + 3] and b[k + 3] >= E[k] for k in range(3))):
                c0_ = PEDRA_COR if p_['i'] in AMB_I else ELETRO_COR
                for fc, fl in zip(p_['faces'], p_['ft']): src.append((fc, c0_, fl, 1, len(shell)))
                shell.append(b)
            continue
        if sd_[1] < 50 or sd_[0] > 60: continue  # REGRA: 3D só com MDF (chapas); suportes, dobradiças, cabideiros, pés = fora
        if (dentro_(b, p_['i']) if ctx else (all(b[k] >= E[k] for k in range(3)) and all(b[k + 3] <= E[k + 3] for k in range(3)))):
            base = p_.get('rgb') or cor.get(p_['i'], (0.80, 0.80, 0.83))
            _pmat[len(shell)] = p_.get('mat'); _pidx[len(shell)] = p_['i']
            for uq, nv, ft in p_['fq']: src.append((uq, base, ft, 1, len(shell)))
            shell.append(b)
    for px_ in PUXADORES:   # REGRA (v23): puxador aparece junto com a porta dele
        if px_['porta'] in _pidx.values():
            for bx_ in px_['caixas']:
                for fc in caixa_faces(bx_): src.append((fc, PUX_TIPO['cor'], [True] * 4, 1, len(shell)))
                shell.append(bx_)
    # REGRA (v36, PORTA AUSENTE DO DXF): módulo com xml_tem_porta=True mas sem porta no DXF
    # recebe face sintética frontal fechada na prancha de listagem (portas fechadas).
    # Não se aplica em cotas (sem_portas=True) nem em subimagens de nicho (itens!=None).
    # ORDEM 006 (v37.2): face sintética liberada também em subimagem de porta ausente (xml_tem_porta).
    # Subimagem de nicho/aberto continua sem face sintética (seus 'its' não têm xml_tem_porta).
    _permite_face = not itens
    if not kw.get('sem_portas') and _permite_face:
        _w0 = PW[pids[0]]; _axd = 0 if f[0] else 1; _axl = 1 - _axd
        for _m in its:
            if _m['tipo'] != 'mod' or not _m.get('xml_tem_porta'): continue
            _mb = _m['bb']
            _area_m = (_mb[_axl + 3] - _mb[_axl]) * (_mb[5] - _mb[2])
            if _area_m <= 0: continue
            _cob = 0.0
            for _pp in P:
                if not _eh_porta(_pp['bb'], _mb, _w0): continue
                _b = _pp['bb']
                _cob += max(0, min(_b[_axl + 3], _mb[_axl + 3]) - max(_b[_axl], _mb[_axl])) * \
                        max(0, min(_b[5], _mb[5]) - max(_b[2], _mb[2]))
            if _cob >= NICHO_MIN_RATIO * _area_m: continue
            _sg = f[_axd]
            _xf = _mb[_axd + 3] if _sg < 0 else _mb[_axd]
            # Cor da face sintética: usa o material lido do XML (xml_mat_porta) para diferenciar vidro/espelho/MDF
            _mat_ = _m.get('xml_mat_porta', 'mdf')
            if _mat_ == 'vidro':
                _cor_m = (0.70, 0.87, 0.95)       # azul-translúcido (vidro)
            elif 'espelho' in _mat_:
                _cor_m = (0.80, 0.82, 0.86)       # prateado (espelho)
            elif _mat_ == 'aluminio':
                _cor_m = (0.75, 0.76, 0.78)       # alumínio escovado (005.A.4)
            else:
                _cor_m = next((pp_.get('rgb') for pp_ in P if pp_['i'] in _m['pecas'] and pp_.get('rgb')), (0.97, 0.97, 0.97))
            if _axd == 0:
                _face = [(_xf, _mb[1], _mb[2]), (_xf, _mb[4], _mb[2]), (_xf, _mb[4], _mb[5]), (_xf, _mb[1], _mb[5])]
            else:
                _face = [(_mb[0], _xf, _mb[2]), (_mb[3], _xf, _mb[2]), (_mb[3], _xf, _mb[5]), (_mb[0], _xf, _mb[5])]
            src.append((_face, _cor_m, [True, True, True, True], 1, len(shell)))
            shell.append([_mb[0] - 1, _mb[1] - 1, _mb[2] - 1, _mb[3] + 1, _mb[4] + 1, _mb[5] + 1])
    if kw.get('fundo_nicho'):   # subimagem de nicho: fundo em madeira quando o nicho não tem peça de fundo
        _ff = _fundo_nicho_face(its, f)
        if _ff:
            src.append((_ff, MADEIRA, [True, True, True, True], 1, len(shell)))
            shell.append([min(v[0] for v in _ff) - 1, min(v[1] for v in _ff) - 1, min(v[2] for v in _ff) - 1,
                          max(v[0] for v in _ff) + 1, max(v[1] for v in _ff) + 1, max(v[2] for v in _ff) + 1])
    mg = kw.get('margem', 700); R = [U[0] - mg, U[1] - mg, 0 if mg >= 700 else U[2] - mg, U[3] + mg, U[4] + mg, U[5] + min(150, mg)]
    if ctx and MALHA_PAR:
        _cob = []; _ilha = U[5] <= 1200   # móvel baixo solto (ilha/bancada): sem parede inventada nem laterais distantes
        for p_ in MALHA_PAR:
            for fc, fl in zip(p_['faces'], p_['ft']):
                c_ = [sum(v[k_] for v in fc) / len(fc) for k_ in range(3)]
                if min((w0['plano'] - v[axd]) * sg for v in fc) > 1300: continue
                if min((w0['plano'] - v[axd]) * sg for v in fc) > _pf_mov + 50: continue   # v33: parede da frente sai inteira
                if c_[axl] < U[axl] - 700 or c_[axl] > U[axl + 3] + 700: continue
                if max(v[axd] for v in fc) - min(v[axd] for v in fc) < 1:   # face "de frente" para a câmera
                    pf = (w0['plano'] - c_[axd]) * sg
                    if pf > 100: continue            # parede NA FRENTE do fundo dos móveis: esconderia móvel
                    lo_, hi_ = max(U[axl], min(v[axl] for v in fc)), min(U[axl + 3], max(v[axl] for v in fc))
                    if hi_ > lo_: _cob.append((lo_, hi_))
                elif _ilha: continue
                src.append((fc, PAREDE_COR, fl, 0, -1))
        _tot = 0; _fim = U[axl]
        for lo_, hi_ in sorted(_cob):
            lo_ = max(lo_, _fim)
            if hi_ > lo_: _tot += hi_ - lo_; _fim = hi_
        if not _ilha and not w0.get('divisoria') and _tot < 0.5 * (U[axl + 3] - U[axl]):   # REGRA: parede real cobre < metade dos móveis -> parede de fundo de referência
            bf = [0.0] * 6; bf[axl] = U[axl] - 400; bf[axl + 3] = U[axl + 3] + 400; bf[2] = 0; bf[5] = U[5] + 150
            pl0 = w0['plano']; bf[axd], bf[axd + 3] = (pl0, pl0 + 100) if sg > 0 else (pl0 - 100, pl0)
            for fc in caixa_faces(bf): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    if ctx and (PAR_DXF or MALHA_PAR):
        # REGRA (João): paredes reais do DXF que compõem o L (fundo e laterais), com janela/abertura; tira só as que ficam na frente
        for p_ in PAR_DXF:
            b = p_['bb']
            if prof_(b) > 1300 or b[axl + 3] < U[axl] - 1800 or b[axl] > U[axl + 3] + 1800: continue
            if _na_frente(b): continue   # v33: parede da frente sai inteira, sem recorte
            for fc in caixa_faces(b): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    elif _iso is None:
        if ctx: R[axl] -= 1800; R[axl + 3] += 1800
        for b in paredes_recorte(R):
            for fc in caixa_faces(b): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    # REGRA (João, 2026-09-28, REAPLICADO): piso não depende mais de "vista com 1 parede só" (ctx).
    # Antes o piso usava eixo/plano de PW[pids[0]] -> em vista de canto (2 paredes, L), ctx era False
    # e o piso não saía (bug: "gerei 11 suíte e não saiu com piso"). Agora é uma laje plana sob toda
    # a área visível (bounding box dos itens + margem), independente de quantas paredes tem a vista.
    # Lógica de parede (_na_frente/etc.) não foi tocada.
    if contexto and not itens:
        _pz = [U[0] - 4000, U[1] - 4000, -20, U[3] + 4000, U[4] + 4000, 0]
        src.append((caixa_faces(_pz)[1], PISO_COR, [True] * 4, 0, -1))
    L = (0.35, -0.45, 0.82); nl = math.sqrt(dot(L, L))
    def pj(v):
        rel = (v[0] - cam[0], v[1] - cam[1], v[2] - cam[2]); z = dot(rel, fw)
        return (dot(rel, r) / z, dot(rel, up) / z, z)
    fcs = []
    for vs, base, ft, gr, pc in src:
        pp = [pj(v) for v in vs]
        if min(t[2] for t in pp) < 50: continue
        nm = _n(vs[0], vs[1], vs[2]); fs_ = 0.72 + 0.28 * abs(dot(nm, L)) / nl
        fcs.append((gr, sum(t[2] for t in pp) / len(pp), [(t[0], t[1]) for t in pp], tuple(min(1, x * fs_) for x in base), ft, pc, vs, fs_))
    if not fcs: return
    fcs = _ordem_pecas(fcs, shell, cam)
    xs = [x for f_ in fcs for x, _ in f_[2]]; ys = [y for f_ in fcs for _, y in f_[2]]
    if itens:   # detalhe: enquadra só as peças do detalhe (zoom)
        _alvo = {pi for i in its for pi in i['pecas']}; _bi = {pc_: b_ for pc_, b_ in enumerate(shell)}
        cc = [pj((b_[i0], b_[1 + j0], b_[2 + k0])) for pc_, b_ in _bi.items() if _pidx.get(pc_) in _alvo for i0 in (0, 3) for j0 in (0, 3) for k0 in (0, 3)]
        cc = [c_ for c_ in cc if c_[2] > 50]
        if cc: xs = [c_[0] for c_ in cc]; ys = [c_[1] for c_ in cc]
    if ctx:   # REGRA (v15, João): a imagem PREENCHE o quadro todo. Enquadra os móveis com folga curta
        # (300 mm dos lados, piso até 150 mm acima do móvel); o ambiente (paredes, piso) completa o resto e é recortado.
        Uq = list(U); Uq[axl] -= 300; Uq[axl + 3] += 300; Uq[2] = 0; Uq[5] += 150
        # móvel pequeno: enquadramento mínimo 2,2 m x 2,0 m (mostra o ambiente, não vira close do móvel)
        _fx = max(0, 2200 - (Uq[axl + 3] - Uq[axl])) / 2; Uq[axl] -= _fx; Uq[axl + 3] += _fx; Uq[5] = max(Uq[5], 2000)
        cc = [pj((Uq[i0], Uq[1 + j0], Uq[2 + k0])) for i0 in (0, 3) for j0 in (0, 3) for k0 in (0, 3)]
        cc = [c_ for c_ in cc if c_[2] > 50]
        xs = [c_[0] for c_ in cc]; ys = [c_[1] for c_ in cc]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mgf = 22 if itens else 4 if ctx else 16
    k = min((rect.width - mgf) / (x1 - x0), (rect.height - mgf) / (y1 - y0))
    ox = rect.x0 + (rect.width - (x1 - x0) * k) / 2; oy = rect.y0 + (rect.height - (y1 - y0) * k) / 2
    T = lambda x, y: (ox + (x - x0) * k, oy + (y1 - y) * k)
    if kw.get('visiveis') is not None and _Im is not None:
        # REGRA (v25): quais peças APARECEM nesta imagem (buffer de identificação, desenho na mesma ordem das faces)
        _s = 2.0; _W = max(1, int(rect.width * _s)); _H = max(1, int(rect.height * _s))
        _ib = _Im.new('I', (_W, _H), 0); _dr = _ImD.Draw(_ib)
        for f_ in fcs:
            Q_ = [((T(x_, y_)[0] - rect.x0) * _s, (T(x_, y_)[1] - rect.y0) * _s) for x_, y_ in f_[2]]
            if len(Q_) >= 3: _dr.polygon(Q_, fill=(f_[5] + 1) if f_[5] is not None and f_[5] >= 0 else 0)
        _vv, _cc = _np.unique(_np.asarray(_ib), return_counts=True)
        _bx = {}
        for f_ in fcs:
            if f_[5] is None or f_[5] < 0: continue
            for x_, y_ in f_[2]:
                px_, py_ = T(x_, y_); b_ = _bx.setdefault(f_[5], [px_, py_, px_, py_])
                b_[0] = min(b_[0], px_); b_[1] = min(b_[1], py_); b_[2] = max(b_[2], px_); b_[3] = max(b_[3], py_)
        for v_, c_ in zip(_vv, _cc):
            pc_ = int(v_) - 1
            if v_ <= 0 or pc_ not in _pidx or pc_ not in _bx: continue
            b_ = _bx[pc_]; area_ = max(1.0, (b_[2] - b_[0]) * (b_[3] - b_[1]) * _s * _s)
            if c_ >= 40 and c_ / area_ >= 0.05: kw['visiveis'].add(_pidx[pc_])   # peça aparece DE VERDADE (15%+ dela)
        if kw.get('so_visiveis'): return
    if os.environ.get('COMPIERE_RENDER','').lower() == 'blender':
        page.insert_image(rect, stream=renderizador.renderizar_blender(PROJETO, _cena,
                          max(640, int(rect.width*2)), max(480, int(rect.height*2)),
                          int(os.environ.get('COMPIERE_BLENDER_AMOSTRAS', '64'))))
    elif _Im is not None and cfg.get('textura', True) and any(textura(m_) for m_ in _pmat.values()):
        _raster3d(page, rect, fcs, T, _pmat)
    else:
        if ctx: _tmp = fz.open(); _tp = _tmp.new_page(width=page.rect.width, height=page.rect.height); sh = _tp.new_shape()
        else: sh = page.new_shape()
        for f_ in fcs:
            q, c_, ft = f_[2], f_[3], f_[4]
            Q = [T(x, y) for x, y in q]
            if area2(Q) < 0.1: continue
            sh.draw_polyline(Q + [Q[0]]); sh.finish(color=c_, fill=c_, width=0.5, closePath=True)
            if any(ft):
                for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
                    if fl_: sh.draw_line(a_, b_)
                sh.finish(color=(0.2, 0.2, 0.2), width=0.35, closePath=False)
        sh.commit()
        if ctx: page.show_pdf_page(rect, _tmp, 0, clip=rect)
    if letra:
        _bal = []; _ja_bal = set()
        for i in its:
            nb = i.get('num_' + letra)
            if not nb or id(i) in kw.get('sem_balao', ()): continue
            if PW.get(i.get('parede'), {}).get('divisoria'):   # REGRA (v18): divisória = UM balão por tipo de peça
                if nb in _ja_bal: continue
                _ja_bal.add(nb)
            b = i['bb']; fi = FV[PW[i['parede']]['key']]; axi = 0 if fi[0] else 1
            c3 = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]
            c3[axi] = b[axi] if (fi[axi] > 0) != bool(kw.get('costas')) else b[axi + 3]
            _us = USINADOS.get(i['pecas'][0])
            if _us: c3[_us['al']] = (b[_us['al']] + _us['u'][0]) / 2   # painel usinado: balão na faixa cheia, não no vão
            t3 = pj(c3); cx, cy = T(t3[0], t3[1]); t_ = str(nb); wv = fz.get_text_length(t_, 'hebo', 7) + 4
            if kw.get('posicoes') is not None: kw['posicoes'][id(i)] = (cx, cy)
            # REGRA: balões não ficam um em cima do outro -> desloca o novo e liga ao ponto com traço fino
            bx, by = cx, cy
            for tent in range(24):
                rr = fz.Rect(bx - wv / 2 - 1, by - 6.5, bx + wv / 2 + 1, by + 6.5)
                if not any(rr.intersects(o_) for o_ in _bal): break
                ang_ = tent * 0.9; dist_ = 10 + 3 * tent
                bx, by = cx + dist_ * math.cos(ang_), cy + dist_ * math.sin(ang_)
            if (bx, by) != (cx, cy):
                page.draw_line((cx, cy), (bx, by), color=PRETO, width=0.35); page.draw_circle((cx, cy), 0.9, color=PRETO, fill=PRETO)
            _bal.append(fz.Rect(bx - wv / 2 - 1, by - 6.5, bx + wv / 2 + 1, by + 6.5))
            page.draw_rect(fz.Rect(bx - wv / 2, by - 5.5, bx + wv / 2, by + 5.5), color=PRETO, fill=(1, 1, 0), width=0.4)
            page.insert_text((bx - wv / 2 + 2, by + 2.5), t_, fontname='hebo', fontsize=7)


# puxador por regra DESLIGADO (João: posições erradas). Só liga com "puxadores_regra": true no config.
PUXADORES = _gerar_puxadores() if cfg.get('puxadores_regra') else []
print('PUXADORES:', len(PUXADORES), '(regra desligada; o DXF não traz puxador)' if not PUXADORES else 'gerados')
# REGRA (v33, João): PEÇA ESCONDIDA NÃO É LISTADA. Antes de montar a tabela, o motor desenha a
# imagem frontal da vista num rascunho e anota quais peças realmente aparecem nela. Item que não
# tem nenhuma peça visível fica FORA da tabela e não ganha balão. Nada de tirar a peça de onde ela
# está para fazer uma imagem só dela.
# (precisa vir depois de render3d estar definido)
# DECISÃO D1 (João, 28/09/2026): elementos com mesma (desc, dim) → mesmo número em TODAS as vistas.
# Na tabela: uma linha, sem quantidade. Na imagem: cada ocorrência tem balão próprio com mesmo número.
def _numerar(ordenados, letra, agrupar=False):
    lin = []
    for i in ordenados:
        k = (i['desc'], i['dim'])
        if agrupar and k in lin: i['num_' + letra] = lin.index(k) + 1; continue
        lin.append(k); i['num_' + letra] = len(lin)
    return [(d, dm, '') for d, dm in lin]

for v in VW:
    its = [i for w in v['paredes'] for i in PW[w]['itens']]
    _vis_v = set()
    _tmp_v = fz.open(); _pg_v = _tmp_v.new_page(width=842, height=595)
    render3d(_pg_v, fz.Rect(AREA_IN.x0 + 258, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1), v['paredes'],
             contexto=True, visiveis=_vis_v, so_visiveis=True)
    # REGRA (João, 28/09/2026 - bloco 1): só PEÇA SOLTA pode ser escondida (base sob módulo,
    # tamponamento sob superior). MÓDULO da vista nunca é escondido nem sai da listagem.
    _fora_v = [i for i in its if i['tipo'] != 'mod' and not any(pi in _vis_v for pi in i['pecas'])]
    if _fora_v:
        print('ESCONDIDAS (fora da listagem) em %s: %d' % (v['titulo'], len(_fora_v)))
        for i in _fora_v: print('    %s %s' % (i['desc'], i['dim']))
        its = [i for i in its if i not in _fora_v] or its
    v['itens_listados'] = its
    ordem = sorted(its, key=lambda i: (i['tipo'] != 'mod', i['n']))
    v['linhas'] = _numerar(ordem, v['letra'], agrupar=True)  # D1: agrupar sempre (iguais = mesmo nº)

# ---------------- montagem ----------------
doc = fz.open(); n = 0; relat = []
n += 1; p = nova_prancha(doc, n, 'CAPA')
render3d(p, fz.Rect(AREA_IN.x0, AREA_IN.y0 + 34, AREA_IN.x1, AREA_IN.y1), [w['id'] for w in paredes])
t = f"CADERNO DE {cfg['tipo_caderno']} - {cfg['dados']['ambiente'].upper()}"
p.insert_text((419.5 - fz.get_text_length(t, 'hebo', 18) / 2, AREA_IN.y0 + 22), t, fontname='hebo', fontsize=18, color=RED)

n += 1; p = nova_prancha(doc, n, 'CONTRATO')
ct = fz.open(cfg['contrato_fonte']); clip = fz.Rect(AREA.x0 + 2, 143, AREA.x1 - 2, 540)
p.show_pdf_page(clip, ct, 0, clip=clip)

# PRANCHA 3: especificações + planta do DXF com cotas e indicação das vistas
n += 1; p = nova_prancha(doc, n, 'PLANTA - ESPECIFICAÇÕES DO PROJETO')
esp = fz.Rect(AREA_IN.x0, AREA_IN.y0, AREA_IN.x0 + 225, AREA_IN.y1)
p.draw_rect(esp, color=PRETO, width=0.6)
# REGRA (reativado): xml_confere agora usa _faltando_real (peças reais que faltam, excluindo
# acessórios/ferragens). Se alguma peça real da listagem não foi localizada no DXF, specs entram
# como CONFERIR (ENGENHARIA.pdf Parte 2, item 4). Acessórios sem DXF são normais e não afetam.
confere = not _faltando_real
# REGRA (João): especificações no modelo fixo, preenchidas com o que está no XML (nome exato). Sem item no projeto = em branco.
itens_esp = PROJETO['xml']['especificacoes']
if not confere:
    itens_esp = [(r_, v_ if v_ is None or 'mm' in v_ else 'CONFERIR') for r_, v_ in itens_esp]
_FH, _FB = fz.Font('helv'), fz.Font('hebo')
def _quebra(t, larg, fs):
    ls, cur = [], ''
    for w_ in t.split(' '):
        tt = (cur + ' ' + w_).strip()
        if cur and _FB.text_length(tt, fs) > larg: ls.append(cur); cur = w_
        else: cur = tt
    return ls + ([cur] if cur else [])
y = esp.y0 + 14
for rot, v in itens_esp:
    if v is None:
        if y > esp.y0 + 20: y += 4
        p.insert_text((esp.x0 + 6, y), rot, fontname='hebo', fontsize=8.5, color=RED if y == esp.y0 + 14 else PRETO)
        y += 14; continue
    rt = rot + ': '; rw = _FH.text_length(rt, 7.3) + 1.5
    p.insert_text((esp.x0 + 6, y), rt, fontname='helv', fontsize=7.3)
    ls = _quebra(v, esp.width - 12 - rw, 7.3) if v else []
    if len(ls) > 1: ls = _quebra(v, esp.width - 18, 7.3); y += 9.5; x_ = esp.x0 + 12
    else: x_ = esp.x0 + 6 + rw
    for l_ in ls:
        p.insert_text((x_, y), l_, fontname='hebo', fontsize=7.3, color=(0.7, 0, 0) if v == 'CONFERIR' else PRETO); y += 9.5
    y += 3.5 if ls else 13
if not confere:
    p.insert_text((esp.x0 + 6, esp.y1 - 8), f'{len(_faltando_real)} item(ns) do XML não bateu(ram) com o DXF — conferir', fontname='helv', fontsize=6.5, color=(0.7, 0, 0))
# planta
pr = fz.Rect(esp.x1 + 8, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1)
todos = [pi for it in inst for pi in it['pecas']]
xs0 = min(P[i]['bb'][0] for i in todos); xs1 = max(P[i]['bb'][3] for i in todos)
ys0 = min(P[i]['bb'][1] for i in todos); ys1 = max(P[i]['bb'][4] for i in todos)
S, k = escala_para(xs1 - xs0, ys1 - ys0, pr.width - 110, pr.height - 90)
ox = pr.x0 + (pr.width - (xs1 - xs0) * k) / 2; oy = pr.y0 + (pr.height - (ys1 - ys0) * k) / 2
PX = lambda x: ox + (x - xs0) * k
PY = lambda y_: oy + (ys1 - y_) * k
cor_de = {}
for it in inst:
    for pi in it['pecas']: cor_de[pi] = MADEIRA if it['tipo'] == 'comp' else BRANCO
fcs = []
# REGRA (João): planta só com MÓVEIS e PAREDES (sem forro, sanca, pedra, eletros por cima dos móveis)
_par_ids = {p_['i'] for p_ in PAREDES_PECAS} | {p_['i'] for p_ in PAR_DXF}
_linhas_par = set()
for p_ in MALHA_PAR:   # paredes em peça única: faces verticais viram as linhas das paredes (vãos ficam abertos)
    for fc in p_['faces']:
        zs_ = [v[2] for v in fc]
        if max(zs_) - min(zs_) < 500 or min(zs_) > 1200: continue
        xy = sorted({(round(v[0]), round(v[1])) for v in fc})
        if len(xy) >= 2 and math.dist(xy[0], xy[-1]) > 20: _linhas_par.add((xy[0], xy[-1]))
for p_ in P:
    b = p_['bb']
    if p_['i'] not in _usadas and p_['i'] not in _par_ids: continue
    if p_['i'] in _usadas and (sorted(p_['dim'])[1] < 50 or sorted(p_['dim'])[0] > 60): continue
    if b[3] < xs0 - 300 or b[0] > xs1 + 300 or b[4] < ys0 - 300 or b[1] > ys1 + 300 or b[2] > 2600: continue
    if p_['dim'][0] > 6000 or p_['dim'][1] > 6000: continue
    if p_['dim'][2] < 40 and p_['dim'][0] > 1200 and p_['dim'][1] > 1200: continue
    for uq, nv, ft in p_['fq']:
        q = [(PX(v[0]), PY(v[1])) for v in uq]
        if area2(q) < 0.2: continue
        fcs.append((max(v[2] for v in uq), q, cor_de.get(p_['i']), ft))
fcs.sort(key=lambda t: t[0])
sh = p.new_shape()
for z, q, cor, ft in fcs:
    q = [(min(max(a, pr.x0), pr.x1), min(max(b_, pr.y0), pr.y1)) for a, b_ in q]
    fill = cor or BRANCO
    sh.draw_polyline(q + [q[0]]); sh.finish(color=fill, fill=fill, width=0.4, closePath=True)
    if any(ft):
        for (a_, b_), f_ in zip(zip(q, q[1:] + q[:1]), ft):
            if f_: sh.draw_line(a_, b_)
        sh.finish(color=PRETO if cor is None else (0.3, 0.3, 0.3), width=0.5 if cor is None else 0.3, closePath=False)
sh.commit()
def _clip(x0, y0, x1, y1, R):   # v30: linha de parede não sai do quadro da planta
    t0, t1 = 0.0, 1.0; dx, dy = x1 - x0, y1 - y0
    for pp, qq in ((-dx, x0 - R.x0), (dx, R.x1 - x0), (-dy, y0 - R.y0), (dy, R.y1 - y0)):
        if pp == 0:
            if qq < 0: return None
        else:
            t = qq / pp
            if pp < 0: t0 = max(t0, t)
            else: t1 = min(t1, t)
    return None if t0 > t1 else ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))
for (a_, b_) in _linhas_par:
    _sg = _clip(PX(a_[0]), PY(a_[1]), PX(b_[0]), PY(b_[1]), pr)
    if _sg: p.draw_line(_sg[0], _sg[1], color=PRETO, width=0.9)
for w in paredes:          # REGRA (v28, João): planta = cota de CADA CONJUNTO de móveis (comprimento + largura), sem cotar o vão entre eles
    f = FV[w['key']]; ax = 1 if w['key'][0] == 'x' else 0; ad = 1 - ax; gr = []
    for i in sorted(w['itens'], key=lambda i: i['bb'][ax]):
        if gr and i['bb'][ax] <= max(j['bb'][ax + 3] for j in gr[-1]) + 50: gr[-1].append(i)
        else: gr.append([i])
    for g in gr:
        a0, a1 = min(i['bb'][ax] for i in g), max(i['bb'][ax + 3] for i in g); d0, d1 = min(i['bb'][ad] for i in g), max(i['bb'][ad + 3] for i in g)
        if ax == 1:
            cadeia_v(p, [a0, a1], PX(w['plano']) + (16 if f[0] > 0 else -16), PX(w['plano']), PY, fs=7)
            cadeia_h(p, [d0, d1], PY(a0) + 14, PY(a0), PX, fs=7)
        else:
            cadeia_h(p, [a0, a1], PY(w['plano']) + (16 if f[1] < 0 else -16), PY(w['plano']), PX, fs=7)
            cadeia_v(p, [d0, d1], PX(a1) + 14, PX(a1), PY, fs=7)
_circ = []
for v in V:                # setas das vistas (uma por parede); se encostar em outra, desliza ao longo da parede
  for wid, letra_ in zip(v['paredes'], v['letras']):
    w = PW[wid]; f = FV[w['key']]; its = w['itens']
    # REGRA (João 28/09/2026): câmera fica no AMBIENTE, aponta para a PAREDE. Fundo=parede, frente=ambiente.
    # f_arr aponta PARA a parede (mesma direção da câmera), coloca o símbolo no lado do ambiente.
    f_arr = FV[w['key']]
    cx = sum((i['bb'][0] + i['bb'][3]) / 2 for i in its) / len(its); cy = sum((i['bb'][1] + i['bb'][4]) / 2 for i in its) / len(its)
    ex, ey = PX(cx) - f_arr[0] * 30, PY(cy) + f_arr[1] * 30
    for _t in range(8):
        sx, sy = ex - f_arr[0] * 32, ey + f_arr[1] * 32
        cc_ = (sx - f_arr[0] * 8, sy + f_arr[1] * 8); seg = [(sx, sy), (ex, ey), cc_]
        if all(math.dist(a_, b_) > 22 for a_ in seg for b_ in _circ): break
        ex += 30 * abs(f_arr[1]) * (1 if _t % 2 == 0 else -2); ey += 30 * abs(f_arr[0]) * (1 if _t % 2 == 0 else -2)
    _circ += [(sx, sy), (ex, ey), (sx - f_arr[0] * 8, sy + f_arr[1] * 8)]
    p.draw_line((sx, sy), (ex, ey), color=RED, width=1.4)
    p.draw_polyline([(ex + f_arr[1] * 4 - f_arr[0] * 7, ey + f_arr[0] * 4 + f_arr[1] * 7), (ex, ey), (ex - f_arr[1] * 4 - f_arr[0] * 7, ey - f_arr[0] * 4 + f_arr[1] * 7)], color=RED, width=1.4)
    p.draw_circle((sx - f_arr[0] * 8, sy + f_arr[1] * 8), 7, color=RED, fill=BRANCO, width=1)
    p.insert_text((sx - f_arr[0] * 8 - 3.5, sy + f_arr[1] * 8 + 3.5), letra_, fontname='hebo', fontsize=10, color=RED)
lab = f'PLANTA BAIXA - ESC. 1:{S}'
p.insert_text((pr.x0 + pr.width / 2 - fz.get_text_length(lab, 'hebo', 8) / 2, pr.y1 - 3), lab, fontname='hebo', fontsize=8)

# PRANCHA 4: visão geral
n += 1; p = nova_prancha(doc, n, 'VISÃO GERAL DOS MÓVEIS')
# REGRA (João, 28/09/2026 - skill V5): de 1 a 4 imagens, observador DENTRO do ambiente (com contexto), sem balão e
# sem cota. Mais de 4 vistas: as vistas vizinhas se juntam em 4 grupos; cada imagem olha a 1ª parede do grupo
# com o ambiente em volta (substitui a v28, que montava o par de paredes visto de fora).
_vg = [x for x in VW if not PW[x['paredes'][0]].get('divisoria')] or VW
_ng = min(4, len(_vg)); _tam = [len(_vg) // _ng + (1 if k < len(_vg) % _ng else 0) for k in range(_ng)]
com_img = []; _k0 = 0
for t_ in _tam:
    g_ = _vg[_k0:_k0 + t_]; _k0 += t_
    com_img.append(dict(titulo=' + '.join(x['titulo'] for x in g_), paredes=[g_[0]['paredes'][0]], img3d=None))
m = len(com_img); a = AREA_IN
_nc = 1 if m == 1 else 2 if m <= 4 else 3; _nr = -(-m // _nc)
cel = [fz.Rect(a.x0 + (i % _nc) * a.width / _nc, a.y0 + (i // _nc) * a.height / _nr, a.x0 + (i % _nc + 1) * a.width / _nc, a.y0 + (i // _nc + 1) * a.height / _nr) for i in range(m)]
for v, c in zip(com_img, cel):
    render3d(p, fz.Rect(c.x0 + 4, c.y0 + 16, c.x1 - 4, c.y1 - 4), v['paredes'], contexto=True, finalidade='visao_geral')
    p.insert_text((c.x0 + 6, c.y0 + 11), v['titulo'], fontname='hebo', fontsize=10, color=RED)
for j in range(1, _nc): p.draw_line((a.x0 + j * a.width / _nc, AREA.y0), (a.x0 + j * a.width / _nc, AREA.y1), color=PRETO, width=0.6)
for j in range(1, _nr): p.draw_line((AREA.x0, a.y0 + j * a.height / _nr), (AREA.x1, a.y0 + j * a.height / _nr), color=PRETO, width=0.6)

# REGRA (v26, João): LISTAGEM POLUÍDA (mais de 15 linhas) = DUAS pranchas: SUPERIORES (armários de cima e altos) e
# INFERIORES (balcões). Cada uma com a tabela e os balões só das suas peças (numeração própria). Sem os dois grupos:
# divide a parede ao meio (PARTE 1 / PARTE 2).
LIST_MAX = 15; LIST_TOL = 2; _extra = 0   # REGRA (ajuste, pedido João): tolerância de +2 (15 a 17
                                            # numa prancha só) - só divide de fato a partir de 18,
                                            # pra não partir uma listagem quase no limite ao meio.
def _partes(s_):
    global _extra
    # REGRA (v34, João): usa a lista JÁ FILTRADA (sem as peças escondidas). Antes esta função relia a
    # lista original e as escondidas voltavam com balão quando a listagem se dividia em duas pranchas.
    its = s_.get('itens_listados') or [i for w in s_['paredes'] for i in PW[w]['itens']]
    if len(s_['linhas']) <= LIST_MAX + LIST_TOL or not its: return [s_]
    sup = [i for i in its if (i['bb'][2] + i['bb'][5]) / 2 > 1300]; inf = [i for i in its if i not in sup]
    if sup and inf: gs = [('SUPERIORES', sup), ('INFERIORES', inf)]
    else:
        f_ = FV[PW[s_['paredes'][0]]['key']]; al = 1 if f_[0] else 0
        o_ = sorted(its, key=lambda i: (i['bb'][al] + i['bb'][al + 3]) / 2); h_ = len(o_) // 2
        gs = [('PARTE 1', o_[:h_]), ('PARTE 2', o_[h_:])]
    out = []
    for k_, (nome, g) in enumerate(gs):
        key = f"{s_['letra']}{k_ + 1}"
        lin = _numerar(sorted(g, key=lambda i: (i['tipo'] != 'mod', i['n'])), key)
        out.append(dict(letra=key, titulo=f"{s_['titulo']} - {nome}", linhas=lin, paredes=s_['paredes'], ids={id(i) for i in g}, primeiro=k_ == 0, base=s_))
    _extra += len(out) - 1
    return out

def _cotas_em(p, GS, R, rotulos):
    # REGRA (v15 + bloco cotas 28/09/2026): elevações 2D (móvel isolado) lado a lado dentro do retângulo R, mesma
    # escala nas colunas, a maior escala que cabe (até 1:10). Usada nas vistas (R = prancha inteira) e nas
    # pranchas extras (R = área à direita da listagem).
    nc = len(GS); zm = max(G['ztop'] for G in GS)
    Wm = [G['vmax'] - G['vmin'] for G in GS]
    S, k = escala_para(sum(Wm), zm, R.width - 80 * nc, R.height - 62, cheio=True)
    sobra = (R.width - sum(w_ * k + 80 for w_ in Wm)) / nc
    cws = [w_ * k + 80 + sobra for w_ in Wm]
    fy = R.y0 + (R.height - 62 - zm * k) / 2 + 22 + zm * k
    for j, G in enumerate(GS):
        cw = cws[j]; cx0 = R.x0 + sum(cws[:j])
        ox = cx0 + (cw - Wm[j] * k) / 2 + (G['umin'] - G['vmin']) * k
        desenhar(p, G, ox, fy, k)
        cotar(p, G, ox, fy, k)
        lab = f"{rotulos[j]} - ESC. 1:{S:g}"
        p.insert_text((cx0 + cw / 2 - fz.get_text_length(lab, 'hebo', 8.5) / 2, min(fy + 44, R.y1 - 2)), lab, fontname='hebo', fontsize=8.5)
        if j: p.draw_line((cx0, R.y0 - IN), (cx0, R.y1 + IN), color=PRETO, width=0.6)

# por bloco: listagem de cada parede (frontal) e depois as cotas do bloco (paredes lado a lado)
for v in V:
    GS = [geom_parede(PW[w]) for w in v['paredes']]
    if v.get('divisoria'):
        # REGRA (v18b): móvel complexo (divisória ripada em L) = SOZINHO, sem o ambiente, em DUAS imagens na
        # diagonal (uma de cada lado do L), cada uma na sua prancha; tabela completa nas duas; um balão por tipo de peça.
        its_ = PW[v['paredes'][0]]['itens']
        # REGRA (v20, João): 1ª prancha = 3D FRONTAL (como a cota, com todas as ripas); 2ª = 3D LATERAL pegando o L
        w_ = PW[v['paredes'][0]]; f_ = FV[w_['key']]; ax_ = 1 if f_[0] else 0; axd_ = 1 - ax_
        rd_ = (f_[1], -f_[0])
        cm_ = sum((i['bb'][ax_] + i['bb'][ax_ + 3]) / 2 for i in its_) / len(its_)
        dd_ = [i for i in its_ if abs((i['bb'][axd_] + i['bb'][axd_ + 3]) / 2 - w_['plano']) > 120]   # peças fora da faixa = perna do L
        lado_ = (sum((i['bb'][ax_] + i['bb'][ax_ + 3]) / 2 for i in dd_) / len(dd_) - cm_) * rd_[ax_] if dd_ else 1
        if w_.get('bloco'):   # REGRA (v26): bloco de painéis = lateral vista pelo lado onde estão os móveis (de dentro do ambiente)
            _ms = [i for i in inst if i['tipo'] == 'mod']
            if _ms: lado_ = (sum((i['bb'][ax_] + i['bb'][ax_ + 3]) / 2 for i in _ms) / len(_ms) - cm_) * rd_[ax_]
        # REGRA (João, 28/09/2026 - skill P3): prancha EXTRA = UMA estrutura por prancha, LISTAGEM E COTAS JUNTAS.
        # Esquerda: tabela + 3D isolado (fundo branco, só as peças, com balões). Direita: elevação 2D com cotas
        # (isolada, sem portas). Sai a 2ª prancha com a lateral a 90° e listagem própria (v24/v25).
        n += 1; p = nova_prancha(doc, n, f"MÓDULOS, PAINÉIS E MEDIDAS - {v['titulo']}")
        yb = tabela(p, v['linhas'], AREA_IN.x0, AREA_IN.y0)
        r3 = fz.Rect(AREA_IN.x0, yb + 10, AREA_IN.x0 + 248, AREA_IN.y1)
        p.draw_rect(r3, color=PRETO, width=0.5)
        render3d(p, fz.Rect(r3.x0 + 2, r3.y0 + 2, r3.x1 - 2, r3.y1 - 2), v['paredes'], letra=v['letra'], itens=its_,
                 ang=(25 if lado_ > 0 else -25), elev=12, dmin=3000, margem=60, isolado=True)
        _cotas_em(p, GS, fz.Rect(AREA_IN.x0 + 258, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1), [v['titulo']])
    for s_ in ([] if v.get('divisoria') else [q_ for s0_ in v['subs'] for q_ in _partes(s0_)]):
        n += 1; p = nova_prancha(doc, n, f"MÓDULOS E PAINÉIS - {s_['titulo']}")
        yb = tabela(p, s_['linhas'], AREA_IN.x0, AREA_IN.y0)
        # REGRA (v33, João): SO NICHO gera segunda imagem na prancha de listagem. Sairam o detalhe
        # das costas, o de rodape/base, o de modulo pequeno e a subimagem de peca escondida.
        # A subimagem fica na MESMA prancha da vista; havendo mais de um nicho, a prancha e
        # replicada com a vista principal apenas como referencia (item 9 da ENGENHARIA).
        nis = [(w, c, 'nicho') for w in s_['paredes'] for c in detalhes(PW[w])]
        if s_.get('ids') is not None:
            nis = [(w, c, t) for w, c, t in nis if any(id(i) in s_['ids'] for i in c)]
        _sb = {id(i) for _, c, _ in nis for i in c}
        _RI = fz.Rect(AREA_IN.x0 + 258, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1)
        render3d(p, _RI, s_['paredes'], letra=s_['letra'], contexto=True, sem_balao=_sb)
        # REGRA (João, 28/09/2026 - skill P1.1): TODOS os nichos da vista ficam na MESMA prancha (caixa dividida),
        # com os números da listagem. Não existe prancha "NICHO k" com listagem própria.
        def _dq(p, w, c, tp_, r_):
            # REGRA (v33, João): o nicho aparece SEM AMBIENTE - sem parede, sem chao, sozinho no
            # espaco (isolado=True), com os seus proprios baloes e a numeracao da listagem.
            # ORDEM 006 (v37.2): módulo com porta ausente no DXF (xml_tem_porta=True) vai FRONTAL (ang=0)
            # para mostrar a face sintética; nicho/aberto segue com ângulo.
            p.draw_rect(r_, color=PRETO, width=0.5)
            p.insert_text((r_.x0 + 4, r_.y0 + 10), 'DETALHE - NICHO', fontname='hebo', fontsize=7.5, color=RED)
            fw_ = FV[PW[w]['key']]; ax_ = 1 if fw_[0] else 0
            cm_ = sum((i['bb'][ax_] + i['bb'][ax_ + 3]) / 2 for i in PW[w]['itens']) / len(PW[w]['itens'])
            cn_ = sum((i['bb'][ax_] + i['bb'][ax_ + 3]) / 2 for i in c) / len(c)
            r_dir = (fw_[1], -fw_[0])
            lado = (cm_ - cn_) * r_dir[ax_]
            larg_ = max(i['bb'][ax_ + 3] for i in c) - min(i['bb'][ax_] for i in c)
            _ang_sub = (-1 if lado > 0 else 1) * (28 if larg_ < 1000 else 14)
            render3d(p, fz.Rect(r_.x0 + 2, r_.y0 + 14, r_.x1 - 2, r_.y1 - 2), [w], letra=s_['letra'], itens=c,
                     ang=_ang_sub, dmin=2200, margem=60, isolado=True, fundo_nicho=True)
        if nis:
            # REGRA (ajuste, pedido João): largura da tabela é sempre fixa (248pt, já era assim).
            # A altura da tabela acompanha a quantidade de itens (até 15 linhas por prancha, já
            # garantido a montante por _partes()/LIST_MAX). A caixa "DETALHE - NICHO" (2ª imagem)
            # acompanha esse vão: sobe quando a listagem é curta, encolhe quando é longa - nunca
            # esbarra, porque nunca começa antes do fim da tabela (yb).
            y0_ = yb + 18
            if AREA_IN.y1 - y0_ < 60:
                print(f"AVISO: caixa do nicho ficou pequena ({AREA_IN.y1 - y0_:.0f}pt) em '{s_['titulo']}'.")
            _hn = (AREA_IN.y1 - y0_ - 4 * (len(nis) - 1)) / len(nis)
            for k2_, (w, c, tp_) in enumerate(nis):
                _y = y0_ + k2_ * (_hn + 4)
                _dq(p, w, c, tp_, fz.Rect(AREA_IN.x0, _y, AREA_IN.x0 + 248, _y + _hn))
    if v.get('divisoria'): continue   # extra: listagem + cotas já saíram na mesma prancha
    # cotas
    n += 1; p = nova_prancha(doc, n, f"MEDIDAS E ALTURAS - {v['titulo']}")
    _cotas_em(p, GS, AREA_IN, [f"VISTA {l_}" for l_ in v['letras']])


# REGRA (v18): DIVISOR DE GAVETA (joias) = prancha própria: listagem das peças, 3D do divisor e
# VISTA DE CIMA com as cotas de todos os vãos (largura e profundidade) + altura das peças.
def _prancha_peca(g_, titulo, rotulo):
    global n, _nl
    n += 1; p = nova_prancha(doc, n, titulo)
    lt_ = letras[_nl]; _nl += 1
    yb = tabela(p, _numerar(sorted(g_, key=lambda i: i['n']), lt_), AREA_IN.x0, AREA_IN.y0)
    wid_ = g_[0].get('parede') if g_[0].get('parede') in PW else paredes[0]['id']
    for i in g_: i['parede'] = wid_
    # REGRA (v20, João): 3D SÓ das peças (isolado), com os balões da listagem
    _h = (AREA_IN.y1 - yb - 12); r3 = fz.Rect(AREA_IN.x0, yb + 12, AREA_IN.x0 + 248, yb + 12 + _h * 0.58)
    p.draw_rect(r3, color=PRETO, width=0.5)
    # REGRA (v28, João): imagem pequena ONDE FICA (a peça dentro do móvel/gaveta, sem portas)
    _U = [min(i['bb'][k] for i in g_) - 80 for k in range(3)] + [max(i['bb'][k + 3] for i in g_) + 80 for k in range(3)]
    _mv = [o for o in inst if o not in g_ and all(o['bb'][k] <= _U[k + 3] and o['bb'][k + 3] >= _U[k] for k in range(3))]
    r4 = fz.Rect(AREA_IN.x0, r3.y1 + 6, AREA_IN.x0 + 248, AREA_IN.y1)
    p.draw_rect(r4, color=PRETO, width=0.5); p.insert_text((r4.x0 + 4, r4.y0 + 10), 'ONDE FICA', fontname='hebo', fontsize=7.5, color=RED)
    if _mv: render3d(p, fz.Rect(r4.x0 + 2, r4.y0 + 14, r4.x1 - 2, r4.y1 - 2), [wid_], itens=g_ + _mv, ang=30, elev=45, dmin=2200, margem=60, isolado=True, sem_portas=True)
    render3d(p, fz.Rect(r3.x0 + 2, r3.y0 + 2, r3.x1 - 2, r3.y1 - 2), [wid_], letra=lt_, itens=g_, ang=30, elev=35, dmin=1800, margem=60, isolado=True)
    x0_ = min(i['bb'][0] for i in g_); x1_ = max(i['bb'][3] for i in g_); y0_ = min(i['bb'][1] for i in g_); y1_ = max(i['bb'][4] for i in g_)
    ra = fz.Rect(AREA_IN.x0 + 262, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1 - 20)
    Sd, kd = next(((S_, MM / S_) for S_ in (2, 2.5, 5, 10, 15, 20) if (x1_ - x0_) * MM / S_ <= ra.width - 90 and (y1_ - y0_) * MM / S_ <= ra.height - 70), (20, MM / 20))
    ox_ = ra.x0 + (ra.width - (x1_ - x0_) * kd) / 2; oy_ = ra.y0 + (ra.height - (y1_ - y0_) * kd) / 2
    X_ = lambda x: ox_ + (x - x0_) * kd
    Y_ = lambda y: oy_ + (y1_ - y) * kd
    fcs_ = []
    for i in g_:
        for pi in i['pecas']:
            b = P[pi]['bb']
            fcs_.append((b[5], [(b[0], b[1]), (b[3], b[1]), (b[3], b[4]), (b[0], b[4])], P[pi].get('rgb', MADEIRA), [True] * 4, P[pi].get('mat'), pi))
    fcs_.sort(key=lambda t: t[0])
    _desenho2d(p, fcs_, lambda x, y: (X_(x), Y_(y)))
    fin = lambda i: (i['bb'][3] - i['bb'][0]) <= 40 or (i['bb'][4] - i['bb'][1]) <= 40
    vx = [v for i in g_ if fin(i) and i['bb'][3] - i['bb'][0] < i['bb'][4] - i['bb'][1] for v in (i['bb'][0], i['bb'][3])]
    vy = [v for i in g_ if fin(i) and i['bb'][3] - i['bb'][0] >= i['bb'][4] - i['bb'][1] for v in (i['bb'][1], i['bb'][4])]
    cadeia_h(p, [x0_, x1_] + vx, Y_(y0_) + 16, Y_(y0_) + 2, X_)
    cadeia_h(p, [x0_, x1_], Y_(y1_) - 14, Y_(y1_) - 2, X_)
    cadeia_v(p, [y0_, y1_] + vy, X_(x1_) + 18, X_(x1_) + 2, lambda y: Y_(y))
    cadeia_v(p, [y0_, y1_], X_(x0_) - 14, X_(x0_) - 2, lambda y: Y_(y))
    alt_ = round(max(i['bb'][5] for i in g_) - min(i['bb'][2] for i in g_))
    lab = f'{rotulo} - VISTA DE CIMA - ESC. 1:{Sd:g}   |   ALTURA: {alt_} mm'
    p.insert_text((ra.x0 + ra.width / 2 - fz.get_text_length(lab, 'hebo', 8.5) / 2, AREA_IN.y1 - 6), lab, fontname='hebo', fontsize=8.5)

# REGRA (v18/v20): DIVISOR DE GAVETA e GAVETA/MÓDULO MONTADO COM PAINÉIS = prancha própria (tabela + 3D isolado + vista de cima)
for g_ in GAVETAS: _prancha_peca(g_, 'GAVETA MONTADA COM PAINÉIS', 'GAVETA')
for g_ in DIVISORES: _prancha_peca(g_, 'DIVISOR DE GAVETA', 'DIVISOR')

# ===== CAPA (design fixo: quadro externo + logo + cliente + EXECUTIVO - AMBIENTE) =====
_W, _H = doc[0].rect.width, doc[0].rect.height
doc.delete_page(0); cp = doc.new_page(0, width=_W, height=_H)
_lp = fz.open(cfg['layout'])[0]
_rs = [d_['rect'] for d_ in _lp.get_drawings() if d_['rect'].width > _W * 0.8 and d_['rect'].height > _H * 0.8]
fr = max(_rs, key=lambda r: r.width * r.height) if _rs else fz.Rect(17, 17, _W - 17, _H - 17)
AC = (0.78, 0.56, 0.29); CZ = (0.30, 0.30, 0.32); cx = (fr.x0 + fr.x1) / 2
cp.draw_rect(fz.Rect(fr.x0, fr.y0, fr.x0 + 10, fr.y1), color=None, fill=AC)
cp.draw_rect(fr, color=PRETO, width=1.2)
_lg = cfg.get('logo') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'LOGO.png')
yb = fr.y0 + 200
if _lg and os.path.exists(_lg):
    _im = fz.Pixmap(_lg); lw = 340; lh = lw * _im.height / _im.width
    cp.insert_image(fz.Rect(cx - lw / 2, fr.y0 + 90, cx + lw / 2, fr.y0 + 90 + lh), filename=_lg); yb = fr.y0 + 90 + lh
y = yb + 40
cp.draw_line((cx - 45, y), (cx + 45, y), color=AC, width=2)
_nm = cfg['dados']['cliente'].upper(); fs_ = 32
while fz.get_text_length(_nm, 'hebo', fs_) > fr.width - 140: fs_ -= 1
cp.insert_text((cx - fz.get_text_length(_nm, 'hebo', fs_) / 2, y + 50), _nm, fontname='hebo', fontsize=fs_, color=CZ)
_sb = 'EXECUTIVO - ' + cfg['dados']['ambiente'].upper()
cp.insert_text((cx - fz.get_text_length(_sb, 'helv', 16) / 2, y + 82), _sb, fontname='helv', fontsize=16, color=AC)
projeto_unificado.validar(PROJETO)  # Auditoria final: desenho/layout não alteraram as decisões da Etapa 4.
_gravar_biblioteca()
doc.save(cfg['saida'], garbage=3, deflate=True)   # BLINDAGEM: nome fixo; se falhar, falha (sem arquivo com horário)

# ---------------- QUALIDADE (nível 1, por script) ----------------
esperado = 4 + len(VW) + _extra + len(V) - sum(1 for v in V if v.get('divisoria')) + len(DIVISORES) + len(GAVETAS)
q = [f"# QUALIDADE — {cfg['dados']['cliente']} / {cfg['dados']['ambiente']} (gerado por script)", '',
     f"- {'APROVADO' if n == esperado else 'REPROVADO'} | nº de pranchas {n} = 4 + {len(VW)} listagens + {len(V)} cotas" + (f" + {len(DIVISORES)} divisor(es) de gaveta" if DIVISORES else '') + (f" + {len(GAVETAS)} gaveta(s) em painéis" if GAVETAS else '') + (f" | divisória ripada: {len(DIVISORIAS)}" if DIVISORIAS else ''),
     f"- {'APROVADO' if not _faltando_real else 'INCERTO'} | itens localizados no DXF: {len(linhas) - len(nao_achados)}/{len(linhas)}" + (f" ({len(_acessorios)} acessório(s) sem DXF — normal)" if _acessorios else '')]
for d, dm in _faltando_real: q.append(f"  - FORA DA LISTAGEM: {d} {dm} (não localizado no DXF, logo não aparece na imagem)")
for d, dm in _acessorios: q.append(f"  - ACESSÓRIO (sem DXF, normal): {d} {dm}")
q.append(f"- {'APROVADO' if confere else 'INCERTO'} | XML confere com o projeto (baseado em itens localizados no DXF)" + ('' if confere else f' — {len(_faltando_real)} item(ns) sem correspondência no DXF, ver acima'))
TEX_FALTA = [m_ for m_ in TEX_FALTA if not textura(m_)] + [m_ for m_, v_ in _cc.items() if not v_ and m_ in _todas_mats]
q.append(f"- {'APROVADO' if not TEX_FALTA else 'INCERTO'} | texturas dos materiais" + ('' if not TEX_FALTA else ' — faltando (sai cor lisa): ' + ', '.join(TEX_FALTA)))
for v in VW:
    _ex = []
    for w_ in v['paredes']:
        _nq = detalhes(PW[w_])
        if _nq: _ex.append(f"{len(_nq)} nicho(s) em subimagem")
        if PW[w_].get('perna_l'): _ex.append("perna do L com vista própria")
    q.append(f"- {v['titulo']}: paredes {', '.join(v['paredes'])} | {len(v['linhas'])} linhas de listagem" + (' | CONDIÇÕES -> ' + ', '.join(_ex) if _ex else ''))
q += [f"  {v['letra']}{i}: {d} {dm}" for v in VW for i, (d, dm, m_) in enumerate(v['linhas'], 1)]
open(os.path.splitext(cfg['saida'])[0] + '_QUALIDADE.md', 'w', encoding='utf-8').write('\n'.join(q))
print('\n'.join(q))
print('OK', cfg['saida'])
