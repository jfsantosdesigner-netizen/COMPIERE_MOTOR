# COMPIERE — ÍNDICE REAL DO CORE MOTOR POR ETAPA

Base analisada: `/core_motor` no Dropbox — 03/10/2026
Objetivo: localizar rapidamente onde cada responsabilidade do motor V35 está implementada antes de alterar código.

## LINHA DE PRODUÇÃO

01 ENTRADA → 02 UNIFICAÇÃO → 03 ENGENHARIA → 04 REPRESENTAÇÃO / ESPECIAIS → 05 LISTAGEM / IDENTIFICAÇÃO → 06 COTAS → 07 PRANCHAS → 08 AUDITORIA → 09 ENTREGA

> Este é um mapa do motor existente. Não é uma nova especificação e não deve duplicar regras.

---

## 01 — ENTRADA

### `launcher.py`
- L21-L32 — `escolher_pasta()`; seleção/preparação da pasta de projeto.
- L33-L93 — `rodar()`; preparação e disparo do processamento.

### `novo_ambiente.py`
- L12-L18 — `_tem_projeto()`; identificação de ambiente/projeto.
- L19-L76 — `processar()`; leitura de configuração, localização de XML/DXF e preparação da execução.

### `gerar_caderno.py`
- L40-L73 — `ler_xml()`; entrada semântica do XML.
- L75-L82 — validação/hash do DXF e preparação do arquivo intermediário de peças.
- L83-L98 — preparação geométrica inicial.

### Entrada efetiva
O motor atual recebe principalmente `config.json`, XML, DXF e arquivo intermediário `_pecas_dxf.json`.

---

## 02 — UNIFICAÇÃO

### `dxf_pecas(motor core).py`
- L18-L25 — estruturas/utilitários de geometria.
- L26-L34 — processamento de entidades.
- L35-L42 — `_bbox_arco()`.
- L43-L204 — `_processar()`; conversão das entidades DXF em peças/geometria.
- L205-L228 — `main()`; execução e gravação do resultado.

### `geo.py`
- L17-L21 — `carregar()`; leitura da representação intermediária.
- L22-L27 — `uniao()` / `dentro()`; operações geométricas básicas.
- L28-L36 — `laterais()`.
- L37-L73 — `casar()`; associação entre listagem/XML e peças DXF.
- L74-L98 — `_cands_mod()`; candidatos de associação.
- L99-L105 — `_sobrepoe()`.
- L106-L109 — `limites()`.
- L110-L124 — `parede_de()`.
- L125-L132 — transformações/elevação.
- L133-L156 — `agrupar_vistas()` / `perto()`.
- L157-L183 — frente/plano e relações espaciais.
- L184-L194 — distância/ordenação espacial.
- L195-L207 — `_montar()`; agrupamento/estrutura dos módulos.
- L208-L263 — `definir_paredes()` e consolidação das paredes.
- L264-L288 — `agrupar_vistas2()`.

### `gerar_caderno.py`
- L75-L82 — hash e cache do DXF.
- L232-L257 — `_juntar_paredes()` e consolidação das paredes.
- L258-L307 — duplicidades, ambiente e classificação preliminar.
- L308-L360 — associação de módulos com paredes reais.
- L397-L428 — arestas/estrutura geométrica.
- L429-L565 — relações, agrupamentos e preparação geométrica.
- L566-L635 — faces/limites de parede.

---

## 03 — ENGENHARIA

### Documentação de regras
`03_ENGENHARIA_REGRAS/motor v33__ENGENHARIA_CADERNO_CLIENTE.md`
- L1-L185 — regras/documentação de engenharia do caderno.

`03_ENGENHARIA_REGRAS/motor v34__ENGENHARIA_IMPLEMENTACAO.md`
- L1-L60 — orientação de implementação das regras.

PDFs de referência:
- `03_ENGENHARIA_REGRAS/MOTOR_ATUAL__ENGENHARIA.pdf`
- `03_ENGENHARIA_REGRAS/MOTOR_CADERNO__ENGENHARIA.pdf`
- `03_ENGENHARIA_REGRAS/motor v34__ENGENHARIA.pdf`

