# GEO — liga cada item da listagem (XML ou caderno) à sua posição real no DXF.
# Módulo = par de laterais (peças finas e altas) cujo volume bate com L x A x P.
# Painel/tamponamento = peça única cujas 3 medidas batem.
import json, re, itertools

TOL = 3.0

def num(s): return float(str(s).replace(',', '.'))

def parse_dim(dm):
    w, h, d = [num(x) for x in dm.lower().split('x')]
    return w, h, d

def eh_componente(desc):
    return bool(re.match(r'\s*(tampon|painel|vista|rodap|fecham|prateleira ext)', desc, re.I))

def carregar(path):
    P = json.load(open(path))
    for i, p in enumerate(P): p['i'] = i
    return P

def uniao(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]), max(a[4], b[4]), max(a[5], b[5])]

def dentro(b, U, tol=2.5):
    return all(b[k] >= U[k] - tol for k in range(3)) and all(b[k + 3] <= U[k + 3] + tol for k in range(3))

def laterais(P, zmin=150):
    out = []
    for p in P:
        dx, dy, dz = p['dim']
        if min(dx, dy) <= 26 and dz >= zmin and max(dx, dy) >= 150:
            p['eixo'] = 'x' if dx <= dy else 'y'
            out.append(p)
    return out

def casar(P, linhas, qtd=None, fontes=None):
    """linhas: [(desc, 'LxAxP')]. Retorna instâncias: dict(n, desc, dim, bb, tipo, pecas)."""
    # REGRA (v26): módulo BAIXO (adega/nicho de 150 mm) tem laterais de 100-150 mm -> entram só para módulo até 200 mm
    fontes = fontes or {}
    contagem = {}
    L = laterais(P, 100)
    usados = set(); inst = []
    # 1) componentes: peça única
    for n, (desc, dm) in enumerate(linhas, 1):
        if not (eh_componente(desc) or (fontes.get((desc, dm), {}).get("componente") and not fontes.get((desc, dm), {}).get("acessorio"))): continue
        alvo = sorted(parse_dim(dm)); lim = (qtd or {}).get((desc, dm)); pegou = 0
        for p in P:
            if lim is not None and pegou >= lim: break
            if p['i'] in usados: continue
            if all(abs(a - b) <= 1.6 for a, b in zip(sorted(p['dim']), alvo)):
                usados.add(p['i']); pegou += 1
                inst.append(dict(n=n, desc=desc, dim=dm, bb=p['bb'], tipo='comp', pecas=[p['i']]))
    # 2) módulos: par de laterais
    cands = []
    for n, (desc, dm) in enumerate(linhas, 1):
        if eh_componente(desc) or (fontes.get((desc, dm), {}).get("componente") and not fontes.get((desc, dm), {}).get("acessorio")): continue
        w, h, d = parse_dim(dm)
        orients = [(w, h, 0)]
        # REGRA (v26): módulo GIRADO no Promob (adega deitada: XML 150 x 870 x 600 = 870 de largura, 150 de altura)
        if h > 2 * w and w <= 300: orients.append((h, w, 5))
        for w, h, pen in orients: cands += _cands_mod(L, n, desc, dm, w, h, d, pen)
        if (desc, dm) in fontes:
            cands += _cands_fonte(P, n, desc, dm, fontes[(desc, dm)])
    cands.sort(key=lambda c: c[0])
    ocupado = []
    for e, n, desc, dm, ia, ib, U, wr in cands:
        if contagem.get(n, 0) >= (qtd or {}).get((desc, dm), float("inf")): continue
        if ia in usados or ib in usados: continue
        if any(_sobrepoe(U, O) for O in ocupado): continue
        usados.update((ia, ib)); ocupado.append(U)
        contagem[n] = contagem.get(n, 0) + 1
        tipo = 'comp' if min(parse_dim(dm)) <= 26 else 'mod'
        inst.append(dict(n=n, desc=desc, dim=dm, bb=U, tipo=tipo, pecas=[ia, ib], larg=wr))
    # peças internas de cada módulo (para o desenho), portas ficam fora porque estão à frente das laterais
    for it in inst:
        if it['tipo'] == 'mod' or len(it['pecas']) > 1:
            it['pecas'] = [p['i'] for p in P if dentro(p['bb'], it['bb'])]
    return inst


