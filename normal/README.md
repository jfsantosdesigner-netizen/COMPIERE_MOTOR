# Fluxo normal de gerar_caderno

O gerar_caderno.py monta capa, contrato, especificações/planta, visão geral e os ciclos de listagem/cotas. As pranchas de especiais e móveis diversos são responsabilidade do pacote especiais e do gerar_caderno_com_especiais.py.

A separação usa especiais.relacoes para manter a mesma identificação construtiva em ambos os fluxos. O catálogo é calculado uma vez e reutilizado pelo motor combinado. Portas com perfil e usinagens técnicas aplicadas permanecem representadas no móvel normal e podem receber detalhamento pelo motor de especiais.

normal.regras aplica as condições normais do documento: gavetas montadas, detalhes funcionais na mesma folha, cantos, prateleiras de vidro, mesas de cabeceira, adegas/cristaleiras, legendas de pino invisível e removível e acessórios internos somente como representação. Subimagens usam as peças efetivamente identificadas no DXF.

normal.vidros lê os nomes de acabamentos do XML. O vidro é translúcido segundo seu acabamento; os quatro perfis são opacos e recebem a cor própria do alumínio. Reflecta Bronze e Champagne são tratados separadamente. As cores e opacidades são uma representação técnica, sem simulação óptica de reflexos reais.

As câmeras de listagem ficam centradas e niveladas. A subimagem da gaveta montada usa seu eixo frontal e uma elevação para mostrar o fundo e a montagem. visual_comum distribui os balões em ambos os motores, dentro do quadro e sem sobreposição.

Validação: geração dos cadernos normais de Suíte Casal e Cozinha, geração combinada de ambos, conferência dos títulos/páginas e dos retângulos dos balões no PDF, teste de 80 balões coincidentes e teste dos acabamentos Bronze/Champagne/transparente/espelho.

Peças funcionais encobertas usam normal.ocultas: detalhe montado, referência de aplicação e balões em superfícies visíveis. Sobreposição genérica não cria subimagem. A engenharia e as referências manuais estão em [SUBIMAGENS_FUNCIONAIS.md](SUBIMAGENS_FUNCIONAIS.md). Regressões: python -m unittest normal.test_regras normal.test_ocultas.


Refinamento de vistas divididas (06/10/2026): nas folhas Superiores/Inferiores ou Parte 1/Parte 2, o alvo da câmera e os balões da imagem principal seguem os itens da listagem daquela folha. Os móveis próximos continuam como contexto. A seleção usa itens_vista, independente do parâmetro itens reservado aos detalhes.

Câmeras dos cantos aprovadas por João Felipe em 06/10/2026: canto reto frontal, elevação 20°; Canto L direito +45° e esquerdo −45°, elevação 20°, foco no centro do módulo e referência nos lados abertos reais do canto. Preservar subimagens funcionais.
