# CONTRATO DO AMBIENTE (versão 1 — extração fiel)

> **Estado (06/10/2026):** `ambiente.py` é o código do ambiente **movido** do `gerar_caderno.py` sem mudar a lógica.
> Prova: 23 cadernos gerados antes e depois são idênticos (texto, pixels e relatório). Os 3 que não geram
> (Guilherme/Suíte Casal, Priscila/Dormitório, Tiago/Dormitório) falham igual nas duas versões pelo erro crítico
> "itens do XML não localizados no DXF" — dado do projeto, não regressão.

## 0. Sequência-alvo (decisão do João, 06/10/2026 — FINAL, substitui as anteriores)
```
 1. DXF
 2. ambiente.py       só DXF: parede, piso, janela, abertura
 3. ambientemodu.py   só DXF: móveis (módulos, painéis, eletros) e pedra, posicionados pelo DXF
 4. UNIFICAÇÃO        cruzamento XML x DXF (ÚNICO ponto onde o XML entra; confirma MDF x pedra)
 5. cores.py          cores/materiais (biblioteca MATERIAIS ao vivo)
 6. puxadores.py
 7. portas de vidro
 8. COMPATIBILIZAÇÃO  vistas (parede/ilha, câmeras, nicho, o que sai/fica em cada prancha)
 9. RENDER            motor Blender: 3D e 2D
10. gerar_caderno.py  pranchas: layout, capa, contrato, posicionamento, listagem e cotas
11. auditoria
12. entrega (PDF + relatório)
```
Decisões:
- Etapas 2 e 3 não leem XML. Mudar imagem/render não mexe nelas nem no cruzamento.
- Eletros ficam com os móveis (etapa 3). Listagem 3D: ambiente completo. Cotas 2D: **sem ambiente e sem piso**, só móveis (eletros fora).
- Parede, piso, janela, abertura, pedra e móveis são peças soltas posicionadas pelo DXF; nada se apoia em móvel.
- Pedra na etapa 3 é *provável* (geometria): sem XML, 86 peças de MDF viram "pedra" nos 27 projetos de teste; nenhum traço do DXF
  (layer, faces, espessura, ordem, cor ACI) separa. A **Unificação (4)** corrige: o que casa com o XML é MDF.
- Render com Blender deve ser determinístico (mesma entrada, mesma imagem): amostragem/seed fixos, sem GPU variável, sem timestamp.
- Piso nas cotas: não existe (decidido). A altura de referência (`piso_z`) deixa de ser desenhada; fica só como número se alguma cota precisar.

## 0.1 Contrato das etapas 2 e 3 (só DXF) e da 4 (Unificação)
Entrada comum: `P` = lista de peças do DXF (`i`, `layer`, `bb`, `dim`, `faces`; 1 layer = 1 peça). Saída: só **índices** de `P` e números.

**`ambiente.construir(P)`** (etapa 2)
| Chave | O que é |
|---|---|
| `piso` | placa(s) de piso: menor lado do plano >1500, espessura ≤60, base ≤1 mm |
| `piso_z` | altura do topo do piso (mm) |
| `malha_par` | parede/casca em peça única (altura ≥1800, comprimento ≥1000, espessura >400) — usa as faces reais, com vãos |
| `fontes_parede` | `malha_par` + paredes finas altas (espessura 60–400, altura ≥1800, comprimento ≥1000) |
| `par_dxf` | candidatas a parede em peça (espessura 60–400, altura ≥100, comprimento <20000, não é peça baixa no chão) |
| `paredes_pecas` | paredes altas em peça (altura ≥2000, espessura 80–400, comprimento ≥1000) |

**`ambientemodu.construir(P, amb)`** (etapa 3)
| Chave | O que é |
|---|---|
| `moveis` | tudo que sobra sem `piso`, `malha_par` e `paredes_pecas`, na ordem do DXF; cada peça traz a posição (`bb`) do DXF |
| `pedra` | placa 15–100 mm, ≥500×250, base entre 700 e 1100 mm (**candidata**) |
| `eletro_a` | objeto com forma (≥10 faces), tamanho de eletro, até 2300 mm de altura (**candidato**) |
| `eletro_b` | objeto baixo (até 1300 mm), sem material, a confirmar que encosta num móvel (**candidato**) |

