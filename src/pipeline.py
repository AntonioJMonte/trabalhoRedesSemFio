"""Orquestracao do pipeline completo, na ordem exigida.

Ordem: carga e validacao -> geometria e BSSID -> RELATORIO DE QUALIDADE ->
analises (path loss, laje, canais, mapas) -> limitacoes -> verificacao contra
as referencias historicas.

O relatorio de qualidade roda antes das analises de proposito: ele descreve o
que o dado permite, e as analises apenas confirmam.
"""

import pandas as pd

from config.predios import PARAMS, PREDIOS
from src import canais, heatmap, laje, limitacoes, pathloss, qualidade
from src.bssid import anotar_dominancia
from src.esquema import carregar_e_validar
from src.geometria import resolver_distancias


def preparar(caminho=None):
    """Carga, validacao, dominancia de BSSID e geometria — nesta ordem."""
    df = carregar_e_validar(caminho)
    df = anotar_dominancia(df, PREDIOS)
    df = resolver_distancias(df, PREDIOS)
    return df


def verificar_referencias(df, cenarios_hist):
    """Confronta a execucao com os valores ja validados (Parte 5.3).

    Divergencia grande aqui indica erro de parsing ou de mapeamento de colunas,
    NAO descoberta. A funcao devolve a tabela de conferencia e um booleano.
    """
    ref = PARAMS["referencias"]
    linhas = []

    h = cenarios_hist[(cenarios_hist["predio"] == "M") &
                      (cenarios_hist["banda"] == "2.4")]
    obtido_alpha = float(h["alpha"].iloc[0]) if len(h) else float("nan")
    obtido_r2 = float(h["r2"].iloc[0]) if len(h) else float("nan")
    obtido_n = int(h["n"].iloc[0]) if len(h) else 0

    linhas.append({
        "verificacao": "alpha M 2.4 GHz (cenario historico)",
        "esperado": ref["alpha_M_2.4_cenario_historico"],
        "obtido": obtido_alpha,
        "tolerancia": ref["tolerancia_alpha"],
        "ok": abs(obtido_alpha - ref["alpha_M_2.4_cenario_historico"]) <= ref["tolerancia_alpha"],
    })
    linhas.append({
        "verificacao": "R2 M 2.4 GHz (cenario historico)",
        "esperado": ref["r2_M_2.4_cenario_historico"],
        "obtido": round(obtido_r2, 3),
        "tolerancia": ref["tolerancia_r2"],
        "ok": abs(obtido_r2 - ref["r2_M_2.4_cenario_historico"]) <= ref["tolerancia_r2"],
    })
    linhas.append({
        "verificacao": "n M 2.4 GHz (cenario historico)",
        "esperado": ref["n_M_2.4_cenario_historico"],
        "obtido": obtido_n,
        "tolerancia": 0,
        "ok": obtido_n == ref["n_M_2.4_cenario_historico"],
    })

    # mismatch de canal em 2.4 GHz, predio M
    t = canais.taxa_mismatch(df[df["banda"] == "2.4"], por=("predio",))
    tm = t[t["predio"] == "M"]
    obtido_mm = float(tm["taxa_pct"].iloc[0]) if len(tm) else float("nan")
    linhas.append({
        "verificacao": "mismatch de canal M 2.4 GHz (%)",
        "esperado": ref["mismatch_M_2.4_pct"],
        "obtido": obtido_mm,
        "tolerancia": 1.0,
        "ok": abs(obtido_mm - ref["mismatch_M_2.4_pct"]) <= 1.0,
    })

    tabela = pd.DataFrame(linhas)
    return tabela, bool(tabela["ok"].all())


def verificar_obstaculo(df, modelo_hist):
    """Confere o L_obstaculo da porta corta-fogo contra a referencia historica."""
    ref = PARAMS["referencias"]["L_obstaculo_porta_corta_fogo_db"]
    tab = pathloss.atenuacao_por_obstaculo(df, modelo_hist, "M", "2.4",
                                           coluna_distancia="dist_historica_m")
    if tab.empty:
        return tab, None, False
    corta_fogo = tab[tab["obstaculos"].str.lower().str.contains("incendio|corta", regex=True)]
    obtido = float(corta_fogo["L_obstaculo_db"].iloc[0]) if len(corta_fogo) else None
    ok = obtido is not None and abs(obtido - ref) <= 1.0
    return tab, obtido, ok


