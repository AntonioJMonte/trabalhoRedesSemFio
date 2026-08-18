"""Normalizacao, agrupamento e diagnostico de BSSIDs.

VOCABULARIO — os BSSIDs foram capturados da lista de varredura do aplicativo
(aba "Pontos de Acesso"). Eles identificam o **AP visivel dominante** no ponto,
NAO o AP ao qual o cliente estava associado. Toda saida deste modulo usa
"AP dominante"; os termos "AP conectado" e "sticky client" nao se aplicam ao
que este dado sustenta.
"""

import re
from collections import defaultdict
from typing import Iterable, Optional

import pandas as pd

from config.predios import PARAMS

_HEX = re.compile(r"[0-9a-f]")


def normalizar(bssid) -> Optional[str]:
    """Devolve o BSSID em minusculas, no formato ``aa:bb:cc:dd:ee:ff``.

    Aceita as formas usuais de transcricao (com ':', '-', '.' ou sem separador).
    Devolve None quando a entrada nao contem 12 digitos hexadecimais — ausencia
    de BSSID nao e erro, e o pipeline degrada graciosamente.
    """
    if bssid is None or (isinstance(bssid, float) and bssid != bssid):
        return None
    texto = str(bssid).strip().lower()
    if not texto or texto in {"nan", "none", "-", ""}:
        return None
    digitos = "".join(_HEX.findall(texto))
    if len(digitos) != 12:
        return None
    return ":".join(digitos[i:i + 2] for i in range(0, 12, 2))


def nibbles(bssid: str) -> list[str]:
    """Os 12 digitos hexadecimais do BSSID, sem separador."""
    return list(bssid.replace(":", ""))


def oui(bssid: str) -> Optional[str]:
    """Os 3 primeiros octetos (o OUI atribuido pelo IEEE)."""
    b = normalizar(bssid)
    return b[:8] if b else None


def chave_de_grupo(bssid, regra: Optional[dict] = None) -> Optional[str]:
    """Chave que identifica o AP fisico ao qual o BSSID pertence.

    A regra vem da configuracao do predio, porque **nao e universal**:

    - ``{"tipo": "prefixo_octetos", "n": 5}`` — BSSIDs que compartilham os N
      primeiros octetos sao o mesmo AP fisico. Confirmado para os APs Ruckus do
      predio M, onde o ultimo octeto varia por radio/SSID.
    - ``{"tipo": "bssid_completo"}`` — regra conservadora: cada BSSID e seu
      proprio grupo. E o padrao quando a regra do predio nao foi confirmada.
    """
    b = normalizar(bssid)
    if b is None:
        return None
    regra = regra or {"tipo": "bssid_completo"}
    if regra.get("tipo") == "prefixo_octetos":
        n = int(regra.get("n", 5))
        return ":".join(b.split(":")[:n])
    return b


def agrupar_por_ap_fisico(bssids: Iterable, regra: Optional[dict] = None) -> dict[str, list[str]]:
    """Agrupa BSSIDs em APs fisicos segundo a regra do predio.

    Devolve ``{chave_do_grupo: [bssids ordenados]}``. Entradas ilegiveis sao
    descartadas silenciosamente aqui — quem as reporta e o relatorio de
    qualidade, que enxerga a linha inteira.
    """
    grupos: dict[str, list[str]] = defaultdict(list)
    for bruto in bssids:
        b = normalizar(bruto)
        if b is None:
            continue
        chave = chave_de_grupo(b, regra)
        if b not in grupos[chave]:
            grupos[chave].append(b)
    return {k: sorted(v) for k, v in sorted(grupos.items())}


def distancia_hamming_nibbles(a: str, b: str) -> int:
    """Numero de digitos hexadecimais em que dois BSSIDs diferem."""
    na, nb = nibbles(a), nibbles(b)
    if len(na) != len(nb):
        return max(len(na), len(nb))
    return sum(1 for x, y in zip(na, nb) if x != y)


