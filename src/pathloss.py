"""Ajuste do modelo log-distancia e atenuacao por obstaculos.

Modelo: RSSI(d) = RSSI(d0) - 10*alpha*log10(d/d0) - L_obstaculo

Duas decisoes de rigor governam este modulo:

1. **alpha e reportado com 2 algarismos significativos.** A amostra e de leitura
   unica por ponto, a distancia foi anotada com "~" na origem e o RSSI 802.11
   varia +-5 a 10 dB por fast fading. Precisao maior seria falsa.
2. **Abaixo de PARAMS["min_pontos_ajuste"] nao sai numero**, sai
   Resultado(status="nao estimavel") com o motivo escrito.
"""

import numpy as np
import pandas as pd
from scipy import stats

from config.predios import PARAMS
from src.resultado import Resultado, arredondar_significativos, nao_estimavel

# -----------------------------------------------------------------------------
# Os 4 cenarios da Parte 5.1. Cada um declara a coluna de distancia e o filtro.
# -----------------------------------------------------------------------------
CENARIOS = {
    "A": {
        "distancia": "dist_campo_m",
        "filtro": "sem_estimada_app",
        "descricao": "distancia de campo; todos exceto dist_origem estimada_app",
    },
    "B": {
        "distancia": "dist_campo_m",
        "filtro": "dominancia_local",
        "descricao": "distancia de campo; apenas dominancia local",
    },
    "C": {
        "distancia": "dist_calc_3d_m",
        "filtro": "sem_estimada_app",
        "descricao": "distancia geometrica 3D; todos exceto estimada_app",
    },
    "D": {
        "distancia": "dist_calc_3d_m",
        "filtro": "dominancia_local",
        "descricao": "distancia geometrica 3D; apenas dominancia local",
    },
}

# Cenario adicional, fora da grade A-D: reproduz exatamente o conjunto usado nas
# execucoes anteriores do projeto, para a verificacao de regressao da Parte 5.3.
CENARIO_HISTORICO = {
    "H": {
        "distancia": "dist_historica_m",
        "filtro": "sem_estimada_app",
        "descricao": ("distancia como gravada no CSV antigo (ao AP dominante, onde "
                      "a campanha anotou dois valores); usado apenas para verificar "
                      "que o parsing reproduz os numeros ja validados"),
    },
}

# Diagnostico: 'local' mais as leituras sem BSSID. Existe porque o filtro estrito
# dos cenarios B e D descarta toda leitura sem BSSID, e a cobertura de BSSID
# desta campanha e parcial — sem esta linha, B e D ficariam sem interpretacao.
CENARIO_DIAGNOSTICO = {
    "B+": {
        "distancia": "dist_campo_m",
        "filtro": "local_ou_sem_dado",
        "descricao": "distancia de campo; dominancia local OU sem_dado (diagnostico)",
    },
}


def aplicar_filtro(df, filtro):
    """Aplica o filtro nomeado do cenario e devolve (subconjunto, descartados).

    Devolve os descartados junto porque nenhuma exclusao pode ser silenciosa:
    quem chama repassa a lista ao relatorio de qualidade.
    """
    # Gate de validade, comum a TODOS os cenarios: alem de apta_regressao e de
    # estar sem obstaculo, a leitura nao pode ter AP dominante comprovadamente
    # nao-local (ver PARAMS["dominancias_excluidas_sempre"]). Esta e a unica
    # exclusao permitida na regressao local, e ela substitui integralmente a
    # antiga lista de pontos excluidos por ID.
    base = df[df["apta_regressao"] & df["sem_obstaculo"] &
              ~df["dominancia"].isin(PARAMS["dominancias_excluidas_sempre"])]
    fora = df.loc[~df.index.isin(base.index)]

    if filtro == "sem_estimada_app":
        return base, fora
    if filtro == "dominancia_local":
        dentro = base[base["dominancia"] == "local"]
    elif filtro == "local_ou_sem_dado":
        dentro = base[base["dominancia"].isin(["local", "sem_dado"])]
    else:
        raise ValueError(f"filtro desconhecido: {filtro}")
    return dentro, pd.concat([fora, base.loc[~base.index.isin(dentro.index)]])


