# -*- coding: utf-8 -*-
"""
unificacao.py — ETAPA 4: onde o XML encontra o DXF. Recebe os CANDIDATOS de ambiente.py e ambientemodu.py e fecha o
ambiente final, descartando o que o XML reconhece como móvel e aplicando o que depende dos móveis.

  fechar(P, amb, modu, usadas, bbs_moveis) -> dict   (mesmo dict que o gerar_caderno sempre consumiu)
    usadas      conjunto de indices de P que pertencem a itens do XML
    bbs_moveis  caixas [x0,y0,z0,x1,y1,z1] dos itens do XML
Pura. Lógica movida do antigo ambiente.construir(P, usadas, bbs) sem alteração.
"""
import hashlib
import json
import copy
from collections import Counter
import ambiente
import ambientemodu
import geo
from ambiente import caixa_faces_, _arestas, validar_pecas


def materiais_por_peca(P, xml):
    """Casamento de materiais existente: dimensões, ordem XML/DXF e ±1 mm.

    O primeiro material do XML vence empates de frequência. Nenhuma biblioteca,
    cor disponível na máquina ou arquivo é consultado aqui.
    """
    validar_pecas(P)
    por_dim = xml['materiais_dimensoes']
    grupos, fixa = {}, {}
    for p in P:
        grupos.setdefault(tuple(sorted(round(v) for v in p['dim'])), []).append(p)
    for dimensoes, referencias in xml['ordem_materiais'].items():
        grupo = grupos.get(dimensoes, [])
        if len(set(referencias)) > 1 and len(grupo) == len(referencias):
            for p, nome in zip(sorted(grupo, key=lambda p: p['i']), reversed(referencias)):
                fixa[p['i']] = nome
    resultado = {}
    for p in P:
        k = tuple(sorted(round(v) for v in p['dim']))
        candidatos = Counter({fixa[p['i']]: 1}) if p['i'] in fixa else por_dim.get(k)
        if not candidatos:
            for delta in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)):
                candidatos = por_dim.get(tuple(sorted(a + b for a, b in zip(k, delta))))
                if candidatos: break
        if candidatos:
            resultado[p['i']] = candidatos.most_common(1)[0][0]
    return resultado


def _adotar_orfas(itens, P):
    """Regra existente: chapa contida no módulo; primeiro módulo na ordem XML."""
    usadas = {pi for it in itens for pi in it['pecas']}
    modulos = [it for it in itens if it['tipo'] == 'mod']
    adotadas = []
    for p in P:
        if p['i'] in usadas: continue
        b = p['bb']; ext = [b[k + 3] - b[k] for k in range(3)]; esp = min(ext)
        if esp > 30 or sorted(ext)[1] < 50: continue
        if ext.index(esp) != 2 and esp > 10: continue
        for modulo in modulos:
            mb = modulo['bb']
            if any(min(b[k + 3], mb[k + 3]) - max(b[k], mb[k]) < -3 for k in range(3)): continue
            uniao = geo.uniao(mb, b)
            limites = sorted(uniao[k + 3] - uniao[k] for k in range(3))
            dimensoes = sorted(geo.parse_dim(modulo['dim']))
            if any(limites[k] > dimensoes[k] + 3 for k in range(3)): continue
            modulo['pecas'].append(p['i']); modulo['bb'] = list(uniao); usadas.add(p['i'])
            adotadas.append([modulo['n'], p['i']])
            break
    return adotadas


def _portas_dos_modulos(itens, xml):
    conhecidas = set(xml['modulos_com_porta'])
    materiais = dict(xml['materiais_porta'])
    for it in itens:
        if it['tipo'] != 'mod': continue
        largura, altura, _ = geo.parse_dim(it['dim'])
        lado = sorted([largura, altura], reverse=True)
        for porta in xml['portas_euronobre'] + xml['portas_avulsas']:
            frente = sorted(porta['dim'], reverse=True)[:2]
            if all(abs(a - b) <= 15 for a, b in zip(frente, lado)):
                conhecidas.add((it['desc'], it['dim']))
                materiais[(it['desc'], it['dim'])] = porta['mat']
                break
        chave = (it['desc'], it['dim'])
        if chave in conhecidas:
            it['xml_tem_porta'] = True
            it['xml_mat_porta'] = materiais.get(chave, 'mdf')


