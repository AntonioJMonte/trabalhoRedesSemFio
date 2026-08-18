"""Carga e validacao de ``dados/leituras.csv``.

Nenhum valor e arbitrado: coluna ausente vira NaN e a analise que dependia dela
e bloqueada com motivo escrito. Nenhuma linha e descartada em silencio — tudo
que sai de uma analise aparece no relatorio de qualidade.
"""

import numpy as np
import pandas as pd

from config.predios import CSV_LEITURAS, PARAMS

# Colunas obrigatorias do schema. A ausencia de qualquer uma e erro de arquivo,
# nao de dado, e interrompe a carga.
COLUNAS_OBRIGATORIAS = [
    "id", "predio", "pavimento", "banda", "rssi_dbm",
    "canal_usado", "canal_melhor", "pct_melhor_canal",
    "dist_campo_m", "dist_origem", "x_m", "y_m",
    "bssid_bruto", "altura_medicao_m", "obstaculos", "local", "datahora",
]

# Colunas opcionais, preenchidas com NaN quando o CSV nao as traz.
COLUNAS_OPCIONAIS = ["dist_ap_conectado_m", "obstaculos_registrado", "obs_campo"]

COLUNAS_NUMERICAS = [
    "id", "pavimento", "rssi_dbm", "canal_usado", "canal_melhor",
    "pct_melhor_canal", "dist_campo_m", "dist_ap_conectado_m",
    "x_m", "y_m", "altura_medicao_m",
]

ORIGENS_DISTANCIA_VALIDAS = {"medida", "estimada_app", "planta", "desconhecida"}

TERMOS_SEM_OBSTACULO = {
    "nenhum", "nenhuma", "sem obstaculo", "sem obstaculo",
    "livre", "-", "", "nan", "none",
}


def _derivar_sem_obstaculo(serie):
    """True quando o texto de obstaculo indica ausencia de obstrucao."""
    return serie.fillna("").astype(str).str.strip().str.lower().isin(TERMOS_SEM_OBSTACULO)


def carregar(caminho=None):
    """Le o CSV, normaliza tipos e deriva as colunas de apoio.

    NAO remove nenhuma linha. Leituras invalidas sao marcadas em colunas
    booleanas para que o relatorio de qualidade as reporte e as analises as
    filtrem explicitamente.
    """
    caminho = caminho or CSV_LEITURAS
    df = pd.read_csv(caminho, dtype={"banda": str, "bssid_bruto": str})

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"{caminho}: colunas obrigatorias ausentes: {', '.join(faltando)}"
        )
    for col in COLUNAS_OPCIONAIS:
        if col not in df.columns:
            df[col] = np.nan

    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["predio"] = df["predio"].astype(str).str.strip()
    df["banda"] = df["banda"].astype(str).str.strip()
    df["dist_origem"] = (df["dist_origem"].fillna("desconhecida")
                         .astype(str).str.strip().str.lower())
    for col in ("obstaculos", "obstaculos_registrado", "local", "obs_campo"):
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["pavimento"] = df["pavimento"].astype("Int64")
    df["sem_obstaculo"] = _derivar_sem_obstaculo(df["obstaculos"])
    df["obstaculo_reclassificado"] = (
        (df["obstaculos_registrado"] != "") &
        (df["obstaculos_registrado"] != df["obstaculos"])
    )

    # Identificador legivel, usado em figuras e tabelas.
    df["ponto_id"] = [f"{p}-{int(i):02d}" for p, i in zip(df["predio"], df["id"])]

    # Distancia historica: a que as execucoes anteriores usaram no ajuste.
    # Onde a campanha anotou dois valores ("6 m real, 15 m do AP conectado"), o
    # CSV antigo gravava o do AP conectado. Preservada para a verificacao de
    # regressao da Parte 5.3 — NAO para uso como distancia geometrica.
    df["dist_historica_m"] = df["dist_ap_conectado_m"].fillna(df["dist_campo_m"])
    df["dist_tem_dois_valores"] = df["dist_ap_conectado_m"].notna()

    return df.sort_values("id").reset_index(drop=True)


def validar(df):
    """Marca (nao remove) as leituras que violam faixa ou vocabulario.

    Acrescenta colunas booleanas ``invalido_*`` e a coluna ``valido``, que as
    analises usam como filtro explicito.
    """
    df = df.copy()
    lo, hi = PARAMS["rssi_faixa_valida"]

    df["invalido_rssi_faixa"] = df["rssi_dbm"].notna() & ~df["rssi_dbm"].between(lo, hi)
    df["rssi_ausente"] = df["rssi_dbm"].isna()
    df["dist_nao_positiva"] = df["dist_campo_m"].notna() & (df["dist_campo_m"] <= 0)
    df["dist_ausente"] = df["dist_campo_m"].isna()
    df["invalido_banda"] = ~df["banda"].isin(PARAMS["bandas_validas"])
    df["invalido_dist_origem"] = ~df["dist_origem"].isin(ORIGENS_DISTANCIA_VALIDAS)

    # 'valido' cobre apenas o que impede QUALQUER uso da linha. RSSI ausente nao
    # invalida a leitura: o ponto 22 do predio M e uma zona cega, e essa e a
    # informacao dele.
    df["valido"] = ~(df["invalido_rssi_faixa"] | df["invalido_banda"] |
                     df["invalido_dist_origem"])

    # Leitura utilizavel em regressao de path loss: precisa de RSSI, de distancia
    # positiva e de origem de distancia que nao seja derivada do proprio RSSI.
    df["apta_regressao"] = (
        df["valido"] & ~df["rssi_ausente"] & ~df["dist_nao_positiva"] &
        ~df["dist_ausente"] & (df["dist_origem"] != "estimada_app")
    )
    df["excluida_por_circularidade"] = df["dist_origem"] == "estimada_app"

    return df


def carregar_e_validar(caminho=None):
    """Atalho: carrega, valida e devolve o DataFrame anotado."""
    return validar(carregar(caminho))
