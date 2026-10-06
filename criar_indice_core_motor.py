notepad "C:\AGENTES COMPIERE\core_motor\criar_indice_core_motor.py"from pathlib import Path

ARQUIVO = Path(r"C:\COMPIERE\COMPIERE_INDICE_CORE_MOTOR_POR_ETAPA.md")

CONTEUDO = """
# COMPIERE — ÍNDICE DO CORE MOTOR POR ETAPA

Base: /core_motor
Objetivo: localizar rapidamente arquivos e linhas antes de alterar o motor.

## LINHA DE PRODUÇÃO

01 ENTRADA
↓
02 UNIFICAÇÃO
↓
03 ENGENHARIA
↓
04 REPRESENTAÇÃO / ESPECIAIS
↓
05 LISTAGEM / IDENTIFICAÇÃO
↓
06 COTAS
↓
07 PRANCHAS
↓
08 AUDITORIA
↓
09 ENTREGA


## 01 — ENTRADA

### gerar_caderno.py
- L30-L39 — estruturas iniciais
- L40-L68 — entrada/configuração
- L70-L80 — preparação dos dados

### novo_ambiente.py
- L12-L18 — configuração inicial
- L19-L76 — preparação/entrada do ambiente

### launcher.py
- L21-L32 — preparação
- L33-L93 — execução


## 02 — UNIFICAÇÃO

### dxf_pecas(motor core).py
- L18-L25 — estruturas
- L26-L34 — leitura
- L35-L42 — entidades
- L43-L204 — processamento geométrico
- L205-L228 — saída

### geo.py
- L17-L21 — estruturas
- L22-L27 — preparação
- L37-L73 — geometria
- L74-L105 — entidades
- L106-L139 — transformação
- L140-L194 — processamento
- L195-L207 — relações
- L208-L263 — operações geométricas
- L264-L288 — resultado

### gerar_caderno.py
- L81-L97 — preparação dos dados
- L232-L257 — estruturas
- L258-L565 — processamento
- L566-L747 — consolidação


## 03 — ENGENHARIA

### 03_ENGENHARIA_REGRAS/
- motor v33__ENGENHARIA_CADERNO_CLIENTE.md
- motor v34__ENGENHARIA_IMPLEMENTACAO.md
- MOTOR_ATUAL__ENGENHARIA.pdf
- MOTOR_CADERNO__ENGENHARIA.pdf
- motor v34__ENGENHARIA.pdf

### gerar_caderno.py
- L17-L24
- L308-L360
- L361-L396
- L429-L565
- L636-L694
- L748-L820
- L1190-L1237
- L1350-L1398
- L1414-L1498
- L1532-L1718
- L1764-L1816
- L1955-L1974
- L1994-L2137
- L2164-L2185


## 04 — REPRESENTAÇÃO / ESPECIAIS

### gerar_caderno.py
- L862-L928
- L1047-L1097
- L1142-L1189
- L1190-L1237
- L1238-L1349
- L1350-L1498
- L1499-L1718
- L1764-L1816
- L2023-L2060
- L2067-L2137

### geo.py
- L125-L139
- L264-L288


## 05 — LISTAGEM / IDENTIFICAÇÃO

### gerar_caderno.py
- L1112-L1133 — listagem
- L1719-L1763 — identificação
- L1768-L1816 — representação
- L1955-L1974 — identificação
- L1994-L2034 — listagem/identificação
- L2071-L2077 — identificação
- L2132-L2136 — fechamento

Observação:
Os balões são consumidos por render3d()/desenhar(), através de baloes e letra.
A numeração é criada em _numerar().


## 06 — COTAS

### gerar_caderno.py
- L857-L861
- L862-L919
- L920-L933
- L934-L969
- L970-L972
- L973-L991
- L992-L1046
- L1134-L1141
- L1207-L1215
- L1975-L1992
- L2035-L2060
- L2098-L2108


## 07 — PRANCHAS

### gerar_caderno.py
- L1098-L1111
- L1112-L1133
- L1134-L1141
- L1975-L1992
- L1994-L2064
- L2067-L2112
- L2114-L2137
- L2138-L2162


## 08 — AUDITORIA

### gerar_caderno.py
- L2164-L2185

### testar_motor.py
- L24-L39
- L40-L166

### testar_lote.py
- L32-L47
- L48-L84

### _diagnostico.py
- L1-L60


## 09 — ENTREGA

### gerar_caderno.py
- L2138-L2162
- L2164-L2185
- L2186

### novo_ambiente.py
- L19-L76

### server.py
- L1-L6


# ARQUIVOS DE CONFIGURAÇÃO E SUPORTE

- padrao.json
- materiais_cores.json
- materiais_index.json
- cores_cache.json
- texturas/
- assets/
- __pycache__/


# ARQUITETURA

### LEI.A NOVA ARUQTETURA.TXT
- L1-L248

### _RAIO_X_CORE_MOTOR/
- 00_RESUMO_RAIO_X.txt
- 01_INVENTARIO_COMPLETO.txt
- 02_PYTHON_MAPA_COMPLETO.txt
- 03_PYTHON_DEPENDENCIAS.txt
- 04_EXECUCAO_E_ARQUIVOS_CENTRAIS.txt
- 05_CONFIGURACOES_E_AUXILIARES.txt
- 06_CODIGOS_PY_COMPLETOS.txt
- 07_ARQUIVOS_TEXTO_COMPLETOS.txt


# MAPA RÁPIDO

Entrada
→ gerar_caderno.py / novo_ambiente.py

Unificação
→ dxf_pecas(motor core).py / geo.py / gerar_caderno.py

Engenharia
→ 03_ENGENHARIA_REGRAS / gerar_caderno.py

Representação / Especiais
→ gerar_caderno.py / geo.py

Listagem / Identificação
→ gerar_caderno.py

Cotas
→ gerar_caderno.py

Pranchas
→ gerar_caderno.py

Auditoria
→ gerar_caderno.py / testar_motor.py / testar_lote.py / _diagnostico.py

Entrega
→ gerar_caderno.py / novo_ambiente.py / server.py


# REGRA DE USO

Este arquivo é um mapa de localização do motor.

Ele NÃO substitui as regras existentes.

Antes de alterar uma função:
1. localizar a etapa;
2. localizar o arquivo;
3. localizar as linhas;
4. ler o contexto da função;
5. verificar dependências;
6. alterar somente a responsabilidade correspondente;
7. testar.

Não duplicar regras.

Se uma função atender mais de uma etapa, manter uma única fonte de verdade.

Após uma refatoração estrutural relevante, este índice deve ser atualizado.
"""

ARQUIVO.write_text(CONTEUDO.strip() + "\n", encoding="utf-8")

print(f"Índice criado com sucesso:")
print(ARQUIVO)