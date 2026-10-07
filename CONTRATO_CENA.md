# CONTRATO DA CENA — versão 1

A Cena é a entrada única do render. Ela deriva do Projeto Unificado e declara quais peças aparecem, qual ambiente acompanha os móveis, quais portas saem e qual câmera será usada.

| Finalidade | Móveis | Ambiente | Portas | Câmera |
|---|---|---|---|---|
| `visao_geral` | todos no contexto | paredes, piso, pedra e eletros | fechadas | perspectiva interior |
| `vista` | itens principais; vizinhos só como contexto | ambiente quando solicitado | fechadas | frontal |
| `cota` | somente itens da parede | nenhum | removidas | ortográfica frontal |

Toda cena carrega a identidade do Projeto Unificado, trabalha em milímetros e rejeita itens ou peças de outro projeto. A câmera e o foco têm altura padrão de 1.500 mm; quando o motor calcula posição e alvo específicos, esses valores são registrados no mesmo campo `camera`.

Para cotas, o contrato impõe a regra rígida: sem parede, piso, pedra, eletro ou porta. `pecas_visiveis` é calculado antes do desenho e pode ser auditado sem abrir o PDF.