def _medidas_batem(a, b, tol=1.6):
    return all(abs(x-y) <= tol for x,y in zip(sorted(a), sorted(b)))


def corrigir_componentes_por_dxf(P, linhas, qtd, fontes, tol=1.6, limite=50.0):
    """Corrige metadado dimensional comprovadamente divergente do volume físico no DXF.

    Alguns XMLs do Promob mantêm a profundidade anterior de um painel após a geometria
    ser redimensionada. A correção só ocorre quando: (1) a espessura e uma dimensão
    estrutural batem; (2) a peça DXF é a única candidata ainda não usada; e (3) nenhum
    outro item XML pendente disputa essa candidata. Assim não se aumenta a tolerância
    geral nem se oculta peça ausente.
    """
    novas = list(linhas)
    usados = set()
    pendentes = []
    for n, (desc, dm) in enumerate(linhas):
        if not eh_componente(desc):
            continue
        alvo = sorted(parse_dim(dm))
        necessidade = (qtd or {}).get((desc, dm), 1)
        exatos = [p for p in P if p['i'] not in usados and _medidas_batem(p['dim'], alvo, tol)]
        for p in exatos[:necessidade]:
            usados.add(p['i'])
        if len(exatos) < necessidade:
            pendentes.append((n, desc, dm, alvo, necessidade - len(exatos)))
    propostas = []
    for n, desc, dm, alvo, falta in pendentes:
        if falta != 1 or not re.match(r'\s*(painel|tampon|vista|fecham)', desc, re.I):
            continue
        candidatos = []
        for p in P:
            if p['i'] in usados:
                continue
            d = sorted(p['dim'])
            dif = [abs(a-b) for a,b in zip(d, alvo)]
            # O caso reconciliável é uma expansão física mantida com a medida
            # anterior no metadado XML. Peças menores de módulos vizinhos não entram.
            if dif[0] <= tol and dif[2] <= tol and alvo[1] + tol < d[1] <= alvo[1] + limite:
                candidatos.append(p)
        if len(candidatos) == 1:
            propostas.append((n, desc, dm, candidatos[0]))
    disputados = {p['i'] for _,_,_,p in propostas if sum(q['i'] == p['i'] for *_,q in propostas) > 1}
    for n, desc, dm, p in propostas:
        if p['i'] in disputados:
            continue
        # Mantém a ordem semântica LxAxP do XML e troca somente a medida
        # divergente pela dimensão física comprovada no DXF.
        orig = list(parse_dim(dm)); fis = list(p['dim']); usados_fis = set()
        for i, v in enumerate(orig):
            j = next((j for j, x in enumerate(fis) if j not in usados_fis and abs(x-v) <= tol), None)
            if j is not None:
                usados_fis.add(j)
            else:
                orig[i] = next(x for j, x in enumerate(fis) if j not in usados_fis)
        novo_dm = 'x'.join(str(int(round(v))) if abs(v-round(v)) < 0.01 else ('%.1f' % v).replace('.', ',') for v in orig)
        chave_antiga = (desc, dm); chave_nova = (desc, novo_dm)
        novas[n] = chave_nova
        qtd[chave_nova] = qtd.pop(chave_antiga)
        if chave_antiga in fontes:
            fontes[chave_nova] = fontes.pop(chave_antiga)
        usados.add(p['i'])
        print('LEITURA XML/DXF: dimensão física corrigida | %s | XML=%s DXF=%s' % (desc, dm, novo_dm))
    return novas