def _incorporar_portas(itens, P, xml):
    usadas = {pi for it in itens for pi in it['pecas']}
    portas = set()
    for p in P:
        if p['i'] in usadas or not p['faces']: continue
        dimensoes = tuple(sorted(round(v) for v in p['dim']))
        if not any(all(abs(a - b) <= 1 for a, b in zip(dimensoes, q)) for q in xml['dimensoes_portas']): continue
        # Regra preservada: menor distância; primeiro item XML em caso de empate.
        dono = min(itens, key=lambda it: geo.dist_caixas(p['bb'], it['bb']), default=None)
        if dono is not None and geo.dist_caixas(p['bb'], dono['bb']) <= 5:
            dono['pecas'].append(p['i']); usadas.add(p['i']); portas.add(p['i'])
    return portas


def construir(P, xml, materiais_xml=None):
    """Etapa 4 completa. Entrada em memória; sem I/O e sem modificar P ou XML.

    Finaliza peças, órfãs, materiais e portas ANTES de fechar o ambiente. Vistas,
    classificação, render e caderno recebem o mesmo Projeto Unificado.
    """
    import projeto_unificado
    validar_pecas(P)
    obrigatorias = {'linhas', 'quantidades', 'modulos_com_porta', 'materiais_porta',
                   'portas_avulsas', 'portas_euronobre', 'dimensoes_portas',
                   'materiais_dimensoes', 'ordem_materiais'}
    if not isinstance(xml, dict) or not obrigatorias <= set(xml):
        raise ValueError('XML interpretado não obedece ao contrato da Unificação')
    materiais = materiais_por_peca(P, xml) if materiais_xml is None else dict(materiais_xml)
    itens = geo.casar(P, xml['linhas'], xml['quantidades'])
    adotadas = _adotar_orfas(itens, P)
    _portas_dos_modulos(itens, xml)
    portas = _incorporar_portas(itens, P, xml)
    usadas = {pi for it in itens for pi in it['pecas']}
    candidatos = ambiente.construir(P)
    final = fechar(P, candidatos, ambientemodu.construir(P, candidatos), usadas, [it['bb'] for it in itens])
    dados = {k: copy.deepcopy(xml.get(k)) for k in
             ('sha256', 'linhas', 'cores', 'puxadores', 'ferragens', 'puxador_tipo', 'especificacoes', 'avisos')}
    dados['quantidades'] = [{'desc': d, 'dim': dm, 'quantidade': q}
                            for (d, dm), q in xml['quantidades'].items()]
    diagnostico = {
        'orfas_adotadas': adotadas,
        'itens_nao_localizados': [[d, dm] for n, (d, dm) in enumerate(xml['linhas'], 1)
                                 if not any(it['n'] == n for it in itens)],
        'portas_xml': sorted(portas),
    }
    return projeto_unificado.construir(P, itens, final, portas, xml=dados,
                                       materiais_xml=materiais, diagnostico=diagnostico)


def _copia_preparada(p_, arestas=False):
    """Copia uma peça para a saída sem modificar a lista P recebida."""
    q_ = dict(p_)
    q_['bb'] = list(p_['bb'])
    q_['dim'] = list(p_['dim'])
    q_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
    if arestas:
        q_['ft'] = _arestas(q_['faces'])
    return q_


def _indices(nome, valores, n):
    if not isinstance(valores, (list, tuple, set)):
        raise TypeError(f'{nome} deve ser uma coleção de índices')
    for i in valores:
        if type(i) is not int or not 0 <= i < n:
            raise ValueError(f'{nome} contém índice inválido: {i!r}')


