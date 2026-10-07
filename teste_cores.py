import copy, json, os, tempfile
import cores, unificacao, projeto_unificado

def test_nome():
    assert cores.normalizar('Carvalho Trêviso') == 'carvalho treviso'
    assert cores.parecido('metalic', 'metallic')

def test_biblioteca():
    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, 'MATERIAIS'))
        json.dump([['x.jpg', 'preto tx', [0.1, 0.2, 0.3]]],
                  open(os.path.join(d, 'materiais_cores.json'), 'w'))
        b = cores.Biblioteca(d)
        caminho = os.path.join(d, 'MATERIAIS', 'x.jpg')
        b.indice = [[caminho, 'preto tx']]
        b.rgb_path[caminho] = [0.1, 0.2, 0.3]
        assert b.cor_material('Preto TX') == (0.1, 0.2, 0.3)

def test_aplicar_projeto_real():
    P = [{'i': 0, 'layer': 'L0', 'bb': [0,0,0,100,100,18],
          'dim': [100,100,18], 'faces': []}]
    amb = {'duplicadas': set(), 'pedra': [], 'malha_par': [], 'eletros': [],
           'par_dxf': [], 'paredes_pecas': [], 'piso_z': 0,
           'faces_parede_real': [], '_quantidade_pecas': 1,
           '_pecas_sha256': unificacao._assinatura(P)}
    item = {'n': 1, 'desc': 'Teste', 'dim': '100x100x18', 'bb': [0,0,0,100,100,18],
            'tipo': 'mod', 'pecas': [0], 'larg': 100}
    projeto = projeto_unificado.construir(P, [item], amb, materiais_xml={0: 'Preto TX'})
    geo_antes = copy.deepcopy((P[0]['bb'], P[0]['dim'], P[0]['faces']))
    class B:
        cache = {'Preto TX': [[0.1,0.2,0.3], r'C:\MATERIAIS\preto.jpg']}
        def cor_material(self, nome): return (0.1,0.2,0.3)
    identidade_antes = projeto['identidade']['projeto_sha256']
    r = cores.aplicar(projeto, B())
    assert r['coloridas'] == 1 and r['usadas']['Preto TX'] == 1
    assert projeto['pecas'][0]['mat'] == 'Preto TX'
    assert projeto['pecas'][0]['rgb'] == (0.1,0.2,0.3)
    assert projeto['materiais'][0]['nome'] == 'Preto TX'
    assert projeto['materiais'][0]['rgb'] == (0.1,0.2,0.3)
    assert projeto['materiais'][0]['textura'] == r'C:\MATERIAIS\preto.jpg'
    assert copy.deepcopy((P[0]['bb'], P[0]['dim'], P[0]['faces'])) == geo_antes
    assert projeto['identidade']['projeto_sha256'] != identidade_antes
    projeto_unificado.validar(projeto)

if __name__ == '__main__':
    test_nome(); test_biblioteca(); test_aplicar_projeto_real()
    print('ETAPA 5 CORES: OK')