def _cands_fonte(P, n, desc, dm, fonte):
    """Alternativas comprovadas pelas peças filhas do XML e coordenadas reais do DXF.

    Abrange módulo girado, laterais assimétricas, frente avulsa e conjunto
    de perfis. Não aumenta a tolerância geral nem altera medidas do XML.
    """
    if fonte.get('acessorio'): return []
    alvo = parse_dim(dm)
    filhos = fonte.get('filhos', [])
    cands = []
    # Peça avulsa ou módulo curvo exportado em uma camada com o volume inteiro.
    for p in P:
        if _medidas_batem(p['dim'], alvo):
            cands.append((6, n, desc, dm, p['i'], p['i'], p['bb'], alvo[0]))
    lat = [f for f in filhos if re.search(r'^(lat\b|lateral)', f['desc'], re.I)]
    bases = [f for f in filhos if re.search(r'^base', f['desc'], re.I)]
    if len(lat) >= 2:
        A = [p for p in P if _medidas_batem(p['dim'], lat[0]['dim'])]
        B = [p for p in P if _medidas_batem(p['dim'], lat[1]['dim'])]
        for a in A:
            for b in B:
                if a['i'] == b['i']: continue
                U = uniao(a['bb'], b['bb'])
                dims = [U[k+3]-U[k] for k in range(3)]
                exato = _medidas_batem(dims, alvo, TOL)
                # Canto reto: largura da caixa = base + duas espessuras.
                # O afastador pertence ao conjunto, não à largura da caixa.
                caixa = False
                if 'canto' in desc.lower() and bases:
                    esp = min(lat[0]['dim']) + min(lat[1]['dim'])
                    caixa = any(_medidas_batem(dims, (f['dim'][0]+esp, alvo[1], sorted(lat[0]['dim'])[1]), TOL) for f in bases)
                if not (exato or caixa): continue
                membros = [p for p in P if dentro(p['bb'], U)]
                # Uma base física confirma que não ligamos laterais de móveis vizinhos.
                if bases and not any(_medidas_batem(p['dim'], f['dim']) for p in membros for f in bases): continue
                if caixa:
                    # Porta cega e afastador têm medidas próprias no XML.
                    # Incluímos as peças reais adjacentes, sem ampliar uma caixa artificial.
                    for f in sorted(filhos, key=lambda f: 'porta cega' not in f['desc'].lower()):
                        if not re.search(r'porta cega|afastador', f['desc'], re.I): continue
                        proximos = []
                        for p in P:
                            if not _medidas_batem(p['dim'], f['dim']) or dentro(p['bb'], U): continue
                            dist = max(max(U[k]-p['bb'][k+3], p['bb'][k]-U[k+3], 0) for k in range(3))
                            E = uniao(U, p['bb'])
                            if dist <= 20 and all(x <= y+TOL for x,y in zip(sorted(E[k+3]-E[k] for k in range(3)), sorted(alvo))):
                                proximos.append((dist, p['i'], E))
                        if proximos: U = min(proximos)[2]
                cands.append((8, n, desc, dm, a['i'], b['i'], U, alvo[0]))
    # Conjunto sem laterais: perfis cuja união reproduz o tamanho do item.
    if filhos and not lat and len(filhos) <= 12:
        pool = [p for p in P if any(_medidas_batem(p['dim'], f['dim']) for f in filhos)]
        for a,b in itertools.combinations(pool,2):
            U = uniao(a['bb'],b['bb'])
            if not _medidas_batem([U[k+3]-U[k] for k in range(3)],alvo): continue
            membros = [p for p in pool if dentro(p['bb'],U)]
            restantes = list(membros)
            for f in filhos:
                for _ in range(f['qtd']):
                    p = next((p for p in restantes if _medidas_batem(p['dim'],f['dim'])),None)
                    if p is None: break
                    restantes.remove(p)
                else: continue
                break
            else:
                cands.append((8,n,desc,dm,a['i'],b['i'],U,alvo[0]))
    return cands

