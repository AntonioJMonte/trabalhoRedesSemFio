"""Estimativa da perda de propagacao atraves da laje entre pavimentos.

Metodo: procurar pares de leituras do MESMO AP fisico (mesmo grupo de BSSID) em
pavimentos diferentes. Para cada par,

    L_laje = delta_RSSI - perda_prevista_pela_variacao_de_distancia

onde a perda prevista usa o alpha do modelo de referencia da mesma banda e
predio. O que sobra depois de descontar a distancia e atribuido a laje.

REGRAS DE HONESTIDADE, implementadas e nao apenas documentadas:

- ``n_pares < PARAMS["min_pares_laje"]``  -> status "nao estimavel", valor None.
  Nunca o valor de um unico par.
- mediana negativa ou proxima de zero -> status "inconsistente", com o alerta
  sobre a instabilidade da referencia de RSSI a 1 m sob o AP.
- os pares individuais sao SEMPRE devolvidos, para inspecao manual.
"""

import numpy as np
import pandas as pd

from config.predios import PARAMS
from src.resultado import Resultado, nao_estimavel

ALERTA_REFERENCIA_INSTAVEL = (
    "estimativa inconsistente — a referencia de RSSI a 1 m sob o AP e instavel "
    "(antenas adaptativas BeamFlex+ e altura de medicao nao controlada)"
)


def _distancia_utilizavel(linha):
    """Distancia da leitura ao seu AP dominante, e a procedencia dessa distancia.

    Preferencia: a geometrica 3D ate o AP dominante; na falta dela, a anotada em
    campo. A procedencia acompanha o par ate o relatorio, porque um par montado
    sobre distancia de campo nao tem o mesmo peso de um montado sobre geometria.
    """
    d = linha.get("dist_ao_ap_dominante_m")
    if pd.notna(d) and d > 0:
        return float(d), "geometrica_3d"
    d = linha.get("dist_campo_m")
    if pd.notna(d) and d > 0:
        return float(d), "campo"
    return None, "indisponivel"


def montar_pares(df, predio, banda):
    """Todos os pares (mesmo grupo de BSSID, pavimentos diferentes) da combinacao."""
    sub = df[(df["predio"] == predio) & (df["banda"] == banda) &
             df["rssi_dbm"].notna() & df["grupo_ap"].notna()]

    linhas = []
    for grupo, g in sub.groupby("grupo_ap"):
        if g["pavimento"].nunique() < 2:
            continue
        registros = g.to_dict("records")
        for i in range(len(registros)):
            for j in range(i + 1, len(registros)):
                a, b = registros[i], registros[j]
                if a["pavimento"] == b["pavimento"]:
                    continue
                da, orig_a = _distancia_utilizavel(a)
                db, orig_b = _distancia_utilizavel(b)
                linhas.append({
                    "predio": predio, "banda": banda, "grupo_ap": grupo,
                    "ponto_a": a["ponto_id"], "pav_a": a["pavimento"],
                    "rssi_a": float(a["rssi_dbm"]), "dist_a_m": da, "origem_dist_a": orig_a,
                    "local_a": a["local"],
                    "ponto_b": b["ponto_id"], "pav_b": b["pavimento"],
                    "rssi_b": float(b["rssi_dbm"]), "dist_b_m": db, "origem_dist_b": orig_b,
                    "local_b": b["local"],
                    "delta_pavimentos": abs(int(a["pavimento"]) - int(b["pavimento"])),
                    "delta_rssi_db": round(abs(float(a["rssi_dbm"]) - float(b["rssi_dbm"])), 1),
                })
    return pd.DataFrame(linhas)


