# CONTRATO DO PROJETO UNIFICADO — versão 1

O Projeto Unificado é a saída canônica da Etapa 4. Depois dele, cores, puxadores, vidros, compatibilização, render, caderno e auditoria consomem a mesma estrutura. Nenhum consumidor volta a cruzar XML com DXF.

## Entrada

- `P`: peças canônicas do DXF, validadas pelo contrato comum.
- `itens`: módulos e componentes produzidos pelo casamento XML × DXF.
- `ambiente_final`: resultado validado de `unificacao.fechar()`.
- `portas_xml`: peças do DXF reconhecidas como portas avulsas do XML.

## Saída

| Campo | Conteúdo |
|---|---|
| `identidade` | quantidade e SHA-256 das peças do DXF |
| `pecas` | geometria canônica do DXF |
| `itens` | itens reconhecidos pelo XML, com posição e peças |
| `modulos` | visão filtrada de `itens` com tipo `mod` |
| `componentes` | visão filtrada de `itens` com tipo `comp` |
| `moveis` | índices das peças pertencentes aos itens |
| `materiais` | material, RGB e textura por índice de peça quando disponíveis |
| `portas` | peças de portas avulsas e módulos marcados com porta pelo XML |
| `ambiente` | pedra, paredes, piso de referência, eletros e planos reais |

## Invariantes

1. Unidade única: milímetros.
2. A identidade do ambiente deve corresponder exatamente a `P`.
3. Todo índice deve existir em `P`.
4. Uma peça reconhecida como móvel não pode exercer papel de ambiente.
5. `modulos` e `componentes` são visões dos mesmos objetos contidos em `itens`.
6. Consumidores usam o projeto recebido; não repetem o casamento XML × DXF.