def _cands_mod(L, n, desc, dm, w, h, d, pen=0):
        cands = []
        tw, td = (45, 110) if 'canto' in desc.lower() else (TOL, 70)
        tz0 = 160 if 'rodap' in desc.lower() else TOL
        for a, b in itertools.combinations(L, 2):
            if h > 200 and min(a['dim'][2], b['dim'][2]) < 150: continue
            if abs(a['bb'][2] - b['bb'][2]) > tz0 or abs(a['bb'][5] - b['bb'][5]) > TOL: continue
            U = uniao(a['bb'], b['bb'])
            ux, uy, uz = U[3] - U[0], U[4] - U[1], U[5] - U[2]
            dh = h - uz
            if not (-TOL <= dh <= (260 if 'rodap' in desc.lower() else 45)): continue
            best = None
            for fw, fd in ((ux, uy), (uy, ux)):
                ew = abs(fw - w); ed = d - fd
                if ew <= tw and -TOL <= ed <= td:
                    e = ew + abs(dh) * (0.02 if 'rodap' in desc.lower() else 0.2) + max(0, ed) * 0.1
                    if best is None or e < best: best = e
            if best is None: continue
            if a['eixo'] == b['eixo']:
                ia = (a['bb'][1], a['bb'][4]) if a['eixo'] == 'x' else (a['bb'][0], a['bb'][3])
                ib = (b['bb'][1], b['bb'][4]) if b['eixo'] == 'x' else (b['bb'][0], b['bb'][3])
                if abs(ia[0] - ib[0]) > 30 or abs(ia[1] - ib[1]) > 30: continue
            cands.append((best + pen, n, desc, dm, a['i'], b['i'], U, w))
        return cands

def _sobrepoe(A, B, folga=5):
    return all(min(A[k + 3], B[k + 3]) - max(A[k], B[k]) > folga for k in range(3))

# ---------------- paredes e vistas ----------------
PAREDES = {  # f = direção do olhar (para dentro da parede)
    'y-': (0, -1), 'y+': (0, 1), 'x-': (-1, 0), 'x+': (1, 0)}

def limites(inst):
    return [min(i['bb'][0] for i in inst), min(i['bb'][1] for i in inst),
            max(i['bb'][3] for i in inst), max(i['bb'][4] for i in inst)]

def parede_de(it, lim, P):
    b = it['bb']
    dist = {'x-': b[0] - lim[0], 'x+': lim[2] - b[3], 'y-': b[1] - lim[1], 'y+': lim[3] - b[4]}
    dx, dy = b[3] - b[0], b[4] - b[1]
    if it['tipo'] == 'mod':
        a = P[it['pecas'][0]].get('eixo') if False else None
    # eixo ao longo da parede = maior extensão horizontal (módulo: largura; painel: comprimento)
    if it['tipo'] == 'mod':
        w = it.get('larg') or parse_dim(it['dim'])[0]
        ao_longo = 'x' if abs(dx - w) <= abs(dy - w) else 'y'
    else:
        ao_longo = 'x' if dx >= dy else 'y'
    ops = ('y-', 'y+') if ao_longo == 'x' else ('x-', 'x+')
    return min(ops, key=lambda k: dist[k])

def uz(p, f):
    """coordenada horizontal na elevação (esquerda->direita de quem olha a parede)"""
    return p[0] * f[1] - p[1] * f[0]

def caixa_elev(bb, f):
    us = [uz((x, y), f) for x in (bb[0], bb[3]) for y in (bb[1], bb[4])]
    return min(us), bb[2], max(us), bb[5]

def agrupar_vistas(inst, paredes):
    """junta paredes vizinhas com móveis encostando no mesmo canto (formando L). Máx. 2 por vista."""
    lim = limites(inst)
    cantos = {('x-', 'y-'): (lim[0], lim[1]), ('x+', 'y-'): (lim[2], lim[1]), ('x-', 'y+'): (lim[0], lim[3]), ('x+', 'y+'): (lim[2], lim[3])}
    liga = []
    for (a, b), (cx, cy) in cantos.items():
        if a not in paredes or b not in paredes: continue
        def perto(w):
            return sum(1 for i in inst if i['parede'] == w and
                       (abs(i['bb'][0] - cx) < 200 or abs(i['bb'][3] - cx) < 200) and (abs(i['bb'][1] - cy) < 200 or abs(i['bb'][4] - cy) < 200))
        s = min(perto(a), perto(b))
        if s: liga.append((s, a, b))
    liga.sort(reverse=True)
    grupo = {}
    for s, a, b in liga:
        if a in grupo or b in grupo: continue
        grupo[a] = grupo[b] = (a, b)
    vistas = []
    for w in paredes:
        g = grupo.get(w, (w,))
        if g not in vistas: vistas.append(g)
    return vistas

