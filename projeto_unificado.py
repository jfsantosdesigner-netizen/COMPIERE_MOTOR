# -*- coding: utf-8 -*-
"""Contrato da ETAPA 4: única fonte de verdade após o cruzamento XML x DXF."""
import hashlib
import json
import geo
from ambiente import validar_pecas, validar_caixa, numero_finito
import unificacao

VERSAO = 2
UNIDADE = 'mm'
CAMPOS_ITEM = ('n', 'desc', 'dim', 'bb', 'tipo', 'pecas', 'larg', 'xml_tem_porta', 'xml_mat_porta')


def _itens_contrato(itens):
    # Parede, num_A e _junto pertencem à compatibilização/layout, não à Etapa 4.
    return [{k: it[k] for k in CAMPOS_ITEM if k in it} for it in itens]


def _sha(dados):
    try:
        raw = json.dumps(dados, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('estado do Projeto Unificado não serializável ou não finito') from exc
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _mesma_geometria(a, b):
    if list(a['bb']) != list(b['bb']) or list(a['dim']) != list(b['dim']): return False
    if len(a['faces']) != len(b['faces']): return False
    return all(len(fa) == len(fb) and all(tuple(va) == tuple(vb) for va, vb in zip(fa, fb))
               for fa, fb in zip(a['faces'], b['faces']))


def _indices(nome, valores, n):
    if not isinstance(valores, (list, tuple, set)):
        raise TypeError(f'{nome} deve ser uma coleção de índices')
    out = set()
    for i in valores:
        if type(i) is not int or not 0 <= i < n:
            raise ValueError(f'{nome} contém índice inválido: {i!r}')
        out.add(i)
    if len(valores) != len(out): raise ValueError(f'{nome} contém índices repetidos')
    return out


def construir(P, itens, ambiente_final, portas_xml=(), *, xml=None, materiais_xml=None, diagnostico=None):
    """Monta o projeto unificado sem copiar a geometria pesada.

    P, itens e ambiente_final são os objetos canônicos em memória. Consumidores
    recebem esses mesmos objetos e não devem refazer XML x DXF.
    """
    validar_pecas(P)
    if not isinstance(itens, list):
        raise TypeError('itens deve ser uma lista produzida por geo.casar')
    n = len(P)
    usados = set()
    for pos, it in enumerate(itens):
        if not isinstance(it, dict): raise TypeError(f'itens[{pos}] deve ser dicionário')
        faltam = {'n', 'desc', 'dim', 'bb', 'tipo', 'pecas'} - set(it)
        if faltam: raise ValueError(f'itens[{pos}] sem chaves: {", ".join(sorted(faltam))}')
        if type(it['n']) is not int or it['n'] < 1: raise ValueError(f'itens[{pos}].n inválido')
        if not isinstance(it['desc'], str) or not isinstance(it['dim'], str): raise ValueError('descrição/dimensões devem ser texto')
        if it['tipo'] not in ('mod', 'comp'): raise ValueError(f'itens[{pos}].tipo inválido: {it["tipo"]!r}')
        validar_caixa(it['bb'], f'itens[{pos}].bb')
        if any(not numero_finito(v) or v < 0 for v in geo.parse_dim(it['dim'])): raise ValueError('dimensões XML inválidas')
        usados |= _indices(f'itens[{pos}].pecas', it['pecas'], n)
    if not isinstance(ambiente_final, dict): raise TypeError('ambiente_final deve ser dicionário')
    obrigatorias = set(unificacao.PAPEIS) | {'piso_z', 'faces_parede_real', '_quantidade_pecas', '_pecas_sha256'}
    if not obrigatorias <= set(ambiente_final): raise ValueError('ambiente_final incompleto')
    for k in ('pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas'):
        if k not in ambiente_final: raise ValueError(f'ambiente_final sem {k}')
    # Validação equivalente para dados produzidos em memória e restaurados.
    unificacao.validar_contrato(unificacao.para_json(ambiente_final), P)
    for papel in unificacao.PAPEIS[1:]:
        for p in ambiente_final[papel]:
            original = P[p['i']]
            if not _mesma_geometria(p, original):
                raise ValueError(f'geometria de ambiente divergente na peça {p["i"]}')
    papeis_amb = {p['i'] for k in ('pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas') for p in ambiente_final[k]}
    conflito = usados & papeis_amb
    if conflito: raise ValueError(f'peças simultaneamente em móvel e ambiente: {sorted(conflito)}')
    if usados & set(ambiente_final['duplicadas']): raise ValueError('peça de móvel marcada como duplicada')
    portas = _indices('portas_xml', portas_xml, n)
    if not portas <= usados: raise ValueError('porta XML sem item proprietário')
    referencias = dict(materiais_xml or {})
    _indices('materiais_xml', list(referencias), n)
    if any(not isinstance(v, str) or not v for v in referencias.values()): raise ValueError('material XML deve ter nome explícito')
    materiais = {p['i']: {'nome': referencias.get(p['i'], p.get('mat')), 'rgb': p.get('rgb'), 'textura': p.get('textura')}
                 for p in P if p['i'] in referencias or p.get('mat') or p.get('rgb') or p.get('textura')}
    dados_xml = xml if xml is not None else {}
    diagnostico = diagnostico if diagnostico is not None else {}
    assinatura = _sha({'pecas_sha256': ambiente_final['_pecas_sha256'], 'itens': _itens_contrato(itens),
                       'materiais': materiais, 'aparencia_pecas': [{k: p[k] for k in ('i', 'mat', 'rgb', 'textura') if k in p} for p in P],
                       'portas_xml': sorted(portas), 'ambiente': unificacao.para_json(ambiente_final),
                       'xml': dados_xml, 'diagnostico': diagnostico})
    return {
        'versao': VERSAO, 'unidade': UNIDADE,
        'identidade': {'quantidade_pecas': n, 'pecas_sha256': ambiente_final['_pecas_sha256'], 'projeto_sha256': assinatura},
        'pecas': P, 'itens': itens,
        'modulos': [it for it in itens if it['tipo'] == 'mod'],
        'componentes': [it for it in itens if it['tipo'] == 'comp'],
        'moveis': usados, 'materiais': materiais,
        'portas': {'pecas_xml': portas,
                   'modulos_xml': [it for it in itens if it.get('xml_tem_porta')]},
        'ambiente': ambiente_final,
        'xml': dados_xml, 'materiais_xml': referencias, 'diagnostico': diagnostico,
    }


def validar(projeto):
    if not isinstance(projeto, dict): raise TypeError('projeto deve ser dicionário')
    if projeto.get('versao') != VERSAO: raise ValueError('versão do Projeto Unificado incompatível')
    if projeto.get('unidade') != UNIDADE: raise ValueError('unidade do Projeto Unificado deve ser mm')
    campos = {'identidade', 'pecas', 'itens', 'ambiente', 'portas', 'modulos', 'componentes', 'moveis', 'materiais', 'materiais_xml', 'xml', 'diagnostico'}
    if not campos <= set(projeto): raise ValueError('Projeto Unificado incompleto')
    reconstruido = construir(projeto['pecas'], projeto['itens'], projeto['ambiente'], projeto['portas']['pecas_xml'],
                             xml=projeto['xml'], materiais_xml=projeto['materiais_xml'], diagnostico=projeto['diagnostico'])
    if reconstruido['identidade'] != projeto.get('identidade'): raise ValueError('identidade do Projeto Unificado divergente')
    for k in ('moveis', 'materiais'):
        if reconstruido[k] != projeto[k]: raise ValueError(f'{k} diverge das decisões da Unificação')
    for k in ('modulos', 'componentes'):
        if [id(it) for it in reconstruido[k]] != [id(it) for it in projeto[k]]:
            raise ValueError(f'{k} não é uma visão dos itens canônicos')
    if [id(it) for it in reconstruido['portas']['modulos_xml']] != [id(it) for it in projeto['portas']['modulos_xml']]:
        raise ValueError('módulos com porta divergem dos itens canônicos')
    return projeto


def para_json(projeto):
    validar(projeto)
    dados = {'versao': VERSAO, 'unidade': UNIDADE, 'identidade': projeto['identidade'],
             'pecas': [{k: p[k] for k in ('i', 'layer', 'bb', 'dim', 'faces', 'mat', 'rgb', 'textura') if k in p} for p in projeto['pecas']],
             'itens': _itens_contrato(projeto['itens']), 'ambiente': unificacao.para_json(projeto['ambiente']),
             'portas_xml': sorted(projeto['portas']['pecas_xml']),
             'materiais_xml': {str(i): nome for i, nome in sorted(projeto['materiais_xml'].items())},
             'xml': projeto['xml'], 'diagnostico': projeto['diagnostico']}
    return json.loads(json.dumps(dados, ensure_ascii=False, allow_nan=False))


def de_json(dados):
    if dados.get('versao') != VERSAO or dados.get('unidade') != UNIDADE:
        raise ValueError('versão/unidade do Projeto Unificado incompatível')
    P = dados['pecas']
    resultado = construir(P, dados['itens'], unificacao.de_json(dados['ambiente'], P), dados['portas_xml'],
                          xml=dados['xml'], materiais_xml={int(i): nome for i, nome in dados['materiais_xml'].items()},
                          diagnostico=dados['diagnostico'])
    if resultado['identidade'] != dados['identidade']: raise ValueError('identidade do Projeto Unificado restaurado divergente')
    return resultado


def resumo(projeto):
    validar(projeto)
    return {
        'versao': projeto['versao'], 'unidade': projeto['unidade'], **projeto['identidade'],
        'itens': len(projeto['itens']), 'modulos': len(projeto['modulos']),
        'componentes': len(projeto['componentes']), 'pecas_moveis': len(projeto['moveis']),
        'materiais': len(projeto['materiais']), 'portas_xml': len(projeto['portas']['pecas_xml']),
        'pedras': len(projeto['ambiente']['pedra']), 'eletros': len(projeto['ambiente']['eletros']),
    }
