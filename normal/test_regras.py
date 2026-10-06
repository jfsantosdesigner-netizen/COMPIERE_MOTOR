"""Regressões das condições que distinguem o fluxo normal do especial."""
import unittest
import xml.etree.ElementTree as ET
import pymupdf as fz
from normal.vidros import estilo,faces_porta
from normal.regras import montar_gavetas
from especiais.detector import _classificar,Sinais
from especiais.regras import Destino
from visual_comum import baloes

class FluxoNormalTest(unittest.TestCase):
    def test_vidro_e_perfil_tem_acabamentos_independentes(self):
        n=ET.fromstring('<ITEM><DESC_ACA REFERENCE="Reflecta"/><DESC_COR_PAI REFERENCE="Bronze"/><DESC_ACA_PER REFERENCE="Champagne"/></ITEM>')
        v=estilo(n)
        self.assertEqual(v["rgb"],(.57,.40,.27))
        self.assertEqual(v["alpha"],.38)
        self.assertEqual(v["perfil_rgb"],(.73,.64,.48))
        faces=faces_porta([0,0,0,820,20.3,2384],(0,1),v)
        self.assertEqual(len(faces),5)
        self.assertEqual(faces[0][2],.38)
        self.assertTrue(all(f[2]==1 for f in faces[1:]))
        self.assertEqual(estilo(ET.fromstring('<ITEM><VIDRO REFERENCE="Espelho"/></ITEM>'))["alpha"],1)

    def test_adega_cristaleira_e_porta_falsa_permanecem_normais(self):
        for desc in ("Armário Adega/Nicho","Cristaleira","Porta falsa"):
            destino,_,_=_classificar(dict(desc=desc,tipo="mod"),Sinais(curva=True,angulo=True,usinagem=True))
            self.assertEqual(destino,Destino.NORMAL)

    def test_gaveta_montada_preserva_pecas_e_dimensoes(self):
        grupo=[dict(bb=[0,0,300,820,480,318],pecas=[0]),dict(bb=[0,0,318,820,18,435],pecas=[1])]
        w=dict(id="W",key="x+",itens=grupo.copy())
        ns=dict(GAVETAS=[grupo],paredes=[w],FV={"x+":(1,0)},fmt=lambda v:str(int(v)),inst=grupo.copy())
        montar_gavetas(ns)
        self.assertEqual(len(w["itens"]),1)
        gaveta=w["itens"][0]
        self.assertEqual(gaveta["dim"],"820x135x480")
        self.assertEqual(gaveta["pecas"],[0,1])
        self.assertEqual(gaveta["_camera_detalhe_key"],"y+")

    def test_baloes_coincidentes_nao_sobrepoem_e_ficam_no_quadro(self):
        d=fz.open()
        try:
            p=d.new_page()
            rect=fz.Rect(10,10,280,280)
            itens=[{"num_A":j+1} for j in range(80)]
            n=baloes({"fz":fz,"PRETO":(0,0,0)},p,rect,itens,"A",{id(i):(140,140) for i in itens})
            caixas=[q["rect"] for q in p.get_drawings() if q.get("fill")==(1,1,0)]
            self.assertEqual(n,80)
            self.assertEqual(len(caixas),80)
            self.assertTrue(all(rect.contains(q) for q in caixas))
            self.assertFalse(any(a.intersects(b) for j,a in enumerate(caixas) for b in caixas[j+1:]))
        finally:
            d.close()

if __name__=="__main__":
    unittest.main()
