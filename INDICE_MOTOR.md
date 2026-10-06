# INDICE DO MOTOR COMPIERE -- core_motor

Gerado: 2026-10-04 16:28

---

## Sumario

| Arquivos | Funcoes | Classes | Constantes |
|---|---|---|---|
| 10 | 80 | 0 | 184 |

---

## `gerar_caderno.py`

- **Bytes:** 140496 | **SHA-256(16):** `8ddabe1cac4e1d09`
- **Linhas:** 2191

**Imports principais:** `PIL.Image,ImageDraw`, `collections`, `collections.OrderedDict`, `geo`, `hashlib`, `heapq`, `io`, `json`, `math`, `numpy`, `os`, `pymupdf`, `re`, `subprocess`, `sys`, `time`, `unicodedata`, `xml.etree.ElementTree`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `cfg` | 10 | `load(...)` |
| `AREA` | 13 | `Rect(...)` |
| `IN` | 13 | `7` |
| `RED` | 14 | `` |
| `CR` | 14 | `` |
| `PRETO` | 14 | `` |
| `BRANCO` | 15 | `` |
| `MADEIRA` | 15 | `` |
| `CINZA` | 15 | `` |
| `MM` | 16 | `` |
| `NICHO_MIN_RATIO` | 20 | `0.4` |
| `ESC` | 21 | `[lista 10]` |
| `ESC_COTA` | 22 | `[lista 10]` |
| `FV` | 23 | `{dict 4}` |
| `AREA_IN` | 24 | `Rect(...)` |
| `QT` | 39 | `{dict 0}` |
| `linhas` | 71 | `` |
| `pj` | 73 | `` |
| `_hx` | 76 | `` |
| `P` | 81 | `carregar(...)` |
| `_MD` | 104 | `dirname(...)` |
| `_MAT` | 109 | `next(...)` |
| `_MI` | 112 | `join(...)` |
| `_MC` | 113 | `join(...)` |
| `_rgbx` | 114 | `{dict 0}` |
| `_CC` | 126 | `join(...)` |
| `_cc` | 127 | `` |
| `_PREF` | 128 | `` |
| `_TXD` | 171 | `join(...)` |
| `_TXC` | 172 | `join(...)` |
| `_txc` | 173 | `{dict 0}` |
| `_dm` | 196 | `{dict 0}` |
| `_ord` | 196 | `{dict 0}` |
| `_fixa` | 206 | `{dict 0}` |
| `_gp` | 206 | `{dict 0}` |
| `_nc` | 212 | `0` |
| `_usadas` | 212 | `Counter(...)` |
| `TEX_FALTA` | 224 | `` |
| `_todas_mats` | 226 | `` |
| `inst` | 228 | `casar(...)` |
| ... | ... | (130 mais) |

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `fmt` | 26 | 3 | `v` | -- |
| `modelo` | 31 | 7 | `it` | -- |
| `ler_xml` | 40 | 29 | `path` | -- |
| `_n` | 84 | 5 | `a, b, c` | -- |
| `preparar` | 89 | 8 | `P` | -- |
| `_norm` | 101 | 3 | `t` | -- |
| `_parecido` | 129 | 8 | `a, b` | -- |
| `cor_material` | 137 | 28 | `nome` | -- |
| `textura` | 174 | 22 | `nome` | -- |
| `_juntar_paredes` | 232 | 19 | `paredes` | -- |
| `_vol` | 258 | 1 | `b` | -- |
| `_vol_int` | 259 | 1 | `A, B` | -- |
| `_faces_parede_real` | 286 | 18 | `` | -- |
| `caixa_faces_` | 304 | 4 | `b` | -- |
| `_parede_real_atras` | 308 | 9 | `it, key, FR, tol` | -- |
| `_eletro_ok` | 361 | 6 | `p_` | -- |
| `_arestas` | 397 | 24 | `faces` | -- |
| `_sd` | 429 | 1 | `it` | -- |
| `parse_dim_` | 430 | 3 | `dm` | -- |
| `_toca` | 433 | 1 | `a, b, tol` | -- |
| `_faces_parede` | 566 | 3 | `` | -- |
| `_tem_frente_solto` | 636 | 21 | `its_, w_` | Testa se um grupo de peças soltas tem porta/frente (≥40% da face frontal coberta |
| `_caixa_fq` | 695 | 6 | `b` | -- |
| `_ancora_regex` | 748 | 3 | `ambiente` | -- |
| `_eh_acessorio` | 768 | 10 | `desc_, dim_` | True se o item é acessório/ferragem/fundo que não aparece no DXF. |
| `_larg` | 821 | 3 | `w` | -- |
| `uu` | 857 | 1 | `x, y, f` | -- |
| `area2` | 859 | 2 | `pts` | -- |
| `_tick` | 862 | 2 | `sh, x, y` | -- |
| `_txt` | 865 | 6 | `page, pos, s, fs, rotate, fundo` | -- |
| `cadeia_h` | 872 | 23 | `page, us, yl, yobj, X, fs, fundo` | -- |
| `cadeia_v` | 896 | 23 | `page, zs, xl, xobj, Y, fs, esquerda, fun` | -- |
| `_uniq` | 920 | 5 | `vals, tol` | -- |
| `_eh_ripa` | 929 | 4 | `it` | -- |
| `cotar_divisoria` | 934 | 35 | `page, G, ox, fy, k` | -- |
| `_u_de` | 970 | 2 | `G, c, al` | -- |
| `cotar_bloco` | 973 | 18 | `page, G, ox, fy, k` | -- |
| `cotar` | 992 | 54 | `page, G, ox, fy, k` | -- |
| `_desenho2d` | 1047 | 48 | `page, faces, XY` | REGRA (v16, João): cotas 2D (frontal e lateral) com as MESMAS cores e TEXTURAS d |
| `nova_prancha` | 1098 | 13 | `doc, n, titulo` | -- |
| `tabela` | 1112 | 21 | `p, linhas, x0, y0, largura, nums` | -- |
| `escala_para` | 1134 | 6 | `larg_mm, alt_mm, W, H, cheio` | -- |
| `desenhar` | 1142 | 7 | `page, G, ox, fy, k, baloes, letra` | -- |
| `caixa_faces` | 1154 | 4 | `b` | -- |
| `paredes_recorte` | 1158 | 6 | `R` | -- |
| `_vista_limites` | 1165 | 24 | `w, f, umin_, umax_, zmax_` | REGRA (v15): limites da elevação 2D = parede a parede (face interna da parede la |
| `_eh_porta` | 1190 | 16 | `b, mb, w` | -- |
| `_portas_cota` | 1207 | 8 | `w` | -- |
| `geom_parede` | 1216 | 21 | `w` | -- |
| `_ordem_pecas` | 1238 | 46 | `fcs, bbs, cam` | -- |
| `_persp` | 1288 | 7 | `dst, src_` | -- |
| `_raster3d` | 1296 | 43 | `page, rect, fcs, T, pmat, dpi` | -- |
| `_puxador_xml` | 1350 | 12 | `` | -- |
| `_gerar_puxadores` | 1364 | 48 | `` | -- |
| `_portas` | 1414 | 9 | `` | -- |
| `tem_porta` | 1424 | 10 | `m, w` | -- |
| `detalhes` | 1435 | 13 | `w` | -- |
| `abertos` | 1449 | 17 | `w` | -- |
| `nichos` | 1467 | 31 | `w` | -- |
| `render3d` | 1499 | 208 | `page, rect, pids, letra, itens, ang, dmi` | -- |
| `_numerar` | 1719 | 7 | `ordenados, letra, agrupar` | -- |
| `_espec` | 1764 | 49 | `xml` | -- |
| `_quebra` | 1817 | 7 | `t, larg, fs` | -- |
| `_clip` | 1884 | 10 | `x0, y0, x1, y1, R` | -- |
| `_partes` | 1959 | 19 | `s_` | -- |
| `_cotas_em` | 1979 | 18 | `p, GS, R, rotulos` | -- |
| `_prancha_peca` | 2073 | 40 | `g_, titulo, rotulo` | -- |

---

## `geo.py`

- **Bytes:** 13687 | **SHA-256(16):** `fa38b7c3ad091bea`
- **Linhas:** 295
- **ERRO DE PARSE:** invalid non-printable character U+FEFF (<unknown>, line 1)

---

## `dxf_pecas(motor core).py`

- **Bytes:** 8659 | **SHA-256(16):** `0878ba9b31096857`
- **Linhas:** 227

**Imports principais:** `ezdxf`, `json`, `math`, `sys`

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `_push_vertex` | 18 | 6 | `peca, v` | Atualiza o bounding box da peça com um vértice (x,y,z). |
| `_push_face` | 26 | 7 | `peca, vs` | Adiciona uma face (lista de 3 ou 4 vértices) à peça, também atualizando bbox. |
| `_bbox_arco` | 35 | 6 | `cx, cy, cz, raio, ini_deg, fim_deg, n` | Discretiza arco/circulo em vértices para o bbox. |
| `_processar` | 43 | 159 | `entidade, layer_pai, pecas` | Processa uma entidade. layer_pai preserva a layer do INSERT que a originou (se h |
| `main` | 205 | 18 | `` | -- |

---

## `novo_ambiente.py`

- **Bytes:** 4157 | **SHA-256(16):** `18b8e3608e61ab28`
- **Linhas:** 75

**Imports principais:** `glob`, `json`, `os`, `re`, `subprocess`, `sys`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `M` | 7 | `dirname(...)` |
| `pad` | 8 | `load(...)` |
| `_ASSETS` | 9 | `join(...)` |

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `_tem_projeto` | 12 | 5 | `pasta` | True se a pasta tem XML+DXF direto nela (é um ambiente, não uma pasta-mãe). |
| `processar` | 19 | 34 | `pasta` | Gera o caderno de UM ambiente. Retorna True/False (sucesso/falha), nunca lança. |

---

## `testar_lote.py`

- **Bytes:** 3792 | **SHA-256(16):** `f579d54617831977`
- **Linhas:** 83

**Imports principais:** `fitz`, `glob`, `json`, `novo_ambiente`, `os`, `shutil`, `sys`, `time`, `traceback`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `M` | 13 | `dirname(...)` |
| `T` | 14 | `join(...)` |
| `CLI` | 15 | `'C:\\CLAUDE\\CLIENTES\\02_ORIGIN'` |
| `PROJETOS` | 18 | `[lista 7]` |

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `_previas` | 32 | 14 | `pdf, destino` | -- |
| `main` | 48 | 31 | `` | -- |

---

## `testar_motor.py`

- **Bytes:** 6519 | **SHA-256(16):** `5785a7acb27c9455`
- **Linhas:** 165

**Imports principais:** `collections`, `dxf_pecas`, `ezdxf`, `glob`, `os`, `sys`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `_HERE` | 19 | `dirname(...)` |

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `_achar_dxf` | 24 | 14 | `` | Procura um DXF nas subpastas do motor / OneDrive / Desktop. |
| `testar` | 40 | 111 | `dxf_path` | -- |

---

## `launcher.py`

- **Bytes:** 2966 | **SHA-256(16):** `4455de55cab617ac`
- **Linhas:** 92
- **Modulo:** LAUNCHER LIVRE - motor_t6
Arrasta QUALQUER pasta de ambiente (com XML + DXF dentro) sobre esse arquivo.
Ele roda o motor_t6 nessa pasta.

Uso:
  1) Arrasta a pasta do ambiente pra cima do LAUNCHER.bat

**Imports principais:** `os`, `pathlib.Path`, `subprocess`, `sys`, `tkinter`, `tkinter.filedialog`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `MOTOR` | 18 | `Path(...)` |

**Funcoes:**

| Funcao | Linha | Linhas | Args | Descricao |
|---|---|---|---|---|
| `escolher_pasta` | 21 | 11 | `` | Abre dialogo do Windows pra escolher a pasta do ambiente. |
| `rodar` | 33 | 48 | `pasta` | -- |

---

## `server.py`

- **Bytes:** 309 | **SHA-256(16):** `cdf95ad38d581910`
- **Linhas:** 5

**Imports principais:** `sys`

---

## `_diagnostico.py`

- **Bytes:** 2669 | **SHA-256(16):** `484f38463fa009d7`
- **Linhas:** 79

**Imports principais:** `json`, `os`, `pathlib.Path`, `re`, `sys`

**Constantes/globais:**

| Nome | Linha | Valor |
|---|---|---|
| `AQUI` | 5 | `` |
| `p` | 21 | `` |
| `a` | 29 | `` |
| `na` | 38 | `` |
| `gc` | 47 | `` |

---

## `criar_indice_core_motor.py`

- **Bytes:** 5120 | **SHA-256(16):** `d6a8ff81f2c5bf70`
- **Linhas:** 279
- **ERRO DE PARSE:** invalid syntax (<unknown>, line 1)

---
