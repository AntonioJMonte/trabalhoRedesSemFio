"""Utilitarios de figura: anotacao padrao, rodape e gravacao.

Toda figura do projeto passa por ``anotar_figura()``, que garante o mesmo
contrato em todas: caixa de texto com o que a figura mostra e com os parametros
do calculo, legenda realocada para nao cobrir dados, e rodape com n, data de
geracao e arquivo de origem.

A escolha do canto da caixa e automatica: o lado com menos dados desenhados.
"""

import textwrap
import unicodedata
from datetime import datetime

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from config.predios import DIR_FIG, PARAMS

matplotlib.rcParams["figure.dpi"] = 110
matplotlib.rcParams["savefig.dpi"] = 150
matplotlib.rcParams["font.size"] = 9
matplotlib.rcParams["axes.grid"] = True
matplotlib.rcParams["grid.alpha"] = 0.25

CARIMBO = datetime.now().strftime("%d/%m/%Y %H:%M")

# Registro global das figuras geradas nesta execucao.
FIGURAS_GERADAS = []


def _pontos_do_eixo(ax):
    """Coordenadas de todos os dados desenhados, em fração dos eixos."""
    pts = []
    for col in ax.collections:
        try:
            off = np.asarray(col.get_offsets(), float)
            if off.size:
                pts.append(off)
        except Exception:
            pass
    for ln in ax.lines:
        xd = np.asarray(ln.get_xdata(), float); yd = np.asarray(ln.get_ydata(), float)
        if xd.size and yd.size and xd.size == yd.size:
            pts.append(np.column_stack([xd, yd]))
    for p in ax.patches:  # barras
        try:
            bb = p.get_bbox()
            pts.append(np.array([[bb.x0, bb.y0], [bb.x1, bb.y1]]))
        except Exception:
            pass
    if not pts:
        return np.empty((0, 2))
    P = np.vstack(pts)
    P = P[np.isfinite(P).all(axis=1)]
    y0, y1 = ax.get_ylim()
    if y1 == y0 or P.size == 0:
        return np.empty((0, 2))
    v = (P[:, 1] - y0) / (y1 - y0)
    return v

def _dim_eixos_pts(ax):
    """Largura e altura dos eixos em pontos tipográficos."""
    larg_pol, alt_pol = ax.figure.get_size_inches()
    pos = ax.get_position()
    return pos.width * larg_pol * 72.0, pos.height * alt_pol * 72.0

def _quebrar(texto, largura_chars):
    """Reflui cada linha lógica respeitando as quebras já escritas no texto."""
    saida = []
    for linha in texto.split("\n"):
        if not linha.strip():
            saida.append("")
            continue
        partes = textwrap.wrap(linha, width=max(40, int(largura_chars)),
                               subsequent_indent="   ", break_long_words=False,
                               break_on_hyphens=False)
        saida.extend(partes or [""])
    return "\n".join(saida)

def _anotar_externa(ax, texto, rodape, fontsize):
    """Caixa abaixo dos eixos, com a figura crescendo para acomodá-la.

    Usado em mapas: com aspecto igual e barra de cores, reservar faixa DENTRO dos
    eixos distorceria a geometria da planta.
    """
    fig = ax.figure
    larg_pol, alt_pol = fig.get_size_inches()
    largura_chars = (larg_pol * 72.0 * 0.94) / (0.55 * fontsize)
    texto = _quebrar(texto, largura_chars)
    n_linhas = texto.count("\n") + 1

    alt_caixa_pol = (n_linhas * 1.28 * fontsize + 14.0) / 72.0
    folga = 0.18
    nova_alt = alt_pol + alt_caixa_pol + folga

    # preserva o tamanho absoluto dos eixos, acrescentando espaço embaixo
    for eixo in fig.axes:
        pos = eixo.get_position()
        eixo.set_position([
            pos.x0,
            (pos.y0 * alt_pol + alt_caixa_pol + folga) / nova_alt,
            pos.width,
            pos.height * alt_pol / nova_alt,
        ])
    fig.set_size_inches(larg_pol, nova_alt)

    fig.text(0.012, (alt_caixa_pol * 0.5 + folga * 0.55) / nova_alt, texto,
             fontsize=fontsize, ha="left", va="center", linespacing=1.28,
             family="DejaVu Sans",
             bbox=dict(boxstyle="round,pad=0.42", facecolor="#FFFFFF",
                       edgecolor="#8A8A8A", alpha=0.88, linewidth=0.6))
    if rodape:
        fig.text(0.005, 0.002, rodape, fontsize=6.2, color="#4A4A4A",
                 ha="left", va="bottom")
    return ax

