# Cobertura Wi-Fi — Prédios M e I

Mapeamento e análise da cobertura Wi-Fi de dois prédios do campus da UFCA, cada um com três
pavimentos (subsolo, térreo, 1º andar) e dois APs por pavimento, nas bandas 2,4 e 5 GHz.

Disciplina **CC0048 — Redes Sem Fio**.

- **O que falta coletar e por quê** → [OBSERVACOES.md](OBSERVACOES.md)
- **Estado dos dados nesta execução** → `saidas/relatorio_qualidade.md` (gerado automaticamente)

---

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Notebook completo:

```bash
.venv/Scripts/python.exe -m nbconvert --to notebook --execute --inplace notebook_fases_5_6.ipynb
```

Ou direto, sem notebook:

```python
from src.pipeline import rodar

S = rodar()
print(S["verificacao"])      # conferência contra os valores já validados
print(S["cenarios"])         # os 4 cenários de path loss
print(S["laje"])             # perda entre pavimentos
```

---

## Estrutura

```
config/predios.py    única fonte de valores por prédio; PARAMS com todos os limiares
dados/leituras.csv   56 leituras, schema único para os dois prédios
src/                 11 módulos de análise — nenhum nome de prédio aparece aqui
notebook_...ipynb    orquestra e exibe; não implementa nada
saidas/              relatório de qualidade, limitações, figuras, rasters
```

| Módulo | Responsabilidade |
|---|---|
| `src/esquema.py` | Carga e validação do CSV; marca linhas inválidas em vez de removê-las |
| `src/bssid.py` | Normalização, agrupamento em AP físico, detecção de transcrição, dominância |
| `src/geometria.py` | Distância 3D, AP mais próximo, resolução de coordenadas |
| `src/pathloss.py` | Os 4 cenários de ajuste, IC 95 %, atenuação por obstáculo |
| `src/laje.py` | Perda entre pavimentos, por pares do mesmo AP físico |
| `src/canais.py` | Descasamento, reuso e qualidade relativa de canal |
| `src/heatmap.py` | Mapas por pavimento, IDW com raio máximo, exportação GeoTIFF |
| `src/qualidade.py` | Relatório de qualidade — roda **primeiro** |
| `src/limitacoes.py` | `saidas/limitacoes.md`, montado a partir dos dados reais |
| `src/viz.py` | Anotação padrão de figura, rodapé, gravação |
| `src/resultado.py` | O tipo `Resultado`, retornado por toda estimativa |
| `src/pipeline.py` | Orquestração na ordem correta |

## Acrescentar um terceiro prédio

Uma entrada nova em `PREDIOS` (em `config/predios.py`) e as linhas no CSV.
**Nenhuma alteração em `src/`.** Se alguma análise precisar de um `if predio == ...` dentro
de `src/`, isso é bug de arquitetura, não caso particular.

---

## Decisões que valem conhecer antes de ler os números

**Não existe exclusão de ponto por ID.** O único critério de exclusão na regressão de path
loss local é a classificação de dominância de AP, derivada do BSSID
(`PARAMS["dominancias_excluidas_sempre"]`). Os pontos 13 e 14 do prédio M, que antes saíam
por uma lista escrita à mão, hoje saem por evidência: OUI estranho ao prédio num caso, 4º
octeto fora do vocabulário observado no outro.

**α sai com 2 algarismos significativos.** Amostra única por ponto, distância anotada com
aproximação na origem, altura de medição não registrada, e RSSI 802.11 variando ±5 a 10 dB
por fast fading. `α ≈ 2,6`, nunca `α = 2,62`.

**Toda estimativa retorna `Resultado(valor, ic, n, status, motivo)`**, nunca um float solto.
Onde a amostra não sustenta, o resultado declarado é a impossibilidade, com o motivo escrito.

**BSSID = AP dominante na varredura**, não AP associado ao cliente. O termo "sticky client"
não é sustentável por este dado, e não aparece em nenhuma saída.

**Os mapas não interpolam a partir de qualquer coisa.** IDW com raio máximo de 8 m, célula
fora do raio fica vazia, e abaixo de 4 posições distintas sai só scatter. Sem krigagem, sem
contorno suave, sem extrapolação até a borda da planta.

**Vazão, latência e perda de pacotes foram removidas do escopo** — não foram medidas. Ver o
marcador em [OBSERVACOES.md](OBSERVACOES.md), seção 4.5.

---

## Verificação de regressão

O pipeline se confere contra valores já validados. Divergência aqui indica erro de parsing ou
de mapeamento de coluna — **não é descoberta**.

| Verificação | Esperado | Obtido |
|---|---|---|
| α prédio M, 2,4 GHz (cenário histórico) | 2,62 | **2,60** ✅ |
| R² | 0,91 | **0,906** ✅ |
| n | 9 | **9** ✅ |
| Descasamento de canal M 2,4 GHz | 76 % | **76,5 %** ✅ |
| L_obstáculo porta corta-fogo | 21,1 dB | **21,1 dB** ✅ |

O "cenário histórico" usa a distância como estava gravada no CSV antigo. Ele existe só para
essa conferência — ver a seção 5.1 de [OBSERVACOES.md](OBSERVACOES.md) sobre por que a
distância mudou.

---

## Saídas

| Arquivo | O que traz |
|---|---|
| `saidas/relatorio_qualidade.md` | 8 seções; a de número 8 é a lista objetiva do que recoletar |
| `saidas/limitacoes.md` | limitações montadas a partir dos dados reais, não hardcoded |
| `saidas/coordenadas_a_levantar.csv` | as 23 posições sem `x_m`/`y_m`, prontas para preencher |
| `saidas/figuras/` | um mapa por prédio × pavimento × banda |
| `saidas/qgis/` | rasters GeoTIFF com o mesmo extent dos mapas |

## O que roda hoje

| Análise | Situação |
|---|---|
| Canais — descasamento, reuso, qualidade relativa | ✅ executável |
| Path loss cenário A | ⚠️ 2 de 4 combinações (só 2,4 GHz) |
| Atenuação por obstáculo | ⚠️ 2 de 4 combinações |
| Path loss cenários B/D, C/D · perda de laje · mapas interpolados | ❌ bloqueadas |

Os bloqueios são de **dado**, não de código: faltam `x_m`/`y_m` (24 de 56 leituras têm), BSSID
completo (31 de 56) e leituras em distâncias intermediárias na banda de 5 GHz.

## Arquivos históricos

`dados/dados_bloco_M.csv` e `dados/dados_bloco_I.csv` são os CSVs originais das campanhas, no
formato antigo. Ficam como proveniência; o pipeline não os lê mais. O diretório `saida/` (sem
"s") guarda figuras da versão anterior do pipeline.
