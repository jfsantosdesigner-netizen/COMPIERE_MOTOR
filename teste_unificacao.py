# -*- coding: utf-8 -*-
"""Contratos e propriedades da Etapa 4. Executar: python -B teste_unificacao.py."""
import ast
import builtins
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import ambiente
import cena_render
import entrada_xml
import geo
import projeto_unificado as U
import unificacao as F


XML = '''<ROOT><CATEGORY DESCRIPTION="MDF"><ITEMS>
<ITEM ID="MOD_BAL" DESCRIPTION="Balcão" WIDTH="600" HEIGHT="700" DEPTH="500">
<REFERENCES><MODEL REFERENCE="Branco"/></REFERENCES><ITEMS>
<ITEM ID="LAT_1" WIDTH="18" HEIGHT="700" DEPTH="500"><REFERENCES><MODEL REFERENCE="Branco"/></REFERENCES></ITEM>
<ITEM ID="LAT_2" WIDTH="18" HEIGHT="700" DEPTH="500"><REFERENCES><MODEL REFERENCE="Branco"/></REFERENCES></ITEM>
<ITEM ID="BAS_1" WIDTH="564" HEIGHT="3" DEPTH="500"><REFERENCES><MODEL REFERENCE="Branco"/></REFERENCES></ITEM>
<ITEM ID="POR_1" DESCRIPTION="Porta" WIDTH="600" HEIGHT="700" DEPTH="18"><REFERENCES><MODEL REFERENCE="Branco"/><MAT REFERENCE="mdf"/></REFERENCES></ITEM>
</ITEMS></ITEM></ITEMS></CATEGORY></ROOT>'''


def pecas():
    caixas = [[0, 0, 0, 18, 500, 700], [582, 0, 0, 600, 500, 700],
              [18, 0, -3, 582, 500, 0], [0, -18, 0, 600, 0, 700],
              [0, 0, 0, 4000, 3000, 5], [-150, 0, 0, 0, 3000, 2600],
              [1500, 0, 850, 3000, 600, 880]]
    return [dict(i=i, layer=f'L{i}', bb=list(b), dim=[b[k + 3] - b[k] for k in range(3)],
                 faces=[[list(v) for v in f] for f in ambiente.caixa_faces_(b)]) for i, b in enumerate(caixas)]


def xml_dados():
    with patch.object(builtins, 'open', return_value=io.BytesIO(XML.encode('utf-8'))) as leitura:
        dados = entrada_xml.ler('entrada_em_memoria.xml')
        assert leitura.call_count == 1
    return dados


class TesteUnificacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xml = xml_dados()

    def projeto(self):
        return F.construir(pecas(), copy.deepcopy(self.xml))

    def test_etapa_pura_preserva_entradas(self):
        P, xml = pecas(), copy.deepcopy(self.xml)
        antes = copy.deepcopy((P, xml))
        with patch.object(builtins, 'open', side_effect=AssertionError('I/O na Etapa 4')):
            resultado = F.construir(P, xml)
        self.assertEqual((P, xml), antes)
        self.assertEqual(resultado['diagnostico']['itens_nao_localizados'], [])

    def test_orfa_incorporada_antes_do_fechamento(self):
        p = self.projeto()
        self.assertIn(2, p['itens'][0]['pecas'])
        self.assertEqual(p['diagnostico']['orfas_adotadas'], [[1, 2]])
        self.assertEqual(p['itens'][0]['bb'][2], -3)

    def test_porta_com_dono_nunca_vira_eletro(self):
        p = self.projeto()
        self.assertEqual(p['portas']['pecas_xml'], {3})
        self.assertIn(3, p['itens'][0]['pecas'])
        for papel in ('pedra', 'malha_par', 'eletros', 'par_dxf', 'paredes_pecas'):
            self.assertNotIn(3, {q['i'] for q in p['ambiente'][papel]})
        c = cena_render.construir(p, 'cota')
        self.assertNotIn(3, c['pecas_visiveis'])
        self.assertFalse(c['ambiente']['piso'])

    def test_material_existe_sem_biblioteca_rgb(self):
        p = self.projeto()
        self.assertEqual(p['materiais'][0]['nome'], 'Branco')
        self.assertIsNone(p['materiais'][0]['rgb'])
        self.assertNotIn('mat', p['pecas'][0])

    def test_reprodutibilidade_e_json_independente(self):
        a, b = self.projeto(), self.projeto()
        self.assertEqual(U.para_json(a), U.para_json(b))
        dados = U.para_json(a)
        restaurado = U.de_json(json.loads(json.dumps(dados)))
        self.assertEqual(U.para_json(restaurado), dados)
        dados['itens'][0]['pecas'].clear()
        self.assertTrue(a['itens'][0]['pecas'])

    def test_mesmo_dxf_outro_xml_tem_identidade_distinta(self):
        a = self.projeto(); xml = copy.deepcopy(self.xml)
        xml['linhas'] = [('Armário', '600x700x500')]
        b = F.construir(pecas(), xml)
        self.assertEqual(a['identidade']['pecas_sha256'], b['identidade']['pecas_sha256'])
        self.assertNotEqual(a['identidade']['projeto_sha256'], b['identidade']['projeto_sha256'])
        with self.assertRaises(ValueError):
            cena_render.validar(cena_render.construir(a, 'vista'), b)

    def test_campos_derivados_divergentes_rejeitados(self):
        alteracoes = [lambda p: p['moveis'].add(6),
                      lambda p: p['materiais'][0].update(nome='Inventado'),
                      lambda p: p.update(modulos=[]),
                      lambda p: p['portas'].update(modulos_xml=[]),
                      lambda p: p['itens'][0]['pecas'].remove(0)]
        for alterar in alteracoes:
            p = self.projeto(); alterar(p)
            with self.assertRaises(ValueError): U.validar(p)

    def test_anotacoes_de_vista_nao_reabrem_unificacao(self):
        p = self.projeto(); identidade = dict(p['identidade'])
        p['itens'][0]['parede'] = 'y+@500'; p['itens'][0]['num_A'] = 1
        U.validar(p)
        self.assertEqual(p['identidade'], identidade)
        self.assertNotIn('num_A', U.para_json(p)['itens'][0])

    def test_cota_rejeita_pedra_e_camera_perspectiva(self):
        p = self.projeto(); c = cena_render.construir(p, 'cota')
        c['pecas_visiveis'].add(6)
        with self.assertRaises(ValueError): cena_render.validar(c, p)
        with self.assertRaises(ValueError):
            cena_render.construir(p, 'cota', camera={'modo': 'perspectiva_interior'})

    def test_geometria_invalida_rejeitada(self):
        for valor in (float('nan'), float('inf'), True):
            P = pecas(); P[0]['bb'][0] = valor
            with self.assertRaises(ValueError): F.construir(P, self.xml)
        P = pecas(); P[0]['faces'][0][0] = [0, float('nan'), 0]
        with self.assertRaises(ValueError): F.construir(P, self.xml)

    def test_contrato_adulterado_rejeitado(self):
        p = self.projeto(); dados = U.para_json(p)
        dados['ambiente']['eletros'].append(6)  # a mesma peça já é pedra
        with self.assertRaises(ValueError): U.de_json(dados)
        dados = U.para_json(p); dados['itens'][0]['desc'] = 'Alterado'
        with self.assertRaises(ValueError): U.de_json(dados)
        dados = U.para_json(p); dados['portas_xml'] = [True]
        with self.assertRaises(ValueError): U.de_json(dados)

    def test_geo_nao_modifica_pecas_nem_compartilha_caixa_componente(self):
        P = pecas(); antes = copy.deepcopy(P)
        itens = geo.casar(P, [('Painel', '600x700x18')])
        self.assertEqual(P, antes)
        itens[0]['bb'][0] = -999
        self.assertEqual(P, antes)

    def test_orientacao_preservada_com_porta_ja_incorporada(self):
        p = self.projeto()
        antigo = copy.deepcopy(p['itens'])
        for it in antigo: it['pecas'] = [i for i in it['pecas'] if i not in p['portas']['pecas_xml']]
        a = geo.definir_paredes(antigo, p['pecas'])
        b = geo.definir_paredes(p['itens'], p['pecas'], p['portas']['pecas_xml'])
        self.assertEqual([(w['key'], w['plano']) for w in a], [(w['key'], w['plano']) for w in b])

    def test_caderno_nao_reinterpreta_xml_ou_refaz_casamento(self):
        fonte = Path(__file__).with_name('gerar_caderno.py').read_text(encoding='utf-8-sig')
        tree = ast.parse(fonte)
        chamadas = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(any(n in chamadas for n in ('ET.parse', '_ET2.parse', 'geo.casar', 'entrada_projeto.casar')))
        self.assertEqual(chamadas.count('entrada_xml.ler'), 1)
        self.assertEqual(chamadas.count('unificacao.construir'), 1)

    def test_reprodutibilidade_entre_processos(self):
        assinaturas = []
        for seed in ('0', '1', '173'):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONIOENCODING='utf-8')
            r = subprocess.run([sys.executable, '-B', __file__, '--assinatura'],
                               capture_output=True, text=True, encoding='utf-8', env=env, check=True)
            assinaturas.append(r.stdout.strip())
        self.assertEqual(len(set(assinaturas)), 1)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--assinatura':
        print(F.construir(pecas(), xml_dados())['identidade']['projeto_sha256'])
    else:
        unittest.main()
