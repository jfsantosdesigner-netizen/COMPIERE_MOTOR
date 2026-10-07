# -*- coding: utf-8 -*-
"""
render_completo.py — ambiente COMPLETO: DXF + XML -> unificacao -> render (piso, parede, pedra, eletros, moveis).
Uso: python -B render_completo.py <arquivo.dxf> <arquivo.xml> <pasta_saida> [final]
Saida: <pasta_saida>\\AMBIENTE_diagonal.png e AMBIENTE_interior.png. Cor/luz/camera: blender_ambiente.py (bloco AJUSTES).
"""
import sys, os, json, glob, subprocess
sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import geo, ambiente, ambientemodu, unificacao, projeto_unificado, cena_render, entrada_xml
from render_ambiente import pecas, caixa, blender


def main(dxf, xml, saida, final=False):
    print('[1/5] DXF -> pecas'); P = pecas(dxf); print(f'      {len(P)} pecas')
    print('[2/5] ambiente.py + ambientemodu.py (so DXF)')
    a = ambiente.construir(P); modu = ambientemodu.construir(P, a)
    print(f"      piso={len(a['piso'])} parede(malha)={len(a['malha_par'])} moveis(cand.)={len(modu['moveis'])} pedra(cand.)={len(modu['pedra'])}")
    print('[3/5] unificacao (XML x DXF)')
    projeto = unificacao.construir(P, entrada_xml.ler(xml))
    inst = projeto['itens']; usadas = projeto['moveis']; res = projeto['ambiente']
    cena = cena_render.construir(projeto, 'visao_geral', contexto=True)
    dup = projeto['ambiente']['duplicadas']
    ocultas = {p['i'] for k in ('pedra', 'eletros') for p in res[k]}
    g = {'parede': [f for p in res['malha_par'] for f in p['faces']] + [f for p in res['paredes_pecas'] for f in caixa(p['bb'])],
         'piso': [f for i in a['piso'] for f in P[i]['faces']],
         'pedra': [f for p in res['pedra'] for f in p['faces']],
         'eletros': [f for p in res['eletros'] for f in p['faces']],
         'moveis': [f for i in sorted(cena['pecas_visiveis']) if i not in dup and i not in ocultas for f in projeto['pecas'][i]['faces']],
         'piso_z': res['piso_z']}
    print(f"      UNIFICADO: {len(inst)} itens do XML, {len(usadas)} pecas de movel, pedra={len(res['pedra'])}, eletros={len(res['eletros'])}, "
          f"parede(malha)={len(res['malha_par'])}, duplicadas ignoradas={len(dup)}")
    print('[4/5] cores/puxadores/vidro/compatibilizacao: ainda dentro do gerar_caderno (render usa cores padrao)')
    print('[5/5] Blender (Cycles CPU, semente 0)'); saida = os.path.abspath(saida); os.makedirs(saida, exist_ok=True)
    gj = os.path.join(saida, '_geo_ambiente.json')
    with open(gj, 'w', encoding='utf-8') as f: json.dump(g, f)
    try:
        r = subprocess.run([blender(), '-b', '--factory-startup', '-P', os.path.join(AQUI, 'blender_ambiente.py'), '--', gj, saida]
                           + (['final'] if final else []), capture_output=True, encoding='utf-8', errors='replace')
        if r.returncode or 'RENDER OK' not in r.stdout:
            print(r.stdout[-2500:], r.stderr[-1500:]); raise SystemExit('Blender falhou')
    finally:
        if os.path.exists(gj): os.remove(gj)
    print('OK:', *sorted(glob.glob(os.path.join(saida, 'AMBIENTE_*.png'))), sep='\n  ')


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], len(sys.argv) == 5 and sys.argv[4] == 'final')