def anotar_figura(ax, texto, rodape=None, loc=None, fontsize=7.2, legenda_fontsize=7.2,
                  modo="faixa"):
    """Aplica a anotação padrão da figura, garantindo que a caixa não cubra dados.

    modo='faixa'   : reserva uma FAIXA dentro dos eixos, expandindo o limite de y de
                     modo que a área ocupada pela caixa fique vazia. A legenda, quando
                     existe, é realocada para a faixa oposta.
    modo='externa' : coloca a caixa abaixo dos eixos, aumentando a figura. Indicado para
                     mapas, onde o aspecto igual não admite expansão dos limites.

    texto  : explicação do gráfico + parâmetros do cálculo + fonte dos dados
    rodape : data de geração, CSV de origem, método de interpolação
    loc    : força 'lower'/'upper'; None = escolhe a metade menos ocupada
    """
    if modo == "externa":
        return _anotar_externa(ax, texto, rodape, fontsize)

    larg_pts, alt_pts = _dim_eixos_pts(ax)
    largura_chars = (larg_pts - 16.0) / (0.55 * fontsize)
    texto = _quebrar(texto, largura_chars)

    n_linhas = texto.count("\n") + 1
    alt_caixa = (n_linhas * 1.28 * fontsize + 10.0) / alt_pts      # fração dos eixos

    # metade menos ocupada por dados decide o lado da caixa
    if loc is None:
        v = _pontos_do_eixo(ax)
        if v.size:
            lado = "lower" if (v < 0.5).sum() <= (v >= 0.5).sum() else "upper"
        else:
            lado = "lower"
    else:
        lado = "lower" if "lower" in loc else "upper"

    # legenda: vai para a faixa oposta, e também recebe reserva
    leg = ax.get_legend()
    alt_leg = 0.0
    if leg is not None:
        # recupera do próprio objeto de legenda, para preservar handles customizados
        handles = list(getattr(leg, "legend_handles", None) or
                       getattr(leg, "legendHandles", []) or [])
        labels = [t.get_text() for t in leg.get_texts()]
        if not handles or len(handles) != len(labels):
            handles, labels = ax.get_legend_handles_labels()
        if handles:
            n_ent = len(handles)
            # a legenda ocupa só o lado direito: reserva parcial basta
            alt_leg = 0.55 * (n_ent * 1.45 * legenda_fontsize + 12.0) / alt_pts
            lado_leg = "upper" if lado == "lower" else "lower"
            ax.legend(handles, labels, loc=f"{lado_leg} right",
                      fontsize=legenda_fontsize, framealpha=0.92)

    # reserva de espaço: expande o eixo y para que a faixa da caixa fique vazia
    fb = (alt_caixa if lado == "lower" else alt_leg) + 0.025
    ft = (alt_caixa if lado == "upper" else alt_leg) + 0.025
    fb, ft = min(fb, 0.45), min(ft, 0.45)
    y0, y1 = ax.get_ylim()
    faixa = y1 - y0
    nova = faixa / max(1.0 - fb - ft, 0.25)
    ax.set_ylim(y0 - nova * fb, y1 + nova * ft)

    py = 0.008 if lado == "lower" else 0.992
    va = "bottom" if lado == "lower" else "top"
    ax.text(0.008, py, texto, transform=ax.transAxes, fontsize=fontsize,
            ha="left", va=va, linespacing=1.28, zorder=20, family="DejaVu Sans",
            bbox=dict(boxstyle="round,pad=0.42", facecolor="#FFFFFF",
                      edgecolor="#8A8A8A", alpha=0.88, linewidth=0.6))
    if rodape:
        ax.figure.text(0.005, 0.002, rodape, fontsize=6.2, color="#4A4A4A",
                       ha="left", va="bottom")
    return ax


def salvar_fig(fig, metrica, predio, banda, pavimento="todos"):
    """Grava em PNG 150 dpi como fig_<metrica>_<predio>_<banda>_<pavimento>.png"""
    def _limpa(s):
        s = str(s).replace("º", "o").replace("ª", "a")
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s.replace(" ", "-").replace("/", "-").replace(",", ".")

    banda_txt = f"{banda}GHz" if not isinstance(banda, (int, float)) else f"{banda:g}GHz"
    nome = f"fig_{_limpa(metrica)}_{_limpa(predio)}_{_limpa(banda_txt)}_{_limpa(pavimento)}.png"
    fig.savefig(DIR_FIG / nome, dpi=150, bbox_inches="tight", facecolor="white")
    if nome not in FIGURAS_GERADAS:
        FIGURAS_GERADAS.append(nome)
    plt.close(fig)
    return nome


def rodape_padrao(n, extra=""):
    """Rodape: data de geracao + n + origem dos dados."""
    partes = [f"Gerado em {CARIMBO}", f"n = {n}", "fonte: dados/leituras.csv"]
    if extra:
        partes.append(extra)
    return "  |  ".join(partes)


def caixa_parametros(**kwargs):
    """Linha de PARAMETROS para a caixa de texto, a partir de pares nome=valor."""
    itens = [f"{k.replace('_', ' ')} = {v}" for k, v in kwargs.items() if v is not None]
    return "PARAMETROS: " + " · ".join(itens) if itens else ""