HIPOTESE_MESMO_AP = "mesmo AP fisico (prefixo de 5 octetos, radio/SSID distinto)"
HIPOTESE_OFFSET_RADIO = "offset de radio 2.4/5 GHz no 4o octeto"
HIPOTESE_TRANSCRICAO = "possivel erro de transcricao"


def _difere_por_offset_de_radio(a: str, b: str) -> bool:
    """True se a e b diferem APENAS no 4o octeto, por um offset conhecido de radio.

    Alguns fabricantes derivam o BSSID do radio de 5 GHz somando uma constante ao
    4o octeto do BSSID de 2.4 GHz. Um par assim NAO e erro de transcricao — e o
    mesmo equipamento visto em duas bandas.
    """
    oa, ob = a.split(":"), b.split(":")
    # O ULTIMO octeto e ignorado de proposito: ele ja varia por radio/SSID dentro
    # de um mesmo AP, entao exigir igualdade nele voltaria a separar equipamentos
    # que este teste existe justamente para reconhecer como um so.
    if [oa[i] for i in (0, 1, 2, 4)] != [ob[i] for i in (0, 1, 2, 4)]:
        return False
    va, vb = int(oa[3], 16), int(ob[3], 16)
    return any(abs(va - vb) == off for off in PARAMS["offsets_radio_4o_octeto"])


def classificar_hipotese(a: str, b: str, bandas_a: set, bandas_b: set) -> str:
    """Explicacao mais provavel para dois BSSIDs quase iguais em grupos distintos.

    Distinguir as tres hipoteses importa porque so uma delas pede correcao do
    dado. As outras duas pedem correcao da REGRA DE AGRUPAMENTO do predio.
    """
    # Compartilham os 5 primeiros octetos: e a regra do predio M, e o ultimo
    # octeto varia por radio/SSID do mesmo equipamento.
    if a.split(":")[:5] == b.split(":")[:5]:
        return HIPOTESE_MESMO_AP
    # Offset conhecido no 4o octeto E separacao limpa por banda.
    if _difere_por_offset_de_radio(a, b) and bandas_a and bandas_b and not (bandas_a & bandas_b):
        return HIPOTESE_OFFSET_RADIO
    return HIPOTESE_TRANSCRICAO



def _alto_nibble_octeto4(b: str) -> str:
    """Primeiro digito hexadecimal do 4o octeto."""
    return b.split(":")[3][0]


def identificar_anomalo(a: str, b: str, vocabulario: dict) -> Optional[str]:
    """Qual dos dois BSSIDs destoa do vocabulario observado no predio.

    Marcar OS DOIS lados de um par suspeito como suspeitos penaliza a leitura
    correta junto com a errada. Quando o predio mostra um padrao no 4o octeto —
    no predio M o digito alto e sempre o mesmo, variando so o baixo — o BSSID
    que rompe esse padrao e o candidato a erro de transcricao, e o outro nao.

    Devolve o BSSID anomalo, ou None quando os dados nao distinguem (nesse caso
    quem chama deve marcar ambos, para nao esconder o problema).
    """
    na, nb = _alto_nibble_octeto4(a), _alto_nibble_octeto4(b)
    if na == nb:
        return None
    freq_a, freq_b = vocabulario.get(na, 0), vocabulario.get(nb, 0)
    if freq_a == freq_b:
        return None
    return b if freq_a > freq_b else a


def vocabulario_octeto4(bssids: Iterable) -> dict:
    """Frequencia de cada digito alto do 4o octeto, por BSSID distinto do predio."""
    freq: dict[str, int] = defaultdict(int)
    for b in {x for x in (normalizar(v) for v in bssids) if x}:
        freq[_alto_nibble_octeto4(b)] += 1
    return dict(freq)


