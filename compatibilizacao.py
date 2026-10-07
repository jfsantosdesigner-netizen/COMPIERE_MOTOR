# -*- coding: utf-8 -*-
"""Etapa 8: classificação e organização espacial consumidas pelo caderno."""
import classificacao, geo

def definir_paredes(itens, pecas, portas_xml=()): return geo.definir_paredes(itens, pecas, portas_xml)
def classificar(item, contexto): return classificacao.classificar_peca(item, contexto)
def grupo(item, contexto): return classificacao._grupo_de(item, contexto)
def nome_tem_porta(nome): return classificacao._nome_tem_porta(nome)
