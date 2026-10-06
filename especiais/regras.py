# -*- coding: utf-8 -*-
"""Regras consolidadas do bloco de pranchas especiais COMPIERE.

Este pacote NÃO altera o gerar_caderno.py. A precedência é:
1) exceção explícita; 2) regra da família; 3) regra geométrica geral; 4) fluxo normal.
"""
from dataclasses import dataclass
from enum import Enum

class Destino(str, Enum):
    NORMAL = "normal"
    ESPECIAL = "especial"
    IGNORAR = "ignorar"

class Familia(str, Enum):
    CAMA = "cama"
    LED = "led"
    PORTA_PERFIL = "porta_perfil"
    METALON = "metalon"
    DIVISORIA = "divisoria"
    DIVISOR_TALHER = "divisor_talher"
    SAPATEIRA = "sapateira"
    FRUTEIRA = "fruteira"
    PORTA_TEMPERO_INCLINADO = "porta_tempero_inclinado"
    PAINEL = "painel"
    PAINEL_RIPADO = "painel_ripado"
    USINAGEM = "usinagem"
    GAVETA_ESPECIAL = "gaveta_especial"
    TAMPONAMENTO_ESPECIAL = "tamponamento_especial"
    CURVO = "curvo"
    ANGULO = "angulo"
    NICHO_ESPECIAL = "nicho_especial"
    VIDRO_APLICADO = "vidro_aplicado"
    FUNDO_FALSO = "fundo_falso"
    PAINEL_TECNICO = "painel_tecnico"
    CONJUNTO_ESPECIAL = "conjunto_especial"

@dataclass(frozen=True)
class RegraVisual:
    subimagem_ambiente: bool = True
    listar: bool = True
    cotar: bool = True
    frente_tras: bool = False
    qtd_pranchas: int = 1

REGRAS_VISUAIS = {
    Familia.PAINEL: RegraVisual(frente_tras=True, qtd_pranchas=2),
    Familia.PAINEL_RIPADO: RegraVisual(qtd_pranchas=2),
    Familia.DIVISORIA: RegraVisual(qtd_pranchas=5),
    Familia.CAMA: RegraVisual(qtd_pranchas=5),
}

# Exceções explícitas: sempre avaliadas antes da geometria.
EXCECOES_NORMAL = (
    "pino invisivel",
    "pino invisível",
    "puxador usinado",
    "cava usinada",
)
EXCECOES_IGNORAR = (
    "espelho decorativo solto",
)

# Itens que pertencem ao fluxo normal do gerar_caderno.py.
NORMAL_POR_NOME = (
    "adega",
    "cristaleira",
    "porta falsa",
)

# Palavras usadas somente como apoio de classificação. A detecção de usinagem
# nunca depende da finalidade semântica ("gato", "gás", "campainha" etc.).
FAMILIAS_POR_NOME = {
    Familia.CAMA: ("cama", "estrado"),
    Familia.LED: (" led", "led ", "fita led", "ilumin"),
    Familia.METALON: ("metalon",),
    Familia.DIVISORIA: ("divisoria", "divisória"),
    Familia.DIVISOR_TALHER: ("divisor de talher", "divisor talher"),
    Familia.SAPATEIRA: ("sapateira",),
    Familia.FRUTEIRA: ("fruteira",),
    Familia.PORTA_TEMPERO_INCLINADO: ("tempero inclinado", "temperos inclinado", "porta tempero inclinado"),
    Familia.PAINEL_RIPADO: ("painel ripado", "porta ripada", "ripado"),
    Familia.FUNDO_FALSO: ("fundo falso",),
    Familia.PAINEL_TECNICO: ("painel tecnico", "painel técnico", "acesso oculto"),
}

def visual_da(familia):
    return REGRAS_VISUAIS.get(familia, RegraVisual())

def precedencia():
    return ("excecao_explicita", "familia", "geometria", "normal")


