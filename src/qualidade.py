"""Relatorio de qualidade dos dados — roda SEMPRE e PRIMEIRO.

A saida mais importante do projeto neste momento nao e um alpha: e a lista
objetiva do que precisa ser recoletado em campo. Este modulo produz
``saidas/relatorio_qualidade.md``, cuja tabela final declara, para cada analise
prevista, se ela e executavel ou o que exatamente a bloqueia.

Nenhuma exclusao do pipeline pode acontecer sem aparecer aqui.
"""

import numpy as np
import pandas as pd

from config.predios import AVISO_PCT_MELHOR_CANAL, DIR_SAIDA, PARAMS, ROTULO_PAVIMENTO
from src.bssid import HIPOTESE_TRANSCRICAO, detectar_bssids_suspeitos, grupos_candidatos

CAMINHO_RELATORIO = DIR_SAIDA / "relatorio_qualidade.md"


def _md(df, vazio="_(nenhum)_"):
    """DataFrame como tabela Markdown, ou um marcador quando vazio."""
    if df is None or len(df) == 0:
        return vazio
    return df.to_markdown(index=False)


def contagem_leituras(df):
    """1. Contagem de leituras por predio x pavimento x banda."""
    g = (df.groupby(["predio", "pavimento", "banda"], dropna=False)
           .size().rename("leituras").reset_index())
    g["pavimento"] = g["pavimento"].map(lambda p: ROTULO_PAVIMENTO.get(p, p))
    return g


def campos_ausentes(df):
    """2. Campos ausentes por coluna, com destaque para os criticos."""
    criticas = {"bssid_bruto", "altura_medicao_m", "x_m", "y_m"}
    linhas = []
    for col in df.columns:
        if col.startswith(("invalido_", "dist_nao_", "rssi_ausente", "apta_",
                           "valido", "excluida_", "sem_obstaculo", "ponto_id",
                           "obstaculo_recl", "dist_tem_")):
            continue
        serie = df[col]
        if serie.dtype == object:
            ausentes = int((serie.isna() | (serie.astype(str).str.strip() == "")).sum())
        else:
            ausentes = int(serie.isna().sum())
        if ausentes == 0:
            continue
        linhas.append({
            "coluna": col,
            "ausentes": ausentes,
            "total": len(df),
            "pct": round(100.0 * ausentes / len(df), 1),
            "critica": "SIM" if col in criticas else "",
        })
    t = pd.DataFrame(linhas)
    return t.sort_values(["critica", "ausentes"], ascending=[False, False]) if len(t) else t


def risco_circularidade(df):
    """3. Leituras cuja distancia nao foi medida — risco de circularidade."""
    sub = df[df["dist_origem"] != "medida"]
    if sub.empty:
        return pd.DataFrame(), 0
    g = (sub.groupby(["predio", "dist_origem"]).size()
           .rename("leituras").reset_index())
    n_circular = int((df["dist_origem"] == "estimada_app").sum())
    return g, n_circular


def rssi_ausente(df):
    """5. Leituras sem RSSI."""
    sub = df[df["rssi_dbm"].isna()]
    if sub.empty:
        return pd.DataFrame()
    return sub[["ponto_id", "predio", "pavimento", "banda", "local", "obs_campo"]]


def distancia_nao_positiva(df):
    """6. Leituras com dist_campo_m <= 0."""
    sub = df[df["dist_campo_m"].notna() & (df["dist_campo_m"] <= 0)]
    if sub.empty:
        return pd.DataFrame()
    return sub[["ponto_id", "predio", "pavimento", "banda", "dist_campo_m",
                "local", "obs_campo"]]


def divergencia_distancias(df, limite=None):
    """7. |dist_campo_m - dist_calc_3d_m| acima do limite, em ordem decrescente."""
    limite = limite if limite is not None else PARAMS["divergencia_distancia_m"]
    if "divergencia_dist_m" not in df.columns:
        return pd.DataFrame(), limite
    sub = df[df["divergencia_dist_m"].notna() & (df["divergencia_dist_m"] > limite)]
    if sub.empty:
        return pd.DataFrame(), limite
    cols = ["ponto_id", "predio", "pavimento", "banda", "dist_campo_m",
            "dist_calc_3d_m", "divergencia_dist_m", "origem_xy", "local"]
    return sub[cols].sort_values("divergencia_dist_m", ascending=False), limite


