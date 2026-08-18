"""Analise da camada de canal: descasamento, reuso e qualidade relativa.

O descasamento (``canal_usado != canal_melhor``) e a evidencia mais direta
disponivel nesta campanha de que a escolha de canal nao acompanha o ambiente.
Ele nao prova congestionamento — para isso faltaria vazao — mas mostra que o
canal em uso nao e o que o proprio aplicativo aponta como melhor.
"""

import numpy as np
import pandas as pd

from config.predios import AVISO_PCT_MELHOR_CANAL, ROTULO_PAVIMENTO
from src.resultado import Resultado, nao_estimavel


def taxa_mismatch(df, por=("predio", "banda", "pavimento")):
    """Taxa de descasamento de canal, agregada pelas chaves indicadas."""
    sub = df[df["canal_usado"].notna() & df["canal_melhor"].notna()].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["mismatch"] = sub["canal_usado"] != sub["canal_melhor"]
    g = (sub.groupby(list(por), dropna=False)
            .agg(leituras=("mismatch", "size"), descasadas=("mismatch", "sum"))
            .reset_index())
    g["taxa_pct"] = (100.0 * g["descasadas"] / g["leituras"]).round(1)
    if "pavimento" in g.columns:
        g["pavimento_rotulo"] = g["pavimento"].map(ROTULO_PAVIMENTO)
    return g


def reuso_de_canal(df):
    """Canais em uso por AP fisico, para detectar reuso dentro do mesmo predio.

    So e calculavel onde ha BSSID: sem identificar o AP, dois pontos no mesmo
    canal podem ser o mesmo AP visto duas vezes. Devolve os grupos de BSSID que
    compartilham canal dentro de um predio e banda.
    """
    sub = df[df["grupo_ap"].notna() & df["canal_usado"].notna()]
    if sub.empty:
        return pd.DataFrame()

    linhas = []
    for (predio, banda), g in sub.groupby(["predio", "banda"]):
        por_canal = (g.groupby("canal_usado")["grupo_ap"]
                      .agg(lambda s: sorted(set(s))).reset_index())
        for _, r in por_canal.iterrows():
            linhas.append({
                "predio": predio, "banda": banda,
                "canal": int(r["canal_usado"]),
                "aps_distintos": len(r["grupo_ap"]),
                "grupos_bssid": ", ".join(r["grupo_ap"]),
                "reuso": len(r["grupo_ap"]) > 1,
            })
    return pd.DataFrame(linhas).sort_values(
        ["predio", "banda", "canal"]).reset_index(drop=True)


def distribuicao_pct(df):
    """Estatisticas de ``pct_melhor_canal`` por predio x banda.

    A metrica e tratada APENAS como comparativa: o aviso de semantica pendente
    acompanha toda saida que a cite.
    """
    sub = df[df["pct_melhor_canal"].notna()]
    if sub.empty:
        return pd.DataFrame(), AVISO_PCT_MELHOR_CANAL
    g = (sub.groupby(["predio", "banda"])["pct_melhor_canal"]
            .agg(n="size", minimo="min", mediana="median", media="mean", maximo="max")
            .round(1).reset_index())
    return g, AVISO_PCT_MELHOR_CANAL


def testar_hipotese_sistematica(df, banda="2.4", limiar_pct=60.0):
    """A hipotese de que o descasamento em 2,4 GHz e sistematico nos DOIS predios.

    A hipotese so se sustenta se a taxa for alta em todos os predios com dados.
    Um predio sozinho apontaria problema local; os dois apontariam ausencia de
    gerenciamento adaptativo de canal em nivel de campus. A funcao NAO afirma a
    conclusao: devolve as taxas e diz se o criterio foi atendido.
    """
    t = taxa_mismatch(df[df["banda"] == banda], por=("predio",))
    if t.empty:
        return nao_estimavel("sem leituras de canal na banda %s" % banda, n=0)

    taxas = dict(zip(t["predio"], t["taxa_pct"]))
    n_total = int(t["leituras"].sum())
    todos_altos = all(v >= limiar_pct for v in taxas.values())
    n_predios = len(taxas)

    if n_predios < 2:
        return nao_estimavel(
            "apenas %d predio com dados de canal — nao ha como distinguir "
            "problema local de padrao de campus" % n_predios,
            n=n_total, taxas=taxas)

    detalhe = ", ".join("%s = %.0f%%" % (k, v) for k, v in sorted(taxas.items()))
    return Resultado(
        valor=float(np.mean(list(taxas.values()))), ic=None, n=n_total,
        status="estimado",
        motivo="",
        extra=dict(taxas=taxas, limiar_pct=limiar_pct, banda=banda,
                   criterio_atendido=todos_altos, detalhe=detalhe,
                   leitura=("descasamento alto nos %d predios (%s) — compativel com "
                            "ausencia de gerenciamento adaptativo de canal em nivel "
                            "de campus, nao com problema de uma edificacao"
                            % (n_predios, detalhe)) if todos_altos else
                           ("descasamento nao e alto em todos os predios (%s) — a "
                            "hipotese de padrao de campus NAO se sustenta" % detalhe)))
