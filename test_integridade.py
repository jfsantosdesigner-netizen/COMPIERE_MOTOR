import unittest
import geo
import integridade


def peca(i, bb):
    return {'i': i, 'bb': bb, 'dim': [bb[k+3]-bb[k] for k in range(3)], 'faces': []}


class IntegridadeTest(unittest.TestCase):
    def test_falta_unica_bloqueia(self):
        r = integridade.conferir([('Painel', '800x18x400')], {}, [])
        self.assertFalse(r['aprovado'])

    def test_fundo_fino_obrigatorio(self):
        self.assertFalse(integridade.conferir([('Fundo', '800x3x400')], {}, [])['aprovado'])

    def test_quantidade_incompleta_bloqueia(self):
        self.assertFalse(integridade.conferir([('Frente', '800x18x70')], {('Frente','800x18x70'):2}, [{'n':1}])['aprovado'])

    def test_silicone_nao_e_movel(self):
        self.assertTrue(integridade.conferir([('Tubo Silicone Branco', '50x320x50')], {}, [])['aprovado'])

    def test_modulo_sem_excesso_roubar_medida_vizinha(self):
        P=[]
        for x in (0,900,1800):
            P.extend([peca(len(P),[x,0,0,x+18,350,622]),peca(len(P)+1,[x+822,0,0,x+840,350,622])])
        linhas=[('Armário','840x622x350'),('Armário','838x622x350')]
        inst=geo.casar(P,linhas,{linhas[0]:2,linhas[1]:1})
        self.assertEqual([sum(i['n']==n for i in inst) for n in (1,2)],[2,1])

    def test_frente_avulsa_componente_xml(self):
        linhas=[('Frente Sapateira','937,5x70x18')]
        inst=geo.casar([peca(0,[0,0,0,18,937.3,70])],linhas,{linhas[0]:1},{linhas[0]:{'componente':True}})
        self.assertEqual(len(inst),1)
        self.assertEqual(inst[0]['tipo'],'comp')

    def test_acessorio_nao_cria_modulo_extra(self):
        k=('Gaveta Corrediça Telescópica','354x90x400')
        P=[peca(0,[0,0,0,354,400,90])]
        f={'componente':True,'acessorio':True,'filhos':[]}
        self.assertEqual(geo.casar(P,[k],{k:1},{k:f}),[])
        self.assertTrue(integridade.conferir([k],{k:1},[])['aprovado'])

    def test_canto_com_caixa_e_afastador_reais(self):
        P=[peca(0,[0,0,0,18,580,2380]),peca(1,[1032,0,0,1050,580,2380]),peca(2,[18,0,0,1032,580,18]),peca(3,[0,580,0,570,598,2380]),peca(4,[512,598,0,530,663,2380])]
        k=('Armário Canto Reto','1100x2380x663')
        f={'filhos':[{'desc':'Lateral Direita','dim':(2380,18,580),'qtd':1},{'desc':'Lateral Esquerda','dim':(2380,18,580),'qtd':1},{'desc':'Base Inferior','dim':(1014,18,580),'qtd':1},{'desc':'Porta Cega','dim':(2380,18,570),'qtd':1},{'desc':'Afastador','dim':(2380,18,65),'qtd':1}]}
        inst=geo.casar(P,[k],{k:1},{k:f})
        self.assertEqual(len(inst),1)
        self.assertEqual(inst[0]['bb'],[0,0,0,1050,663,2380])
        self.assertEqual(set(inst[0]['pecas']),set(range(5)))

    def test_rotacao_com_base_confirmada(self):
        P=[peca(0,[0,0,0,18,413,432]),peca(1,[589,0,0,607,413,432]),peca(2,[18,0,0,589,18,432])]
        k=('Armário','607x413x432')
        f={'filhos':[{'desc':'Lat Direita','dim':(413,18,432),'qtd':1},{'desc':'Lat Esquerda','dim':(413,18,432),'qtd':1},{'desc':'Base Inferior','dim':(571,18,432),'qtd':1}]}
        self.assertEqual(len(geo.casar(P,[k],{k:1},{k:f})),1)
        self.assertEqual(len(geo.casar(P[:2],[k],{k:1},{k:f})),0)

if __name__ == '__main__': unittest.main()
