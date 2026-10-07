# -*- coding: utf-8 -*-
"""
classificacao.py — Fase 1 da reorganizacao do motor Compiere.

Funcao pura: classificar_peca(peca, contexto) -> tipo (str)

Tipos: MODULO_COMUM, CANTO_L_ESQ, CANTO_L_DIR, CANTO_RETO,
       NICHO, PAINEL_OCULTO, RODAPE_OCULTO

Regra de canto (autoridade = nomenclatura do XML, geometria so valida):
  - "Canto L"    -> CANTO_L_ESQ / CANTO_L_DIR (lado = "Esquerdo"/"Direito" do XML)
  - "Canto Reto" -> CANTO_RETO (o Esq/Dir do XML nao muda o tipo)
  - Cantoneira / Suporte / Dobradica nunca sao canto.
  A decisao NAO depende de geometria; validar_canto() so confirma (Fase 1: relatorio).
"""
import unicodedata
import geo  # geo.uniao: pura, reaproveitada

NICHO_MIN_RATIO  = 0.4
NICHO_LARG_MAX   = 2000.0
NICHO_ALT_MAX    = 1200.0
NICHO_MIN_PECAS  = 3
NICHO_MIN_HORIZ  = 2

CANTO_TOL_PAREDE = 200.0   # folga real medida ate o limite do ambiente: ate ~180 mm
CANTO_EXT_MIN    = 300.0

RODAPE_PISO_TOL   = 30.0   # peca apoiada no piso: z0 ate 30 mm acima do piso
RODAPE_SOBRE_TOL  = 20.0   # modulo em cima: z0 do modulo >= topo da peca - 20 mm
RODAPE_SOBREPOSICAO = 0.5  # fracao da planta da peca coberta pelo modulo
OCLUSAO_MIN_RATIO = 0.6
ARQ_ESP_MIN       = 60.0   # peca sem item no XML com as 3 dimensoes >= 60 mm = parede/pilar/casca, nao movel (tampo e frente sao finos)
ILHA_ALT_MAX      = 1300.0  # modulo baixo (balcao/ilha)
ILHA_FOLGA        = 30.0    # painel encostado na traseira do modulo
ILHA_PAREDE_MIN   = 300.0   # menos que isso atras = ha parede, nao e ilha
GRUPO_TOL         = 5.0    # pecas soltas se tocam se a folga entre bbs <= 5 mm

TIPOS = ('MODULO_COMUM', 'CANTO_L_ESQ', 'CANTO_L_DIR', 'CANTO_RETO',
         'NICHO', 'PAINEL_OCULTO', 'RODAPE_OCULTO')

_NAO_CANTO = ('cantoneira', 'suporte', 'dobradica')


def classificar_peca(peca, contexto):
    if peca.get('tipo') == 'grupo' or 'itens' in peca:
        return 'MODULO_COMUM'

    if peca.get('tipo') == 'mod':
        canto = _canto_por_nomenclatura(peca.get('desc', ''))
        if canto is not None:
            return canto
        if _eh_nicho_modulo(peca, contexto):
            return 'NICHO'
        return 'MODULO_COMUM'

    if peca.get('tipo') == 'comp':
        if _eh_nicho_conjunto(_grupo_de(peca, contexto), contexto):
            return 'NICHO'
        if _eh_oculto(peca, contexto):
            return 'RODAPE_OCULTO' if _eh_rodape(peca, contexto) else 'PAINEL_OCULTO'
        return 'MODULO_COMUM'

    return 'MODULO_COMUM'


def _nome_tem_porta(desc):
    d = ' ' + _norm(desc) + ' '
    return any(' ' + k + ' ' in d for k in ('porta', 'portas', 'gaveta', 'gavetas', 'gaveteiro', 'basculante'))


def _norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _canto_por_nomenclatura(desc):
    d = ' ' + _norm(desc) + ' '
    if any(x in d for x in _NAO_CANTO):
        return None
    if ' canto reto ' in d:
        return 'CANTO_RETO'
    if ' canto l ' in d:
        if 'esquerd' in d:
            return 'CANTO_L_ESQ'
        if 'direit' in d:
            return 'CANTO_L_DIR'
    return None


def paredes_tocadas(peca, contexto):
    """Paredes do limite do ambiente que o modulo toca (folga <= CANTO_TOL_PAREDE)."""
    lim, b = contexto['lim'], peca['bb']
    d = {'x-': b[0] - lim[0], 'x+': lim[2] - b[3], 'y-': b[1] - lim[1], 'y+': lim[3] - b[4]}
    return sorted(k for k, v in d.items() if abs(v) <= CANTO_TOL_PAREDE)


def validar_canto(peca, contexto):
    """True se a geometria confirma a nomenclatura. L: duas paredes perpendiculares.
    Reto: ao menos uma parede. Nao-canto: True."""
    tipo = _canto_por_nomenclatura(peca.get('desc', ''))
    if tipo is None:
        return True
    tocadas = paredes_tocadas(peca, contexto)
    if tipo == 'CANTO_RETO':
        return len(tocadas) >= 1
    return any(k[0] == 'x' for k in tocadas) and any(k[0] == 'y' for k in tocadas)


