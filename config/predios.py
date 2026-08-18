"""Configuracao declarativa do estudo de cobertura Wi-Fi.

Este modulo e a **unica** fonte de valores especificos de predio. Nenhum arquivo
de ``src/`` pode conter o nome de um predio: as analises recebem o identificador
como parametro e leem tudo daqui.

Para acrescentar um terceiro predio, basta uma nova entrada em ``PREDIOS`` e as
linhas correspondentes em ``dados/leituras.csv``. Nada em ``src/`` muda.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Caminhos
# -----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
DIR_DADOS = BASE / "dados"
DIR_SAIDA = BASE / "saidas"
DIR_FIG = DIR_SAIDA / "figuras"
DIR_QGIS = DIR_SAIDA / "qgis"

CSV_LEITURAS = DIR_DADOS / "leituras.csv"

for _d in (DIR_DADOS, DIR_SAIDA, DIR_FIG, DIR_QGIS):
    _d.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Geometria compartilhada
# -----------------------------------------------------------------------------
# Os dois predios tem geometria identica (mesmo projeto arquitetonico), entao a
# descricao e escrita uma unica vez e composta em cada entrada de PREDIOS.
GEOMETRIA_PADRAO = {
    "aps": {
        "AP1": {"x": 7.40, "y": 9.55},
        "AP2": {"x": 24.05, "y": 9.55},
    },
    "origem": "eixo 06 (x=0), eixo A (y=0)",
    "extensao_m": (30.08, 19.99),
    "pe_direito_m": 3.40,          # vale para subsolo->terreo e terreo->1o andar
    "pavimentos": [-1, 0, 1],
}

# Rotulos de pavimento, para figuras e tabelas. Chave = valor da coluna
# 'pavimento' do CSV.
ROTULO_PAVIMENTO = {-1: "Subsolo", 0: "Terreo", 1: "1o andar"}

# -----------------------------------------------------------------------------
# PREDIOS
# -----------------------------------------------------------------------------
PREDIOS = {

    "M": {
        **GEOMETRIA_PADRAO,

        "fabricante_ap": "Ruckus Wireless",
        "modelo_ap": None,          # nao registrado em campo
        "data_campanha": "2026-08-07",

        # Mapeamento BSSID -> AP fisico. Preenchido MANUALMENTE, apos conferencia
        # dos grupos candidatos emitidos por src.bssid.agrupar_por_ap_fisico().
        # Chave = prefixo de agrupamento; valor = rotulo do AP fisico.
        "bssid_para_ap": {
            "e0:10:7f:3c:c6": {"ap": "AP2", "pavimento": 0},
            "e0:10:7f:3d:ea": {"ap": "AP1", "pavimento": 0},
        },

        # Regra de agrupamento de BSSIDs em AP fisico, confirmada empiricamente
        # para os APs Ruckus deste predio: BSSIDs que compartilham os 5 primeiros
        # octetos pertencem ao mesmo AP fisico (o ultimo octeto varia por
        # radio/SSID).
        "regra_agrupamento_bssid": {"tipo": "prefixo_octetos", "n": 5},

        "plantas": {
            -1: DIR_DADOS / "planta_M_subsolo.png",   # prancha 01/13
            0: DIR_DADOS / "planta_M_terreo.png",     # prancha 02/13
            1: DIR_DADOS / "planta_M_1andar.png",     # prancha 03/13
        },
        "ambiente": {
            -1: "corredor/salas",
            0: "corredor/salas",
            1: "corredor/salas",
        },
    },

    "I": {
        **GEOMETRIA_PADRAO,

        # NAO inferir a partir do OUI sem consulta a base IEEE. Enquanto None, a
        # ressalva de comparabilidade entre predios permanece aberta.
        "fabricante_ap": None,
        "modelo_ap": None,
        "data_campanha": "2026-08-07",

        # Vazio de proposito: a regra de agrupamento do predio M NAO foi
        # confirmada aqui (ver saidas/relatorio_qualidade.md, secao de BSSID).
        # Preencher somente apos conferencia manual dos grupos candidatos.
        "bssid_para_ap": {},

        # Hipotese a confirmar: neste predio o 4o octeto difere em +0x40 entre o
        # radio de 2.4 GHz e o de 5 GHz do mesmo AP fisico, de modo que a regra
        # de 5 octetos do predio M separaria radios do mesmo equipamento.
        # Enquanto nao confirmada, vale a regra conservadora (BSSID inteiro).
        "regra_agrupamento_bssid": {"tipo": "bssid_completo"},

        "plantas": {-1: None, 0: None, 1: None},
        "ambiente": {
            -1: "biblioteca (prateleiras metalicas, colunas)",
            0: "corredor/salas",
            1: "corredor/salas",
        },
    },

}

# -----------------------------------------------------------------------------
# PARAMS — limiares e constantes de decisao
# -----------------------------------------------------------------------------
PARAMS = {
    # --- modelo log-distancia ---
    "d0_m": 1.0,                     # distancia de referencia FIXA
    "min_pontos_ajuste": 5,          # abaixo disso: status "nao estimavel"
    "min_distancias_distintas": 3,   # sem alavanca em distancia, alpha e ruido
    "r2_minimo_confiavel": 0.30,
    "alpha_teorico": (2.0, 4.0),
    "algarismos_significativos_alpha": 2,
    "ic_confianca": 0.95,

    # --- perda de laje ---
    "min_pares_laje": 3,

    # --- BSSID ---
    "hamming_nibbles_suspeito": 2,   # distancia <= isso, fora do grupo => suspeito
    # Deslocamentos ja observados no 4o octeto entre radios do MESMO AP fisico.
    # Servem para separar "radio distinto do mesmo equipamento" de "erro de
    # transcricao" na tabela de BSSIDs suspeitos. Nao sao regra de agrupamento:
    # o agrupamento continua vindo de 'regra_agrupamento_bssid' de cada predio.
    "offsets_radio_4o_octeto": [0x40],
    # Classes de dominancia que saem de QUALQUER regressao de path loss local.
    # Nao e filtro de cenario: e gate de validade. Uma leitura cujo AP dominante
    # comprovadamente nao e um AP local do pavimento nao mede perda de percurso
    # local, entao entra-la no ajuste mistura dois fenomenos distintos.
    # 'sem_dado' NAO esta na lista: ausencia de BSSID nao e evidencia de nada.
    "dominancias_excluidas_sempre": ("suspeito", "outro_predio", "ap_nao_mapeado"),

    # --- SNR / capacidade ---
    "piso_ruido_dbm": -95.0,         # ADOTADO, nao medido
    "largura_canal_hz": 20e6,

    # --- heatmap ---
    "idw_potencia": 2.0,
    "idw_raio_max_m": 8.0,           # IDW nao extrapola alem disso
    "resolucao_malha": 200,
    "min_pontos_interpolacao": 4,    # abaixo disso: apenas scatter
    "contornos_rssi": [-67.0, -70.0],

    # --- validacao ---
    "bandas_validas": {"2.4", "5"},
    "rssi_faixa_valida": (-100.0, -10.0),
    "divergencia_distancia_m": 3.0,  # |dist_campo - dist_calc_3d| acima disso e reportada

    # --- verificacao contra referencias historicas (Parte 5.3) ---
    "referencias": {
        "alpha_M_2.4_cenario_historico": 2.62,
        "r2_M_2.4_cenario_historico": 0.91,
        "n_M_2.4_cenario_historico": 9,
        "L_obstaculo_porta_corta_fogo_db": 21.1,
        "mismatch_M_2.4_pct": 76.0,
        "tolerancia_alpha": 0.10,
        "tolerancia_r2": 0.03,
    },
}

# -----------------------------------------------------------------------------
# Semantica pendente — avisos emitidos pelo pipeline
# -----------------------------------------------------------------------------
AVISO_PCT_MELHOR_CANAL = (
    "SEMANTICA PENDENTE: 'pct_melhor_canal' tem interpretacao ambigua (qualidade do "
    "melhor canal vs. ocupacao do melhor canal). O pipeline a trata APENAS como metrica "
    "relativa comparativa, nunca como grandeza fisica. Defina explicitamente no relatorio "
    "antes de citar qualquer valor absoluto."
)