**`unificacao.fechar(P, amb, modu, usadas, bbs_moveis)`** (etapa 4, único ponto com XML)
- `usadas` = índices de `P` que o XML reconhece; `bbs_moveis` = caixas dos itens do XML.
- Remove dos candidatos o que está em `usadas` (corrige a pedra que é MDF), recalcula `faces_parede_real` só com o que sobrou,
  aplica "encostado no móvel" e "sobre a pedra" aos eletros e devolve `duplicadas, pedra, malha_par, eletros, par_dxf,
  paredes_pecas, piso_z, faces_parede_real` (o dicionário que o `gerar_caderno` consome).
- Regras que **não** podem entrar em `ambiente`/`ambientemodu`: qualquer uso de `usadas`, de `bbs_moveis` ou de nome/categoria do XML.

**Ainda aberto (decisão do João):** o DXF não marca onde um módulo começa e termina (1 layer = 1 peça). Hoje o agrupamento em
módulos (`geo.casar`, órfãs, nichos) precisa das linhas do XML e continua na Unificação. Agrupar módulos só pelo DXF
(vizinhança geométrica) não foi feito e não foi medido.

### Mapa do que já existe -> etapa
| Hoje | Vai para |
|---|---|
| `ambiente.py` (parede, piso, malha, par_dxf, pedra, eletros) | 2 (parede/piso/abertura) e 3 (pedra, eletros) |
| `geo.casar`, `classificacao.py`, órfãs, nichos | 3 e 4 |
| materiais/cores em `gerar_caderno` | 5 |
| puxadores, porta de vidro em `gerar_caderno` | 6 e 7 |
| `faces_parede_real`, câmeras, subimagem de nicho | 8 |
| `render3d` (PyMuPDF/desenho próprio) | 9 (Blender) |
| pranchas, layout, listagem, cotas | 10 |

Separação entre **móvel** (XML + DXF → `gerar_caderno.py`) e **ambiente** (alvenaria/estrutura → `ambiente.py`).
Regra: o `gerar_caderno` **não constrói** ambiente; ele **consome** o contrato. Quem produz o ambiente pode ser
este módulo (hoje) ou um motor próprio (amanhã), desde que entregue o mesmo conteúdo.

## 1. O que é ambiente
| Papel | O que é | Critério atual (peça do DXF **sem item no XML**) |
|---|---|---|
| `pedra` | Tampo/bancada de apoio, só desenho | placa 15–100 mm de espessura, ≥500 × ≥250 mm, base entre 700 e 1100 mm |
| `malha_par` | Parede/casca em peça única, com vãos de porta e janela | altura ≥1800, comprimento ≥1000, espessura >400 mm (usa as **faces** reais) |
| `par_dxf` | Parede/pilar em peça avulsa | espessura 60–400, altura ≥100, <20 m, fora da pedra e dos eletros; peça baixa no chão não conta |
| `paredes_pecas` | Paredes altas, usadas para limites da elevação | altura ≥2000, espessura 80–400, comprimento ≥1000 (**inclui peças que são móvel do XML**: não filtra) |
| `eletros` | Objetos de apoio (geladeira, forno, cuba, coifa, revestimento) | forma real (>12 faces), fora de pedra/parede; só baixo se estiver sobre a pedra; mais as peças soltas encostadas (≤20 mm) em móvel |
| `duplicadas` | Cópia de peça listada (mesmo lugar, ≥80% do volume) | não é desenhada |
| `piso_z` | Nível do piso pronto (mm) | topo da maior placa fina do chão (≥1500 × ≥1500, ≤60 mm) |
| `faces_parede_real` | Planos de parede reais `(eixo 'x'\|'y', coordenada, início, fim)`, agrupados a ±10 mm | vem de `malha_par` e de peças altas avulsas |

**Não é ambiente:** móvel, componente, porta, frente, puxador (isso é do XML). O ambiente é o que **sobra**.