# ================= v2: parede pelo lado das portas =================
def _ov(a0, a1, b0, b1): return max(0.0, min(a1, b1) - max(a0, b0))

def lado_frontal(it, P, ocupadas=()):
    # REGRA: Prioriza portas/frentes. Se não houver, procura painéis (ilhas).
    U = it['bb']; dentro_ = set(it['pecas']) | set(ocupadas); area = {'-x': 0, '+x': 0, '-y': 0, '+y': 0}
    for p in P:
        if p['i'] in dentro_: continue
        b = p['bb']; dx, dy, dz = p['dim']
        oz = _ov(b[2], b[5], U[2], U[5])
        if dz <= 0 or oz < 0.5 * dz: continue
        desc = p.get('desc', '').lower()
        # Portas e frentes definem a face frontal com peso alto
        peso = 10.0 if re.search(r'(porta|frente|gaveta)', desc) else 1.0
        if dx <= 26:
            oy = _ov(b[1], b[4], U[1], U[4])
            if dy > 0 and oy >= 0.5 * dy:
                if abs(b[3] - U[0]) <= 35: area['-x'] += oy * oz * peso
                if abs(b[0] - U[3]) <= 35: area['+x'] += oy * oz * peso
        if dy <= 26:
            ox = _ov(b[0], b[3], U[0], U[3])
            if dx > 0 and ox >= 0.5 * dx:
                if abs(b[4] - U[1]) <= 35: area['-y'] += ox * oz * peso
                if abs(b[1] - U[4]) <= 35: area['+y'] += ox * oz * peso
    lado = max(area, key=area.get)
    # Mapeamento para garantir notação esperada pelo motor
    return lado if area[lado] > 0 else None

OPOSTO = {
    'x+': 'x-', 'x-': 'x+', 'y+': 'y-', 'y-': 'y+',
    '-x': 'x+', '+x': 'x-', '-y': 'y+', '+y': 'y-'
}

def plano(key, bb):
    return {'x+': bb[3], 'x-': bb[0], 'y+': bb[4], 'y-': bb[1]}[key]

