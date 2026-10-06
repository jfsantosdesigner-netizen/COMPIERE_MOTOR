"""Conferência XML/DXF: quantidades e evidências, sem fabricar geometria."""
from collections import Counter
import re


def dimensoes(item):
    return tuple(float(item.get(k, '0').replace(',', '.')) for k in ('WIDTH', 'HEIGHT', 'DEPTH'))


def fonte(item):
    filhos = []
    for ch in item.findall('ITEMS/ITEM'):
        desc = ch.get('DESCRIPTION', '')
        if ch.get('COMPONENT') != 'Y' and 'per_bar' not in ch.get('ID', '').lower():
            continue
        dm = dimensoes(ch)
        if min(dm) <= 0:
            continue
        filhos.append({'desc': desc, 'dim': dm, 'qtd': max(1, int(float(ch.get('QUANTITY') or 1)))})
    avulso = len(filhos) == 1 and filhos[0]['qtd'] == 1 and all(abs(a-b) <= 0.01 for a,b in zip(sorted(filhos[0]['dim']), sorted(dimensoes(item))))
    return {'id': item.get('ID', ''), 'componente': item.get('COMPONENT') == 'Y' or avulso, 'filhos': filhos, 'acessorio': bool(_ACESSORIO.search(item.get('DESCRIPTION', '')))}


_ACESSORIO = re.compile(r'\bkit\b|tapa[- ]?furo|corredi[cç]a|suporte\s+fixa[cç][aã]o|\bdesliz\b|puxador|\bpux[.]|\btrilho\b|dobradi[cç]a|parafuso|amortecedor|\bsapata\b|cantoneira|\brebite\b|tubo\s+silicone|fita\s+de\s+borda', re.I)


def conferir(linhas, qtd, inst):
    encontrados = Counter(i['n'] for i in inst)
    itens = []
    for n, (desc, dm) in enumerate(linhas, 1):
        esperado = qtd.get((desc, dm), 1)
        achado = encontrados[n]
        acessorio = bool(_ACESSORIO.search(desc))
        itens.append({'n': n, 'descricao': desc, 'dimensoes_xml': dm,
                      'quantidade_xml': esperado, 'quantidade_dxf': achado,
                      'obrigatorio': not acessorio,
                      'status': 'OK' if achado == esperado else 'DISPENSADO' if acessorio and achado == 0 else 'FALHA'})
    return {'aprovado': all(i['status'] != 'FALHA' for i in itens), 'itens': itens}
