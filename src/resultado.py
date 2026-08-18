"""Tipo de retorno unico para toda estimativa do pipeline.

Nenhuma funcao de estimativa devolve um float solto. O contrato e sempre
``Resultado``, de modo que quem consome recebe junto o n, o intervalo de
confianca e — quando nao ha estimativa — o motivo por escrito.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from config.predios import PARAMS


def arredondar_significativos(valor: Optional[float], n: int = 2) -> Optional[float]:
    """Arredonda para ``n`` algarismos significativos.

    Existe porque reportar alpha com 2 casas decimais sugere precisao que a
    amostra nao tem: leitura unica por ponto, distancia anotada com '~' na
    origem e RSSI 802.11 variando +-5 a 10 dB por fast fading.
    """
    if valor is None:
        return None
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    if v == 0 or v != v or v in (float("inf"), float("-inf")):
        return v if v == 0 else None
    from math import floor, log10
    return round(v, -int(floor(log10(abs(v)))) + (n - 1))


@dataclass
class Resultado:
    """Resultado de uma estimativa, com a incerteza junto.

    valor  : estimativa pontual, ou None quando nao estimavel
    ic     : (inferior, superior) do intervalo de confianca, ou None
    n      : tamanho da amostra efetivamente usada
    status : "estimado" | "nao estimavel" | "inconsistente"
    motivo : texto obrigatorio quando status != "estimado"
    extra  : metricas auxiliares (r2, rmse, pontos usados, ...)
    """

    valor: Optional[float] = None
    ic: Optional[tuple] = None
    n: int = 0
    status: str = "nao estimavel"
    motivo: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "estimado"

    def valor_significativo(self, n_alg: Optional[int] = None) -> Optional[float]:
        """O valor com o numero de algarismos significativos declarado em PARAMS."""
        n_alg = n_alg or PARAMS["algarismos_significativos_alpha"]
        return arredondar_significativos(self.valor, n_alg)

    def texto(self, unidade: str = "", n_alg: Optional[int] = None) -> str:
        """Uma linha legivel, para tabelas e caixas de figura."""
        if not self.ok:
            return f"nao estimavel (n={self.n}) — {self.motivo}"
        v = self.valor_significativo(n_alg)
        txt = f"{v:g}{unidade}"
        if self.ic and all(x == x for x in self.ic):
            lo = arredondar_significativos(self.ic[0], (n_alg or 2) + 1)
            hi = arredondar_significativos(self.ic[1], (n_alg or 2) + 1)
            txt += f" (IC95% {lo:g} a {hi:g})"
        txt += f", n={self.n}"
        if self.status == "inconsistente":
            txt += f" — ALERTA: {self.motivo}"
        return txt

    def como_dict(self, prefixo: str = "") -> dict[str, Any]:
        """Forma achatada, para montar DataFrames de tabela comparativa."""
        p = f"{prefixo}_" if prefixo else ""
        return {
            f"{p}valor": self.valor_significativo(),
            f"{p}ic_inf": self.ic[0] if self.ic else None,
            f"{p}ic_sup": self.ic[1] if self.ic else None,
            f"{p}n": self.n,
            f"{p}status": self.status,
            f"{p}motivo": self.motivo,
        }


def nao_estimavel(motivo: str, n: int = 0, **extra) -> Resultado:
    """Atalho para o caso em que a amostra nao sustenta uma estimativa."""
    return Resultado(valor=None, ic=None, n=n, status="nao estimavel",
                     motivo=motivo, extra=extra)
