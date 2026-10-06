# Cotas executivas — motor normal e especiais

Decisão de João Felipe, 06/10/2026. Esta regra atualiza o isolamento das cotas: permanece somente a marcenaria daquela vista e a geometria das pedras pertinentes como referência.

## Geometria

- Mostrar o conjunto montado, com caixas, prateleiras, gavetas, fechamentos, vistas, tamponamentos e demais componentes construtivos atribuídos.
- Retirar portas reais do conjunto, incluindo as portas avulsas identificadas no XML. Não criar uma seção do móvel para revelar seu interior.
- Fechamentos, vistas, tamponamentos, painéis, rodapés, afastadores e cunhas atribuídos como componentes construtivos são protegidos contra a heurística de porta. Uma porta efetivamente identificada no XML continua sendo retirada.
- Componentes construtivos estreitos não são eliminados pelo filtro dimensional dos acessórios internos dos módulos. Ferragens internas continuam seguindo a regra de representação, sem cotas próprias.
- Não incluir paredes, piso, aberturas, eletros ou móveis de outras vistas.
- Pedra, mármore ou granito entram pela geometria real reconhecida no DXF, em cinza claro, sem textura, listagem ou cadeia própria de cotas. A entidade é preservada inteira, sem recortar seus vértices.
- A referência de pedra deve estar próxima do conjunto (até 180 mm entre envelopes) e ter pelo menos 60% da largura projetada na extensão da vista. Isso evita trazer uma bancada de outro trecho apenas porque encosta na extremidade do conjunto.
- O quadro e a escala incluem a referência selecionada por inteiro. A geometria dos móveis não é cortada para caber.

## Contornos

`cotas_comum.contornos` desenha uma camada final escura depois das texturas e preenchimentos. O mapa de identificação usa a mesma projeção e ordem das faces do desenho 2D.

As bordas são obtidas por peça visível, independentemente das flags de aresta que vieram no DXF. Faces trianguladas da mesma peça não geram uma diagonal. Peças completamente encobertas não acrescentam linhas internas. Peças diferentes continuam delimitadas mesmo quando têm o mesmo material.

A máscara usa 250 dpi e espessura aproximada de 0,86 pt. As cotas vermelhas e seus números são desenhados depois dessa camada. A projeção e as medidas existentes permanecem em escala.

O desenho 2D é compartilhado pelos dois motores. As duas faces da prancha especial de cotas de painel passam pelo renderer 2D; a traseira utiliza direção invertida, mantendo as posições reais das peças. O divisor em vista superior também utiliza a mesma camada de contornos.

## Cristaleira da cozinha Priscila

O módulo de 400 × 2390 × 580 mm contém laterais que delimitam um vão interno de 364 mm. Uma peça vertical localizada de 320 mm estava sendo tratada como divisória de toda a altura, criando vãos artificiais de 244 e 105 mm e duas cadeias iguais de alturas das prateleiras.

A detecção de vãos agora considera a extensão vertical e os encontros com prateleiras. Uma divisória parcial real, com prateleiras encostadas em suas bordas, continua válida. Uma peça localizada não divide automaticamente o armário inteiro. Cadeias com os mesmos níveis no mesmo módulo são desenhadas uma única vez; níveis diferentes continuam cotados.

## Verificação

- Sete testes específicos: contorno sem flags, triangulação, ocultação, junção de peças, cristaleira, divisória parcial real e seleção de portas/componentes/pedra sem modificar a geometria.
- Dezesseis regressões das câmeras, materiais, balões e detalhes funcionais.
- Geração das 21 categorias especiais em fixture visual controlada, que não substitui projetos reais de cada família.
- Regeneração dos cadernos normais e combinados de suíte/cozinha Priscila; auditoria de seleção da geometria, contornos, vãos, câmeras e balões.

Execução dos testes: `python -m unittest test_cotas_comum test_camera_comum normal.test_regras normal.test_ocultas`.
