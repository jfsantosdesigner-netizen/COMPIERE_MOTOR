"""Condições de recuperação funcional, sem promover toda peça encoberta."""
import unittest,geo
from normal.ocultas import candidatos
class OcultasTest(unittest.TestCase):
    def contexto(self):
        m=dict(n=1,desc="Balcão",tipo="mod",bb=[0,0,80,1550,390,755],pecas=[10],parede="W")
        return {"geo":geo},dict(id="W",key="x+",itens=[m]),m
    def item(self,n,bb,desc="Tamponamento Inferior"):
        return dict(n=n,desc=desc,tipo="comp",bb=bb,pecas=[n],parede="W")
    def test_base_conectada_sob_modulo_recebe_detalhe(self):
        ns,w,m=self.contexto()
        g=[self.item(2,[0,0,60,1550,80,78]),self.item(3,[0,80,60,80,390,78]),self.item(4,[1470,80,60,1550,390,78])]
        w["itens"]+=g
        plans=candidatos(ns,w,g)
        self.assertEqual(len(plans),1)
        self.assertEqual({id(i) for i in plans[0][0]},{id(i) for i in g})
        self.assertIs(plans[0][1],m)
    def test_base_parcialmente_oculta_mantem_conjunto_inteiro(self):
        ns,w,m=self.contexto()
        g=[self.item(2,[0,0,60,1550,80,78]),self.item(3,[0,80,60,80,390,78]),self.item(4,[1470,80,60,1550,390,78])]
        w["itens"]+=g
        planos=candidatos(ns,w,[g[0]])
        self.assertEqual(len(planos[0][0]),3)
    def test_chapa_sobreposta_generica_continua_excluida(self):
        ns,w,_=self.contexto()
        i=self.item(2,[0,0,60,1550,390,78]);w["itens"].append(i)
        self.assertEqual(candidatos(ns,w,[i]),[])
    def test_sem_hospedeiro_nao_inventa_aplicacao(self):
        ns,w,_=self.contexto()
        i=self.item(2,[3000,0,60,4550,80,78],"Base do trilho")
        w["itens"].append(i)
        self.assertEqual(candidatos(ns,w,[i]),[])
    def test_fixacao_explicita_com_hospedeiro(self):
        ns,w,m=self.contexto()
        i=self.item(2,[0,0,60,1550,80,78],"Base do trilho")
        w["itens"].append(i)
        self.assertIs(candidatos(ns,w,[i])[0][1],m)
    def test_pecas_de_outra_parede_nao_formam_base(self):
        ns,w,_=self.contexto()
        i=self.item(2,[0,0,60,1550,80,78],"Base do trilho")
        i["parede"]="OUTRA"
        w["itens"].append(i)
        self.assertEqual(candidatos(ns,w,[i]),[])
if __name__=="__main__": unittest.main()
