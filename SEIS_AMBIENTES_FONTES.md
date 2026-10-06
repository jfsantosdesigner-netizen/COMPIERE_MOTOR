# Seis ambientes para avaliação — 06/10/2026

| Tipo | Cliente | Pasta em PROJETOS TESTES |
|---|---|---|
| Cozinha | Caroline | CAROLINE_COZINHA |
| Cozinha | Felipe | FELIPE_COZINHA |
| Dormitório | Adriana Ojeda | ADRIANA OJEDA/DORMITÓRIO |
| Dormitório casal | Tiago Volpi | TIAGO VOLPI/DORMITÓRIO CASAL |
| Closet | Jaqueline da Silva | JAQUELINE DA SILVA/CLOSET |
| Closet | Leticia Mateus | LETICIA MATEUS |

O fluxo padrão gera configuração nova a cada execução, elimina o cache de peças e ignora JSONs anteriores de dados, cores e materiais. XML e DXF são as fontes de geometria e identificação. Layout, contrato, logo e imagens oficiais continuam como recursos visuais do motor. Os JSONs produzidos nesta execução são intermediários ou relatórios, não referências anteriores.

A busca de materiais reconstrói seu índice das imagens em MATERIAIS e texturas, sem depender de materiais_cores.json. Ausência de imagem continua registrada em QUALIDADE.md.

executar_seis_fontes.py valida a presença das fontes, retira os derivados anteriores das seis pastas, limpa caches compartilhados de cores/índice/texturas e executa novo_ambiente.py no PC. As referências anteriores são guardadas em AUDITORIA_SEIS_FONTES_<horário>/anteriores para futura comparação. SHA-256 confirma a preservação dos XMLs/DXFs. resultado.json registra retorno, PDF, páginas, integridade e preservação das fontes.

validar_seis_fontes.py abre os PDFs, apresenta pendências do relatório de qualidade e cria imagens das páginas 5–8 para inspeção. Isso não constitui aprovação final do projeto: estes seis cadernos são a base para a próxima avaliação.