def distancias_com_dois_valores(df):
    """Leituras cuja anotacao de campo trouxe DUAS distancias.

    Nao esta na lista original das 7 verificacoes, mas e a divergencia de maior
    consequencia numerica encontrada: e a diferenca entre a distancia real e a
    distancia ate o AP dominante, e ela muda o alpha.
    """
    sub = df[df["dist_tem_dois_valores"]]
    if sub.empty:
        return pd.DataFrame()
    return sub[["ponto_id", "predio", "pavimento", "banda", "dist_campo_m",
                "dist_ap_conectado_m", "rssi_dbm", "local"]]


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 8. Tabela de executabilidade — a saida mais importante do relatorio
# -----------------------------------------------------------------------------
# A situacao de cada analise e decidida pelo RESULTADO que ela produziu, e nao
# apenas pela cobertura das colunas. Coluna parcialmente vazia nem sempre
# bloqueia: o ponto M-22 nao tem RSSI porque e uma zona cega, e essa ausencia e
# o proprio dado. Tres situacoes possiveis:
#
#   executavel              — produziu resultado em todas as combinacoes
#   executavel com ressalva — produziu em parte delas; o motivo diz onde faltou
#   bloqueada               — nao produziu nada; o motivo diz o que falta coletar

EXECUTAVEL = "executavel"
RESSALVA = "executavel com ressalva"
BLOQUEADA = "bloqueada"


def _situacao(n_ok, n_total):
    if n_total == 0 or n_ok == 0:
        return BLOQUEADA
    return EXECUTAVEL if n_ok == n_total else RESSALVA


def _sem_resultado(tab, coluna_status="status", ok="estimado"):
    """Rotulos 'predio banda' das linhas que nao produziram estimativa."""
    if tab is None or len(tab) == 0:
        return []
    ruins = tab[tab[coluna_status] != ok]
    return ["%s %s GHz" % (r.predio, r.banda) for r in ruins.itertuples()]


def _cobertura_parcial(df, coluna):
    """Texto 'predio: preenchidas/total' para as colunas incompletas."""
    if coluna not in df.columns:
        return "coluna ausente"
    serie = df[coluna]
    if serie.dtype == object:
        ok = serie.notna() & (serie.astype(str).str.strip() != "")
    else:
        ok = serie.notna()
    total = df.groupby("predio").size()
    cheio = df[ok].groupby("predio").size()
    partes = []
    for predio in sorted(total.index):
        tem = int(cheio.get(predio, 0))
        if tem < int(total[predio]):
            partes.append("%s: %d/%d" % (predio, tem, int(total[predio])))
    return ", ".join(partes) if partes else "completa"