# Catálogo executável das decisões consolidadas. Serve como fonte única para
# detector/geradores e mantém separado o que ainda pertence ao gerar_caderno.py.
REGRAS_FUNCIONAIS = {
    "global": {
        "ordem_precedencia": precedencia(),
        "subimagem_contexto": True,
        "principal_lista_e_cotas": True,
        "agrupar_mesma_geometria_dimensoes_diferentes": True,
        "novo_grupo_se_mudar_geometria_raio_angulo_usinagem": True,
        "canto_l_especial": False,
    },
    "usinagem": {
        "detectar_por_geometria": True,
        "nao_detectar_por_seta_ou_texto": True,
        "nao_inferir_finalidade_semantica": True,
        "varias_usinagens_mesma_peca_uma_prancha": True,
        "pino_invisivel_so_legenda": True,
        "cava_puxador_nao_porta_fluxo_normal": True,
        "porta_mdf_usinada_peca_inteira_especial": True,
    },
    "geometria": {
        "raio_curva_especial": True,
        "angulo_diferente_90_especial": True,
        "cantoneira_90_normal": True,
        "fechamento_so_geometria_ou_usinagem_representada": True,
        "nicho_com_raio_curva_angulo_especial": True,
    },
    "cama": {
        "estrutura_externa": True,
        "usinagens": True,
        "gavetas": True,
        "estrado": True,
        "estrutura_interna_sob_estrado": True,
        "um_bloco_funcional_por_prancha": True,
    },
    "led": {
        "regra_geral_prancha_propria": True,
        "mostrar_posicao_comprimento_orientacao": True,
        "painel_ripado_pode_incorporar": True,
    },
    "porta_perfil": {
        "separar_por_funcao": True,
        "conjunto_unico": True,
        "especificar_perfil_cor_vidro_espelho": True,
        "porta_vidro_sem_perfil_prevista": False,
    },
    "metalon": {
        "uma_prancha_por_ambiente": True,
        "listar_secao_espessura_comprimento_cor": True,
        "nao_separar_por_conjunto_fisico": True,
    },
    "divisoria": {
        "listagem_frontal": True,
        "listagem_lateral": True,
        "cotas_frontal": True,
        "cotas_lateral": True,
        "subimagem_3d_mesma_orientacao_da_cota": True,
        "prancha_sequencia_quatro_etapas": True,
        "sequencia_depende_engenharia_real": True,
    },
    "paineis": {
        "aplica_cabeceira_tv_parede_ripado": True,
        "prancha_1_listagem_frente_tras": True,
        "prancha_2_cotas_frente_tras": True,
        "listar_afastadores_cunhas_paineis": True,
        "espelho_aplicado_subimagem_com_espelho_principal_so_mdf": True,
    },
    "ripado": {
        "um_balao_em_uma_ripa": True,
        "listagem_quantidade_agregada": True,
        "detalhe_redondo_espacamento": True,
        "com_fundo_segunda_prancha_sem_ripa_e_com_ripa": True,
        "subimagem_ambiente_inferior_esquerda": True,
        "led_pode_ir_no_detalhe_redondo": True,
    },
    "vidro": {
        "espelho_solto_ignorar": True,
        "vidro_aplicado_em_mdf_ou_perfil_especial": True,
        "prateleira_vidro_fluxo_normal": True,
        "prateleira_vidro_dentro_mov_subimagem_lista_baloes": True,
        "prateleira_vidro_parede_lista_balao_imagem_principal": True,
    },
    "modulos": {
        "curvo_por_pecas_seltas_especial_conjunto": True,
        "curvo_pronto_fabrica_normal": True,
        "conjunto_especial_cotar_largura_altura_profundidade": True,
        "conjunto_especial_listar_todas_pecas": True,
    },
    "tecnico": {
        "fundo_falso_removivel_especial": True,
        "fundo_falso_varias_pecas_uma_prancha": True,
        "painel_acesso_oculto_especial": True,
        "base_removivel_fluxo_normal_legenda": True,
        "porta_falsa_decorativa_fluxo_normal": True,
    },
    "outros": {
        "divisor_talher_mdf_especial": True,
        "sapateira_especial": True,
        "fruteira_especial_por_tipo": True,
        "porta_tempero_inclinado_especial": True,
        "adega_fluxo_normal_como_nicho": True,
        "cristaleira_fluxo_normal": True,
        "gaveta_comum_fluxo_normal_montada": True,
        "acessorio_nao_mdf_subimagem_sem_lista_sem_cotas": True,
    },
}

REGRAS_GERAR_CADERNO_PENDENTES = {
    "gaveta_comum": "listar como conjunto montado + subimagem própria",
    "mesa_cabeceira": "subimagem própria; listar módulo e tamponamentos",
    "cava_puxador_nao_porta": "subimagem no fluxo normal; não gerar especial",
    "prateleira_vidro_movel": "subimagem + balões + listagem",
    "prateleira_vidro_parede": "balão + listagem na imagem principal",
    "acessorio_nao_mdf": "subimagem representativa sem listagem e sem cotas",
    "adega": "regra de nicho no fluxo normal",
    "cristaleira": "normal; componentes especiais tratados separadamente",
    "modulo_curvo_fabrica": "normal como módulo único, sem explodir",
    "base_tecnica_removivel": "normal + legenda REMOVÍVEL",
    "porta_falsa_decorativa": "normal + balão + listagem",
    "pino_invisivel": "sem detalhar rasgos/furos; somente legenda",
}