def estimar_perda_laje(df, config, predio, banda, modelo, n_minimo=None):
    """Perda por laje, em dB. Devolve (Resultado, DataFrame dos pares).

    ``modelo`` e o ``Resultado`` do ajuste de path loss que fornece o alpha. Sem
    alpha nao ha como separar o que e laje do que e distancia, e a funcao devolve
    "nao estimavel" em vez de atribuir toda a diferenca a laje.
    """
    n_minimo = n_minimo if n_minimo is not None else PARAMS["min_pares_laje"]
    pares = montar_pares(df, predio, banda)

    if pares.empty:
        return nao_estimavel(
            "nenhum par de leituras do mesmo AP fisico em pavimentos diferentes",
            n=0, predio=predio, banda=banda), pares

    if not modelo.ok:
        return nao_estimavel(
            "sem alpha valido para a combinacao (%s): a diferenca de RSSI nao "
            "pode ser separada em parcela de distancia e parcela de laje"
            % modelo.motivo, n=len(pares), predio=predio, banda=banda), pares

    alpha = modelo.valor
    perdas, utilizaveis = [], []
    for _, p in pares.iterrows():
        if p["dist_a_m"] is None or p["dist_b_m"] is None:
            perdas.append(np.nan); utilizaveis.append(False)
            continue
        # Perda esperada apenas pela mudanca de distancia, no sentido a -> b.
        prevista = 10.0 * alpha * np.log10(p["dist_b_m"] / p["dist_a_m"])
        observada = p["rssi_a"] - p["rssi_b"]
        perdas.append(round(float(observada - prevista), 1))
        utilizaveis.append(True)

    pares = pares.copy()
    pares["L_laje_db"] = perdas
    pares["utilizavel"] = utilizaveis
    pares["alpha_usado"] = round(alpha, 3)

    validos = pares[pares["utilizavel"] & pares["L_laje_db"].notna()]
    n = len(validos)

    if n < n_minimo:
        return nao_estimavel(
            "apenas %d par(es) utilizavel(is), minimo %d — um unico par nao "
            "sustenta estimativa de perda de laje" % (n, n_minimo),
            n=n, predio=predio, banda=banda, alpha_usado=alpha), pares

    valores = validos["L_laje_db"].to_numpy(float)
    mediana = float(np.median(valores))
    # IC da mediana por bootstrap percentil: amostra pequena demais para
    # aproximacao normal, e a mediana nao tem erro padrao fechado simples.
    rng = np.random.default_rng(12345)
    reamostras = rng.choice(valores, size=(2000, n), replace=True)
    medianas = np.median(reamostras, axis=1)
    ic = (float(np.percentile(medianas, 2.5)), float(np.percentile(medianas, 97.5)))

    extra = dict(predio=predio, banda=banda, alpha_usado=alpha,
                 pares=list(zip(validos["ponto_a"], validos["ponto_b"])),
                 valores_db=[float(v) for v in valores])

    if mediana <= 1.0:
        return Resultado(valor=mediana, ic=ic, n=n, status="inconsistente",
                         motivo=ALERTA_REFERENCIA_INSTAVEL, extra=extra), pares

    return Resultado(valor=mediana, ic=ic, n=n, status="estimado",
                     motivo="", extra=extra), pares


def rodar(df, config, modelos_por_combinacao):
    """Roda a estimativa para todas as combinacoes. Devolve (resumo, pares).

    ``modelos_por_combinacao`` mapeia (predio, banda) -> (nome_cenario, Resultado).
    """
    resumo, todos_pares = [], []
    for (predio, banda) in sorted({(p, b) for p, b in
                                   zip(df["predio"], df["banda"])}):
        cenario, modelo = modelos_por_combinacao.get((predio, banda), (None, None))
        if modelo is None:
            continue
        res, pares = estimar_perda_laje(df, config, predio, banda, modelo)
        linha = {"predio": predio, "banda": banda,
                 "cenario_alpha": cenario,
                 "alpha_usado": modelo.valor_significativo() if modelo.ok else None,
                 "L_laje_mediana_db": round(res.valor, 1) if res.valor is not None else None,
                 "ic95_inf": round(res.ic[0], 1) if res.ic else None,
                 "ic95_sup": round(res.ic[1], 1) if res.ic else None,
                 "n_pares": res.n, "status": res.status, "motivo": res.motivo}
        resumo.append(linha)
        if not pares.empty:
            todos_pares.append(pares)

    pares_df = pd.concat(todos_pares, ignore_index=True) if todos_pares else pd.DataFrame()
    return pd.DataFrame(resumo), pares_df
