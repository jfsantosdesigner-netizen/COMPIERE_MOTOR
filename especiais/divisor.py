"""Ferramenta de detalhe superior do divisor, fora do fluxo normal."""
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