def tabela_executabilidade(df, config, cenarios_df=None, laje_df=None,
                           heatmap_df=None, obstaculos_df=None, mismatch_df=None):
    """Para cada analise prevista: executavel, com ressalva, ou bloqueada."""
    linhas = []
    combos = df.groupby(["predio", "banda"]).ngroups

    def registrar(nome, situacao, motivo, falta):
        linhas.append({"analise": nome, "situacao": situacao,
                       "motivo": motivo, "o_que_falta_coletar": falta})

    # --- 1. path loss, cenario A --------------------------------------------
    if cenarios_df is not None and len(cenarios_df):
        a = cenarios_df[cenarios_df["cenario"] == "A"]
        ok = int((a["status"] == "estimado").sum())
        falhas = _sem_resultado(a)
        registrar("1. Path loss — cenario A (distancia de campo)",
                  _situacao(ok, len(a)),
                  "estimado em %d de %d combinacoes%s" % (
                      ok, len(a),
                      ("; sem estimativa em: " + ", ".join(falhas)) if falhas else ""),
                  "leituras sem obstaculo em distancias intermediarias (6, 10 e 15 m), "
                  "sobretudo em 5 GHz, onde ha apenas 2 distancias distintas")
    else:
        registrar("1. Path loss — cenario A (distancia de campo)", BLOQUEADA,
                  "cenarios nao executados", "dist_campo_m e rssi_dbm")

    # --- 2. path loss, cenarios B/D (dominancia de AP) ----------------------
    if cenarios_df is not None and len(cenarios_df):
        bd = cenarios_df[cenarios_df["cenario"].isin(["B", "D"])]
        ok = int((bd["status"] == "estimado").sum())
        sem_mapa = [p for p in sorted(df["predio"].unique())
                    if not (config.get(p) or {}).get("bssid_para_ap")]
        motivo = ("estimado em %d de %d combinacoes; cobertura de bssid_bruto "
                  "parcial (%s)" % (ok, len(bd), _cobertura_parcial(df, "bssid_bruto")))
        if sem_mapa:
            motivo += "; mapa de AP vazio em: %s" % ", ".join(sem_mapa)
        registrar("2. Path loss — cenarios B/D (dominancia de AP)",
                  _situacao(ok, len(bd)), motivo,
                  "BSSID em TODAS as leituras (faltam %d de %d) e confirmacao manual "
                  "dos grupos de AP dos predios sem mapa"
                  % (int(df["bssid"].isna().sum()), len(df)))

    # --- 3. path loss, cenarios C/D (geometria 3D) --------------------------
    if cenarios_df is not None and len(cenarios_df):
        cd = cenarios_df[cenarios_df["cenario"].isin(["C", "D"])]
        ok = int((cd["status"] == "estimado").sum())
        registrar("3. Path loss — cenarios C/D (geometria 3D)",
                  _situacao(ok, len(cd)),
                  "estimado em %d de %d combinacoes; x/y so sao conhecidos onde o "
                  "local e 'Abaixo do APn' (%s)"
                  % (ok, len(cd), _cobertura_parcial(df, "x_m")),
                  "x_m e y_m lidos em planta para TODOS os pontos (duas distancias "
                  "perpendiculares por ponto; precisao de +-0,5 m basta)")

    # --- 4. perda de laje ----------------------------------------------------
    if laje_df is not None and len(laje_df):
        ok = int((laje_df["status"] == "estimado").sum())
        detalhe = ", ".join("%s %s GHz: %d" % (r.predio, r.banda, r.n_pares)
                            for r in laje_df.itertuples())
        registrar("4. Perda de laje", _situacao(ok, len(laje_df)),
                  "minimo de %d pares utilizaveis por combinacao; obtido — %s"
                  % (PARAMS["min_pares_laje"], detalhe),
                  "BSSID em todas as leituras, para achar o mesmo AP fisico visto de "
                  "pavimentos diferentes; e x/y, para descontar a distancia")
    else:
        registrar("4. Perda de laje", BLOQUEADA, "nenhum par avaliado",
                  "BSSID em todas as leituras")

    # --- 5. atenuacao por obstaculo -----------------------------------------
    if obstaculos_df is not None and len(obstaculos_df):
        n_comb = obstaculos_df.groupby(["predio", "banda"]).ngroups
        incoerentes = int(obstaculos_df["incoerente"].sum())
        registrar("5. Atenuacao por obstaculo", _situacao(n_comb, combos),
                  "calculada em %d de %d combinacoes; %d ponto(s) com L <= 0, "
                  "sinalizados e nao recategorizados" % (n_comb, combos, incoerentes),
                  "alpha valido em 5 GHz — hoje sem alavanca em distancia — para "
                  "estender o calculo aquela banda")
    else:
        registrar("5. Atenuacao por obstaculo", BLOQUEADA,
                  "nenhum alpha valido disponivel", "alpha estimavel em alguma banda")

    # --- 6. canais -----------------------------------------------------------
    if mismatch_df is not None and len(mismatch_df):
        registrar("6. Canais (descasamento, reuso, qualidade)", EXECUTAVEL,
                  "descasamento calculado em %d grupos predio x banda x pavimento; "
                  "reuso identificavel apenas onde ha BSSID" % len(mismatch_df),
                  "definicao explicita da semantica de pct_melhor_canal; BSSID "
                  "completo para fechar o mapa de reuso de canal")
    else:
        registrar("6. Canais (descasamento, reuso, qualidade)", BLOQUEADA,
                  "sem colunas de canal", "canal_usado e canal_melhor")

    # --- 7. mapas de calor ---------------------------------------------------
    if heatmap_df is not None and len(heatmap_df):
        geradas = heatmap_df[heatmap_df["situacao"] == "gerada"]
        interpoladas = (int(geradas["motivo"].str.startswith("IDW").sum())
                        if len(geradas) else 0)
        registrar("7. Mapas de calor por pavimento",
                  _situacao(interpoladas, len(heatmap_df)),
                  "%d mapa(s) gerado(s), %d com superficie interpolada; os demais "
                  "saem como scatter porque ha menos de %d posicoes distintas com "
                  "coordenada" % (len(geradas), interpoladas,
                                  PARAMS["min_pontos_interpolacao"]),
                  "x/y de todos os pontos e as imagens de planta por pavimento")
    else:
        registrar("7. Mapas de calor por pavimento", BLOQUEADA,
                  "nenhum mapa gerado", "x_m, y_m e plantas")

    return pd.DataFrame(linhas)


