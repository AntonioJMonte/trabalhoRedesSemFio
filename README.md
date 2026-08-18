# Cobertura Wi-Fi — Predios M e I

Analise de cobertura Wi-Fi de dois predios do campus (UFCA), 3 pavimentos cada,
2 APs por pavimento, bandas 2,4 e 5 GHz. Disciplina CC0048 — Redes Sem Fio.

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m nbconvert --to notebook --execute --inplace notebook_fases_5_6.ipynb
```

Ou, sem notebook:

```python
from src.pipeline import rodar
S = rodar()
print(S["verificacao"])
```

## Estrutura

```
config/predios.py   unica fonte de valores por predio; PARAMS com todos os limiares
dados/leituras.csv  56 leituras, schema unico para os dois predios
src/                modulos de analise (nenhum nome de predio aparece aqui)
saidas/             relatorio_qualidade.md, limitacoes.md, figuras/, qgis/
```

## Acrescentar um terceiro predio

Uma entrada nova em `PREDIOS` (em `config/predios.py`) e as linhas no CSV.
**Nenhuma alteracao em `src/`.** Se alguma analise precisar de um `if predio == ...`
dentro de `src/`, isso e bug de arquitetura, nao caso particular.

## Decisoes que valem conhecer antes de ler os numeros

- **Nao existe exclusao de ponto por ID.** O unico criterio de exclusao na regressao
  de path loss local e a classificacao de dominancia de AP, derivada do BSSID
  (`PARAMS["dominancias_excluidas_sempre"]`).
- **`alpha` sai com 2 algarismos significativos.** A amostra e de leitura unica por
  ponto, com altura de medicao nao controlada. Precisao maior seria falsa.
- **Toda estimativa retorna `Resultado(valor, ic, n, status, motivo)`**, nunca um
  float solto. Onde a amostra nao sustenta, o resultado declarado e a
  impossibilidade, com o motivo por escrito.
- **BSSID = AP dominante na varredura**, nao AP associado ao cliente. O termo
  "sticky client" nao e sustentavel por este dado.
- **Vazao, latencia e perda de pacotes foram removidas do escopo**: nao foram
  medidas. Ver o marcador em `OBSERVACOES.md`, secao 3.2.

## Saidas

| Arquivo | O que traz |
|---|---|
| `saidas/relatorio_qualidade.md` | 8 secoes; a de numero 8 e a lista objetiva do que recoletar em campo |
| `saidas/limitacoes.md` | limitacoes montadas a partir dos dados reais, nao hardcoded |
| `saidas/figuras/` | um mapa por predio x pavimento x banda |
| `saidas/qgis/` | rasters GeoTIFF com o mesmo extent dos mapas |

## Arquivos historicos

`dados/dados_bloco_M.csv` e `dados/dados_bloco_I.csv` sao os CSVs originais das
campanhas, no formato antigo. Ficam como proveniencia; o pipeline nao os le mais.
O diretorio `saida/` (sem "s") guarda figuras da versao anterior do pipeline.
