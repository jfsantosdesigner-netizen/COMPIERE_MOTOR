# Extrai do DXF do Promob as peças (1 camada = 1 peça) com bounding box e faces.
# LEITOR ROBUSTO (2026-09-28, ordem do João): expandido para não deixar peça sumir.
#   - 3DFACE, POLYLINE (3D)           -> faces + bbox (comportamento original preservado)
#   - LWPOLYLINE                       -> pontos 2D no Z do plano da entidade -> bbox
#   - LINE                             -> 2 pontos -> bbox
#   - CIRCLE / ARC / ELLIPSE           -> flatten em segmentos -> bbox
#   - SPLINE                           -> flatten em vertices  -> bbox
#   - INSERT (blocos, incl. aninhados) -> virtual_entities() em cascata (transforma p/ WCS)
#   - 3DSOLID / SOLID3D / BODY / REGION-> MeshBuilder.from_mesh() -> faces triangulares + bbox
# 1 layer DXF = 1 peça. A layer usada é a da PRIMEIRA entidade encontrada na cadeia (topo do INSERT).
# Uso: python dxf_pecas.py arquivo.dxf saida.json
import sys, json, math
import ezdxf

sys.stdout.reconfigure(encoding='utf-8')


def _push_vertex(peca, v):
    """Atualiza o bounding box da peça com um vértice (x,y,z)."""
    b = peca['bb']
    for i in range(3):
        if v[i] < b[i]: b[i] = v[i]
        if v[i] > b[i + 3]: b[i + 3] = v[i]


def _push_face(peca, vs):
    """Adiciona uma face (lista de 3 ou 4 vértices) à peça, também atualizando bbox."""
    for v in vs: _push_vertex(peca, v)
    face = [[round(c, 1) for c in v] for v in vs]
    # motor original espera 4 vértices por face -> se vier triangulo, duplica o último
    if len(face) == 3: face.append(face[-1])
    peca['faces'].append(face)


def _bbox_arco(cx, cy, cz, raio, ini_deg, fim_deg, n=32):
    """Discretiza arco/circulo em vértices para o bbox."""
    if fim_deg < ini_deg: fim_deg += 360
    return [(cx + raio * math.cos(math.radians(ini_deg + (fim_deg - ini_deg) * k / n)),
             cy + raio * math.sin(math.radians(ini_deg + (fim_deg - ini_deg) * k / n)),
             cz) for k in range(n + 1)]


