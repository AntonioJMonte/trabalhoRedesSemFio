"""Geometria dos pontos de medicao e dos APs.

O modulo separa duas coisas que a campanha misturou:

- ``dist_campo_m``   — o que foi anotado em campo/planta;
- ``dist_calc_3d_m`` — o que a geometria declarada em ``config/predios.py`` diz.

As duas ficam lado a lado no DataFrame. A divergencia entre elas e **resultado a
ser reportado**, nao erro a ser silenciado: ela mede o quanto a distancia
anotada corresponde a um AP diferente do geometricamente mais proximo.
"""

import math
import re

import numpy as np
import pandas as pd

from config.predios import PARAMS

# "Abaixo do AP1", "Abaixo do AP 2 do 1o andar", "Sob o AP2" ...
_SOB_O_AP = re.compile(r"\b(?:abaixo|sob)\s+d[eo]s?\s+ap\s*(\d+)", re.IGNORECASE)


def distancia_3d(ponto, ap, pavimento_ap, pe_direito, pavimento_ponto=None, d0=None):
    """Distancia euclidiana 3D entre um ponto e um AP, em metros.

    ``sqrt(dx^2 + dy^2 + (dpav * pe_direito)^2)``, com piso em ``d0`` (1,0 m por
    padrao). O piso existe porque o modelo log-distancia e indefinido em d=0 e
    porque nenhuma medicao "sob o AP" esta de fato a zero metros: ha o pe
    direito entre a antena e o aparelho na mao de quem mede.

    ``ponto`` e ``ap`` sao mapeaveis com chaves ``x``/``y`` (ou ``x_m``/``y_m``).
    Devolve NaN quando qualquer coordenada esta ausente.
    """
    d0 = PARAMS["d0_m"] if d0 is None else d0

    def _xy(o):
        if o is None:
            return None, None
        x = o.get("x", o.get("x_m"))
        y = o.get("y", o.get("y_m"))
        return x, y

    px, py = _xy(ponto)
    ax, ay = _xy(ap)
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (px, py, ax, ay)):
        return float("nan")

    if pavimento_ponto is None:
        pavimento_ponto = ponto.get("pavimento")
    if pavimento_ponto is None or pavimento_ap is None:
        dz = 0.0
    else:
        dz = (int(pavimento_ap) - int(pavimento_ponto)) * float(pe_direito)

    d = math.sqrt((float(px) - float(ax)) ** 2 +
                  (float(py) - float(ay)) ** 2 +
                  dz ** 2)
    return max(d, float(d0))


def ap_mais_proximo(ponto, pavimento, config_predio):
    """Rotulo do AP do MESMO pavimento geometricamente mais proximo do ponto.

    Devolve None quando o ponto nao tem coordenadas. Nao inventa: sem x/y nao ha
    AP mais proximo, e a coluna fica vazia.
    """
    aps = (config_predio or {}).get("aps") or {}
    if not aps:
        return None
    pe = (config_predio or {}).get("pe_direito_m", 0.0)
    melhor, menor = None, float("inf")
    for nome, coord in aps.items():
        d = distancia_3d(ponto, coord, pavimento, pe, pavimento_ponto=pavimento)
        if d == d and d < menor:
            melhor, menor = nome, d
    return melhor


def resolver_coordenadas(df, config):
    """Preenche ``x_m``/``y_m`` onde o local de campo as determina sem ambiguidade.

    Uma leitura descrita como "Abaixo do AP2" esta, por definicao, na projecao
    vertical do AP2 — isso e leitura literal da anotacao, nao inferencia sobre
    posicao. A coluna ``origem_xy`` registra a procedencia de cada coordenada:

        "declarada"      — x/y vieram preenchidos no CSV
        "sob_ap"         — derivada do local "Abaixo do APn"
        "desconhecida"   — sem coordenada; toda geometria depende disso fica NaN

    Coordenadas derivadas NAO sao equivalentes a medidas e o relatorio de
    qualidade as reporta separadamente.
    """
    df = df.copy()
    origem = []
    xs, ys = [], []

    for _, r in df.iterrows():
        x, y = r.get("x_m"), r.get("y_m")
        if pd.notna(x) and pd.notna(y):
            xs.append(float(x)); ys.append(float(y)); origem.append("declarada")
            continue

        cfg = config.get(r["predio"]) or {}
        aps = cfg.get("aps") or {}
        m = _SOB_O_AP.search(str(r.get("local", "")))
        if m and aps:
            rotulo = f"AP{m.group(1)}"
            coord = aps.get(rotulo)
            if coord:
                xs.append(float(coord["x"])); ys.append(float(coord["y"]))
                origem.append("sob_ap")
                continue

        xs.append(np.nan); ys.append(np.nan); origem.append("desconhecida")

    df["x_m"] = xs
    df["y_m"] = ys
    df["origem_xy"] = origem
    return df


