import copy
import unittest
import xml.etree.ElementTree as ET
from .cameras import orientar, portas_do_canto, tampas_modulos_deitados


class DetalhesCameraTest(unittest.TestCase):
    def corpo(self):
        caixas = [[0,0,0,18,450,800], [582,0,0,600,450,800],
                  [18,0,0,582,450,18], [18,0,782,582,450,800],
                  [18,432,18,582,450,782]]
        return [dict(i=n,bb=b) for n,b in enumerate(caixas)]

    def test_abertura_prevalece_sobre_lateral_fechada_sem_mover_pecas(self):
        p=self.corpo(); antes=copy.deepcopy(p)
        grupo=[dict(desc='Nicho',pecas=list(range(5)))]
        op=orientar(grupo,p,'x+')
        self.assertEqual(op['camera_key'],'y+')
        self.assertGreater(op['elev'],0)
        self.assertEqual(p,antes)

    def test_corpo_girado_mantem_abertura_fisica(self):
        p=self.corpo()
        for i in p:
            b=i['bb'];i['bb']=[b[1],b[0],b[2],b[4],b[3],b[5]]
        self.assertEqual(orientar([dict(desc='Nicho',pecas=list(range(5)))],p,'y+')['camera_key'],'x+')

    def test_gaveta_mantem_camera_de_montagem(self):
        g=[dict(_gaveta_montada=True,_camera_detalhe_key='y-')]
        self.assertEqual(orientar(g,[],'x+'),dict(camera_key='y-',ang=15,elev=22))

    def test_prateleira_revela_face_de_apoio(self):
        op=orientar([dict(desc='Prateleira vidro',pecas=[0])],[dict(i=0,bb=[0,0,0,800,400,6])],'y+')
        self.assertEqual(op['elev'],30)

    def test_painel_vertical_nao_aparece_de_perfil(self):
        op=orientar([dict(desc='Painel',pecas=[0])],[dict(i=0,bb=[0,0,0,800,18,2200])],'x-')
        self.assertEqual(op['camera_key'],'y-')

    def test_canto_l_direito_segue_regra_explicita(self):
        caixas=[[0,0,0,18,580,2500],[902,0,0,920,950,2500],
                [0,0,0,920,18,2500],[340,932,0,920,950,2500],
                [18,0,0,920,580,18],[340,580,0,920,932,18],
                [18,0,2482,920,580,2500],[340,580,2482,920,932,2500]]
        p=[dict(i=n,bb=b) for n,b in enumerate(caixas)]
        op=orientar([dict(desc='Armário Canto L Direito',pecas=list(range(8)))],p,'x+')
        self.assertEqual(op['camera_key'],'y-')
        self.assertEqual(op['ang'],45)
        self.assertEqual(op['elev'],20)

    def test_regras_explicitas_dos_cantos_nas_quatro_frentes(self):
        for chave in ('x+','x-','y+','y-'):
            for nome,ang in [('Canto Reto Direito',0),('Canto Reto Esquerdo',0),('Canto L Direito',45),('Canto L Esquerdo',-45)]:
                with self.subTest(chave=chave,nome=nome):
                    op=orientar([dict(desc=nome,pecas=[0])],self.corpo(),chave)
                    self.assertEqual(op,dict(camera_key=chave,ang=ang,elev=20))

    def test_adega_deitada_preserva_leitura_dos_vaos(self):
        p=self.corpo()
        for i in p:
            i['bb'][2]*=.15;i['bb'][5]*=.15
        op=orientar([dict(desc='Armário Adega/Nicho',pecas=list(range(5)))],p,'y+')
        self.assertLessEqual(op['elev'],10)

    def test_tampa_de_caixa_deitada_somente_no_detalhe(self):
        b=[172, -4155, 0, 585, -3548, 432]
        pecas=[dict(i=1,bb=[187,-4141,18,570,-3562,24]),
               dict(i=2,bb=[175,-4153,432,582,-3550,450]),
               dict(i=3,bb=[173,-4137,0,191,-3566,432])]
        modulo=dict(tipo='mod',desc='Armário Superior',bb=b,pecas=[1,2,3])
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),{2})
        pecas[1]['bb'][2]=380
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),set())
        pecas[1]['bb'][2]=432
        modulo['desc']='Armário Canto L Direito'
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),set())

    def test_portas_internas_do_canto_exigem_medidas_xml(self):
        root=ET.fromstring('<ROOT><ITEM ID="POR_PAI_PORTA" WIDTH="2464" HEIGHT="18" DEPTH="345"/></ROOT>')
        p=[dict(i=0,dim=[18,345,2464]),dict(i=1,dim=[18,580,2470]),dict(i=2,dim=[18,345,2464])]
        g=[dict(desc='Armário Canto L Direito',pecas=[0,1])]
        self.assertEqual(portas_do_canto(dict(XML_TREE=root,P=p),g),{0})
        self.assertEqual(portas_do_canto(dict(XML_TREE=root,P=p),[dict(desc='Armário comum',pecas=[0,1])]),set())

    def test_porta_falsa_decorativa_nao_e_retirada_pelo_detalhe(self):
        root=ET.fromstring('<ROOT><ITEM ID="POR_PAI_PORTA" DESCRIPTION="Porta falsa" WIDTH="800" HEIGHT="18" DEPTH="400"/></ROOT>')
        ns=dict(XML_TREE=root,P=[dict(i=0,dim=[800,18,400])])
        self.assertEqual(portas_do_canto(ns,[dict(desc='Canto L',pecas=[0])]),set())


if __name__=='__main__': unittest.main()