def detectar_bssids_suspeitos(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Sinaliza BSSIDs provavelmente mal transcritos.

    Criterio: a distancia de Hamming (em nibbles) para outro BSSID do **mesmo
    predio** e <= ``PARAMS["hamming_nibbles_suspeito"]``, mas os dois **nao caem
    no mesmo grupo** de AP fisico. Dois BSSIDs quase iguais que a regra de
    agrupamento separa sao ou um erro de transcricao, ou uma regra de
    agrupamento errada para aquele predio — os dois casos pedem inspecao humana.

    Nao decide qual dos dois e o certo: apenas emite o par e a diferenca.
    """
    linhas = []
    for predio, sub in df.groupby("predio", sort=True):
        regra = (config.get(predio) or {}).get("regra_agrupamento_bssid")
        pares_vistos = set()

        # BSSID -> leituras em que aparece, e bandas em que foi visto
        por_bssid: dict[str, list] = defaultdict(list)
        bandas: dict[str, set] = defaultdict(set)
        for _, r in sub.iterrows():
            b = normalizar(r.get("bssid_bruto"))
            if b:
                por_bssid[b].append(int(r["id"]))
                bandas[b].add(str(r.get("banda")))

        chaves = {b: chave_de_grupo(b, regra) for b in por_bssid}
        limite = PARAMS["hamming_nibbles_suspeito"]
        vocab = vocabulario_octeto4(por_bssid)

        for a in sorted(por_bssid):
            for b in sorted(por_bssid):
                if a >= b or (a, b) in pares_vistos:
                    continue
                pares_vistos.add((a, b))
                d = distancia_hamming_nibbles(a, b)
                if d > limite or chaves[a] == chaves[b]:
                    continue
                posicoes = [i for i, (x, y) in enumerate(zip(nibbles(a), nibbles(b))) if x != y]
                linhas.append({
                    "predio": predio,
                    "bssid_a": a,
                    "bssid_b": b,
                    "leituras_a": por_bssid[a],
                    "leituras_b": por_bssid[b],
                    "bandas_a": sorted(bandas[a]),
                    "bandas_b": sorted(bandas[b]),
                    "hamming_nibbles": d,
                    "nibbles_divergentes": posicoes,
                    "octetos_divergentes": sorted({p // 2 + 1 for p in posicoes}),
                    "grupo_a": chaves[a],
                    "grupo_b": chaves[b],
                    "hipotese": classificar_hipotese(a, b, bandas[a], bandas[b]),
                    "bssid_anomalo": identificar_anomalo(a, b, vocab),
                })
    return pd.DataFrame(linhas)


def classificar_dominancia(leitura, mapa_bssid_ap: dict, grupos_por_predio: dict,
                           suspeitos: set, regra: Optional[dict] = None) -> str:
    """Classifica de onde vem o AP dominante da leitura.

    Retorna:
        "local"           — AP dominante e do mesmo pavimento da leitura
        "outro_pavimento" — AP dominante e de pavimento diferente
        "outro_predio"    — AP dominante pertence a outro predio
        "sem_dado"        — BSSID ausente ou ilegivel (NAO e erro)
        "suspeito"        — o BSSID foi sinalizado por detectar_bssids_suspeitos

    Esta e a **unica** classificacao autorizada a filtrar leituras na regressao
    de path loss local. Nao ha exclusao por ID de ponto em lugar nenhum.
    """
    b = normalizar(leitura.get("bssid_bruto"))
    if b is None:
        return "sem_dado"
    if b in suspeitos:
        return "suspeito"

    chave = chave_de_grupo(b, regra)
    predio_leitura = leitura.get("predio")

    # O grupo pertence a outro predio?
    for predio, chaves in grupos_por_predio.items():
        if predio != predio_leitura and chave in chaves:
            return "outro_predio"

    if not mapa_bssid_ap:
        # O predio ainda nao teve 'bssid_para_ap' preenchido (a regra de
        # agrupamento nao foi confirmada). Sem mapa NAO ha do que estar fora:
        # a leitura e desconhecida, nao estrangeira. Tratar como nao-mapeada
        # aqui excluiria o predio inteiro das analises por falta de conferencia
        # manual, o que e conclusao forte demais para uma pendencia de cadastro.
        return "sem_dado"

    destino = mapa_bssid_ap.get(chave)
    if destino is None:
        # BSSID legivel, porem nao corresponde a nenhum AP declarado do predio.
        # E diferente de "sem_dado": aqui HA evidencia de que o AP dominante nao
        # e um dos APs conhecidos desta edificacao.
        return "ap_nao_mapeado"

    pav_ap = destino.get("pavimento")
    if pav_ap is None:
        return "ap_nao_mapeado"
    return "local" if pav_ap == leitura.get("pavimento") else "outro_pavimento"


def anotar_dominancia(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Acrescenta ``bssid``, ``grupo_ap``, ``dominancia`` e ``bssid_suspeito``."""
    df = df.copy()
    df["bssid"] = df["bssid_bruto"].map(normalizar)
    df["grupo_ap"] = [
        chave_de_grupo(b, (config.get(p) or {}).get("regra_agrupamento_bssid"))
        for b, p in zip(df["bssid"], df["predio"])
    ]

    # Apenas os pares cuja hipotese e ERRO DE TRANSCRICAO marcam a leitura como
    # suspeita. Pares explicados por radio/SSID do mesmo AP, ou por offset de
    # radio entre bandas, sao problema da REGRA DE AGRUPAMENTO do predio — nao
    # do dado — e sao reportados sem contaminar a classificacao de dominancia.
    suspeitos_df = detectar_bssids_suspeitos(df, config)
    suspeitos = set()
    if not suspeitos_df.empty:
        erro = suspeitos_df[suspeitos_df["hipotese"] == HIPOTESE_TRANSCRICAO]
        for _, par in erro.iterrows():
            if par["bssid_anomalo"]:
                suspeitos.add(par["bssid_anomalo"])
            else:
                # sem criterio para distinguir: marca os dois, para nao esconder
                suspeitos.update([par["bssid_a"], par["bssid_b"]])

    grupos_por_predio = {
        p: set(agrupar_por_ap_fisico(sub["bssid"].dropna(),
                                     (config.get(p) or {}).get("regra_agrupamento_bssid")))
        for p, sub in df.groupby("predio", sort=True)
    }

    dominancias = []
    for _, r in df.iterrows():
        cfg = config.get(r["predio"]) or {}
        dominancias.append(classificar_dominancia(
            r,
            mapa_bssid_ap=cfg.get("bssid_para_ap") or {},
            grupos_por_predio=grupos_por_predio,
            suspeitos=suspeitos,
            regra=cfg.get("regra_agrupamento_bssid"),
        ))
    df["dominancia"] = dominancias
    df["bssid_suspeito"] = df["bssid"].isin(suspeitos)
    return df


def grupos_candidatos(df: pd.DataFrame, predio: str, config: dict) -> pd.DataFrame:
    """Grupos candidatos de AP fisico, para conferencia manual.

    Emitido para predios cujo ``bssid_para_ap`` ainda nao foi preenchido. A
    confirmacao e humana: gravar em ``config/predios.py`` so depois de conferir.
    """
    sub = df[df["predio"] == predio]
    regra = (config.get(predio) or {}).get("regra_agrupamento_bssid")
    grupos = agrupar_por_ap_fisico(sub["bssid_bruto"], regra)
    linhas = []
    for chave, membros in grupos.items():
        leituras = sub[sub["bssid"].isin(membros)]
        linhas.append({
            "grupo": chave,
            "bssids": ", ".join(membros),
            "oui": oui(membros[0]),
            "leituras": sorted(int(i) for i in leituras["id"]),
            "pavimentos": sorted(int(v) for v in set(leituras["pavimento"])),
            "bandas": sorted(set(leituras["banda"].astype(str))),
            "locais": "; ".join(sorted(set(leituras["local"].astype(str)))),
        })
    return pd.DataFrame(linhas)