def dist_caixas(A, B):
    d = [max(0, max(A[k], B[k]) - min(A[k + 3], B[k + 3])) for k in range(3)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5

def _ao_longo(it):
    b = it['bb']; dx, dy = b[3] - b[0], b[4] - b[1]
    if it['tipo'] == 'mod':
        w = it.get('larg') or parse_dim(it['dim'])[0]
        return 'x' if abs(dx - w) <= abs(dy - w) else 'y'
    return 'x' if dx >= dy else 'y'

def _montar(inst):
    paredes = []
    for it in sorted(inst, key=lambda i: i['tipo'] != 'mod'):
        k = it['parede_key']; pl = plano(k, it['bb'])
        alvo = next((w for w in paredes if w['key'] == k and abs(w['plano'] - pl) <= 60), None)
        if alvo is None:
            alvo = {'key': k, 'plano': pl, 'itens': []}; paredes.append(alvo)
        alvo['itens'].append(it)
    for w in paredes:
        w['id'] = f"{w['key']}@{round(w['plano'])}"
        for it in w['itens']: it['parede'] = w['id']
    return paredes

def definir_paredes(inst, P):
    lim = limites(inst)
    mods = [i for i in inst if i['tipo'] == 'mod']
    ocup = set()
    for i in inst: ocup.update(i['pecas'])
    # 1) módulos: lado das portas
    for it in mods:
        lf = lado_frontal(it, P, ocup)
        it['frente'] = lf
        it['parede_key'] = OPOSTO[lf] if lf else parede_de(it, lim, P)
    # 2) módulos: costas encostadas no plano de uma parede já formada, largura ao longo dela
    for _ in range(2):
        paredes = _montar(mods)
        for it in mods:
            eixo = _ao_longo(it)
            keys = ('y-', 'y+') if eixo == 'x' else ('x-', 'x+')
            cand = [w for w in paredes if w['key'] in keys and abs(plano(w['key'], it['bb']) - w['plano']) <= 30]
            if not cand: continue
            atual = next(w for w in paredes if w['id'] == it.get('parede'))
            melhor = max(cand, key=lambda w: len(w['itens']))
            if atual['key'] not in keys or len(melhor['itens']) > len(atual['itens']):
                it['parede_key'] = melhor['key']
    paredes = _montar(mods)
    # 3) componentes: mesma regra; senão herda do módulo mais próximo
    for it in inst:
        if it['tipo'] == 'mod': continue
        eixo = _ao_longo(it)
        keys = ('y-', 'y+') if eixo == 'x' else ('x-', 'x+')
        cand = [w for w in paredes if w['key'] in keys and abs(plano(w['key'], it['bb']) - w['plano']) <= 40]
        if cand:
            it['parede_key'] = max(cand, key=lambda w: len(w['itens']))['key']; continue
        m = min(mods, key=lambda m: dist_caixas(it['bb'], m['bb'])) if mods else None
        if m and dist_caixas(it['bb'], m['bb']) <= 400:
            it['parede_key'] = m['parede_key']; it['_forca'] = m['parede']
        else:
            it['parede_key'] = parede_de(it, lim, P); it['_solto'] = True
    # REGRA (v15): peça solta (tamponamento/painel) que não encosta em parede nem em módulo, mas ENCOSTA (até 60 mm)
    # em outra peça do projeto, vai para a parede dessa peça (ex.: tamponamento de apoio na ponta do painel).
    # Nunca forma uma parede (vista) sozinha.
    for it in inst:
        if not it.get('_solto'): continue
        viz = [o for o in inst if o is not it and not o.get('_solto')]
        o = min(viz, key=lambda o: dist_caixas(it['bb'], o['bb'])) if viz else None
        if o is not None and dist_caixas(it['bb'], o['bb']) <= 60:
            it['parede_key'] = o['parede_key']; it['_junto'] = o
    paredes = _montar([i for i in inst if not i.get('_forca') and not i.get('_junto')])
    for it in inst:
        if it.get('_forca'):
            w = next(w for w in paredes if w['id'] == it['_forca']); w['itens'].append(it); it['parede'] = w['id']
    for it in inst:
        if it.get('_junto'):
            alvo = it['_junto']
            while alvo.get('_junto'): alvo = alvo['_junto']
            w = next(w for w in paredes if w['id'] == alvo['parede']); w['itens'].append(it); it['parede'] = w['id']
    return paredes

def agrupar_vistas2(paredes, raio=650):
    """duas paredes perpendiculares com móveis chegando no mesmo canto formam uma vista (L)."""
    def perto(w, cx, cy):
        return any((abs(i['bb'][0] - cx) < raio or abs(i['bb'][3] - cx) < raio) and
                   (abs(i['bb'][1] - cy) < raio or abs(i['bb'][4] - cy) < raio) for i in w['itens'])
    liga = []
    for a in paredes:
        for b in paredes:
            if a is b or a['key'][0] != 'x' or b['key'][0] != 'y': continue
            cx, cy = a['plano'], b['plano']
            if perto(a, cx, cy) and perto(b, cx, cy):
                liga.append((len(a['itens']) + len(b['itens']), a['id'], b['id']))
    liga.sort(reverse=True); g = {}
    for s, a, b in liga:
        if a in g or b in g: continue
        g[a] = g[b] = (a, b)
    vistas = []
    ordem = sorted(paredes, key=lambda w: -len(w['itens']))
    for w in ordem:
        grupo = g.get(w['id'], (w['id'],))
        if grupo not in vistas: vistas.append(grupo)
    return vistas