def _processar(entidade, layer_pai, pecas):
    """Processa uma entidade. layer_pai preserva a layer do INSERT que a originou (se houver)."""
    tipo = entidade.dxftype()
    # layer: prefere a da entidade; se veio de dentro de um INSERT ('0' vira herdada), usa a do pai
    layer = entidade.dxf.layer if hasattr(entidade.dxf, 'layer') else layer_pai
    if layer_pai is not None and (layer == '0' or not layer):
        layer = layer_pai
    p = pecas.setdefault(layer, {'bb': [1e18, 1e18, 1e18, -1e18, -1e18, -1e18], 'faces': []})

    # ------ INSERT: expande recursivamente (blocos aninhados) ------
    if tipo == 'INSERT':
        try:
            for sub in entidade.virtual_entities():
                _processar(sub, layer_pai=layer, pecas=pecas)
        except Exception as e:
            print(f'  AVISO: INSERT layer="{layer}" nao pode ser expandido: {e}', file=sys.stderr)
        return

    # ------ 3DFACE ------
    if tipo == '3DFACE':
        try:
            vs = [(v.x, v.y, v.z) for v in (entidade.dxf.vtx0, entidade.dxf.vtx1,
                                             entidade.dxf.vtx2, entidade.dxf.vtx3)]
            _push_face(p, vs)
        except Exception:
            pass
        return

    # ------ POLYLINE (3D) ------
    if tipo == 'POLYLINE':
        try:
            vs = [tuple(v.dxf.location) for v in entidade.vertices]
            for v in vs: _push_vertex(p, v)
        except Exception:
            pass
        return

    # ------ LWPOLYLINE ------
    if tipo == 'LWPOLYLINE':
        try:
            z = float(getattr(entidade.dxf, 'elevation', 0.0) or 0.0)
            for pt in entidade.get_points('xy'):
                _push_vertex(p, (float(pt[0]), float(pt[1]), z))
        except Exception:
            pass
        return

    # ------ LINE ------
    if tipo == 'LINE':
        try:
            s = entidade.dxf.start; e_ = entidade.dxf.end
            _push_vertex(p, (s.x, s.y, s.z))
            _push_vertex(p, (e_.x, e_.y, e_.z))
        except Exception:
            pass
        return

    # ------ CIRCLE ------
    if tipo == 'CIRCLE':
        try:
            c = entidade.dxf.center; r = float(entidade.dxf.radius)
            for v in _bbox_arco(c.x, c.y, c.z, r, 0, 360, n=24):
                _push_vertex(p, v)
        except Exception:
            pass
        return

    # ------ ARC ------
    if tipo == 'ARC':
        try:
            c = entidade.dxf.center; r = float(entidade.dxf.radius)
            a0 = float(entidade.dxf.start_angle); a1 = float(entidade.dxf.end_angle)
            for v in _bbox_arco(c.x, c.y, c.z, r, a0, a1, n=24):
                _push_vertex(p, v)
        except Exception:
            pass
        return

    # ------ ELLIPSE ------
    if tipo == 'ELLIPSE':
        try:
            # flatten() ja discretiza; fallback: 32 pontos
            try:
                for v in entidade.flattening(distance=0.5):
                    _push_vertex(p, (v.x, v.y, v.z))
            except Exception:
                c = entidade.dxf.center
                for k in range(33):
                    ang = 2 * math.pi * k / 32
                    _push_vertex(p, (c.x + math.cos(ang), c.y + math.sin(ang), c.z))
        except Exception:
            pass
        return

    # ------ SPLINE ------
    if tipo == 'SPLINE':
        try:
            for v in entidade.flattening(distance=0.5):
                _push_vertex(p, (v.x, v.y, v.z))
        except Exception:
            try:
                for v in entidade.control_points:
                    _push_vertex(p, (v.x, v.y, v.z))
            except Exception:
                pass
        return

    # ------ 3DSOLID / BODY / REGION ------
    if tipo in ('3DSOLID', 'SOLID3D', 'BODY', 'REGION'):
        try:
            mesh = entidade.mesh()   # retorna MeshBuilder em ezdxf >= 1.0
            verts = list(mesh.vertices)
            for face in mesh.faces:
                vs = [verts[i] for i in face]
                if len(vs) < 3:
                    for v in vs: _push_vertex(p, (v[0], v[1], v[2]))
                    continue
                # triangulariza em fan; face de 3 ou 4 pontos vira 1 face
                if len(vs) <= 4:
                    _push_face(p, [(v[0], v[1], v[2]) for v in vs])
                else:
                    for k in range(1, len(vs) - 1):
                        _push_face(p, [(vs[0][0], vs[0][1], vs[0][2]),
                                       (vs[k][0], vs[k][1], vs[k][2]),
                                       (vs[k + 1][0], vs[k + 1][1], vs[k + 1][2])])
        except Exception as e:
            # se ACIS binario nao puder ser lido, ao menos registra a layer com bbox degenerado
            print(f'  AVISO: 3DSOLID layer="{layer}" sem mesh disponivel: {e}', file=sys.stderr)
        return

    # ------ SOLID / TRACE (2D preenchido, 4 vertices) ------
    if tipo in ('SOLID', 'TRACE'):
        try:
            vs = [(entidade.dxf.vtx0.x, entidade.dxf.vtx0.y, entidade.dxf.vtx0.z),
                  (entidade.dxf.vtx1.x, entidade.dxf.vtx1.y, entidade.dxf.vtx1.z),
                  (entidade.dxf.vtx2.x, entidade.dxf.vtx2.y, entidade.dxf.vtx2.z),
                  (entidade.dxf.vtx3.x, entidade.dxf.vtx3.y, entidade.dxf.vtx3.z)]
            _push_face(p, vs)
        except Exception:
            pass
        return

    # ------ MESH ------
    if tipo == 'MESH':
        try:
            verts = [tuple(v) for v in entidade.vertices]
            for face in entidade.faces:
                vs = [verts[i] for i in face]
                if len(vs) < 3:
                    for v in vs: _push_vertex(p, v)
                    continue
                if len(vs) <= 4:
                    _push_face(p, vs)
                else:
                    for k in range(1, len(vs) - 1):
                        _push_face(p, [vs[0], vs[k], vs[k + 1]])
        except Exception:
            pass
        return
    # tipos desconhecidos: ignora silenciosamente (mantem comportamento do leitor antigo)


def main():
    doc = ezdxf.readfile(sys.argv[1])
    pecas = {}
    for e in doc.modelspace():
        _processar(e, layer_pai=None, pecas=pecas)

    # descarta layers sem geometria (bbox degenerado)
    out = []
    for L, p in pecas.items():
        b = p['bb']
        if b[0] > b[3] or b[1] > b[4] or b[2] > b[5]:
            continue   # nunca recebeu vertice
        out.append({'layer': L,
                    'bb': [round(x, 1) for x in b],
                    'dim': [round(b[i + 3] - b[i], 1) for i in range(3)],
                    'faces': p['faces']})
    json.dump(out, open(sys.argv[2], 'w'), separators=(',', ':'))
    print('pecas', len(out))


if __name__ == '__main__':
    main()