def rodar(caminho=None, gerar_figuras=True):
    """Executa o pipeline inteiro. Devolve um dicionario com todas as saidas."""
    saidas = {}

    # --- 1. dados ------------------------------------------------------------
    df = preparar(caminho)
    saidas["df"] = df

    # --- 2. cenarios de path loss --------------------------------------------
    cen = pathloss.rodar_cenarios(df)
    cen_hist = pathloss.rodar_cenarios(df, pathloss.CENARIO_HISTORICO)
    cen_diag = pathloss.rodar_cenarios(df, pathloss.CENARIO_DIAGNOSTICO)
    saidas["cenarios"] = cen
    saidas["cenarios_historico"] = cen_hist
    saidas["cenarios_diagnostico"] = cen_diag

    # --- 3. modelos de referencia e laje -------------------------------------
    combos = sorted({(p, b) for p, b in zip(df["predio"], df["banda"])})
    modelos = {c: pathloss.melhor_modelo_disponivel(df, *c) for c in combos}
    saidas["modelos"] = modelos
    resumo_laje, pares_laje = laje.rodar(df, PREDIOS, modelos)
    saidas["laje"] = resumo_laje
    saidas["laje_pares"] = pares_laje

    # --- 4. obstaculos --------------------------------------------------------
    obst = []
    for (predio, banda), (nome_cen, modelo) in modelos.items():
        t = pathloss.atenuacao_por_obstaculo(df, modelo, predio, banda)
        if not t.empty:
            t = t.copy()
            t["cenario_alpha"] = nome_cen
            obst.append(t)
    saidas["obstaculos"] = pd.concat(obst, ignore_index=True) if obst else pd.DataFrame()

    # --- 5. canais ------------------------------------------------------------
    saidas["mismatch"] = canais.taxa_mismatch(df)
    saidas["mismatch_banda"] = canais.taxa_mismatch(df, por=("predio", "banda"))
    saidas["reuso"] = canais.reuso_de_canal(df)
    saidas["pct"], saidas["aviso_pct"] = canais.distribuicao_pct(df)
    saidas["hipotese_canal"] = canais.testar_hipotese_sistematica(df)

    # --- 6. mapas -------------------------------------------------------------
    saidas["heatmaps"] = (heatmap.rodar(df, PREDIOS) if gerar_figuras
                          else pd.DataFrame())

    # --- 7. relatorio de qualidade (gravado por ultimo, informado por tudo) ---
    saidas["relatorio_qualidade"] = qualidade.gerar_relatorio(
        df, PREDIOS, cenarios_df=cen, laje_df=resumo_laje,
        heatmap_df=saidas["heatmaps"], obstaculos_df=saidas["obstaculos"],
        mismatch_df=saidas["mismatch"])

    # --- 8. limitacoes --------------------------------------------------------
    saidas["limitacoes"] = limitacoes.gerar(df, PREDIOS, cenarios_df=cen)

    # --- 9. verificacao contra as referencias ---------------------------------
    tabela_ref, tudo_ok = verificar_referencias(df, cen_hist)
    modelo_hist = pathloss.ajustar(
        pathloss.aplicar_filtro(df[(df["predio"] == "M") & (df["banda"] == "2.4")],
                                "sem_estimada_app")[0],
        "dist_historica_m", rotulo="M 2.4 GHz — historico")
    tab_obst, l_obst, obst_ok = verificar_obstaculo(df, modelo_hist)
    saidas["verificacao"] = tabela_ref
    saidas["verificacao_ok"] = tudo_ok and obst_ok
    saidas["obstaculo_historico"] = tab_obst
    saidas["L_obstaculo_corta_fogo"] = l_obst
    saidas["L_obstaculo_ok"] = obst_ok

    return saidas
