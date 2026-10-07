# -*- coding: utf-8 -*-
"""
render_ambiente.py — renderiza SÓ o ambiente (piso + parede) gerado por ambiente.py. Sem móvel, sem XML.
Uso: python -B render_ambiente.py <arquivo.dxf> <pasta_saida> [final]   (sem 'final' = previa rapida, 960x600)
Saida: <pasta_saida>\\AMBIENTE_diagonal.png e AMBIENTE_interior.png (o json de geometria e apagado ao final).
Ajustes de cor/luz/encontro piso-parede ficam em blender_ambiente.py (bloco AJUSTES).
"""
import sys, os, json, glob, subprocess
sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ambiente


def caixa(b):
    x0, y0, z0, x1, y1, z1 = b
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return [[v[i] for i in f] for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]


def pecas(dxf):
    r = subprocess.run([sys.executable, '-B', os.path.join(AQUI, 'dxf_pecas(motor core).py'), dxf, '-'],
                       capture_output=True, encoding='utf-8')
    if r.returncode: raise SystemExit('dxf_pecas falhou: ' + r.stderr[-500:])
    P = json.loads(r.stdout)
    for i, p in enumerate(P): p['i'] = i
    return P


def blender():
    c = sorted(glob.glob(r'C:\Program Files\Blender Foundation\Blender *\blender.exe'))
    if not c: raise SystemExit('Blender nao encontrado em C:\\Program Files\\Blender Foundation')
    return c[-1]


def main(dxf, saida, final=False):
    P = pecas(dxf); A = ambiente.construir(P)
    par = [f for i in A['malha_par'] for f in P[i]['faces']] + [f for i in A['paredes_pecas'] for f in caixa(P[i]['bb'])]
    piso = [f for i in A['piso'] for f in P[i]['faces']]
    print(f"AMBIENTE: {len(A['malha_par'])} malha(s) de parede, {len(A['paredes_pecas'])} parede(s) em peca, {len(A['piso'])} piso(s), piso_z={A['piso_z']}")
    if not par and not piso: raise SystemExit('DXF sem parede nem piso reconhecidos')
    saida = os.path.abspath(saida); os.makedirs(saida, exist_ok=True)
    gj = os.path.join(saida, '_geo_ambiente.json')
    with open(gj, 'w', encoding='utf-8') as f: json.dump({'parede': par, 'piso': piso, 'piso_z': A['piso_z']}, f)
    try:
        r = subprocess.run([blender(), '-b', '--factory-startup', '-P', os.path.join(AQUI, 'blender_ambiente.py'), '--', gj, saida] + (['final'] if final else []),
                           capture_output=True, encoding='utf-8', errors='replace')
        if r.returncode or 'RENDER OK' not in r.stdout:
            print(r.stdout[-2500:], r.stderr[-1500:]); raise SystemExit('Blender falhou')
    finally:
        if os.path.exists(gj): os.remove(gj)
    print('OK:', *sorted(glob.glob(os.path.join(saida, 'AMBIENTE_*.png'))), sep='\n  ')


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4): raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], len(sys.argv) == 4 and sys.argv[3] == 'final')
