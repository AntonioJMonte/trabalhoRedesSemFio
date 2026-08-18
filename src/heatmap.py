"""Mapas de cobertura por pavimento, em metros, com a planta ao fundo.

DECISAO DE INTERPOLACAO, deliberada: com 4 a 6 pontos por pavimento nao se
constroi superficie continua honesta. Krigagem e contornos suaves a partir de 5
amostras sao ficcao visual — desenham confianca que o dado nao tem. Por isso:

- interpolacao por IDW com raio maximo (PARAMS["idw_raio_max_m"]);
- fora do raio, celula vazia — nunca extrapolacao ate a borda da planta;
- abaixo de PARAMS["min_pontos_interpolacao"] posicoes, apenas scatter, com a
  limitacao escrita no rodape da figura.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from config.predios import DIR_QGIS, PARAMS, ROTULO_PAVIMENTO
from src.viz import anotar_figura, caixa_parametros, rodape_padrao, salvar_fig

try:
    import rasterio
    from rasterio.transform import from_origin
    TEM_RASTERIO = True
except ImportError:
    TEM_RASTERIO = False


def malha(extensao_m, n=None):
    """Grade regular cobrindo a envoltoria do pavimento."""
    n = n or PARAMS["resolucao_malha"]
    largura, altura = extensao_m
    gx = np.linspace(0.0, largura, n)
    gy = np.linspace(0.0, altura, n)
    return np.meshgrid(gx, gy)


def idw(pontos_xy, valores, GX, GY, potencia=None, raio_max=None):
    """Inverse Distance Weighting com raio maximo.

    Celulas sem nenhuma amostra dentro do raio ficam NaN: o mapa mostra
    explicitamente onde a amostragem nao alcanca, em vez de preencher.
    """
    potencia = potencia if potencia is not None else PARAMS["idw_potencia"]
    raio_max = raio_max if raio_max is not None else PARAMS["idw_raio_max_m"]

    pts = np.asarray(pontos_xy, float)
    val = np.asarray(valores, float)
    forma = GX.shape
    destino = np.column_stack([GX.ravel(), GY.ravel()])

    d = np.sqrt(((destino[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2))
    dentro = d <= raio_max

    d = np.where(d < 1e-9, 1e-9, d)
    peso = np.where(dentro, d ** (-potencia), 0.0)
    soma = peso.sum(axis=1)

    z = np.full(destino.shape[0], np.nan)
    ok = soma > 0
    z[ok] = (peso[ok] * val[None, :]).sum(axis=1) / soma[ok]

    # coincidencia exata com uma amostra: usa o valor medido
    for i, j in np.argwhere(d < 1e-6):
        z[i] = val[j]
    return z.reshape(forma)


def pontos_do_pavimento(df, predio, pavimento, banda, metrica="rssi_dbm"):
    """Leituras com coordenada conhecida na combinacao pedida."""
    return df[(df["predio"] == predio) & (df["pavimento"] == pavimento) &
              (df["banda"] == banda) & df[metrica].notna() &
              df["x_m"].notna() & df["y_m"].notna()]


def exportar_geotiff(Z, extensao_m, nome):
    """Grava o raster com o mesmo extent do mapa, para sobrepor no QGIS."""
    if not TEM_RASTERIO:
        return None
    largura, altura = extensao_m
    n_y, n_x = Z.shape
    transform = from_origin(0.0, altura, largura / n_x, altura / n_y)
    caminho = DIR_QGIS / (nome + ".tif")
    with rasterio.open(caminho, "w", driver="GTiff", height=n_y, width=n_x,
                       count=1, dtype="float32", crs=None, transform=transform,
                       nodata=np.nan) as dst:
        dst.write(np.flipud(Z).astype("float32"), 1)
    return caminho.name


def figura_pavimento(df, predio, pavimento, banda, config, metrica="rssi_dbm",
                     rotulo_metrica="RSSI", unidade="dBm"):
    """Mapa de um (predio x pavimento x banda). Devolve (nome_figura, nota)."""
    cfg = config[predio]
    extensao = cfg["extensao_m"]
    sub = pontos_do_pavimento(df, predio, pavimento, banda, metrica)
    n = len(sub)
    if n == 0:
        return None, "sem leituras com coordenada neste pavimento/banda"

    xs = sub["x_m"].to_numpy(float)
    ys = sub["y_m"].to_numpy(float)
    vs = sub[metrica].to_numpy(float)
    n_posicoes = len({(round(a, 2), round(b, 2)) for a, b in zip(xs, ys)})

    fig, ax = plt.subplots(figsize=(8.6, 6.2))

    # --- planta ao fundo -----------------------------------------------------
    planta = (cfg.get("plantas") or {}).get(pavimento)
    tem_planta = False
    if planta is not None:
        try:
            img = mpimg.imread(str(planta))
            ax.imshow(img, extent=(0, extensao[0], 0, extensao[1]),
                      alpha=0.35, aspect="equal", zorder=0)
            tem_planta = True
        except (FileNotFoundError, OSError):
            tem_planta = False

    # --- superficie, so quando a amostragem a sustenta -----------------------
    interpolou = False
    minimo = PARAMS["min_pontos_interpolacao"]
    if n_posicoes >= minimo:
        GX, GY = malha(extensao)
        Z = idw(np.column_stack([xs, ys]), vs, GX, GY)
        im = ax.imshow(Z, extent=(0, extensao[0], 0, extensao[1]), origin="lower",
                       cmap="RdYlGn", alpha=0.75, aspect="equal", zorder=1)
        fig.colorbar(im, ax=ax, label=rotulo_metrica + " (" + unidade + ")", shrink=0.82)
        interpolou = True
        nota_metodo = ("IDW potencia %g, raio maximo %g m; celulas fora do raio "
                       "ficam vazias" % (PARAMS["idw_potencia"], PARAMS["idw_raio_max_m"]))
        exportar_geotiff(Z, extensao, "raster_%s_%s_pav%s_%sGHz"
                         % (metrica, predio, pavimento, banda))
    else:
        nota_metodo = ("APENAS SCATTER: %d posicao(oes) distinta(s), abaixo do minimo "
                       "%d para interpolar. Superficie continua a partir desta amostra "
                       "seria ficcao visual." % (n_posicoes, minimo))

    sc = ax.scatter(xs, ys, c=vs, s=150, cmap="RdYlGn", edgecolors="black",
                    linewidths=0.9, zorder=4)
    if not interpolou:
        fig.colorbar(sc, ax=ax, label=rotulo_metrica + " (" + unidade + ")", shrink=0.82)
    for _, r in sub.iterrows():
        ax.annotate(r["ponto_id"], (r["x_m"], r["y_m"]), fontsize=6.4,
                    xytext=(5, 5), textcoords="offset points", zorder=5)

    # --- APs nas coordenadas reais ------------------------------------------
    for nome_ap, coord in (cfg.get("aps") or {}).items():
        ax.plot(coord["x"], coord["y"], marker="^", markersize=13,
                color="#1565c0", markeredgecolor="white", markeredgewidth=1.2,
                zorder=6, linestyle="none")
        ax.annotate(nome_ap, (coord["x"], coord["y"]), fontsize=8, fontweight="bold",
                    color="#0d47a1", xytext=(7, -12), textcoords="offset points",
                    zorder=6)

    ax.set_xlim(0, extensao[0])
    ax.set_ylim(0, extensao[1])
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("%s — Predio %s · %s · %s GHz"
                 % (rotulo_metrica, predio,
                    ROTULO_PAVIMENTO.get(pavimento, pavimento), banda), fontsize=11)

    texto = (
        "O QUE MOSTRA: %s medido nos pontos com coordenada conhecida do pavimento, "
        "sobre a envoltoria real de %g x %g m.\n%s\n"
        "LIMITACAO: %d leitura(s) em %d posicao(oes); amostra unica por ponto, sem "
        "repeticao nem media."
        % (rotulo_metrica.lower(), extensao[0], extensao[1],
           caixa_parametros(metodo=nota_metodo,
                            planta=("sim" if tem_planta else "indisponivel"),
                            origem=cfg.get("origem")),
           n, n_posicoes))
    anotar_figura(ax, texto, rodape=rodape_padrao(n), modo="externa")
    nome = salvar_fig(fig, metrica, predio, banda, pavimento="pav%s" % pavimento)
    return nome, nota_metodo


def rodar(df, config, metrica="rssi_dbm", rotulo_metrica="RSSI", unidade="dBm"):
    """Gera um mapa por (predio x pavimento x banda). Devolve o log do que saiu."""
    linhas = []
    for predio, cfg in config.items():
        for pavimento in cfg.get("pavimentos", []):
            for banda in sorted(df["banda"].dropna().unique()):
                sub = pontos_do_pavimento(df, predio, pavimento, banda, metrica)
                if sub.empty:
                    linhas.append({"predio": predio, "pavimento": pavimento,
                                   "banda": banda, "figura": None, "n": 0,
                                   "situacao": "bloqueada",
                                   "motivo": "nenhuma leitura com x/y neste pavimento"})
                    continue
                nome, nota = figura_pavimento(df, predio, pavimento, banda, config,
                                              metrica, rotulo_metrica, unidade)
                linhas.append({"predio": predio, "pavimento": pavimento,
                               "banda": banda, "figura": nome, "n": len(sub),
                               "situacao": "gerada", "motivo": nota})
    return pd.DataFrame(linhas)
