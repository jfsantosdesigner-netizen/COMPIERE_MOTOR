import ambiente,ambientemodu,unificacao,projeto_unificado,cena_render,renderizador
from teste_ambiente import cena
P=cena();P[1]['bb']=[0,0,0,4000,3000,5];P[1]['dim']=[4000,3000,5]
it=[dict(n=1,desc='M',dim='600x700x500',bb=P[0]['bb'],tipo='mod',pecas=[0])]
a=ambiente.construir(P);af=unificacao.fechar(P,a,ambientemodu.construir(P,a),{0},[P[0]['bb']]);pr=projeto_unificado.construir(P,it,af);ce=cena_render.construir(pr,'visao_geral',contexto=True)
pk=renderizador.pacote(pr,ce);assert pk['versao']==1 and pk['moveis'] and pk['paredes']
print('OK: pacote da Etapa 9')
