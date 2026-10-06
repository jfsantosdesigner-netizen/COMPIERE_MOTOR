# Fluxo normal de gerar_caderno

O gerar_caderno.py monta capa, contrato, especificações/planta, visão geral e os ciclos de listagem/cotas. As pranchas de especiais e móveis diversos são responsabilidade do pacote especiais e do gerar_caderno_com_especiais.py.

A separação usa especiais.relacoes para manter a mesma identificação construtiva em ambos os fluxos. O catálogo é calculado uma vez e reutilizado pelo motor combinado. Portas com perfil e usinagens técnicas aplicadas permanecem representadas no móvel normal e podem receber detalhamento pelo motor de especiais.

normal.regras aplica as condições normais do documento: gavetas montadas, detalhes funcionais na mesma folha, cantos, prateleiras de vidro, mesas de cabeceira, adegas/cristaleiras, legendas de pino invisível e removível e acessórios internos somente como representação. Subimagens usam as peças efetivamente identificadas no DXF.

normal.vidros lê os nomes de acabamentos do XML. O vidro é translúcido segundo seu acabamento; os quatro perfis são opacos e recebem a cor própria do alumínio. Reflecta Bronze e Champagne são tratados separadamente. As cores e opacidades são uma representação técnica, sem simulação óptica de reflexos reais.

As câmeras de listagem ficam centradas e niveladas. A subimagem da gaveta montada usa seu eixo frontal e uma elevação para mostrar o fundo e a montagem. visual_comum distribui os balões em ambos os motores, dentro do quadro e sem sobreposição.

Validação: geração dos cadernos normais de Suíte Casal e Cozinha, geração combinada de ambos, conferência dos títulos/páginas e dos retângulos dos balões no PDF, teste de 80 balões coincidentes e teste dos acabamentos Bronze/Champagne/transparente/espelho.
