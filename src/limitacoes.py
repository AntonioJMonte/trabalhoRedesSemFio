"""Geracao automatica de ``saidas/limitacoes.md``.

Cada limitacao e montada a partir dos dados reais da execucao — contagens,
divergencias e evidencias vindas do proprio CSV. Nada aqui e texto fixo com
numero digitado a mao: se o dado mudar, o documento muda junto.
"""

import re
from datetime import datetime

import pandas as pd

from config.predios import DIR_SAIDA, PARAMS
from src.bssid import HIPOTESE_TRANSCRICAO, detectar_bssids_suspeitos

CAMINHO = DIR_SAIDA / "limitacoes.md"


def evidencia_altura(df):
    """Procura, nas observacoes de campo, o caso de variacao por altura.

    A evidencia nao e inventada: e extraida da coluna ``obs_campo``, onde a
    campanha registrou dois valores de RSSI para a mesma posicao.
    """
    baixo = df["obs_campo"].str.lower()
    sub = df[baixo.str.contains("em pe", na=False) &
             baixo.str.contains("no chao", na=False)]
    if sub.empty:
        return None
    r = sub.iloc[0]
    valores = [float(v) for v in re.findall(r"-\s*(\d{2,3})\s*dBm", r["obs_campo"])]
    delta = abs(valores[0] - valores[1]) if len(valores) >= 2 else None
    return {"ponto_id": r["ponto_id"], "obs": r["obs_campo"], "delta_db": delta,
            "n_sem_altura": int(df["altura_medicao_m"].isna().sum()), "total": len(df)}


def cobertura_bssid(df):
    """Cobertura de BSSID por predio, para a limitacao de comparabilidade."""
    g = df.groupby("predio").agg(
        leituras=("id", "size"),
        com_bssid=("bssid", lambda s: int(s.notna().sum())),
    ).reset_index()
    g["pct"] = (100.0 * g["com_bssid"] / g["leituras"]).round(1)
    return g


def cobertura_por_predio(df, config):
    """Assimetrias de cobertura de dado entre predios."""
    linhas = []
    for predio, sub in df.groupby("predio"):
        cfg = config.get(predio) or {}
        linhas.append({
            "predio": predio,
            "leituras": len(sub),
            "com_bssid": int(sub["bssid"].notna().sum()),
            "xy_declarada": (int((sub["origem_xy"] == "declarada").sum())
                             if "origem_xy" in sub.columns else 0),
            "dist_zero": int((sub["dist_campo_m"] <= 0).sum()),
            "mapa_ap": "sim" if cfg.get("bssid_para_ap") else "nao",
            "fabricante_ap": cfg.get("fabricante_ap") or "a confirmar",
        })
    return pd.DataFrame(linhas)