def ajustar(sub, coluna_distancia, d0=None, rotulo=""):
    """Regressao linear de RSSI contra 10*log10(d/d0). Devolve um Resultado.

    Resultado.valor e o alpha; Resultado.ic e o IC 95% do alpha, obtido do erro
    padrao da inclinacao com distribuicao t de Student e n-2 graus de liberdade.
    O campo extra traz r2, rmse, rssi_d0 e a lista de pontos usados.
    """
    d0 = PARAMS["d0_m"] if d0 is None else d0
    if sub is None or len(sub) == 0:
        return nao_estimavel("nenhuma leitura no conjunto", n=0, rotulo=rotulo,
                             coluna_distancia=coluna_distancia)

    val = sub[sub[coluna_distancia].notna() & sub["rssi_dbm"].notna()]
    val = val[val[coluna_distancia] > 0]
    n = len(val)
    pontos = list(val["ponto_id"]) if n else []
    comum = dict(rotulo=rotulo, coluna_distancia=coluna_distancia, d0=d0, pontos=pontos)

    if n < PARAMS["min_pontos_ajuste"]:
        return nao_estimavel(
            "amostra insuficiente: n = %d, minimo %d" % (n, PARAMS["min_pontos_ajuste"]),
            n=n, **comum)

    n_dist = val[coluna_distancia].nunique()
    comum["n_distancias"] = n_dist
    if n_dist < PARAMS["min_distancias_distintas"]:
        return nao_estimavel(
            "amostra concentrada: apenas %d distancia(s) distinta(s), minimo %d — "
            "sem alavanca em distancia, alpha descreve a dispersao da amostra, "
            "nao a perda de percurso" % (n_dist, PARAMS["min_distancias_distintas"]),
            n=n, **comum)

    X = 10.0 * np.log10(val[coluna_distancia].to_numpy(float) / d0)
    Y = val["rssi_dbm"].to_numpy(float)

    inclinacao, intercepto, r, _, se_inclinacao = stats.linregress(X, Y)
    alpha = -inclinacao
    r2 = float(r) ** 2
    residuos = Y - (intercepto + inclinacao * X)
    rmse = float(np.sqrt((residuos ** 2).mean()))

    t = stats.t.ppf(0.5 + PARAMS["ic_confianca"] / 2.0, n - 2)
    ic = (float(alpha - t * se_inclinacao), float(alpha + t * se_inclinacao))

    comum.update(r2=round(r2, 4), rmse=round(rmse, 2),
                 rssi_d0_dbm=round(float(intercepto), 2),
                 erro_padrao_alpha=round(float(se_inclinacao), 4))

    if alpha < 0:
        return Resultado(
            valor=float(alpha), ic=ic, n=n, status="inconsistente",
            motivo=("alpha negativo — implicaria sinal crescendo com a distancia, "
                    "sem significado fisico; nao usar como estimativa"),
            extra=comum)

    if r2 < PARAMS["r2_minimo_confiavel"]:
        return Resultado(
            valor=float(alpha), ic=ic, n=n, status="inconsistente",
            motivo=("ajuste nao confiavel: R2 = %.2f, abaixo do minimo %.2f — a "
                    "distancia explica apenas %.0f%% da variacao do RSSI"
                    % (r2, PARAMS["r2_minimo_confiavel"], 100 * r2)),
            extra=comum)

    return Resultado(valor=float(alpha), ic=ic, n=n, status="estimado",
                     motivo="", extra=comum)