def _assinatura(P):
    base = [{'i': p['i'], 'layer': p['layer'], 'bb': p['bb'], 'dim': p['dim'], 'faces': p['faces']} for p in P]
    raw = json.dumps(base, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def fechar(P, amb, modu, usadas, bbs_moveis):
    validar_pecas(P)
    obrig_a = {'piso', 'malha_par', 'fontes_parede', 'par_dxf', 'paredes_pecas', 'piso_z'}
    obrig_m = {'moveis', 'pedra', 'eletro_a', 'eletro_b'}
    if not isinstance(amb, dict) or not obrig_a.issubset(amb): raise ValueError('amb não obedece ao contrato da etapa 2')
    if not isinstance(modu, dict) or not obrig_m.issubset(modu): raise ValueError('modu não obedece ao contrato da etapa 3')
    for k in obrig_a - {'piso_z'}: _indices('amb.' + k, amb[k], len(P))
    for k in obrig_m: _indices('modu.' + k, modu[k], len(P))
    _indices('usadas', usadas, len(P))
    if not isinstance(bbs_moveis, (list, tuple)) or any(not isinstance(b, (list, tuple)) or len(b) != 6 for b in bbs_moveis):
        raise ValueError('bbs_moveis deve ser uma lista de caixas com 6 números')
    for b in bbs_moveis:
        ambiente.validar_caixa(b, 'bbs_moveis')
    _usadas = usadas; _inst_bb = bbs_moveis
    def _vol(b): return max(0, b[3] - b[0]) * max(0, b[4] - b[1]) * max(0, b[5] - b[2])
    def _vol_int(A, B): return _vol([max(A[0], B[0]), max(A[1], B[1]), max(A[2], B[2]), min(A[3], B[3]), min(A[4], B[4]), min(A[5], B[5])]) if all(min(A[k + 3], B[k + 3]) > max(A[k], B[k]) for k in range(3)) else 0
    _bb_list = [P[pi]['bb'] for pi in _usadas]
    DUP_I = {p_['i'] for p_ in P if p_['i'] not in _usadas and _vol(p_['bb']) > 0 and sorted(p_['dim'])[1] >= 50
             and any(_vol_int(p_["bb"], b_) >= 0.8 * max(_vol(p_["bb"]), _vol(b_)) for b_ in _bb_list)}
    AMB = [P[i] for i in modu['pedra'] if i not in _usadas]
    AMB_I = {p_['i'] for p_ in AMB}
    MALHA_PAR_I = [i for i in amb['malha_par'] if i not in _usadas and i not in AMB_I]
    MALHA_PAR = [P[i] for i in MALHA_PAR_I]
    MALHA_I = {p_['i'] for p_ in MALHA_PAR}
    def _faces_parede_real():
        out = []   # (eixo 'x'|'y', coordenada, a0, a1)
        malha_cand = set(amb['malha_par'])
        for i_ in amb['fontes_parede']:
            p_ = P[i_]
            if i_ in malha_cand:
                if i_ not in MALHA_I: continue      # parede-malha que o XML reconheceu como móvel
            elif i_ in _usadas: continue            # parede fina que o XML reconheceu como móvel
            fcs = p_['faces'] if i_ in MALHA_I else caixa_faces_(p_['bb'])
            for fc in fcs:
                xs = [v[0] for v in fc]; ys = [v[1] for v in fc]; zs = [v[2] for v in fc]
                if max(zs) - min(zs) < 1500: continue
                if max(xs) - min(xs) <= 1 and max(ys) - min(ys) >= 300: out.append(('x', sum(xs) / len(xs), min(ys), max(ys)))
                elif max(ys) - min(ys) <= 1 and max(xs) - min(xs) >= 300: out.append(('y', sum(ys) / len(ys), min(xs), max(xs)))
        # faces no MESMO plano (±10 mm) = uma parede só, de ponta a ponta: o vão de porta/janela não quebra a parede
        lin = []
        for e, c, a0, a1 in sorted(out):
            o = next((l for l in lin if l[0] == e and abs(l[1] - c) <= 10), None)
            if o is None: lin.append([e, c, a0, a1])
            else: o[2] = min(o[2], a0); o[3] = max(o[3], a1)
        return [tuple(l) for l in lin]
    _FR = _faces_parede_real()
    ELETROS = [P[i] for i in modu['eletro_a'] if i not in _usadas and i not in AMB_I and i not in MALHA_I]
    # REGRA (João): blocos QUADRADOS (caixa simples, 12 faces) não entram — atrapalham a imagem. Fica objeto com forma
    # real (> 12 faces); em cima da pedra, só o que for baixo (cuba, cooktop: até 300 mm acima da pedra).
    _topo_pedra = [p_['bb'][5] for p_ in AMB]
    def _eletro_ok(p_):
        if len(p_['faces']) <= 12: return False
        if p_['bb'][2] < 50 and p_['bb'][5] < 250: return False   # base/rodapé solto no chão não é eletro
        for t_ in _topo_pedra:
            if p_['bb'][2] <= t_ + 15 and p_['bb'][5] > t_ - 60: return p_['bb'][5] <= t_ + 300
        return True
    ELETROS = [p_ for p_ in ELETROS if _eletro_ok(p_)]
    _ja_e = {q['i'] for q in ELETROS}
    ELETROS += [P[i] for i in modu['eletro_b'] if i not in _usadas and i not in AMB_I and i not in MALHA_I and i not in _ja_e
                and any(geo.dist_caixas(P[i]['bb'], b_) <= 20 for b_ in _inst_bb)]
    ELETRO_I = {p_['i'] for p_ in ELETROS}
    AMB = [_copia_preparada(p_, True) for p_ in AMB]
    MALHA_PAR = [_copia_preparada(p_, True) for p_ in MALHA_PAR]
    ELETROS = [_copia_preparada(p_, True) for p_ in ELETROS]
    PAR_DXF = [P[i] for i in amb['par_dxf'] if i not in _usadas and i not in AMB_I and i not in ELETRO_I]
    # Candidata alta reconhecida pelo XML é móvel, jamais parede do ambiente.
    PAREDES_PECAS = [_copia_preparada(P[i]) for i in amb['paredes_pecas'] if i not in _usadas and i not in AMB_I and i not in ELETRO_I]
    PAR_DXF = [_copia_preparada(p_) for p_ in PAR_DXF]
    return dict(duplicadas=DUP_I, pedra=AMB, malha_par=MALHA_PAR, eletros=ELETROS, par_dxf=PAR_DXF,
                paredes_pecas=PAREDES_PECAS, piso_z=amb['piso_z'], faces_parede_real=_FR,
                _quantidade_pecas=len(P), _pecas_sha256=_assinatura(P))


# ---- Contrato (JSON) do resultado final: so indices e numeros --------------------------------------------------
VERSAO = 2
PAPEIS = ('duplicadas', 'pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas')


def para_json(res):
    d = {'versao': VERSAO, 'piso_z': res['piso_z'], 'faces_parede_real': [list(f) for f in res['faces_parede_real']]}
    d['duplicadas'] = sorted(res['duplicadas'])
    for k in PAPEIS[1:]:
        d[k] = [p['i'] for p in res[k]]
    if '_pecas_sha256' not in res or '_quantidade_pecas' not in res:
        raise ValueError('resultado sem identidade da entrada P')
    d['unidade'] = 'mm'; d['quantidade_pecas'] = res['_quantidade_pecas']; d['pecas_sha256'] = res['_pecas_sha256']
    return d


def validar_contrato(d, P):
    validar_pecas(P)
    if d.get('versao') != VERSAO:
        raise ValueError(f"contrato de ambiente versao {d.get('versao')} != {VERSAO}")
    if d.get('unidade') != 'mm': raise ValueError('contrato de ambiente sem unidade mm')
    if d.get('quantidade_pecas') != len(P): raise ValueError('contrato pertence a outra quantidade de peças')
    if d.get('pecas_sha256') != _assinatura(P): raise ValueError('contrato pertence a outro DXF/conjunto de peças')
    for k in PAPEIS: _indices(k, d.get(k), len(P))
    for k in PAPEIS:
        if len(d[k]) != len(set(d[k])): raise ValueError(f'{k} contém índices repetidos')
    exclusivos = [set(d[k]) for k in ('pedra', 'malha_par', 'eletros')]
    if any(a & b for pos, a in enumerate(exclusivos) for b in exclusivos[pos + 1:]):
        raise ValueError('peça em papéis exclusivos do ambiente')
    if not ambiente.numero_finito(d.get('piso_z')):
        raise ValueError('piso_z deve ser um número finito')
    for f in d.get('faces_parede_real', ()):
        if (not isinstance(f, (list, tuple)) or len(f) != 4 or f[0] not in ('x', 'y')
                or not all(ambiente.numero_finito(v) for v in f[1:]) or f[2] > f[3]):
            raise ValueError('plano de parede inválido')
    return d


def de_json(d, P):
    validar_contrato(d, P)
    res = {k: [_copia_preparada(P[i], k in ('pedra', 'malha_par', 'eletros')) for i in d[k]] for k in PAPEIS[1:]}
    res['duplicadas'] = set(d['duplicadas']); res['piso_z'] = d['piso_z']
    res['faces_parede_real'] = [tuple(f) for f in d['faces_parede_real']]
    res['_quantidade_pecas'] = len(P); res['_pecas_sha256'] = _assinatura(P)
    return res
