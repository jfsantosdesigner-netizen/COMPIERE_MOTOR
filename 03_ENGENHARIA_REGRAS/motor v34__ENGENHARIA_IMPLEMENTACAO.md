# ENGENHARIA — CADERNO CLIENTE (Referência de Implementação)

## PARTE 1 — FUNCIONAMENTO DO MOTOR
1. FONTES DE DADOS
- XML: identidade, estrutura, ambiente, materiais, ferragens.
- DXF: geometria, medidas, posição.
- **Regra:** Cruzamento XML + DXF é obrigatório. Divergência = Erro de processamento.

2. OBJETIVO
- Documento visual e informativo (não é manual de instalação).

3. LISTAGEM
- Unidade = módulo/elemento.
- **Regra:** 10 ocorrências reais = 10 itens na listagem. Nenhum item pode desaparecer.

4. IDENTIFICAÇÃO
- Cruzamento XML (sentido) + DXF (geometria).
- Não criar ambiguidades artificiais.

5. SEQUÊNCIA
- Seguir lógica espacial do ambiente (Obter do XML).
- Exemplos: Cozinha (pia), Quarto (guarda-roupa), etc.

6. VISTAS
- Geradas a partir do DXF.
- Limpas (sem balões/cotas na vista geral).
- Escala dinâmica (mobília + área útil).

7. COTAS
- Preservar lógica atual (não mexer se funciona).
- Cotas externas (medidas totais) e internas (prateleiras).

8. BALÕES
- Item único na listagem = balão único no conjunto.
- Conflitos -> Subimagem.

9. NICHOS
- Categoria especial (dimensão).
- Geralmente vão para subimagem (um por prancha se possível).

10. AGRUPAMENTOS
- Cruzamento XML+DXF. Não isolar blocos se a semântica está no XML.

11. BASE / RODAPÉ
- Peças ocultas/piso.

12. ESPECIFICAÇÕES
- Dados do XML + Texto padrão.

13. PAGINAÇÃO
- > 15 itens = blocos.
- Qualidade/legibilidade > redução de páginas.

## PARTE 2 — CONTROLE, VALIDAÇÃO E FINALIZAÇÃO
- **Princípio:** Simples, modular e conservador. Se funciona, não mexer.
- **Validação:** XML vs DXF (conferir perdas e duplicidade).
- **Tratamento de Falhas:** Identificar, corrigir o necessário, testar (não fazer reengenharia).
- **Congelamento:** Validação feita -> Corrigir apenas erros comprovados.
