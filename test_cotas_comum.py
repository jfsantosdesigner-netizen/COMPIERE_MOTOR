import ast,copy,math,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from cotas_comum import mascara_contornos,vaos_prateleiras,assinatura_vaos


class ContornosTest(unittest.TestCase):
    def test_triangulacao_nao_cria_diagonal_e_contorno_independe_das_flags(self):
        mask,ids=mascara_contornos([([(5,5),(25,5),(25,25)],0),
                                  ([(5,5),(25,25),(5,25)],0)],(32,32))
        a=np.asarray(mask)
        self.assertEqual(a[15,15],0)
        self.assertGreater(a[15,5],0)

    def test_peca_oculta_nao_acrescenta_linha_interna(self):
        mask,ids=mascara_contornos([([(8,8),(20,8),(20,20),(8,20)],0),
                                  ([(4,4),(25,4),(25,25),(4,25)],1)],(32,32))
        self.assertEqual(np.asarray(mask)[8,8],0)
        self.assertEqual(len(np.unique(ids[ids>0])),1)

    def test_duas_pecas_mantem_contorno_na_juncao(self):
        mask,_=mascara_contornos([([(3,3),(15,3),(15,25),(3,25)],0),
                                ([(15,3),(27,3),(27,25),(15,25)],1)],(32,32))
        self.assertGreater(np.asarray(mask)[15,15],0)


class PrateleirasTest(unittest.TestCase):
    def test_cristaleira_nao_usa_peca_vertical_local_como_divisoria_total(self):
        vert=[(3311,3329,155,2545),(3693,3711,155,2545),(3573,3588,1190,1510)]
        hor=[(3329,z,3693,z+18) for z in (156,494,832,1170,1508,1841,2184,2526)]
        self.assertEqual(vaos_prateleiras(vert,hor,2390),[(3329,3693)])

    def test_divisoria_parcial_real_com_prateleiras_encostadas_continua_valida(self):
        vert=[(0,18,0,2400),(382,400,0,2400),(190,208,900,2400)]
        hor=[(18,1000,190,1018),(208,1000,382,1018),
             (18,1400,190,1418),(208,1400,382,1418)]
        self.assertEqual(vaos_prateleiras(vert,hor,2400),[(18,190),(208,382)])

    def test_cadeias_iguais_tem_assinatura_unica_sem_apagar_niveis_diferentes(self):
        self.assertEqual(assinatura_vaos([(10,300)]),assinatura_vaos([(10,300)]))
        self.assertNotEqual(assinatura_vaos([(10,300)]),assinatura_vaos([(10,320)]))


class GeometriaCotasTest(unittest.TestCase):
    def test_somente_portas_saem_fechamentos_vistas_e_pedra_ficam_sem_corte(self):
        tree=ast.parse(Path(__file__).with_name('gerar_caderno.py').read_text(encoding='utf-8-sig'))
        tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and
                   n.name in ('_eh_porta','_portas_cota','geom_parede')]
        import re
        def distancia(a,b):
            return math.sqrt(sum(max(0,a[k]-b[k+3],b[k]-a[k+3])**2 for k in range(3)))
        geo=SimpleNamespace(dist_caixas=distancia,
                            caixa_elev=lambda b,f:(-b[4],b[2],-b[1],b[5]))
        bbs=[[580,0,0,598,600,800],[-18,0,0,0,100,800],[-18,100,0,0,600,800],
             [-18,620,0,0,640,800],[-30,0,820,650,600,850],
             [3000,0,820,3600,600,850],[-30,1000,0,0,1600,800],
             [-30,-1600,820,650,-10,850]]
        pieces=[]
        for pi,b in enumerate(bbs):
            fc=[(b[0],b[1],b[2]),(b[0],b[4],b[2]),(b[0],b[4],b[5]),(b[0],b[1],b[5])]
            pieces.append(dict(i=pi,bb=b,dim=[b[k+3]-b[k] for k in range(3)],
                               fq=[(fc,None,[False]*4)],faces=[fc],ft=[[False]*4]))
        itens=[dict(tipo='mod',desc='Armario',bb=[0,0,0,600,600,800],pecas=[0,1,2]),
               dict(tipo='comp',desc='Fechamento lateral',bb=bbs[1],pecas=[1]),
               dict(tipo='comp',desc='Vista acabamento',bb=bbs[3],pecas=[3])]
        ns=dict(P=pieces,geo=geo,FV={'x+':(1,0)},PORTAS_XML={2},AMB_I={4,5,7},
                AMB=[pieces[4],pieces[5],pieces[7]],MADEIRA=(.8,.6,.4),BRANCO=(1,1,1),re=re,
                uu=lambda x,y,f:-y)
        original=copy.deepcopy(pieces)
        exec(compile(tree,'gerar_caderno.py','exec'),ns)
        g=ns['geom_parede'](dict(key='x+',id='teste',itens=itens))
        self.assertEqual(g['portas_cotas'],{2})
        self.assertEqual(g['pecas_cotas'],{0,1,3})
        self.assertEqual(g['pedras_cotas'],[4])
        self.assertEqual({f[5] for f in g['faces']},{0,1,3,4})
        self.assertEqual(pieces,original)
        self.assertEqual(g['ztop'],900)


if __name__=='__main__':
    unittest.main()
