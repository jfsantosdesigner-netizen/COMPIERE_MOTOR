import unittest
from camera_comum import cantos, dot, posicionar, obstaculos, enquadrar


class CamerasTest(unittest.TestCase):
    def test_camera_fora_de_todo_mobiliario_nas_quatro_frentes(self):
        alvo = [0,0,100,2800,600,2700]
        vizinho = [-20000,-20000,0,20000,20000,3200]
        for frente in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0)):
            with self.subTest(frente=frente):
                centro,d,camera = posicionar(alvo,frente,4200,True,[vizinho])
                self.assertEqual(camera[2],1500)
                self.assertTrue(all(dot(tuple(v[k]-camera[k] for k in range(3)),frente)>=199.99
                                    for b in (alvo,vizinho) for v in cantos(b)))

    def test_detalhe_preserva_centro_e_inclinacao_funcional(self):
        _,_,cam = posicionar([0,0,0,600,400,80],(0,.8,-.6),3200)
        self.assertGreater(cam[2],40)

    def test_retira_modulo_inteiro_quando_uma_frente_obstrui(self):
        pecas = [dict(i=0,bb=[0,0,0,600,600,800]),dict(i=1,bb=[0,-300,0,600,-200,800]),
                 dict(i=2,bb=[0,-200,0,600,200,800])]
        itens=[dict(pecas=[0],bb=pecas[0]['bb']),dict(pecas=[1,2],bb=[0,-300,0,600,200,800])]
        self.assertEqual(obstaculos(itens,pecas,{0},(0,1,0)),{1,2})
        self.assertEqual(pecas[2]['bb'],[0,-200,0,600,200,800])

    def test_vizinho_sem_sobreposicao_e_peca_interna_sao_preservados(self):
        pecas=[dict(i=0,bb=[0,0,0,600,600,800]),dict(i=1,bb=[700,-300,0,900,-200,800]),
               dict(i=2,bb=[0,200,0,600,300,800])]
        self.assertEqual(obstaculos([],pecas,{0},(0,1,0)),set())

    def test_alvo_tem_precedencia_sobre_retirada(self):
        pecas=[dict(i=0,bb=[0,0,0,600,600,800]),dict(i=1,bb=[0,-300,0,600,-200,800])]
        itens=[dict(pecas=[0,1],bb=[0,-300,0,600,600,800])]
        self.assertEqual(obstaculos(itens,pecas,{0},(0,1,0)),set())

    def test_enquadramento_preserva_conjunto_e_vizinho_inteiro(self):
        alvo=[0,0,100,1200,600,2400];vizinho=[1200,0,0,1800,600,2600]
        quadro=enquadrar(alvo,0,[vizinho])
        self.assertTrue(all(quadro[k]<=alvo[k] and quadro[k+3]>=alvo[k+3] for k in range(3)))
        self.assertGreaterEqual(quadro[3],vizinho[3]+300)
        self.assertGreaterEqual(quadro[5],vizinho[5]+150)


if __name__ == '__main__':
    unittest.main()