### Implementação efetiva no V35
`gerar_caderno.py` concentra grande parte da engenharia atual:
- L17-L24 — regras globais/configuração.
- L40-L73 — interpretação do XML.
- L119-L166 — materiais/cores e regras de correspondência.
- L232-L360 — paredes, duplicidades e relação módulo/ambiente.
- L361-L396 — condições espaciais.
- L429-L565 — relações geométricas e agrupamentos.
- L566-L748 — paredes, vistas e condições de ambiente.
- L768-L820 — classificação/condições de acessórios e elementos.
- L1190-L1237 — portas, cotas de portas e geometria de parede.
- L1350-L1498 — puxadores, portas, detalhes, abertos e nichos.
- L1719-L1816 — numeração e interpretação de especiais.
- L1955-L2137 — regras de cotas, peças e composição de pranchas.

> Observação crítica: no motor atual, Engenharia não está isolada em um módulo. Ela está misturada ao gerador. A nova arquitetura deve separar responsabilidade sem reescrever cegamente essas regras validadas.

---

## 04 — REPRESENTAÇÃO / ESPECIAIS

### Representação 2D/3D — `gerar_caderno.py`
- L857-L861 — utilitários de área/coordenação.
- L862-L919 — desenho de cadeias de cotas/elementos gráficos auxiliares.
- L1047-L1097 — `_desenho2d()` e preparação de desenho.
- L1142-L1189 — `desenhar()`, caixas e limites de vista.
- L1216-L1237 — `geom_parede()`.
- L1238-L1295 — ordenação e projeção.
- L1296-L1349 — `_raster3d()` e transformação de perspectiva.
- L1499-L1718 — `render3d()`; geração das vistas 3D e composição dos elementos.

### Especiais — `gerar_caderno.py`
- L1350-L1398 — puxadores.
- L1414-L1434 — portas/frentes.
- L1435-L1466 — detalhes e abertos.
- L1467-L1498 — nichos.
- L1764-L1816 — `_espec()` e tratamento/agrupamento de especiais.
- L2023-L2060 — peças/detalhes associados às pranchas.
- L2067-L2137 — prancha específica de peça/detalhe e composição final.

### `geo.py`
- L125-L139 — transformação/elevação/agru­pamento de vistas.
- L264-L288 — agrupamento de vistas.

---

## 05 — LISTAGEM / IDENTIFICAÇÃO

### Listagem
`gerar_caderno.py`
- L40-L73 — formação de `linhas_xml`.
- L1719-L1763 — `_numerar()`; identificação/numeração dos elementos representados.
- L1955-L1974 — preparação de partes/elementos para composição.
- L1994-L2034 — composição das informações por vista/peça.

### Identificação/balões
- L1142-L1153 — `desenhar()` recebe `baloes` e `letra`.
- L1499-L1718 — `render3d()` recebe/posiciona os elementos de identificação.
- L1719-L1763 — fonte da numeração.
- L2132-L2137 — fechamento das relações de identificação/prancha.

> O princípio para a nova arquitetura: Listagem deve consumir identidade já consolidada; não deve redescobrir XML/DXF.

---

## 06 — COTAS

### `gerar_caderno.py`
- L857-L861 — preparação geométrica para cotas.
- L862-L919 — `cadeia_h()` / `cadeia_v()`.
- L920-L933 — `_uniq()` e classificação de elementos para cotagem.
- L934-L969 — `cotar_divisoria()`.
- L970-L991 — conversão de coordenadas e `cotar_bloco()`.
- L992-L1046 — `cotar()`; regra central de cotagem.
- L1134-L1141 — `escala_para()`.
- L1207-L1215 — `_portas_cota()`.
- L1975-L1992 — `_cotas_em()`.
- L2035-L2060 — `_dq()` e informações dimensionais.
- L2098-L2108 — aplicação final de cotas na prancha.

> Cotas já possui uma fronteira relativamente clara: deve consumir geometria consolidada e decidir referências, hierarquia e apresentação das dimensões.

---

## 07 — PRANCHAS

### `gerar_caderno.py`
- L1098-L1111 — `nova_prancha()`; criação da página.
- L1112-L1133 — `tabela()`; composição de tabelas.
- L1134-L1141 — escala.
- L1142-L1189 — desenho principal da prancha.
- L1975-L1992 — cotas dentro da prancha.
- L1994-L2034 — composição/listagem.
- L2035-L2064 — elementos dimensionais.
- L2067-L2137 — pranchas específicas e composição de peças/detalhes.
- L2138-L2162 — fechamento e salvamento do PDF.

> Pranchas deve receber decisões prontas de Engenharia, Representação, Listagem e Cotas. Não deve decidir engenharia.

