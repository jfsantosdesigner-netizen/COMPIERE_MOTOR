"""Relações especiais e separação de responsabilidade do fluxo normal."""
import re,geo
from .regras import Familia
def _sd(it): return sorted(parse_dim_(it['dim']))
def parse_dim_(dm):
    try: return [float(x) for x in re.findall(r'[\d.]+', dm.replace(',', '.'))[:3]]
    except Exception: return [0, 0, 0]
def _toca(a, b, tol=6): return geo.dist_caixas(a['bb'], b['bb']) <= tol

def separar_relacoes(ns):
    inst=ns['inst']; P=ns['P']; FV=ns['FV']; paredes=ns['paredes']; especiais=[]
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
    fora={id(i) for d in DIVISORIAS for i in d['itens']}|{id(i) for g in DIVISORES for i in g}
    for w in paredes: w['itens']=[i for i in w['itens'] if id(i) not in fora]
    paredes=[w for w in paredes if w['itens']]
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
        especiais.append(w); d['parede'] = w['id']
    ns.update(DIVISORIAS=DIVISORIAS,DIVISORES=DIVISORES,GAVETAS=GAVETAS,
              paredes=paredes,_paredes_especiais=especiais)
    from normal.regras import montar_gavetas
    montar_gavetas(ns)

def agrupar_paineis(ns):
    paredes=ns['paredes']; FV=ns['FV']; especiais=ns['_paredes_especiais']
    _faces_parede=ns['_faces_parede']
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
        fr_ = max(b, key=_af)
        from normal.regras import corpo_com_frente
        if corpo_com_frente(its_,fr_['key'],FV): continue
        f_ = FV[fr_['key']]; ad = 0 if f_[0] else 1; sg_ = f_[ad]; pl = fr_['plano']
        for fc in _faces_parede():
            vs = [v[ad] for v in fc]
            if max(vs) - min(vs) <= 1 and 0 < (vs[0] - pl) * sg_ <= 150: pl_ = vs[0]; break
        else: pl_ = pl
        for o in b: paredes.remove(o)
        nicho_ = any(re.match(r'tampon', i['desc'], re.I) for i in its_) and any(_sd(i)[0] <= 8 for i in its_)
        nw = dict(key=fr_['key'], plano=pl_, itens=its_, id=f"BLOCO@{round(pl_)}", divisoria=True, bloco='PAINEL COM NICHOS' if nicho_ else 'CONJUNTO DE PAINÉIS')
        for i in its_: i['parede'] = nw['id']
        especiais.append(nw); BLOCOS.append(nw)
    ns['BLOCOS']=BLOCOS
    ns['PW']={w['id']:w for w in paredes+especiais}

def separar_catalogo(ns):
    from .detector import detectar
    especiais=detectar(ns)
    ns['_especiais_detectados']=especiais
    ids=set()
    for esp in especiais:
        # Portas aplicadas e usinagens técnicas também permanecem nas vistas normais.
        if esp.familia in (Familia.PORTA_PERFIL,Familia.USINAGEM): continue
        ids.update(id(i) for i in esp.itens)
    normais=[]
    for w in ns['paredes']:
        its=[i for i in w['itens'] if id(i) not in ids]
        if its:
            copia=dict(w,itens=its); normais.append(copia); ns['PW'][w['id']]=copia
    ns['paredes']=normais
    ns['_ESPECIAL_I']={pi for esp in especiais for i in esp.itens if id(i) in ids for pi in i['pecas']}
    print('FLUXO NORMAL:',len(normais),'paredes;',len(especiais),'grupos destinados aos especiais')