def _area_uniao(rects):
    """Area da uniao de retangulos (x0, y0, x1, y1)."""
    if not rects:
        return 0.0
    xs = sorted(set([r[0] for r in rects] + [r[2] for r in rects]))
    ys = sorted(set([r[1] for r in rects] + [r[3] for r in rects]))
    area = 0.0
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2.0
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2.0
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects):
                area += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return area


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


def _eh_porta(b, mb, f):
    """Porta/frente de gaveta/basculante/porta de correr = chapa fina (<= 30 mm na profundidade)
    na FRENTE do modulo (150 mm a frente ate 80 mm para dentro), dentro da largura/altura do modulo
    (folga 60 mm). Nao e porta: chapa que vai da base ao topo do modulo e cobre >= metade da largura
    (lateral/fechamento do proprio modulo). f = direcao do olhar (dx, dy). Mesma regra do motor antigo."""
    ad = 0 if f[0] else 1
    al = 1 - ad
    sg = f[ad]
    perto = lambda bb: min(bb[ad] * sg, bb[ad + 3] * sg)
    fr = perto(mb)
    if b[ad + 3] - b[ad] > 30 or (b[al + 3] - b[al]) < 100 or (b[5] - b[2]) < 60:
        return False
    if not (fr - 150 <= perto(b) <= fr + 80):
        return False
    if b[al] < mb[al] - 60 or b[al + 3] > mb[al + 3] + 60 or b[2] < mb[2] - 60 or b[5] > mb[5] + 60:
        return False
    if perto(b) >= fr - 1 and abs(b[2] - mb[2]) <= 2 and abs(b[5] - mb[5]) <= 2 \
            and (b[al + 3] - b[al]) >= 0.5 * (mb[al + 3] - mb[al]):
        return False
    return True


def _cobertura_portas(peca, contexto):
    """Fracao da face frontal do modulo coberta por portas/frentes (pecas do DXF, proprias ou nao)."""
    f = contexto.get('eixo_vista')
    if not f:
        return 0.0
    mb = peca['bb']
    al = 1 if f[0] else 0
    area = (mb[al + 3] - mb[al]) * (mb[5] - mb[2])
    if area <= 0:
        return 0.0
    cob = 0.0
    for p in contexto['P']:
        b = p['bb']
        if not _eh_porta(b, mb, f):
            continue
        cob += max(0.0, min(b[al + 3], mb[al + 3]) - max(b[al], mb[al])) * \
               max(0.0, min(b[5], mb[5]) - max(b[2], mb[2]))
    return cob / area


def _eh_nicho_modulo(peca, contexto):
    """Modulo sem porta e sem frente. Frente (gaveta) ou porta (armario) => nunca e nicho.
    Porta de vidro/espelho nao esta no DXF: o XML (xml_tem_porta) ou o nome decide."""
    b = peca['bb']
    if max(b[3] - b[0], b[4] - b[1]) > NICHO_LARG_MAX or (b[5] - b[2]) > NICHO_ALT_MAX:
        return False
    if peca.get('xml_tem_porta') or _nome_tem_porta(peca.get('desc', '')):
        return False
    f = contexto.get('eixo_vista')
    if f and any(_eh_porta(contexto['P'][pi]['bb'], b, f) for pi in peca.get('pecas', [])):
        return False   # tem frente/porta propria (mesmo parcial: gaveta, basculante) => nao e nicho
    if _cobertura_portas(peca, contexto) >= NICHO_MIN_RATIO:
        return False   # porta de outra peca (avulsa) cobrindo a face
    return _cobertura_frontal_max(peca, contexto['P']) < NICHO_MIN_RATIO


def _grupo_de(peca, contexto):
    """Pecas soltas (comp) da mesma parede ligadas a 'peca' por contato (folga <= GRUPO_TOL),
    transitivamente. Nao ha conjunto definido no XML: o grupo nasce do contato."""
    soltas = [i for i in contexto['soltas'] if i['tipo'] == 'comp']
    grupo, fila = [peca], [peca]
    visto = {id(peca)}
    while fila:
        a = fila.pop()['bb']
        for o in soltas:
            if id(o) in visto:
                continue
            ob = o['bb']
            if all(min(a[k + 3], ob[k + 3]) - max(a[k], ob[k]) >= -GRUPO_TOL for k in range(3)):
                visto.add(id(o)); grupo.append(o); fila.append(o)
    return grupo


def _eh_nicho_conjunto(itens, contexto):
    """Grupo de pecas soltas SEM porta: >=3 pecas, >=2 horizontais, tamanho de nicho
    (peca grande nao e nicho) e frente nao coberta por moveis (porta)."""
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
    if largura > NICHO_LARG_MAX or altura > NICHO_ALT_MAX:
        return False
    visiveis = sum(1 for i in itens if not _eh_oculto(i, contexto))
    return visiveis * 2 >= len(itens)


