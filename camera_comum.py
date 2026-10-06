"""Câmeras executivas compartilhadas pelo motor normal e pelos especiais.

Medidas em mm. Apenas seleção visual: nenhuma geometria é movida ou cortada.
"""
from itertools import product

ALTURA_OLHOS = 1500
FOLGA_CAMERA = 200


def cantos(b):
    return [tuple(b[k + j] for k, j in enumerate(js))
            for js in product((0, 3), repeat=3)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unir(bbs):
    return [min(b[k] for b in bbs) for k in range(3)] + [max(b[k+3] for b in bbs) for k in range(3)]


def posicionar(alvo, frente, distancia_minima, ambiente=False, caixas=()):
    """Câmera nivelada à altura dos olhos no ambiente; centro no detalhe.

    Recuo antes de todo o mobiliário/modelo evita colocar a câmera dentro
    de uma peça vizinha ou atravessar o plano próximo da projeção.
    """
    centro = tuple((alvo[k]+alvo[k+3])/2 for k in range(3))
    if ambiente:
        centro = (centro[0], centro[1], ALTURA_OLHOS)
    distancia = max(max(alvo[k+3]-alvo[k] for k in range(3))*1.9,
                    distancia_minima, 7000 if ambiente else 0)
    caixas = list(caixas) + [alvo]
    proximo = min(dot(tuple(v[k]-centro[k] for k in range(3)), frente)
                  for b in caixas for v in cantos(b))
    distancia = max(distancia, FOLGA_CAMERA-proximo)
    camera = tuple(centro[k]-frente[k]*distancia for k in range(3))
    return centro, distancia, camera


def obstaculos(itens, pecas, alvos, frente):
    """Retira entidades inteiras à frente do alvo, nunca o próprio alvo.

    Só vistas frontais niveladas: sobreposição nos eixos de largura/altura
    e separação em profundidade. Não confundir peças internas com obstáculos.
    """
    if abs(frente[2]) > 1e-8 or min(abs(frente[0]), abs(frente[1])) > 1e-8:
        return set()
    ax = 0 if abs(frente[0]) > .5 else 1
    lateral = 1-ax
    sinal = frente[ax]
    bbs_alvo = [p['bb'] for p in pecas if p['i'] in alvos]
    removidos = set()
    def bloqueia(b):
        fundo = max(b[ax]*sinal, b[ax+3]*sinal)
        return any(fundo < min(t[ax]*sinal, t[ax+3]*sinal)-25 and
                   min(b[lateral+3],t[lateral+3])-max(b[lateral],t[lateral]) > 10 and
                   min(b[5],t[5])-max(b[2],t[2]) > 10 for t in bbs_alvo)
    cobertas = set()
    por_id = {p['i']:p for p in pecas}
    for item in itens:
        ids = set(item['pecas'])
        cobertas.update(ids)
        if ids & alvos:
            continue
        if bloqueia(item['bb']) or any(bloqueia(por_id[pi]['bb']) for pi in ids if pi in por_id):
            removidos.update(ids)
    for p in pecas:
        if p['i'] not in cobertas and p['i'] not in alvos and bloqueia(p['bb']):
            removidos.add(p['i'])
    return removidos


def enquadrar(alvo, lateral, vizinhos=()):
    """Conjunto completo, piso e folga; vizinhos próximos entram inteiros."""
    b = list(alvo)
    for v in vizinhos:
        if v[lateral] >= alvo[lateral]-700 and v[lateral+3] <= alvo[lateral+3]+700:
            b[lateral] = min(b[lateral],v[lateral])
            b[lateral+3] = max(b[lateral+3],v[lateral+3])
            b[5] = max(b[5],v[5])
    b[lateral] -= 300
    b[lateral+3] += 300
    b[2] = min(0,alvo[2])
    b[5] = max(b[5]+150,2000)
    folga = max(0,2200-(b[lateral+3]-b[lateral]))/2
    b[lateral] -= folga
    b[lateral+3] += folga
    return b
