# -*- coding: utf-8 -*-
"""Contrato da Cena: entrada única para qualquer render 3D ou 2D."""
import projeto_unificado

VERSAO = 1
FINALIDADES = ('visao_geral', 'vista', 'cota')


def construir(projeto, finalidade, itens=None, paredes=(), contexto=False, isolado=False,
              portas_geometricas=(), camera=None):
    if finalidade not in FINALIDADES: raise ValueError(f'finalidade inválida: {finalidade!r}')
    itens = list(projeto['itens'] if itens is None else itens)
    ids_validos = {id(i) for i in projeto['itens']}
    if any(id(i) not in ids_validos for i in itens): raise ValueError('a cena contém item de outro Projeto Unificado')
    principais = {pi for it in itens for pi in it['pecas']}
    portas = set(projeto['portas']['pecas_xml']) | set(portas_geometricas)
    if not portas <= set(range(len(projeto['pecas']))): raise ValueError('a cena contém porta inexistente')
    if finalidade == 'cota':
        visiveis = principais - portas
        ambiente = {'paredes': [], 'pedra': [], 'eletros': [], 'piso': False}
        modo, contexto, isolado = 'ortografica_frontal', False, True
    else:
        visiveis = set(projeto['moveis']) if contexto and not isolado else principais
        a = projeto['ambiente']
        ambiente = {
            'paredes': [p['i'] for k in ('malha_par', 'par_dxf', 'paredes_pecas') for p in a[k]] if contexto else [],
            'pedra': [p['i'] for p in a['pedra']] if contexto else [],
            'eletros': [p['i'] for p in a['eletros']] if contexto else [],
            'piso': bool(contexto),
        }
        modo = 'perspectiva_interior' if finalidade == 'visao_geral' else 'frontal'
    cam = dict(camera or {})
    cam.setdefault('modo', modo); cam.setdefault('altura_mm', 1500); cam.setdefault('foco_altura_mm', 1500)
    cena = {
        'versao': VERSAO, 'unidade': 'mm', 'finalidade': finalidade,
        'projeto_identidade': dict(projeto['identidade']), 'paredes': list(paredes),
        'itens': itens, 'pecas_principais': principais, 'pecas_visiveis': visiveis,
        'portas_removidas': portas if finalidade == 'cota' else set(),
        'ambiente': ambiente, 'contexto': bool(contexto), 'isolado': bool(isolado), 'camera': cam,
    }
    return validar(cena, projeto)


def validar(cena, projeto):
    # A geometria é auditada na Unificação e antes da entrega. A Cena verifica
    # somente seus vínculos, evitando revalidar todas as faces a cada imagem.
    if projeto.get('versao') != projeto_unificado.VERSAO or projeto.get('unidade') != 'mm':
        raise ValueError('Cena exige um Projeto Unificado compatível')
    if cena.get('versao') != VERSAO or cena.get('unidade') != 'mm': raise ValueError('versão/unidade da Cena incompatível')
    if cena.get('finalidade') not in FINALIDADES: raise ValueError('finalidade da Cena incompatível')
    if cena.get('projeto_identidade') != projeto.get('identidade'): raise ValueError('Cena pertence a outro Projeto Unificado')
    ids_validos = {id(it) for it in projeto['itens']}
    if any(id(it) not in ids_validos for it in cena['itens']): raise ValueError('a cena contém item de outro Projeto Unificado')
    principais = {pi for it in cena['itens'] for pi in it['pecas']}
    if set(cena['pecas_principais']) != principais: raise ValueError('peças principais divergem dos itens da cena')
    universo = set(range(len(projeto['pecas'])))
    for k in ('pecas_principais', 'pecas_visiveis', 'portas_removidas'):
        indices = projeto_unificado._indices(k, cena[k], len(projeto['pecas']))
        if not indices <= universo: raise ValueError(f'{k} contém peça inexistente')
    if not set(cena['pecas_visiveis']) <= projeto['moveis']:
        raise ValueError('peça de ambiente ou sem proprietário usada como móvel na cena')
    if cena['finalidade'] == 'cota':
        if any(cena['ambiente'][k] for k in ('paredes', 'pedra', 'eletros')) or cena['ambiente']['piso']:
            raise ValueError('cota deve ser isolada, sem ambiente')
        if set(cena['pecas_visiveis']) & set(cena['portas_removidas']): raise ValueError('porta permaneceu visível na cota')
        if set(cena['pecas_visiveis']) != principais - set(cena['portas_removidas']):
            raise ValueError('cota diverge das peças dos itens e das portas removidas')
        if cena['camera']['modo'] != 'ortografica_frontal': raise ValueError('cota exige câmera ortográfica frontal')
    return cena


def resumo(cena):
    return {'finalidade': cena['finalidade'], 'paredes': len(cena['paredes']), 'itens': len(cena['itens']),
            'pecas_visiveis': len(cena['pecas_visiveis']), 'portas_removidas': len(cena['portas_removidas']),
            'com_ambiente': bool(cena['ambiente']['paredes'] or cena['ambiente']['piso']), 'camera': cena['camera']['modo']}