## 2. Entrada de `construir(P, usadas, bbs_moveis)`
- `P`: peças do DXF (`i`, `layer`, `bb`, `dim`, `faces`, opcional `mat`).
- `usadas`: índices de `P` que pertencem a itens do XML.
- `bbs_moveis`: caixas dos itens do XML.

Sentido único da dependência: **primeiro o móvel, depois o ambiente** (o ambiente é o resto). O ambiente nunca altera o móvel.

## 3. Saída (contrato)
`construir()` devolve `dict` com as chaves: `duplicadas, pedra, malha_par, eletros, par_dxf, paredes_pecas, piso_z, faces_parede_real`.
`para_json()` / `de_json(d, P)` serializam e restauram (versão 1 aponta peças por **índice** do DXF):
```json
{"versao": 1, "piso_z": 5.0, "duplicadas": [4], "pedra": [2], "malha_par": [], "eletros": [],
 "par_dxf": [3], "paredes_pecas": [3], "faces_parede_real": [["x", -150.0, 0.0, 3000.0]]}
```
Efeito colateral declarado: `pedra`, `eletros` e `malha_par` recebem `faces` em tuplas e `ft` (arestas nítidas) — preparação para o desenho.

## 4. Quem consome no `gerar_caderno.py`
| Consumidor | Usa | Para quê |
|---|---|---|
| `_juntar/paredes` pela parede real, câmera 005.B | `faces_parede_real` | decidir a parede/frente de cada módulo (**afeta o móvel**, não só o desenho) |
| parede cortada por pilar | `par_dxf`, `malha_par` | separar vista em dois lados |
| `elevação` (limites da cota) | `paredes_pecas`, `par_dxf`, `malha_par` | parede a parede e teto — **cotas externas** |
| cotas de altura | `piso_z` | todas as alturas partem do piso pronto |
| `render3d` | `pedra`, `eletros`, `malha_par`, `par_dxf`, `duplicadas`, cores | desenho de parede, piso, pedra, eletros |
| planta (prancha de cores/vistas) | `malha_par`, `par_dxf`, `paredes_pecas` | linhas das paredes |

## 5. Invariantes
1. Determinismo: mesma `P` + mesmos `usadas` → mesmo resultado (testado em `teste_ambiente.py`).
2. Sem arquivo, sem cache, sem estado global; função pura.
3. Nenhum índice aparece em dois papéis exclusivos (`pedra`, `malha_par`, `eletros`).
4. `gerar_caderno` não recalcula nada disso: se precisar de outro dado de ambiente, entra no contrato.

## 6. Como o motor novo do ambiente entra
1. Produzir o JSON da seção 3 (versão 1) para o mesmo DXF.
2. No `gerar_caderno`, trocar `ambiente.construir(...)` por `ambiente.de_json(json, P)` (uma linha).
3. Rodar a comparação antes × depois (`comparar-cadernos`) — as cotas externas não podem mudar.

## 7. Versão 2 (quando o motor novo gerar geometria própria)
Hoje os papéis apontam peças **do DXF**. Se o novo motor desenhar paredes/piso/janelas que **não existem no DXF**, o contrato passa a
carregar a geometria (cada elemento com `papel`, `bb`, `faces`). Mudança necessária no `gerar_caderno`: o laço de `render3d`
(`for p_ in P` com teste de papel) passa a percorrer os elementos do ambiente. É a única mudança estrutural; o resto já fica pronto na v1.

## 8. Pendências de unificação (regras duplicadas fora do módulo)
| Onde | Duplicidade | Ação sugerida |
|---|---|---|
| `classificacao._piso_z` | piso = topo da `LAYER0`; o ambiente usa a placa fina ≥1500 | ambos devem ler `piso_z` do contrato |
| `classificacao._eh_arquitetura` | arquitetura = sem item e espessura ≥60 | derivar de `malha_par` + `par_dxf` |
| `geo.limites(inst)` | limites do ambiente pelos móveis, não pelas paredes | usar `faces_parede_real` quando existir |
| `render3d` `sd_[1] < 50 or sd_[0] > 60` | filtro "só chapa" local | fica no móvel; documentar |

Essas quatro só mudam **depois** que o motor novo existir e a comparação provar equivalência.