---

## 08 — AUDITORIA

### `gerar_caderno.py`
- L2164-L2185 — geração/fechamento da saída de qualidade e relatório.

### `testar_motor.py`
- L24-L39 — localização/preparação do DXF.
- L40-L166 — `testar()`; inspeção de peças, medidas e associações.

### `testar_lote.py`
- L32-L47 — geração das prévias.
- L48-L84 — execução em lote e verificação dos resultados.

### `_diagnostico.py`
- L1-L60 — diagnóstico do estado/arquivos.

> Auditoria hoje está parcialmente externa ao gerador. A nova etapa deve consolidar os checks sem duplicar as regras de produção.

---

## 09 — ENTREGA

### `gerar_caderno.py`
- L2138-L2162 — finalização/salvamento do PDF.
- L2164-L2185 — relatório/qualidade.
- L2186 — encerramento.

### `novo_ambiente.py`
- L19-L76 — preparação do ambiente e chamada do motor.

### `server.py`
- L1-L6 — camada mínima de servidor/execução.

### Saídas existentes nos projetos
- `CADERNO - *.pdf`
- `CADERNO - *_QUALIDADE.md`
- `_pecas_dxf.json`
- `_pecas_dxf.json.md5`

---

# ARQUIVOS CENTRAIS DO MOTOR

| Arquivo | Papel real observado |
|---|---|
| `gerar_caderno.py` | Motor monolítico principal: entrada, engenharia, representação, cotas, listagem, pranchas e entrega |
| `geo.py` | Geometria, associação XML/listagem ↔ DXF, paredes, vistas e relações espaciais |
| `dxf_pecas(motor core).py` | Extração DXF → peças/representação intermediária |
| `novo_ambiente.py` | Preparação/execução de ambientes |
| `launcher.py` | Interface/acionamento |
| `testar_motor.py` | Testes técnicos de DXF/associação |
| `testar_lote.py` | Testes de lote e prévias |
| `_diagnostico.py` | Diagnóstico |
| `03_ENGENHARIA_REGRAS/` | Documentação das regras de engenharia |
| `_RAIO_X_CORE_MOTOR/` | Inventário e raio-X já produzido do motor |

# ARQUIVOS DE SUPORTE

- `padrao.json` — configuração padrão.
- `materiais_cores.json` — índice/cores de materiais.
- `materiais_index.json` — índice de materiais.
- `cores_cache.json` — cache de cores.
- `texturas/` — assets visuais oficiais.
- `assets/` — layout/logo/contrato.
- `02_ESTADO_E_TRILHA/` — estado e histórico de desenvolvimento.
- `PROJETOS/` — projetos reais de teste/validação e respectivas entradas/saídas.
- `_RAIO_X_CORE_MOTOR/` — inventário, dependências, execução e cópias completas de código/texto.

# ACHADO ARQUITETURAL PRINCIPAL

O V35 não é nove blocos independentes. O núcleo atual está fortemente concentrado em `gerar_caderno.py` (140221 bytes na versão analisada), com apoio de `geo.py` e `dxf_pecas...py`.

Portanto, a migração para a linha de produção deve ser feita por **extração de responsabilidades**, preservando as regras validadas, e não por reescrita do comportamento.

## Regra de alteração

1. Localizar a etapa.
2. Localizar arquivo e linhas.
3. Ler a função inteira e suas dependências.
4. Identificar se a regra é compartilhada.
5. Extrair/mover uma responsabilidade por vez.
6. Manter uma única fonte de verdade.
7. Executar teste do comportamento afetado.
8. Atualizar este índice quando a localização estrutural mudar.

## Fonte adicional

O diretório `_RAIO_X_CORE_MOTOR` já contém:
- `00_RESUMO_RAIO_X.txt`
- `01_INVENTARIO_COMPLETO.txt`
- `02_PYTHON_MAPA_COMPLETO.txt`
- `03_PYTHON_DEPENDENCIAS.txt`
- `04_EXECUCAO_E_ARQUIVOS_CENTRAIS.txt`
- `05_CONFIGURACOES_E_AUXILIARES.txt`
- `06_CODIGOS_PY_COMPLETOS.txt`
- `07_ARQUIVOS_TEXTO_COMPLETOS.txt`

Esses arquivos devem ser consultados antes de concluir que uma responsabilidade não existe no motor.