def gerar_relatorio(df, config, cenarios_df=None, laje_df=None, heatmap_df=None,
                    obstaculos_df=None, mismatch_df=None, caminho=None):
    """Monta e grava ``saidas/relatorio_qualidade.md``. Devolve o texto."""
    caminho = caminho or CAMINHO_RELATORIO
    from datetime import datetime

    partes = []
    add = partes.append

    add("# Relatorio de qualidade dos dados\n")
    add("Gerado automaticamente em %s a partir de `dados/leituras.csv`.\n"
        % datetime.now().strftime("%d/%m/%Y %H:%M"))
    add("Este relatorio roda **antes** de qualquer analise. Nenhuma leitura e "
        "descartada pelo pipeline sem aparecer em alguma secao abaixo.\n")

    # --- 1 --------------------------------------------------------------------
    add("\n## 1. Contagem de leituras\n")
    add(_md(contagem_leituras(df)))
    add("\n**Total: %d leituras.**\n" % len(df))

    # --- 2 --------------------------------------------------------------------
    add("\n## 2. Campos ausentes por coluna\n")
    t = campos_ausentes(df)
    add(_md(t, "_(nenhuma coluna com valor ausente)_"))
    if len(t) and (t["critica"] == "SIM").any():
        add("\n> As colunas marcadas como criticas sustentam analises inteiras: "
            "`bssid_bruto` decide a dominancia de AP (cenarios B/D e perda de laje) "
            "e `x_m`/`y_m` decidem toda a geometria (cenarios C/D e mapas).\n")

    # --- 3 --------------------------------------------------------------------
    add("\n## 3. Origem da distancia — risco de circularidade\n")
    g, n_circular = risco_circularidade(df)
    add(_md(g, "_(todas as leituras tem dist_origem = 'medida')_"))
    if n_circular:
        add("\n> **%d leitura(s) com `dist_origem = 'estimada_app'`.** O aplicativo "
            "deriva essa distancia do proprio RSSI por um modelo de path loss "
            "interno. Entra-las na regressao recuperaria o alpha do aplicativo, nao "
            "o do predio. O pipeline as exclui automaticamente de toda regressao.\n"
            % n_circular)
    else:
        add("\n> **Nenhuma leitura com `dist_origem = 'estimada_app'`.** Nao ha risco "
            "de circularidade: a regressao nao recupera o modelo interno do "
            "aplicativo. As distancias declaradas como `planta` foram lidas do "
            "projeto arquitetonico, e sao independentes do RSSI medido.\n")

    # --- 4 --------------------------------------------------------------------
    add("\n## 4. BSSIDs suspeitos de erro de transcricao\n")
    sus = detectar_bssids_suspeitos(df, config)
    if len(sus):
        cols = ["predio", "bssid_a", "leituras_a", "bssid_b", "leituras_b",
                "hamming_nibbles", "octetos_divergentes", "hipotese", "bssid_anomalo"]
        add(_md(sus[cols]))
        erro = sus[sus["hipotese"] == HIPOTESE_TRANSCRICAO]
        add("\n> Sinalizado todo par com distancia de Hamming (em nibbles) <= %d "
            "que a regra de agrupamento do predio separa em APs distintos. "
            "**Apenas os %d par(es) classificados como erro de transcricao marcam a "
            "leitura como suspeita**; os demais indicam que a regra de agrupamento "
            "daquele predio precisa de revisao, nao que o dado esteja errado.\n"
            % (PARAMS["hamming_nibbles_suspeito"], len(erro)))
    else:
        add("_(nenhum par suspeito)_\n")

    # --- grupos candidatos, para os predios sem mapa ---------------------------
    for predio in sorted(df["predio"].unique()):
        if (config.get(predio) or {}).get("bssid_para_ap"):
            continue
        add("\n### Grupos candidatos de AP fisico — predio %s\n" % predio)
        add("O mapeamento `bssid_para_ap` deste predio esta vazio: a regra de "
            "agrupamento confirmada para outro predio **nao foi assumida aqui**. "
            "Confira os grupos abaixo e preencha `config/predios.py` manualmente.\n")
        add(_md(grupos_candidatos(df, predio, config)))

    # --- 5 --------------------------------------------------------------------
    add("\n## 5. Leituras sem RSSI\n")
    add(_md(rssi_ausente(df), "_(todas as leituras tem RSSI)_"))

    # --- 6 --------------------------------------------------------------------
    add("\n## 6. Leituras com distancia de campo <= 0\n")
    t6 = distancia_nao_positiva(df)
    add(_md(t6, "_(nenhuma)_"))
    if len(t6):
        add("\n> Anotadas em campo como 0 m (medicao diretamente sob o AP). "
            "`log10(0)` e indefinido, entao essas leituras **saem de toda "
            "regressao** — o pipeline nao as normaliza para d0 em silencio. "
            "Recoletar com a distancia horizontal real ao AP resolveria.\n")

    # --- 7 --------------------------------------------------------------------
    add("\n## 7. Divergencia entre distancia de campo e geometria 3D\n")
    t7, limite = divergencia_distancias(df)
    add("Limite de reporte: **%g m**.\n" % limite)
    add(_md(t7, "_(nenhuma divergencia acima do limite — ou geometria indisponivel)_"))

    add("\n### 7b. Leituras com DUAS distancias anotadas em campo\n")
    t7b = distancias_com_dois_valores(df)
    add(_md(t7b, "_(nenhuma)_"))
    if len(t7b):
        add("\n> A campanha anotou distancia real **e** distancia ao AP dominante. "
            "`dist_campo_m` recebe a real (lida da planta); a outra fica em "
            "`dist_ap_conectado_m`. A escolha muda o alpha de forma material e esta "
            "reportada na tabela comparativa de cenarios.\n")

    # --- 8 --------------------------------------------------------------------
    add("\n## 8. Executabilidade das analises\n")
    add("Esta e a lista objetiva do que precisa ser recoletado em campo.\n")
    add(_md(tabela_executabilidade(df, config, cenarios_df, laje_df, heatmap_df,
                                   obstaculos_df, mismatch_df)))

    add("\n---\n")
    add("\n## Avisos de semantica\n")
    add("- %s\n" % AVISO_PCT_MELHOR_CANAL)
    add("- Os BSSIDs identificam o **AP dominante** na varredura, nao o AP ao qual "
        "o cliente estava associado. Nenhuma conclusao sobre associacao de cliente "
        "pode ser tirada deste dado.\n")

    texto = "\n".join(partes)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return texto


CAMINHO_COORDENADAS = DIR_SAIDA / "coordenadas_a_levantar.csv"


def template_coordenadas(df, caminho=None):
    """Grava a lista de posicoes distintas que ainda nao tem x/y.

    Sai como CSV pronto para preencher em campo: uma linha por posicao fisica
    (nao por leitura), com as leituras que a compartilham e a distancia ja
    anotada, e as colunas x_m/y_m em branco. E a contrapartida acionavel do
    item 3 da tabela de executabilidade.
    """
    caminho = caminho or CAMINHO_COORDENADAS
    sem = df[df["x_m"].isna()]
    if sem.empty:
        return pd.DataFrame()

    t = (sem.groupby(["predio", "pavimento", "local"])
            .agg(leituras=("id", lambda s: ", ".join(str(int(v)) for v in sorted(s))),
                 dist_campo_m=("dist_campo_m",
                               lambda s: ", ".join("%g" % v for v in sorted(set(s.dropna())))))
            .reset_index())
    t["x_m"] = ""
    t["y_m"] = ""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(caminho, index=False, encoding="utf-8")
    return t
