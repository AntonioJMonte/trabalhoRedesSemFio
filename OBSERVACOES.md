# Observações — o que faltou e como preencher

Projeto Mapa de Cobertura Wi-Fi · CC0048 — Redes Sem Fio · UFCA
Referente à execução do notebook `notebook_fases_5_6.ipynb` com os dados do **Bloco M**
(campanha de 07/08/2026, 30 leituras, 29 com conexão — o ponto 22 foi zona cega em 5 GHz).

Este documento lista **apenas o que está faltando**. Nada aqui é defeito de código: todas as
análises abaixo estão implementadas e testadas, e ligam sozinhas assim que o dado existir.
Nenhuma exige alteração na lógica de análise.

---

## 1. Situação atual

**Rodou e foi validado**

- Fase 5.1 — carga, validação e relatório de completude
- Fase 6.1 — path-loss (α = 2,62 · RSSI(d₀) = −28,5 dBm · R² = 0,91 · n = 9 em 2,4 GHz),
  atenuação por obstáculos, teste de alavancagem
- Fase 6.2 — apenas a camada de canal (descasamento 13/17 = 76 %, qualidade média 20,4 %)
- Fase 6.3 — capacidade de Shannon como teto teórico
- 8 figuras em `saida/figuras/`, teste de regressão 11/11

**Não rodou, por falta de dado**