def ajuste_do_guia(sub, coluna_distancia="dist_campo_m"):
    """Metodo do guia da disciplina: polyfit com d0 = menor distancia observada.

    Mantido em paralelo ao metodo rigoroso apenas para comparacao — usa TODOS os
    pontos, sem as guardas de suficiencia amostral.
    """
    val = sub[sub[coluna_distancia].notna() & sub["rssi_dbm"].notna()]
    val = val[val[coluna_distancia] > 0]
    if len(val) < 2 or val[coluna_distancia].nunique() < 2:
        return nao_estimavel("dados insuficientes para o metodo do guia", n=len(val))

    d0 = float(val[coluna_distancia].min())
    X = 10.0 * np.log10(val[coluna_distancia].to_numpy(float) / d0)
    Y = val["rssi_dbm"].to_numpy(float)
    inclinacao, intercepto = np.polyfit(X, Y, 1)
    Yhat = intercepto + inclinacao * X
    ss_res = float(((Y - Yhat) ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return Resultado(
        valor=float(-inclinacao), ic=None, n=len(val), status="estimado",
        motivo="", extra=dict(metodo="guia da disciplina (polyfit, d0 = menor d)",
                              d0=d0, r2=round(r2, 4),
                              rssi_d0_dbm=round(float(intercepto), 2),
                              coluna_distancia=coluna_distancia))


def rodar_cenarios(df, cenarios=None):
    """Roda os cenarios para cada (predio x banda). Devolve DataFrame longo."""
    cenarios = cenarios or CENARIOS
    linhas = []
    for (predio, banda), sub in df.groupby(["predio", "banda"], sort=True):
        for nome, spec in cenarios.items():
            dentro, _fora = aplicar_filtro(sub, spec["filtro"])
            res = ajustar(dentro, spec["distancia"],
                          rotulo="%s %s GHz — cenario %s" % (predio, banda, nome))
            e = res.extra
            linhas.append({
                "predio": predio, "banda": banda, "cenario": nome,
                "descricao": spec["descricao"],
                "coluna_distancia": spec["distancia"],
                "alpha": res.valor_significativo(),
                "ic95_inf": arredondar_significativos(res.ic[0], 3) if res.ic else None,
                "ic95_sup": arredondar_significativos(res.ic[1], 3) if res.ic else None,
                "r2": e.get("r2"), "n": res.n, "rmse_db": e.get("rmse"),
                "rssi_d0_dbm": e.get("rssi_d0_dbm"),
                "n_distancias": e.get("n_distancias"),
                "status": res.status, "motivo": res.motivo,
                "pontos": ", ".join(e.get("pontos", [])),
            })
    return pd.DataFrame(linhas)


def modelo_de_referencia(df, predio, banda, cenario="D", cenarios=None):
    """O Resultado do cenario indicado, para uso por outros modulos.

    A perda de laje e a atenuacao por obstaculo precisam de um alpha; qual
    cenario alimenta cada uma e decisao declarada, nunca implicita.
    """
    cenarios = cenarios or CENARIOS
    spec = cenarios[cenario]
    sub = df[(df["predio"] == predio) & (df["banda"] == banda)]
    dentro, _ = aplicar_filtro(sub, spec["filtro"])
    return ajustar(dentro, spec["distancia"],
                   rotulo="%s %s GHz — cenario %s" % (predio, banda, cenario))


def melhor_modelo_disponivel(df, predio, banda, ordem=("D", "C", "B", "A")):
    """Primeiro cenario da ordem de preferencia que produziu estimativa valida.

    A ordem existe porque os modulos que consomem um alpha (laje, obstaculos)
    precisam de UM modelo, e a preferencia — geometria 3D e dominancia local
    antes de distancia de campo e amostra completa — e decisao metodologica que
    fica escrita aqui, nao espalhada por quem chama.

    Devolve (cenario, Resultado). Se nenhum cenario estimar, devolve o ultimo
    tentado, com seu motivo preservado.
    """
    ultimo = (None, nao_estimavel("nenhum cenario avaliado"))
    for nome in ordem:
        res = modelo_de_referencia(df, predio, banda, cenario=nome)
        ultimo = (nome, res)
        if res.ok:
            return nome, res
    return ultimo


def atenuacao_por_obstaculo(df, modelo, predio, banda, coluna_distancia="dist_campo_m"):
    """L_obstaculo = RSSI_previsto - RSSI_medido, para as leituras obstruidas.

    L <= 0 significa que um ponto declarado obstruido mediu sinal igual ou melhor
    que o previsto. Isso e incoerente com haver barreira no caminho do enlace, e
    o caso mais comum e de ANOTACAO (obstaculo no entorno do ponto, e nao
    interposto entre o ponto e o AP). Este modulo SINALIZA; recategorizar e
    decisao de quem leu as anotacoes de campo.
    """
    if not modelo.ok:
        return pd.DataFrame()

    alpha = modelo.valor
    rssi_d0 = modelo.extra["rssi_d0_dbm"]
    d0 = modelo.extra["d0"]

    sub = df[(df["predio"] == predio) & (df["banda"] == banda) &
             ~df["sem_obstaculo"] & df["rssi_dbm"].notna() &
             df[coluna_distancia].notna() & (df[coluna_distancia] > 0)]

    linhas = []
    for _, r in sub.iterrows():
        previsto = rssi_d0 - 10.0 * alpha * np.log10(r[coluna_distancia] / d0)
        perda = float(previsto - r["rssi_dbm"])
        linhas.append({
            "predio": predio, "banda": banda, "ponto_id": r["ponto_id"],
            "pavimento": r["pavimento"], "local": r["local"],
            "obstaculos": r["obstaculos"], "dist_m": float(r[coluna_distancia]),
            "rssi_previsto_dbm": round(float(previsto), 1),
            "rssi_medido_dbm": float(r["rssi_dbm"]),
            "L_obstaculo_db": round(perda, 1),
            "incoerente": perda <= 0,
        })
    if not linhas:
        return pd.DataFrame()
    return pd.DataFrame(linhas).sort_values("L_obstaculo_db", ascending=False)
