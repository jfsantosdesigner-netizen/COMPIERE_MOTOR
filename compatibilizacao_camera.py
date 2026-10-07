# -*- coding: utf-8 -*-
"""Etapa 8: decide a câmera; o gerador apenas consome o resultado."""
import math


def calcular(f, caixa, quantidade_paredes=1, angulo=None, elevacao=None,
             distancia_minima=4200, contexto=False, detalhe=False):
    a = 0.0
    if angulo is not None: a = math.radians(angulo)
    hx = f[0] * math.cos(a) - f[1] * math.sin(a)
    hy = f[0] * math.sin(a) + f[1] * math.cos(a)
    e = math.radians((0 if contexto and not detalhe else 9) if elevacao is None else elevacao)
    frente = (hx * math.cos(e), hy * math.cos(e), -math.sin(e))
    rn = math.hypot(hy, hx)
    direita = (hy / rn, -hx / rn, 0.0)
    acima = (direita[1] * frente[2] - direita[2] * frente[1],
             direita[2] * frente[0] - direita[0] * frente[2],
             direita[0] * frente[1] - direita[1] * frente[0])
    alvo = tuple((caixa[k] + caixa[k + 3]) / 2 for k in range(3))
    distancia = max(max(caixa[3] - caixa[0], caixa[4] - caixa[1], caixa[5] - caixa[2]) * 1.9, distancia_minima)
    if contexto and not detalhe and quantidade_paredes == 1: distancia = max(distancia, 7000)
    posicao = tuple(alvo[k] - frente[k] * distancia for k in range(3))
    return {'posicao': posicao, 'alvo': alvo, 'frente': frente, 'direita': direita, 'acima': acima,
            'distancia': distancia, 'altura_mm': posicao[2], 'foco_altura_mm': alvo[2]}
