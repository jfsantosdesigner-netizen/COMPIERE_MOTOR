"""Orientação de detalhes montados, usando apenas as peças reais do conjunto."""
from .vidros import normalizar

FRENTES = {'x+': (1, 0), 'x-': (-1, 0), 'y+': (0, 1), 'y-': (0, -1)}


def portas_do_canto(ns, grupo):
    """Portas dentro da caixa do canto, comprovadas por ID e medidas do XML."""
    if not any('canto l' in normalizar(i['desc']) for i in grupo):
        return set()
    medidas = []
    for node in ns['XML_TREE'].iter('ITEM'):
        ident = node.get('ID','').upper()
        if not (ident.startswith('POR_') or '_POR_' in ident):
            continue
        if 'falsa' in normalizar(node.get('DESCRIPTION','')):
            continue
        try:
            dm = sorted(float(node.get(k,'0').replace(',','.')) for k in ('WIDTH','HEIGHT','DEPTH'))
        except ValueError:
            continue
        if dm[0] <= 30 and dm[1] >= 100 and dm[2] >= 100:
            medidas.append(dm)
    ids = {pi for i in grupo for pi in i['pecas']}
    return {p['i'] for p in ns['P'] if p['i'] in ids and
            any(all(abs(a-b)<=1.6 for a,b in zip(sorted(p['dim']),dm)) for dm in medidas)}


def _area_uniao(rects):
    xs = sorted({x for r in rects for x in (r[0], r[2])})
    area = 0.
    for a, b in zip(xs, xs[1:]):
        ys = sorted((r[1], r[3]) for r in rects if r[0] < b and r[2] > a)
        fim = None
        for c, d in ys:
            inicio = c if fim is None else max(c, fim)
            area += (b-a)*max(0, d-inicio)
            fim = d if fim is None else max(fim, d)
    return area


def orientar(grupo, pecas, chave, portas=()):
    """Subimagem oblíqua; gavetas mantêm sua câmera funcional já definida.

    Uma câmera da parede só é trocada quando os painéis reais comprovam
    que ela olha para uma face fechada e outra direção revela a abertura.
    Nenhuma dimensão, associação, peça ou regra de listagem é alterada.
    """
    gaveta = next((i for i in grupo if i.get('_gaveta_montada')), None)
    if gaveta:
        return dict(camera_key=gaveta['_camera_detalhe_key'], ang=15, elev=22)
    # Regra explícita de João Felipe: prevalece sobre qualquer escolha geométrica.
    nome = normalizar(' '.join(i['desc'] for i in grupo))
    if 'canto reto' in nome:
        return dict(camera_key=chave, ang=0, elev=20)
    canto_l = 'canto l' in nome and ('direito' in nome or 'esquerdo' in nome)
    ang_canto = 45 if 'direito' in nome else -45
    ids = {pi for i in grupo for pi in i['pecas']} - set(portas)
    caixas = [p['bb'] for p in pecas if p['i'] in ids]
    if not caixas:
        if canto_l: return dict(camera_key=chave,ang=ang_canto,elev=20)
        return dict(camera_key=chave, ang=0, elev=0)
    bb = [min(b[k] for b in caixas) for k in range(3)] + [max(b[k+3] for b in caixas) for k in range(3)]
    ext = [bb[k+3]-bb[k] for k in range(3)]
    cobertura = {}
    for key, f in FRENTES.items():
        ad = 0 if f[0] else 1
        al = 1-ad
        plano = bb[ad] if f[ad] > 0 else bb[ad+3]
        rects = []
        for b in caixas:
            if b[ad+3]-b[ad] > 30 or b[5]-b[2] <= 30:
                continue
            face = b[ad] if f[ad] > 0 else b[ad+3]
            if abs(face-plano) <= 60:
                rects.append((b[al], b[2], b[al+3], b[5]))
        cobertura[key] = _area_uniao(rects)/max(1, ext[al]*ext[2])
    horizontais = sum(b[5]-b[2] <= 30 for b in caixas)
    corpo = len(caixas) >= 3 and horizontais >= 2
    if canto_l:
        if corpo:
            # Frente local do módulo: os dois lados mais abertos do L, em
            # contraste com as costas. O ângulo prescrito não é otimizado.
            pares = {}
            for key, f in FRENTES.items():
                direcao = (-f[1],f[0]) if ang_canto > 0 else (f[1],-f[0])
                outra = next(k for k,v in FRENTES.items() if v==direcao)
                pares[key] = cobertura[key]+cobertura[outra]
            melhor = min(pares,key=lambda k:(pares[k],k!=chave))
            if max(pares.values())-pares[melhor] >= .25:
                chave = melhor
        return dict(camera_key=chave,ang=ang_canto,elev=20)
    if corpo:
        melhor = min(cobertura, key=lambda k: (cobertura[k], k != chave))
        if cobertura[chave]-cobertura[melhor] >= .25:
            chave = melhor
    elif min(ext[:2]) <= 30 and ext[2] > 30:
        # Peça vertical isolada: a subimagem deve revelar sua face, não a espessura.
        eixo = 'x' if ext[0] <= ext[1] else 'y'
        chave = eixo + chave[-1]
    ang, elev = 18, 15
    if ext[2] <= 150:
        # Adega deitada precisa conservar a leitura dos vãos frontais; uma
        # chapa isolada precisa mostrar a superfície de apoio.
        elev = 8 if corpo else 30
    elif ext[2] > 1800:
        elev = 10
    return dict(camera_key=chave, ang=ang, elev=elev)


def tampas_modulos_deitados(grupo, pecas):
    """Tampas acima de uma caixa deitada, com fundo fino embaixo.

    Exige as duas superfícies reais no DXF; não remove painéis verticais,
    portas decorativas ou módulos normalmente montados em pé.
    """
    por_id = {p['i']: p for p in pecas}
    tampas = set()
    for item in grupo:
        if item.get('tipo') != 'mod' or 'canto' in normalizar(item.get('desc','')):
            continue
        b = item['bb']
        larg, prof = b[3]-b[0], b[4]-b[1]
        area = larg * prof
        if area <= 0 or b[5]-b[2] > 1000:
            continue
        placas = [por_id[pi] for pi in item['pecas'] if pi in por_id]
        def cobertura(p):
            q=p['bb']
            return max(0,min(q[3],b[3])-max(q[0],b[0])) * max(0,min(q[4],b[4])-max(q[1],b[1]))
        fundos=[p for p in placas if p['bb'][5]-p['bb'][2]<=10
                and b[2]-2<=p['bb'][2]<=b[2]+30 and cobertura(p)>=.60*area]
        caps=[p for p in placas if p['bb'][5]-p['bb'][2]<=30
              and b[5]-2<=p['bb'][2]<=b[5]+5 and cobertura(p)>=.60*area]
        if fundos and len(caps)==1:
            tampas.add(caps[0]['i'])
    return tampas