| Análise | Falta | Seção deste doc |
|---|---|---|
| 5.2 Heatmaps interpolados | `x`, `y`, planta, dimensões | [3.1](#31-coordenadas-planta-e-dimensões) |
| 5.3 Rasters e camada de pontos no QGIS | idem | [3.1](#31-coordenadas-planta-e-dimensões) |
| SINR real (hoje só há SNR) | `redes_vizinhas_mesmo_canal` | [3.3](#33-redes-vizinhas--sinr-real) |
| α em 5 GHz | leituras em distâncias maiores | [3.4](#34-distâncias-intermediárias) |
| Ajuste isolado do 1º andar | idem | [3.4](#34-distâncias-intermediárias) |
| 6.4 Comparativo entre blocos | o Bloco I inteiro | [3.7](#37-bloco-i-completo) |

**Pendências que não são de dado**

Além do que falta coletar, há 4 limitações da implementação — detalhadas na
[seção 7](#7-pendências-do-notebook-código). Uma delas, `planta` e `aps` serem únicos por bloco
em vez de por andar, **precisa ser resolvida antes da campanha**, porque muda o formato do que
você anota em campo.

Se quiser ir direto ao que fazer, veja o [checklist de campo consolidado](#8-checklist-de-campo-consolidado).

---

## 2. Como o notebook trata a ausência

Três garantias, para que nada disso vire erro silencioso:

1. **Nenhum valor é arbitrado.** Coluna vazia gera aviso e a leitura sai daquela análise —
   nunca entra com um valor padrão.
2. **Nenhum α sem medida de confiança.** Toda estimativa vem com R², n e a guarda de
   suficiência amostral. Onde a amostra não sustenta, o resultado declarado é a
   impossibilidade, não um número.
3. **Ausência não interrompe.** O notebook roda até o fim com o que existir e imprime, ao
   final, a lista de bloqueios e a coluna que falta em cada um.

---

## 3. Como preencher

### Nota geral sobre o CSV

O arquivo [`dados/dados_bloco_M.csv`](dados/dados_bloco_M.csv) está no formato original da
coleta (`ponto, banda, rssi, d, obst, canal, melhor, pct, andar, livre`) e é convertido para
o schema canônico pelo `mapa_colunas` da configuração.

**Para acrescentar dado novo, basta adicionar a coluna já com o nome canônico.** Colunas com
nome canônico passam direto, sem precisar mexer no `mapa_colunas`. Ou seja: abra o CSV,
acrescente `x_m`, `y_m`, `bssid_bruto` etc. e preencha. Nada mais.

Schema canônico completo:

```
bloco, ponto, andar, local, x, y, banda_ghz, rssi_dbm, snr_estimado_db,
canal, canal_melhor, qualidade_melhor_canal_pct, redes_vizinhas_mesmo_canal,
dist_campo_m, dist_origem, obstaculos, bssid_bruto, altura_medicao_m
```

Deixe em branco o que não foi medido. **Não preencha com 0, com a média nem com estimativa** —
o notebook detecta o vazio e bloqueia a análise correspondente, que é o comportamento correto.

---

### 3.1 Coordenadas, planta e dimensões

**Destrava:** heatmaps das 4 métricas (Fase 5.2), rasters georreferenciados e camada de
pontos plotável no QGIS (Fase 5.3).

**Por que está bloqueado.** A campanha registrou a posição como descrição textual — "Fundo da
M102", "Escada de incêndio, 1º andar". Converter texto em coordenada seria inventar dado, e a
interpolação herdaria essa invenção com aparência de medição. Por isso o notebook se recusa a
fazê-lo. A coluna `local` inclusive está vazia no CSV atual; vale preenchê-la junto.

#### O que essas coordenadas geram

Com os dados atuais, **12 figuras**: RSSI e SNR × 2 bandas × 3 pavimentos. Cada uma traz a
planta ao fundo, o campo interpolado em RdYlGn por cima, os pontos medidos, os APs e as linhas
de contorno em **−67 e −70 dBm**. Medindo também vazão e latência, sobe para **24 figuras**.

Mais as camadas do QGIS: um raster `.png` + `.pgw` por métrica/banda/andar, e o `pontos_M.csv`
com geometria.

O que o mapa responde e as tabelas não: onde exatamente ficam as zonas fracas, onde instalar AP
novo, se há sobreposição ou vão entre APs, e qual a extensão espacial do sombreamento das portas
metálicas.

**O que as coordenadas NÃO mudam:** nada da Fase 6.1. O α = 2,62, os L_obstáculo, o descasamento
de canal e o teste de alavancagem dependem de `distancia_ao_ap`, não de `x`/`y` — já estão
completos e validados. As coordenadas servem exclusivamente à Fase 5, que é a única fase hoje
inteiramente bloqueada e a que dá nome ao projeto.

#### Ressalva de cobertura — leia antes de ir a campo

Com 5 a 6 pontos por pavimento, **o mapa sai majoritariamente vazio**. O `griddata` linear só
interpola dentro do fecho convexo dos pontos medidos; fora dele o notebook aplica hachura e
declara "sem medição, não extrapolado". No teste com 6 pontos num pavimento de 30 × 20 m,
**89 % da planta saiu hachurada** — mapa honesto, cobrindo um décimo do andar.

São duas ações diferentes:

| Ação | Resultado |
|---|---|
| Só medir `x`, `y` dos 17 pontos atuais | Destrava o pipeline. Mapa correto, cobrindo fração pequena de cada andar |
| Medir `x`, `y` **e acrescentar pontos** | Mapa que efetivamente cobre a edificação |

Para um mapa que se sustente como entregável, o razoável é **15 a 25 pontos por pavimento**,
distribuídos por circulação e salas — não só perto dos APs, que é onde a campanha atual se
concentrou (8 das 17 leituras de 2,4 GHz estão a 1 m ou menos de um AP).

#### Que tipo de coordenada é

**Não é GPS.** Nada de latitude/longitude nem UTM. É um **sistema cartesiano local, em metros**,
válido só dentro do prédio — o que o guia chama de "coordenadas locais em metros". São **dois
números por ponto**: as distâncias até duas paredes perpendiculares de referência.

```
  A ┌─────────────────────────────────────┐
    │                                     │
    │            M-01 ●                   │   y = 7,1 m  (até a parede de baixo)
    │                 ╎                   │
    │                 ╎                   │
  0 └─────────────────┴───────────────────┘
    (0,0)          x = 22,4 m             L
     origem
```

**As três regras**

1. Origem `(0,0)` num canto do prédio — de preferência o inferior esquerdo da planta.
2. `x` cresce para a direita, `y` cresce para cima, na orientação em que a planta será usada.
3. **O mesmo canto do prédio nos três pavimentos.** Origens diferentes por andar fazem os
   mapas não se sobreporem, e a comparação entre pavimentos se perde.

**Como obter.** Você não mede "a coordenada" — mede **duas distâncias perpendiculares**. Com
trena a laser: encoste na parede de referência de `x` e meça até o ponto (é o `x`); repita na
parede perpendicular (é o `y`). Dois disparos por ponto. Sem trena, se a planta for cotada ou
estiver em escala, dá para ler direto contando módulos construtivos.

Anote em **metros decimais**, ponto como separador: `22.4`, `7.1`.

**Precisão: ±0,5 m basta.** Não vale buscar centímetros — a variação de RSSI por orientação do
aparelho no mesmo ponto chegou a 15 dB nesta campanha (caso do M-02, em pé versus no chão).
Meio metro de incerteza posicional é irrelevante perto disso.

#### Lista concreta de coordenadas a medir

> **Pareamento entre bandas: CONFIRMADO.** 2,4 GHz e 5 GHz foram medidos no mesmo dia, mesmo
> horário e mesmos locais. São **17 posições distintas** preenchendo 29 linhas do CSV — nas
> linhas pareadas, repita o mesmo `x`, `y`.

| Andar | 5 GHz ↔ 2,4 GHz | Locais sem leitura de 5 GHz |
|---|---|---|
| 1º andar | M-18↔M-01, M-19↔M-02, M-20↔M-03, M-21↔M-04 | — (o M-05 é o M-22, zona cega) |
| Térreo | M-23↔M-06, M-24↔M-07, M-25↔M-08, M-26↔M-09 | M-10, M-11 |
| Subsolo | M-27↔M-12, M-28↔M-13, M-29↔M-14, M-30↔M-17 | M-15, M-16 |

> **A distância difere entre bandas no mesmo local, e isso está correto.** M-01 registra 8,5 m
> e M-18 registra 4,0 m na mesma posição, porque `distancia_ao_ap` é a distância ao **AP
> associado**, e o aparelho associou a APs diferentes em cada banda — o *band steering* foi
> observado no M-03. O `x`, `y` é compartilhado; a distância, não.

As descrições abaixo vêm do documento v2, que nomeou apenas os 6 pontos com obstáculo. Os
demais estão como ⬜ **a identificar** — recupere-os das anotações da campanha. Não invente.

**1º andar — 5 coordenadas**

| Medir | Ponto | Dist. AP | Referência |
|---|---|---|---|
| Fundo da sala **M102** | M-01 | 8,5 m | ✅ conhecida |
| Ponto a 1 m do AP (nº 1) | M-02 | 1,0 m | ⬜ a identificar — leitura de referência do modelo |
| Ponto a 1 m do AP (nº 2) | M-03 | 1,0 m | ⬜ a identificar — onde houve *band steering* p/ 5 GHz |
| Ponto a 4 m sem obstáculo | M-04 | 4,0 m | ⬜ a identificar |
| **Escada de incêndio** | M-05 | 6,0 m | ✅ conhecida — porta corta-fogo, 21,1 dB; é onde o 5 GHz não conectou (M-22) |

*Não medir separado:* M-18, M-19, M-20 e M-21 são os mesmos locais de M-01, M-02, M-03 e M-04.

**Térreo — 6 coordenadas**

| Medir | Ponto | Dist. AP | Referência |
|---|---|---|---|
| **Sala entre os dois APs** | M-06 | 4,0 m | ✅ conhecida |
| Ponto a 1 m do AP (nº 1) | M-07 | 1,0 m | ⬜ a identificar — RSSI −25 dBm com 0 % de qualidade de canal |
| Ponto a 1 m do AP (nº 2) | M-08 | 1,0 m | ⬜ a identificar |
| Ponto a 3 m sem obstáculo | M-09 | 3,0 m | ⬜ a identificar |
| **Escada do Térreo** | M-10 | 6,0 m | ✅ conhecida — porta metálica, 9,1 dB |
| Ponto a 2 m sem obstáculo | M-11 | 2,0 m | ⬜ a identificar |

*Não medir separado:* M-23, M-24, M-25 e M-26 são os mesmos locais de M-06, M-07, M-08 e M-09.

**Subsolo — 6 coordenadas**

| Medir | Ponto | Dist. AP | Referência |
|---|---|---|---|
| **Sala entre os dois APs** | M-12 | 4,0 m | ✅ conhecida |
| Ponto a 1 m do AP (nº 1) | M-13 | 1,0 m | ⬜ a identificar — excluído do ajuste |
| Ponto a 1 m do AP (nº 2) | M-14 | 1,0 m | ⬜ a identificar — excluído do ajuste |
| Ponto a **15 m do AP associado** | M-15 | 15,0 m | ⬜ a identificar — *sticky client*; sustenta todo o α |
| **Escada do Subsolo** | M-16 | 18,0 m | ✅ conhecida — porta metálica, 6,6 dB |
| Ponto a 3 m sem obstáculo | M-17 | 3,0 m | ⬜ a identificar |

*Não medir separado:* M-27, M-28, M-29 e M-30 são os mesmos locais de M-12, M-13, M-14 e M-17.

**Total: 17 posições** — 5 no 1º andar, 6 no Térreo, 6 no Subsolo, preenchendo as 29 linhas do CSV.

**APs — quantidade a levantar em campo**

Não sei quantos são. O que os dados permitem afirmar:

- **1º andar:** ao menos 2 (duas leituras distintas a 1 m — M-02 e M-03)
- **Térreo:** ao menos 2 — "sala **entre** APs" mais duas leituras a 1 m
- **Subsolo:** ao menos 2 — "sala **entre** APs", duas leituras a 1 m, e mais um AP distante
  (o do M-15, a 15 m)

Estimativa: **6 a 7 APs**, a confirmar.

**Cantos dos pavimentos — 4 por andar, não se mede**

Bastam a largura `L` e a altura `A` do pavimento; as coordenadas saem prontas e são os pontos
de controle que você digita no Georreferenciador do QGIS:
`(0, 0)` · `(L, 0)` · `(L, A)` · `(0, A)`. Leia **L** e **A** das cotas da planta.

---

#### Plantas do Bloco M — já disponíveis

O projeto arquitetônico executivo da UFCA (2019, arq. Louise Buarque de Gusmão Barbosa,
escala **1:75**) cobre os três pavimentos da campanha:

| Prancha | Título no projeto | `andar` no CSV |
|---|---|---|
| `01/13` | PLANTA-BAIXA — **1º PAVIMENTO** — SUBSOLO | `Subsolo` |
| `02/13` | PLANTA-BAIXA — **2º PAVIMENTO** — TÉRREO | `Terreo` |
| `03/13` | PLANTA-BAIXA — **3º PAVIMENTO** — 1º andar | `1o` |

> ⚠️ **A numeração de pavimento do projeto não é a da campanha.** O que a campanha chama de
> "1º andar" é o **3º pavimento** na planta. Cuidado ao nomear os arquivos.

**O que as plantas resolvem**

- **Salas nomeadas:** `M01`–`M05` no Subsolo, `M101`–`M105` no 1º andar. Isso localiza o
  **M-01** ("fundo da M102" — sala do meio da ala inferior do 1º andar) e confirma que a M102
  é mesmo do 1º andar, não a M02 do Subsolo.
- **Escadas** identificáveis nos três pavimentos, junto ao hall e aos elevadores — localiza
  **M-05**, **M-10** e **M-16**.
- **Corroboração do obstáculo:** o Quadro de Esquadrias lista a **P7, porta corta-fogo,
  100×210 cm, em "Escadas"** — é o obstáculo dos 21,1 dB do M-05, confirmado pelo projeto.

**O que as plantas NÃO resolvem**

- **Posição dos APs.** São plantas *arquitetônicas*. Access points estariam no projeto de
  **cabeamento estruturado / telecom**, outra prancha do conjunto de 13. Vale pedir; se não
  existir, levante em campo — AP instalado nem sempre está onde o projeto previu.
- **Os 11 locais marcados como ⬜.** Nenhuma planta supre a anotação de campo.

**Conferência de ordem de grandeza:** área total do Bloco M = **3.914,52 m²**; o Quadro de
Cobogós cita "Escadas — 4º Andar", indicando ~6 pavimentos. Isso dá ≈ **650 m²/pavimento**,
compatível com uma envoltória da ordem de **32 × 20 m**. Use como conferência do que você ler
nas cotas — **não como medida**.

---

#### Como funciona a medição

**Use a malha estrutural, não a trena.** As plantas trazem eixos estruturais cotados —
numerados `01` a `06` na horizontal e `A` a `D` na vertical, com as distâncias entre eixos
escritas na cadeia de cotas (vãos aparentemente regulares, na ordem de 6,20 m).

Isso é melhor que medir com trena a partir de paredes: os **pilares são visíveis em campo**,
então você tem referências físicas espalhadas pelo prédio inteiro e nunca precisa esticar
trena por 20 m.

**Procedimento, por pavimento**

1. Adote a interseção do **eixo 01 com o eixo A** como origem `(0, 0)`.
2. Leia na planta a cota acumulada de cada eixo a partir da origem (ex.: eixo 02 em
   x = 6,20 m; eixo 03 em x = 12,40 m; e assim por diante).
3. Em campo, para cada ponto: identifique entre quais eixos ele está e meça apenas o
   **deslocamento até o eixo mais próximo** — distância curta, trena comum resolve.
4. `x` = cota acumulada do eixo + deslocamento medido. Mesma lógica para `y` com os eixos A–D.
5. Repita para **cada AP**.

**Regras do referencial**

- `x` cresce para a direita, `y` cresce para cima, na orientação em que a planta será usada.
- **Mesmo canto do prédio como origem nos três pavimentos.** Origens diferentes por andar
  fazem os mapas não se sobreporem, e a comparação entre pavimentos se perde.
- Unidade: **metros decimais**, ponto como separador — `22.4`, `7.1`.

**Precisão: ±0,5 m basta.** Não vale buscar centímetros — a variação de RSSI por orientação do
aparelho no mesmo ponto chegou a 15 dB nesta campanha (caso do M-02, em pé versus no chão).

---

**Como registrar no CSV**

Acrescente as colunas `x`, `y` (e `local`, o rótulo textual). Nas linhas pareadas de 5 GHz,
**repita o mesmo `x`, `y`**:

```csv
ponto,banda,rssi,d,obst,canal,melhor,pct,andar,livre,x,y,local
1,2.4,-60,8.5,"Parede, porta",1,6,35,1o,False,22.4,7.1,Fundo da sala M102
18,5.0,-62,4.0,Parede/porta,36,100,100,1o,False,22.4,7.1,Fundo da sala M102
```

**Como registrar na configuração**

`planta`, `dimensoes_m` e `aps` são declarados **por pavimento**. As chaves devem ser
exatamente os valores da coluna `andar` do CSV:

```python
"planta": {
    "Terreo":  DIR_DADOS / "planta_M_terreo.png",   # prancha 02/13
    "1o":      DIR_DADOS / "planta_M_1andar.png",   # prancha 03/13
    "Subsolo": DIR_DADOS / "planta_M_subsolo.png",  # prancha 01/13
},
"dimensoes_m": {
    "Terreo":  (32.0, 20.0),      # (largura, altura) REAIS, lidas das cotas
    "1o":      (32.0, 20.0),
    "Subsolo": (32.0, 20.0),
},
"aps": {
    "Terreo":  {"AP-M-T1": (12.0, 8.0), "AP-M-T2": (24.0, 8.0)},
    "1o":      {"AP-M-11": (14.0, 9.5)},
    "Subsolo": {"AP-M-S1": (10.0, 6.0)},
},
```

Pavimento sem `dimensoes_m` é **pulado com aviso**; os demais seguem normalmente. Assim você
pode preencher um andar de cada vez, à medida que mede.

> **Recorte a planta antes de exportar.** As pranchas trazem carimbo, Quadro de Esquadrias e
> Quadro de Revestimentos ocupando quase metade da folha. Se você exportar a página inteira,
> o `dimensoes_m` vai mapear a folha toda nos metros informados e o desenho sairá comprimido
> num canto, com **todas as coordenadas erradas**. Exporte só a área do desenho, recortando
> exatamente na envoltória cujas dimensões você declarar. Use 150–200 dpi. Os PDFs são
> vetoriais, então o zoom não perde nitidez — e o recorte elimina de quebra a tarja
> "PRODUCED BY AN AUTODESK STUDENT VERSION" das bordas.

**Resultado.** Passam a ser gerados `fig_rssi_dbm_M_<banda>_pav<n>.png`, além de SNR e
latência quando essas colunas existirem — com contornos destacados em −67 e −70 dBm e hachura
sobre a região fora do fecho convexo da amostragem. E em `saida/qgis/`, um par `.png` + `.pgw`
por métrica/banda/andar, mais o `pontos_M.csv` agora com geometria.

> **Atenção — `planta` e `aps` são únicos por bloco, não por andar.** Como o Bloco M tem 3
> pavimentos com plantas e posições de AP diferentes, isso não comporta o que você vai medir:
> os APs do Subsolo apareceriam desenhados também no mapa do Térreo. **Resolver antes de ir a
> campo.** Ver seção 7.1.

---

### 3.2 ~~Vazão e latência~~ — REMOVIDO

<!-- REMOVIDO: vazão/latência não medidas -->

> **Estas medições não foram realizadas e foram removidas do escopo.** O pipeline não
> possui mais módulo, coluna nem célula de vazão, latência ou perda de pacotes.
>
> Consequência metodológica que permanece registrada: sem vazão não se distingue um ponto
> limitado por **propagação** de um ponto limitado por **disputa do meio**. A suspeita de
> congestionamento em 2,4 GHz se apoia apenas na camada de canal (descasamento e
> `pct_melhor_canal`), que é indicador relativo, não medida de desempenho.

---

### 3.3 Redes vizinhas → SINR real

**Destrava:** o "I" do SINR. Hoje o notebook calcula **SNR**, não SINR.

**Por que.** Sem a lista de vizinhos não há termo de interferência no denominador. O piso de
ruído adotado é **−95 dBm, uniforme, não medido** (parâmetro `PARAMS["piso_ruido_dbm"]`,
impresso em toda figura que dependa dele). A capacidade de Shannon calculada é, portanto, um
**teto otimista**.

**Como medir.** Varredura passiva, sem nova campanha completa: em cada ponto, registre a lista
de redes vizinhas com SSID, canal e RSSI — o WiFi Analyzer já exibe isso. Para o schema atual,
basta a contagem de vizinhas **no mesmo canal**:

```csv
...,redes_vizinhas_mesmo_canal
...,4
```

**Para o cálculo rigoroso de SINR** (além do que o schema atual cobre), o procedimento é:

1. converter o RSSI de cada vizinha de dBm para mW e **somar em potência linear** — dBm não se
   soma diretamente;
2. ponderar cada vizinha pelo fator de sobreposição espectral (em 2,4 GHz os canais distam
   5 MHz com largura de 20 MHz, então canais adjacentes interferem parcialmente);
3. aplicar `SINR = S / (I + N)` com `N = −95 dBm`, e daí `C = B·log₂(1 + SINR)`.

Se você coletar a lista completa de vizinhas (uma linha por vizinha, por ponto), me avise:
esse cálculo pede uma tabela auxiliar e uma função a mais, que ainda não estão implementadas —
o notebook hoje só consome a contagem `redes_vizinhas_mesmo_canal`.

---

### 3.4 Distâncias intermediárias

**Destrava:** α em 5 GHz, o ajuste isolado do 1º andar, e resolve a fragilidade do modelo de
2,4 GHz.

Este item não é uma coluna faltando — é **cobertura amostral**. Três problemas, uma só causa:

| Problema | Diagnóstico da execução |
|---|---|
| α em 5 GHz não estimável | as 9 leituras sem obstáculo estão em apenas **2 distâncias** (1 m e 3 m); o mínimo é 3. A dispersão a 1 m chega a 21 dB, superando a variação esperada entre 1 m e 3 m |
| 1º andar sem ajuste próprio | apenas **2 distâncias distintas** sem obstáculo |
| α de 2,4 GHz frágil | **M-15, a 15 m, é a única leitura livre além de 4 m**. Removendo-o, α cai de 2,11 para 1,61 e o R² de 0,64 para 0,30 — o teste de alavancagem sinaliza esse ponto em vermelho |

**O que medir.** Leituras **sem obstáculo** a **6, 10 e 15 m**, nas duas bandas, em cada
pavimento. É a mesma recomendação para os três problemas: preenche o vazio entre 4 m e 15 m em
2,4 GHz e cria alavanca em 5 GHz.

**Como registrar.** Linhas novas no CSV, com `obst` igual a `Nenhum` e a numeração de ponto
continuando a sequência. Nada muda na configuração.

> As guardas que produzem esses bloqueios são parametrizadas — `PARAMS["min_distancias_distintas"] = 3`
> e `PARAMS["min_pontos_ajuste"] = 3`. **Não as afrouxe para "destravar" a análise**: elas
> existem para impedir que um α sem sustentação amostral seja reportado como se fosse medida.

---

### 3.5 BSSID (recomendado)

**Não está no schema canônico, mas resolveria duas ambiguidades reais do estudo:**

1. **A exclusão de P13/P14.** Ambos foram medidos a 1 m de um AP no Subsolo e registram −40 e
   −44 dBm, contra −25 e −28 dBm em leituras equivalentes a 1 m no Térreo. Uma diferença de até
   19 dB na mesma distância nominal não é explicável por perda de percurso. A hipótese é que o
   aparelho estivesse associado a outro AP — mas **sem o BSSID não há como confirmar**, e por
   isso a exclusão está declarada explicitamente em `exclusoes_ajuste`, com o motivo por escrito,
   para que o leitor possa recusá-la.
2. **Os casos de sticky client.** Nos pontos 15 e 16 o aparelho permaneceu associado a um AP a
   15–18 m havendo alternativa a 6–8 m. O BSSID confirmaria isso objetivamente.

Se for coletar, acrescente uma coluna `bssid` ao CSV. Ela será carregada e exportada para o
QGIS, mas **nenhuma análise a consome hoje** — me avise se quiser que o ajuste passe a agrupar
por AP associado.

---

### 3.6 Metadados do bloco

Campos da configuração que estão vazios e alimentam o **aviso de comparabilidade** da Fase 6.4:

```python
"modelo_ap": None,   # <- não registrado em campo
```

Potência de transmissão e ganho de antena distintos deslocam o RSSI(d₀) **sem que a construção
tenha mudado**. Sem esse campo, a Fase 6.4 emite o alerta de que a diferença de α entre blocos
pode refletir infraestrutura, e não a edificação. Preencha com o modelo real do AP
(ex.: `"Ubiquiti UniFi AC Pro"`) — a informação costuma estar na etiqueta do equipamento ou com
a equipe de TI.

---

### 3.7 Bloco I completo

Abra a seção **`>>> ADICIONAR BLOCO I AQUI <<<`** do notebook, descomente e preencha:

```python
BLOCOS["I"] = {
    "csv": DIR_DADOS / "dados_bloco_I.csv",
    "data_campanha": "AAAA-MM-DD",
    "modelo_ap": "PREENCHER",
    "n_leituras_campanha": None,
    "planta": DIR_DADOS / "planta_I.png",
    "dimensoes_m": (0.0, 0.0),
    "aps": {"AP-I1": (0.0, 0.0)},
    "prefixo_ponto": "I",                # gera IDs únicos I-01, I-02, ...
    "mapa_colunas": {},                  # vazio: colete já no schema canônico
    "exclusoes_ajuste": {},              # só se houver ponto a excluir, COM motivo
}
```

**Recomendações para a coleta do Bloco I**

- Colete **já no schema canônico** — assim `mapa_colunas` fica vazio.
- Meça `x`, `y` desde o início: é o item que mais custa recuperar depois.
- Garanta **pelo menos 3 distâncias distintas sem obstáculo por banda**, cobrindo 1, 3, 6, 10 e
  15 m. Isso evita repetir o bloqueio de α que ocorreu em 5 GHz no Bloco M.
- Meça vazão e latência ao menos num subconjunto de pontos.
- Mantenha o mesmo protocolo do Bloco M: mesma orientação do aparelho, distância ao **AP
  associado** (não ao mais próximo), e obstáculos descritos em texto.

O identificador de ponto é prefixado por bloco (`M-01`, `I-01`), então **não há colisão de
numeração** — pode numerar a partir de 1 novamente.

Com dois blocos, a Fase 6.4 liga sozinha: figura com as retas de ajuste sobrepostas por banda,
tabela comparativa (α, R², faixa de RSSI, vazão média, qualidade de canal, taxa de descasamento)
e os avisos de comparabilidade. **O ajuste continua sendo feito por bloco × banda, nunca
agregando blocos** — e `andar` é sempre tratado dentro do bloco, de modo que "Térreo do M" e
"Térreo do I" jamais caem no mesmo grupo.

---

## 4. Como verificar que destravou

Rode o notebook inteiro e confira, na ordem:

1. **Fase 5.1 — relatório de completude.** A coluna preenchida sai da lista de VAZIAS e a
   análise correspondente muda de `BLOQUEADA` para `HABILITADA` na tabela de habilitação.
2. **Seção final — "ANÁLISES BLOQUEADAS".** O item some da lista.
3. **Seção final — "O QUE PREENCHER PARA DESTRAVAR CADA ANÁLISE".** Deixa de citar a coluna.
4. **Teste de regressão.** Deve continuar **11/11**. Os valores do Bloco M em 2,4 GHz não podem
   mudar por acrescentar coluna nova ou outro bloco — se mudarem, há erro de digitação nos
   dados existentes. Acrescentar **linhas** em 2,4 GHz (seção 3.4), por outro lado, **vai**
   alterar α legitimamente; nesse caso atualize os valores esperados na célula do teste e
   registre o motivo.

---

## 5. Ambiente

- `pandas`, `numpy`, `scipy`, `matplotlib` — **presentes**.
- `rasterio` — **ausente**. A exportação usa **PNG + world file `.pgw`**, que o QGIS lê
  nativamente. Não é necessário instalar; se instalar, o notebook passa a gerar GeoTIFF sozinho.
- `pykrige` — **ausente**. Não é usado; a interpolação é `griddata` com alternativa IDW.
- `ipykernel` — **ausente**. É o único que atrapalha: o VS Code vai pedir para instalar na
  primeira vez que você selecionar o kernel. Aceite o prompt, ou rode `pip install ipykernel`.

---

## 6. Resumo por prioridade

### 6.1 Pendências de dado (dependem de campo)

| Prioridade | Item | Esforço | Destrava |
|---|---|---|---|
| **Alta** | `x`, `y` + planta + dimensões | campanha de medição em planta | toda a Fase 5.2 e 5.3, o georreferenciamento |
| **Alta** | Distâncias de 6, 10 e 15 m sem obstáculo | poucas leituras extras | α em 5 GHz, robustez do α em 2,4 GHz |
| **Alta** | Adensar a malha (15–25 pontos/andar) | a maior parte do esforço de campo | mapa com cobertura útil, não 90 % hachurado |
| Média | Redes vizinhas por ponto | varredura passiva | SINR real no lugar de SNR |
| Média | `modelo_ap` | consulta à equipe de TI | aviso de comparabilidade da 6.4 |
| Média | Preencher a coluna `local` | anotações da campanha | rótulos legíveis nas figuras e no QGIS |
| Baixa | BSSID | registro durante a coleta | confirma a exclusão de P13/P14 e o sticky client |
| — | Bloco I | campanha completa | Fase 6.4 |

### 6.2 Pendências de código (não dependem de campo)

Detalhadas na seção 7.

| Prioridade | Item | Quando resolver |
|---|---|---|
| ✅ | ~~`planta` e `aps` por andar~~ | **resolvido** — ver 7.1 |
| Baixa | Suporte a zona cega (leitura sem RSSI) | antes de mapear o M-22 |
| Baixa | Cálculo rigoroso de SINR | só se coletar a lista completa de vizinhas |
| Baixa | Consumir `bssid` na análise | só se registrar BSSID |

---

## 7. Pendências do notebook (código)

Diferente das anteriores: estas não dependem de coleta. São limitações da implementação atual,
registradas para não serem descobertas tarde demais.

### 7.1 ~~`planta` e `aps` únicos por bloco~~ — ✅ RESOLVIDO

`planta`, `dimensoes_m` e `aps` passaram a ser declarados **por pavimento**, com as chaves
iguais aos valores da coluna `andar`. Cada pavimento tem seu próprio referencial local e sua
própria transformação afim no QGIS.

Implementação: resolvedores `planta_do_andar()`, `dimensoes_do_andar()` e `aps_do_andar()`.
A forma antiga (valor único por bloco) continua aceita e é aplicada a todos os andares, então
nada quebra. Pavimento sem `dimensoes_m` é pulado com aviso, e as análises não-espaciais desse
pavimento seguem normalmente.

Validado com um bloco de teste de 3 pavimentos de dimensões diferentes: os world files saíram
com resolução distinta por andar (0,15 m/px num pavimento de 30 m, 0,12 m/px num de 24 m), e o
pavimento sem geometria foi pulado sem interromper a execução. Teste de regressão intacto.

### 7.2 Zona cega não é representável

O **ponto 22** (5 GHz, no local do M-05 — escada de incêndio do 1º andar) não estabeleceu
conexão e **não tem linha no CSV**. É informação
relevante para o mapa — "aqui não conectou" —, mas hoje não há como representá-la: a validação
da Fase 5.1 descarta linhas sem RSSI, por decisão de projeto (leitura sem RSSI não entra em
nenhum cálculo).

Para marcá-la na planta seria preciso uma coordenada **e** um tratamento específico de zona
cega — uma categoria à parte, plotada como marcador, fora da interpolação. Não implementado.

### 7.3 SINR rigoroso não implementado

O notebook consome apenas a contagem `redes_vizinhas_mesmo_canal` e calcula **SNR**, não SINR,
com piso de ruído adotado de −95 dBm (uniforme, não medido). O procedimento correto — soma em
potência linear, ponderação por sobreposição espectral — está descrito na seção 3.3, mas exige
uma tabela auxiliar (uma linha por vizinha, por ponto) e uma função nova.

### 7.4 `bssid` é carregado, mas nenhuma análise o consome

Se a coluna existir, ela é lida e exportada para o QGIS. Nenhum cálculo a utiliza. Para que o
ajuste passasse a agrupar por AP associado, seria preciso alterar a Fase 6.1.

---

## 8. Checklist de campo consolidado

Tudo que precisa ser levantado, numa ida só. Os itens de coordenada estão detalhados na
seção 3.1; os de medição, nas seções 3.2 a 3.4.

**Antes de sair**

- [x] ~~Resolver a pendência 7.1 (`planta`/`aps` por andar)~~ — feito
- [x] ~~Obter as 3 plantas baixas~~ — pranchas 01/13, 02/13 e 03/13 do projeto executivo
- [ ] Ler nas cotas: largura `L` e altura `A` de cada pavimento — **3 pares de números**
- [ ] Ler as cotas acumuladas dos eixos estruturais `01`–`06` e `A`–`D`
- [ ] Recortar cada prancha, deixando **só o desenho da planta**, a 150–200 dpi
- [ ] Pedir a prancha de **cabeamento estruturado / telecom**, se existir (posição dos APs)
- [ ] Fixar a origem `(0,0)` na interseção dos eixos `01` × `A`, **a mesma nos três pavimentos**

**Geometria**

- [ ] Coordenada de **cada AP**, por pavimento — estimados **6 a 7** no total

**Pontos já existentes** (para georreferenciar o que já foi medido)

- [ ] 1º andar: coordenadas de M-01 a M-05 — **5 pontos**
- [ ] Térreo: coordenadas de M-06 a M-11 — **6 pontos**
- [ ] Subsolo: coordenadas de M-12 a M-17 — **6 pontos**
- [ ] Ao preencher o CSV, repetir o mesmo `x`, `y` nas linhas de 5 GHz pareadas (quadro da seção 3.1)
- [ ] Preencher a coluna `local` dos 11 pontos marcados como ⬜ *a identificar*

**Pontos novos** (para o mapa cobrir o prédio e destravar o α de 5 GHz)

- [ ] Adensar até **15 a 25 pontos por pavimento**, distribuídos por circulação e salas
- [ ] Garantir leituras **sem obstáculo a 6, 10 e 15 m**, nas duas bandas, em cada pavimento
- [ ] Anotar `x`, `y` de cada ponto novo no mesmo referencial

**Medições por ponto** (ao menos num subconjunto representativo)

- [ ] RSSI nas duas bandas, mesma orientação do aparelho usada na campanha original
- [ ] Distância ao **AP associado** (não ao mais próximo)
- [ ] Obstáculos descritos em texto
- [ ] Contagem de redes vizinhas no mesmo canal → `redes_vizinhas_mesmo_canal`
- [ ] BSSID do AP associado (opcional, mas resolve a ambiguidade de P13/P14)

**Metadados**

- [ ] Modelo do AP → `modelo_ap` na configuração
- [ ] Data da campanha → `data_campanha`

> **Uma campanha resolve tudo.** Coordenadas, adensamento da malha, distâncias intermediárias,
> vazão e latência são o mesmo trabalho de campo. Se for voltar ao Bloco M, faça os quatro na
> mesma ida — e aplique o mesmo protocolo desde o início no Bloco I, onde nada disso precisa
> ser remediado depois.
