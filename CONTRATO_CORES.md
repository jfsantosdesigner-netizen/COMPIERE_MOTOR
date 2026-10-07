# CONTRATO DE MATERIAIS/CORES — Etapa 5

## Responsabilidade
A Etapa 5 recebe o Projeto Unificado produzido pela Etapa 4. Ela não lê XML para refazer casamento e não decide geometria.
Resolve exclusivamente a aparência das referências já presentes em `projeto['materiais_xml']`.

## Entrada
- Projeto Unificado válido.
- Biblioteca `MATERIAIS` ao vivo, dentro do motor ou caminho configurado.
- `materiais_cores.json` como cache permitido da cor média dos arquivos da biblioteca.
- `texturas/` somente como reserva versionada de leitura.

## Saída
Para cada peça com material reconhecido:
- `mat`: nome exato da referência de material.
- `rgb`: cor média normalizada 0..1.
- `projeto['materiais'][i]`: nome, RGB e caminho de textura resolvido.
A identidade do Projeto Unificado é recalculada após a aparência ser aplicada.

## Invariantes
1. Não executa XML x DXF.
2. Não altera faces, caixas, itens, ambiente, portas ou classificação.
3. A biblioteca MATERIAIS é varrida a cada rodada.
4. JPEG/PNG da biblioteca não é copiado nem alterado.
5. O único cache persistente permitido é `materiais_cores.json`.
6. Ausência de textura não altera geometria: consumidor usa cor lisa/fallback.
7. Mesma biblioteca + mesmo Projeto Unificado produzem a mesma resolução.

## Validação 07/10/2026
Rafael Claret / Escritório:
- 104 peças coloridas: Branco 80, Preto TX 14, Chumbo 10.
- Antes x depois: 6/6 páginas com texto idêntico e pixels idênticos.
- Testes de Unificação e Projeto Unificado continuam aprovados.
