# -*- coding: utf-8 -*-
"""Bloco isolado de pranchas especiais COMPIERE."""
from .detector import detectar, Especial, Sinais
from .pranchas import gerar

__all__ = ["detectar", "gerar", "Especial", "Sinais"]
