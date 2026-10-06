# Padrão de câmeras dos cadernos COMPIERE

## Referências examinadas

Foram analisados dez cadernos manuais da pasta Projetos João Felipe, com 103 páginas no total. A tabela identifica as páginas físicas do PDF usadas como evidência de enquadramento. Não são dez versões do mesmo arquivo.

| Caderno | Páginas de referência | Padrão observado |
|---|---|---|
| [Priscila — Suíte casal](https://drive.google.com/file/d/1z8m4DKzxibqIPXR6FhIl15V3PF23lJB6/view) | 4, 6, 8, 10, 13–17 | Frontal completa entre paredes/janela; ângulo para apoio, montagem e aplicação do divisor. |
| [Priscila — Cozinha](https://drive.google.com/file/d/1ay-zOMpusapWM4IoXwIP6XcWwMRTU-Da/view) | 4–11, 13–16 | Parede inteira na frontal; pedra e eletros localizam o conjunto; diagonais explicam canto e fixação. |
| [Glauber — Cozinha](https://drive.google.com/file/d/1MMhC7JyL6Z8-jtsmV24UHuGBPC59sSV9/view) | 4–10, 12 | Cada trecho do L tem sua frontal; vistas elevadas revelam apoio e estrutura da máquina de lavar. |
| [Alexandre — Closet](https://drive.google.com/file/d/1FYyztY1J-Kx4DjOrumPYcZYUQ9JjeFYh/view) | 4–9, 11–17 | Módulos completos na frontal; gavetas e trilhos em complemento; base em vista elevada pela sua geometria horizontal. |
| [Daniel Furtado — Montagem cozinha](https://drive.google.com/file/d/17Arcg4gUBTmBQVxW7-6aZS81DO4TL58A/view) | 4, 6–9 | Frontal mantém a relação com pedra, parede e eletros; diagonal localizada para montagem da torre. |
| [Alexandre — Cozinha](https://drive.google.com/file/d/1wdBsVW9-xKV3v5cpE43p46zrKFmwiBpn/view) | 3–5 | Parede e ilha em vistas distintas; frontal da ilha inteira; perspectiva superior só para os divisores. |
| [Alexandre — Banho Laidi](https://drive.google.com/file/d/1htWrdwE54Dfg-rySH3zhUg0kIm_Vndh5/view) | 3–4 | Frontal do armário com bancada, cuba e paredes laterais; complemento elevado mostra profundidade. |
| [Willian Fonseca — Sala](https://drive.google.com/file/d/122C4VFBdp6bLl8JPH0FCfhOXQcHVCmsY/view) | 3–6 | Painel/rack completos, TV e arquitetura como referência; vista A não substitui a vista B. |
| [Willian Fonseca — Dormitório casal](https://drive.google.com/file/d/19BdXEbaVjOX_QEtoW4lcZjFkWMq2uzNu/view) | 3–8 | Uma frontal para cada parede, com janela, portas, painel e piso; internos abertos em complemento. |
| [Taciana Honório — Área de serviço](https://drive.google.com/file/d/1U47vcWws3UteX28PtGn9P7OXF76mjpQG/view) | 3–7 | Conjunto superior/inferior completo com tanque e máquina; subimagem localiza a base; diagonal complementar. |

Os PDFs permitem reconhecer o resultado visual, mas não recuperar numericamente a câmera original do Promob. Os valores abaixo são parâmetros de engenharia definidos para reproduzir esse padrão, não medições das câmeras dos arquivos.

## Padrão compartilhado

| Uso | Direção | Enquadramento e contexto |
|---|---|---|
| Listagem normal | Frontal à parede da vista, rotação e elevação zero | Todos os móveis daquela vista por inteiro. Piso, fundo, paredes laterais e elementos próximos ajudam a localizar. Numeração e tabela somente da vista. |
| Listagem especial | Frontal à face em análise | Conjunto montado completo. Frente/lateral/trás continuam separados quando necessários à identificação das peças visíveis. Referência frontal mostra a aplicação no ambiente. |
| Visão geral | Frontal por vista | Mantém contexto. A capa pode usar diagonal para um conjunto em L, quando uma única frontal não explica as duas direções. |
| Detalhe funcional | Frontal como ponto de partida; ângulo previsto pela função quando necessário | Gaveta, divisor, base horizontal, trilho ou fixação podem exigir elevação/diagonal para revelar sua montagem. Mantém posições reais, sem transformar o detalhe em corte ou explosão. |
| Referência de localização | Frontal, nivelada | Hospedeiro completo e ambiente próximo; caixa vermelha destaca a posição real da peça, mesmo que esteja encoberta. Não cria balão de peça oculta na imagem principal. |
| Cotas | Elevação 2D frontal existente | Mantém escala, agrupamento e isolamento definidos nas regras anteriores. |

### Posição e distância

- Câmeras do ambiente niveladas a 1.500 mm de altura. Não inclinar para alcançar o topo de um móvel alto: ajustar enquadramento e recuar.
- Centralizar horizontalmente no envelope de todos os móveis daquela vista. O quadro inclui o envelope inteiro, inclusive quando o XML é maior que as faces exportadas no DXF.
- Distância inicial: maior entre 1,9 vezes a maior dimensão do conjunto e o mínimo do renderer. Em ambiente, mínimo de 7.000 mm para reduzir a variação de perspectiva.
- Recuo adicional quando necessário para deixar todo o modelo pelo menos 200 mm à frente do plano da câmera. Evita câmera dentro de móvel vizinho e descarte de faces pelo plano próximo.
- Detalhes mantêm o centro do conjunto e as inclinações funcionais já definidas por categoria; utilizam o mesmo cálculo de distância segura para a geometria exibida.

### Obstáculos e elementos do ambiente

1. Preservar sempre as peças do alvo. Nenhum alvo pode pertencer à seleção de objetos retirados.
2. Para uma frontal, identificar entidade externa à frente do alvo com sobreposição em largura e altura. Retirar o módulo inteiro se seu corpo ou alguma de suas peças obstruir o alvo; não recortar suas chapas ao meio.
3. Preservar vizinhos sem sobreposição. Selecionar sua presença usando o envelope do módulo, em vez de aceitar umas chapas e rejeitar outras pela distância.
4. Retirar paredes da frente antes de ajustar ângulo. O fallback de paredes usa caixas completas, sem fabricar segmentos pelo recorte da área de interesse. A seleção das superfícies arquitetônicas do DXF mantém fundo e referências laterais pertinentes.
5. Piso e arquitetura completam o quadro; não são peças listadas. Um especial vizinho pode aparecer como contexto no motor normal, sem voltar à tabela ou gerar prancha especial nesse motor.
6. Quando a necessidade for construtiva, utilizar a subimagem funcional existente. Não trocar automaticamente uma frontal por diagonal para contornar obstáculos.

### Quadro e prioridade visual

O envelope do conjunto listado cabe integralmente no quadro. A referência ambiental acrescenta 300 mm laterais, piso e 150 mm acima do conjunto, com mínimo de 2.200 mm de largura e 2.000 mm de altura. Vizinhos próximos que cabem até 700 mm além das extremidades ampliam o quadro por inteiro. Elementos distantes podem ficar fora do enquadramento: preservar contexto não significa reduzir o móvel até mostrar todo o imóvel em cada imagem.

A seleção não move, redimensiona nem corta a geometria do projeto. A moldura do PDF continua sendo o limite da imagem. Vidros, materiais, balões, regras funcionais, catálogo normal/especial e vistas de cotas mantêm seus fluxos existentes.

## Aplicação e verificação

`camera_comum.py` centraliza posição segura, remoção de obstáculos por entidade e enquadramento. `gerar_caderno.py` usa o padrão; o renderer dos especiais deriva dessa mesma função. As referências de localização dos dois motores passam pelo fluxo ambiental frontal.

A auditoria de cada render registra posição, ângulo, alvo, quadro e peças retiradas. O renderer verifica o envelope projetado do alvo dentro do quadro e protege seus IDs contra retirada. Os testes geométricos cobrem quatro frentes, câmera fora do mobiliário, módulo parcialmente obstrutivo retirado inteiro, vizinho sem sobreposição preservado e prioridade do alvo. A validação de integração usa suíte/cozinha reais e as 21 categorias especiais em fixture controlada; essa fixture não substitui a validação construtiva de 21 projetos reais distintos.