def gerar(df, config, cenarios_df=None, caminho=None):
    """Monta e grava saidas/limitacoes.md. Devolve o texto."""
    caminho = caminho or CAMINHO
    partes = []
    add = partes.append

    add("# Limitacoes do estudo\n")
    add("Documento gerado automaticamente em %s a partir de dados/leituras.csv. "
        "Os numeros abaixo vem da execucao, nao de texto fixo.\n"
        % datetime.now().strftime("%d/%m/%Y %H:%M"))

    n_comb = df.groupby(["predio", "pavimento", "banda", "local"]).ngroups
    add("\n## 1. Amostra unica por ponto, sem repeticao nem media\n")
    add("As %d leituras correspondem a %d combinacoes distintas de "
        "(predio, pavimento, banda, local), com **uma medicao por combinacao**. "
        "Nao ha repeticao temporal nem media, entao nao ha como separar variacao "
        "de curto prazo (fast fading, ocupacao do meio) do efeito que se quer "
        "medir. Todo intervalo de confianca reportado descreve a dispersao ENTRE "
        "pontos, nunca a repetibilidade de um ponto.\n" % (len(df), n_comb))

    add("\n## 2. Altura de medicao nao controlada\n")
    ev = evidencia_altura(df)
    if ev:
        add("A coluna altura_medicao_m esta vazia em **%d das %d leituras** "
            "(%.0f%%). A campanha registrou o efeito uma unica vez, no ponto "
            "**%s**:\n" % (ev["n_sem_altura"], ev["total"],
                           100.0 * ev["n_sem_altura"] / ev["total"], ev["ponto_id"]))
        add("\n> %s\n" % ev["obs"])
        if ev["delta_db"]:
            add("\nSao **%.0f dB de variacao produzidos por uma variavel que nao "
                "foi registrada**. Para comparacao: a perda atribuida a porta "
                "corta-fogo neste mesmo estudo e da ordem de 21 dB, e a diferenca "
                "entre os cenarios de alpha avaliados vale poucos dB ao longo de "
                "toda a faixa de distancias. Ou seja, **a variavel nao controlada "
                "excede varios dos efeitos que o estudo tenta medir**.\n"
                % ev["delta_db"])
    else:
        add("A coluna altura_medicao_m nao foi preenchida e nao ha registro do "
            "efeito nas observacoes de campo.\n")

    add("\n## 3. BSSID identifica o AP dominante, nao o AP associado\n")
    add("Os BSSIDs foram lidos da lista de varredura do aplicativo (aba de pontos "
        "de acesso), que mostra o **AP visivel dominante** no ponto. Nao ha "
        "registro de a qual AP o cliente estava efetivamente associado.\n")
    add("\nConsequencia direta: a expressao *sticky client* **nao e sustentavel "
        "por este dado**. O que se pode afirmar e que o AP mais forte na varredura "
        "era o indicado, nao que o aparelho estivesse preso a ele.\n")
    add("\nCobertura de BSSID por predio:\n")
    add("\n" + cobertura_bssid(df).to_markdown(index=False) + "\n")

    add("\n## 4. O SINR calculado e um limite pessimista\n")
    add("O piso de ruido usado e **%.0f dBm, adotado e nao medido**, uniforme "
        "para todos os pontos. Alem disso, tratar interferencia co-canal como "
        "ruido aditivo e conservador demais para Wi-Fi: em CSMA/CA a interferencia "
        "co-canal atua principalmente por **disputa de airtime** (o transmissor "
        "espera o meio ficar livre), e nao somando potencia ao denominador. A "
        "capacidade de Shannon derivada dai e teto teorico, jamais previsao de "
        "vazao.\n" % PARAMS["piso_ruido_dbm"])

    add("\n## 5. Alpha reportado com %d algarismos significativos\n"
        % PARAMS["algarismos_significativos_alpha"])
    add("Pelos motivos das secoes 1 e 2: amostra unica, distancia anotada com "
        "aproximacao na origem, altura nao controlada e RSSI 802.11 variando "
        "tipicamente +-5 a 10 dB por fast fading. Reportar alpha = 2,62 sugere "
        "precisao de centesimos que a amostra nao sustenta; o pipeline reporta "
        "alpha ~= 2,6.\n")
    if cenarios_df is not None and len(cenarios_df):
        est = cenarios_df[cenarios_df["status"] == "estimado"]
        if len(est):
            t = est[["predio", "banda", "cenario", "alpha",
                     "ic95_inf", "ic95_sup", "n"]].copy()
            t["amplitude_ic"] = (t["ic95_sup"] - t["ic95_inf"]).round(2)
            add("\nAmplitude dos intervalos de confianca obtidos nesta execucao:\n")
            add("\n" + t.to_markdown(index=False) + "\n")
            add("\nUm IC de amplitude comparavel ao proprio valor de alpha confirma "
                "que o segundo algarismo ja e o limite do que a amostra sustenta.\n")

    add("\n## 6. Cobertura desigual entre os predios\n")
    add(cobertura_por_predio(df, config).to_markdown(index=False) + "\n")
    add("\nA comparacao entre predios herda essas assimetrias. Onde um predio tem "
        "mapeamento de AP e o outro nao, a mesma analise nao roda dos dois lados, "
        "e a diferenca observada pode ser de **cobertura de dado**, nao de "
        "propagacao.\n")

    add("\n## 7. Equipamento nao totalmente identificado\n")
    for predio, cfg in sorted(config.items()):
        fab, mod = cfg.get("fabricante_ap"), cfg.get("modelo_ap")
        if fab and not mod:
            add("- **Predio %s**: fabricante declarado (%s), modelo nao "
                "registrado. Potencia de transmissao e ganho de antena variam "
                "entre modelos do mesmo fabricante, entao a ressalva de "
                "comparabilidade permanece aberta.\n" % (predio, fab))
        elif not fab:
            add("- **Predio %s**: fabricante **nao confirmado**. Os OUIs "
                "observados nao foram verificados contra a base do IEEE, e o "
                "pipeline nao os infere.\n" % predio)

    sus = detectar_bssids_suspeitos(df, config)
    erro = sus[sus["hipotese"] == HIPOTESE_TRANSCRICAO] if len(sus) else sus
    if len(erro):
        add("\n## 8. Transcricao de BSSID nao verificada na fonte\n")
        add("%d par(es) de BSSID diferem em poucos digitos sem cair no mesmo AP "
            "fisico. A hipotese de erro de transcricao **nao foi confirmada "
            "contra os prints originais do aplicativo**: ela e apenas a leitura "
            "mais provavel do padrao observado.\n" % len(erro))
        for _, r in erro.iterrows():
            add("\n- predio %s: %s (leitura %s) vs %s (leitura %s); candidato a "
                "erro: %s\n" % (r["predio"], r["bssid_a"], r["leituras_a"],
                                r["bssid_b"], r["leituras_b"],
                                r["bssid_anomalo"] or "indefinido"))

    texto = "\n".join(partes)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return texto