def resolver_distancias(df, config):
    """Acrescenta as colunas geometricas derivadas da configuracao dos predios.

    Colunas acrescentadas:
        ``x_m``/``y_m``/``origem_xy``  — ver resolver_coordenadas()
        ``ap_local``                   — AP do mesmo pavimento mais proximo
        ``dist_calc_2d_m``             — distancia 2D ao ``ap_local``
        ``dist_calc_3d_m``             — distancia 3D ao ``ap_local``
        ``ap_dominante``               — AP identificado pelo BSSID (se houver)
        ``delta_pavimento``            — pavimento(AP dominante) - pavimento(ponto)
        ``dist_ao_ap_dominante_m``     — distancia 3D ate o AP dominante
        ``divergencia_dist_m``         — |dist_campo_m - dist_calc_3d_m|
    """
    df = resolver_coordenadas(df, config)

    ap_local, d2d, d3d = [], [], []
    ap_dom, delta_pav, d_dom = [], [], []

    for _, r in df.iterrows():
        cfg = config.get(r["predio"]) or {}
        aps = cfg.get("aps") or {}
        pe = cfg.get("pe_direito_m", 0.0)
        pav = r.get("pavimento")
        pav = int(pav) if pd.notna(pav) else None
        ponto = {"x": r.get("x_m"), "y": r.get("y_m")}

        # --- AP local (mesmo pavimento) --------------------------------------
        nome = ap_mais_proximo(ponto, pav, cfg)
        ap_local.append(nome)
        if nome and pav is not None:
            coord = aps[nome]
            d3 = distancia_3d(ponto, coord, pav, pe, pavimento_ponto=pav)
            d2 = distancia_3d({"x": ponto["x"], "y": ponto["y"]}, coord, pav, pe,
                              pavimento_ponto=pav)
            d3d.append(d3); d2d.append(d2)
        else:
            d3d.append(np.nan); d2d.append(np.nan)

        # --- AP dominante (identificado pelo BSSID) --------------------------
        destino = None
        grupo = r.get("grupo_ap")
        if grupo is not None and isinstance(grupo, str):
            destino = (cfg.get("bssid_para_ap") or {}).get(grupo)

        if destino is None or pav is None:
            ap_dom.append(None); delta_pav.append(pd.NA); d_dom.append(np.nan)
            continue

        rotulo_dom = destino.get("ap")
        pav_dom = destino.get("pavimento")
        ap_dom.append(rotulo_dom)
        delta_pav.append(int(pav_dom) - pav if pav_dom is not None else pd.NA)

        coord = aps.get(rotulo_dom)
        if coord and pav_dom is not None:
            d_dom.append(distancia_3d(ponto, coord, pav_dom, pe, pavimento_ponto=pav))
        else:
            d_dom.append(np.nan)

    df["ap_local"] = ap_local
    df["dist_calc_2d_m"] = d2d
    df["dist_calc_3d_m"] = d3d
    df["ap_dominante"] = ap_dom
    df["delta_pavimento"] = pd.array(delta_pav, dtype="Int64")
    df["dist_ao_ap_dominante_m"] = d_dom

    df["divergencia_dist_m"] = (df["dist_campo_m"] - df["dist_calc_3d_m"]).abs()
    return df


def resumo_cobertura_geometrica(df):
    """Quantas leituras tem coordenada, por predio x procedencia. Para o relatorio."""
    if "origem_xy" not in df.columns:
        return pd.DataFrame()
    tab = (df.groupby(["predio", "origem_xy"], dropna=False)
             .size().rename("leituras").reset_index())
    return tab.sort_values(["predio", "origem_xy"]).reset_index(drop=True)