def _eh_arquitetura(o, moveis):
    """Peca fora do XML e grossa nas 3 dimensoes (parede, pilar, casca) ou o piso.
    Frente de porta/gaveta tambem nao casa com o XML, mas e fina: continua cobrindo."""
    if o['i'] in moveis:
        return False
    return o['layer'] == 'LAYER0' or min(o['dim']) >= ARQ_ESP_MIN


def _eh_oculto(peca, contexto):
    eixo = contexto.get('eixo_vista')
    if eixo is None:
        return False
    ad = 0 if eixo[0] else 1
    al = 1 - ad
    sinal = eixo[ad]
    b = peca['bb']
    face = b[ad] if sinal > 0 else b[ad + 3]
    area_face = max(1.0, (b[al + 3] - b[al]) * (b[5] - b[2]))
    excluir = set(peca.get('pecas', []))
    moveis = contexto['moveis']   # indices das pecas casadas com itens do XML
    rects = []
    for o in contexto['P']:
        if o['i'] in excluir or _eh_arquitetura(o, moveis):
            continue
        ob = o['bb']
        frente_o = ob[ad] if sinal > 0 else ob[ad + 3]
        if (face - frente_o) * sinal <= 5:   # 'o' precisa estar MAIS perto da camera que a face
            continue
        r = (max(ob[al], b[al]), max(ob[2], b[2]), min(ob[al + 3], b[al + 3]), min(ob[5], b[5]))
        if r[2] > r[0] and r[3] > r[1]:
            rects.append(r)
    return (_area_uniao(rects) / area_face) >= OCLUSAO_MIN_RATIO


def _piso_z(P):
    """Cota do piso = topo da placa LAYER0 do ambiente (0 se nao houver)."""
    return max([p['bb'][5] for p in P if p['layer'] == 'LAYER0'] or [0.0])


def _eh_rodape(peca, contexto):
    """Rodape/base = peca oculta, apoiada no piso, com modulo em cima dela
    (balcao, guarda-roupa, criado-mudo...). Oculta fora disso = PAINEL_OCULTO."""
    b = peca['bb']
    if b[2] - _piso_z(contexto['P']) > RODAPE_PISO_TOL:
        return False
    area = max(1.0, (b[3] - b[0]) * (b[4] - b[1]))
    for m in contexto['soltas']:
        if m['tipo'] != 'mod':
            continue
        mb = m['bb']
        if mb[2] < b[5] - RODAPE_SOBRE_TOL:
            continue
        ox = max(0.0, min(mb[3], b[3]) - max(mb[0], b[0]))
        oy = max(0.0, min(mb[4], b[4]) - max(mb[1], b[1]))
        if ox * oy / area >= RODAPE_SOBREPOSICAO:
            return True
    return False


def painel_traseiro_ilha(peca, contexto):
    """True se a peca e painel de acabamento ATRAS de uma ilha: oculta, encostada
    (<= ILHA_FOLGA) na traseira de modulos baixos que cobrem >= 50% da sua largura, e SEM
    parede/pilar/casca a menos de ILHA_PAREDE_MIN atras dela. O tipo continua PAINEL_OCULTO;
    o desenho usa este indicador para gerar a subimagem da traseira da ilha."""
    eixo = contexto.get('eixo_vista')
    if eixo is None or peca.get('tipo') != 'comp' or not _eh_oculto(peca, contexto):
        return False
    ad = 0 if eixo[0] else 1
    al = 1 - ad
    sinal = eixo[ad]
    b = peca['bb']
    frente = b[ad] if sinal > 0 else b[ad + 3]      # face voltada para a camera
    fundo = b[ad + 3] if sinal > 0 else b[ad]       # face voltada para a parede
    cobertos = 0.0
    for m in contexto['soltas']:
        if m['tipo'] != 'mod' or m['bb'][5] > ILHA_ALT_MAX:
            continue
        mb = m['bb']
        traseira = mb[ad + 3] if sinal > 0 else mb[ad]
        if abs(traseira - frente) > ILHA_FOLGA:
            continue
        cobertos += max(0.0, min(mb[al + 3], b[al + 3]) - max(mb[al], b[al]))
    if cobertos < 0.5 * (b[al + 3] - b[al]):
        return False
    moveis = contexto['moveis']
    for o in contexto['P']:
        if o['i'] in moveis or not _eh_arquitetura(o, moveis) or o['layer'] == 'LAYER0':
            continue
        ob = o['bb']
        if min(ob[al + 3], b[al + 3]) - max(ob[al], b[al]) <= 0:
            continue
        if ob[ad] <= b[ad] and ob[ad + 3] >= b[ad + 3]:        # casca que contem a peca
            dist = (ob[ad + 3] - fundo) if sinal > 0 else (fundo - ob[ad])
        else:                                                  # parede/pilar atras
            dist = (ob[ad] - fundo) if sinal > 0 else (fundo - ob[ad + 3])
            if dist < -5:
                continue
        if dist < ILHA_PAREDE_MIN:
            return False
    return True
