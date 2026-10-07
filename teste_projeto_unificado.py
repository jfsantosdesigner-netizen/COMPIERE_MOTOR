# -*- coding: utf-8 -*-
"""Teste sintético do contrato do Projeto Unificado."""
import copy
import ambiente, ambientemodu, unificacao, projeto_unificado as U
from teste_ambiente import cena

P = cena(); P[1]['bb'] = [0, 0, 0, 4000, 3000, 5]; P[1]['dim'] = [4000, 3000, 5]
itens = [dict(n=1, desc='Balcão', dim='600x700x500', bb=P[0]['bb'], tipo='mod', pecas=[0])]
a = ambiente.construir(P); m = ambientemodu.construir(P, a)
amb = unificacao.fechar(P, a, m, {0}, [P[0]['bb']])
antes = copy.deepcopy(P)
u = U.construir(P, itens, amb, portas_xml={0})
assert U.validar(u) is u and P == antes
assert u['modulos'] == itens and not u['componentes']
assert u['moveis'] == {0} and u['portas']['pecas_xml'] == {0}
assert U.resumo(u)['quantidade_pecas'] == len(P)
try:
    U.construir(P, itens, amb, portas_xml={99}); raise SystemExit('deveria recusar porta inválida')
except ValueError: pass
print('OK: contrato do Projeto Unificado')
