# Engenharia das subimagens funcionais

Referências analisadas na pasta PROJETOS JOÃO FELIPE do Google Drive: cinco cadernos manuais. Os números abaixo são páginas do PDF, que podem diferir da numeração impressa.

| Referência | Páginas | Observação |
|---|---|---|
| [Priscila — Suíte Casal](https://drive.google.com/file/d/1z8m4DKzxibqIPXR6FhIl15V3PF23lJB6/view) | 7, 10, 17 | Base sob balcão mostrada montada; afastadores no plano de fixação; divisor localizado na gaveta. |
| [Priscila — Cozinha](https://drive.google.com/file/d/1ay-zOMpusapWM4IoXwIP6XcWwMRTU-Da/view) | 6–8 | Estrutura de apoio e etapa com os módulos aplicados; canto aberto e móvel montado como referências complementares. |
| [Glauber — Cozinha](https://drive.google.com/file/d/1MMhC7JyL6Z8-jtsmV24UHuGBPC59sSV9/view) | 9, 10, 12 | Quadros e sarrafos revelados na montagem; base sob móveis mostrada sem o corpo que a encobre, preservando sua implantação. |
| [Alexandre Giardino — Closet](https://drive.google.com/file/d/1FYyztY1J-Kx4DjOrumPYcZYUQ9JjeFYh/view) | 13, 14, 17 | Bases dos trilhos superiores e prateleira acima da porta em vistas de detalhe, vinculadas à composição do móvel. |
| [Daniel Furtado — Cozinha, Montagem](https://drive.google.com/file/d/17Arcg4gUBTmBQVxW7-6aZS81DO4TL58A/view) | 6–8 | Fechamento e passagem de mangueira apresentados em detalhe ao lado do conjunto montado. |

## Lógica deduzida das referências

A subimagem comunica função e instalação. A imagem montada localiza o conjunto; a vista de detalhe revela o que é necessário para compreender apoio, fixação ou aplicação. Retirar o corpo que encobre um quadro não significa explodir suas peças ou mudar sua posição. Essa é a engenharia adotada; os layouts dos PDFs manuais não foram copiados.

## Aplicação no motor normal

- Exceções e famílias do documento funcional continuam com precedência.
- A detecção de especiais permanece separada e não recebe novas famílias por causa da ocultação.
- Uma chapa simplesmente sobreposta continua excluída da listagem.
- Uma base de apoio pode receber detalhe quando há ao menos três tiras fisicamente conectadas, em dois eixos, sob um módulo da mesma vista.
- Fixações nomeadas explicitamente e detalhes normais previstos no documento exigem um hospedeiro físico compatível.
- Ausência de hospedeiro ou geometria não produz uma aplicação inventada.
- As peças são renderizadas nas coordenadas reais do DXF, como conjunto montado.
- A subimagem inclui referência do móvel e retângulo vermelho na posição do conjunto.
- Só ocorrências com superfície visível no detalhe entram na tabela e recebem balão nesse detalhe. Não recebem balão sobre o corpo que as encobre na imagem principal.
- Itens iguais mantêm o mesmo número; cada ocorrência visível recebe sua chamada.
- A regra não promove peças internas de módulos prontos de fábrica nem acessórios representativos a itens de produção.

As tolerâncias de proximidade, altura e largura em normal.ocultas são critérios de implementação. Não são medidas prescritas nos cadernos manuais.

## Verificação

Na suíte da Priscila, a base do balcão da Vista B ganhou detalhe e referência, com quatro ocorrências visíveis correspondendo a dois itens da tabela. As demais sobreposições continuaram excluídas. O caderno normal permaneceu com 11 pranchas; a cozinha, com 10. Foram conferidas a correspondência tabela/balões, a propriedade da vista e a integração com os especiais.
