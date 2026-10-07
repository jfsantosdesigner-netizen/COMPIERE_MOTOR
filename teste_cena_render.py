# -*- coding: utf-8 -*-
import ambiente, ambientemodu, unificacao, projeto_unificado, cena_render
from teste_ambiente import cena

P = cena(); P[1]['bb'] = [0, 0, 0, 4000, 3000, 5]; P[1]['dim'] = [4000, 3000, 5]
itens = [dict(n=1, desc='Balcão', dim='600x700x500', bb=P[0]['bb'], tipo='mod', pecas=[0, 4])]
a = ambiente.construir(P)
af = unificacao.fechar(P, a, ambientemodu.construir(P, a), {0, 4}, [P[0]['bb']])
projeto = projeto_unificado.construir(P, itens, af, portas_xml={4})
geral = cena_render.construir(projeto, 'visao_geral', itens, ['A'], contexto=True)
vista = cena_render.construir(projeto, 'vista', itens, ['A'], contexto=True)
cota = cena_render.construir(projeto, 'cota', itens, ['A'], portas_geometricas={4})
assert geral['ambiente']['piso'] and geral['camera']['altura_mm'] == 1500
assert vista['pecas_principais'] == {0, 4}
assert not cota['ambiente']['piso'] and cota['pecas_visiveis'] == {0} and cota['portas_removidas'] == {4}
print('OK: contrato da Cena (visão geral, vista e cota)')
