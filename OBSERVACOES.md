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
| 6.2 Cruzamento RSSI × throughput | `throughput_tcp_mbps` | [3.2](#32-vazão-e-latência) |
| 6.3 Shannon vs. vazão medida | `throughput_tcp_mbps` | [3.2](#32-vazão-e-latência) |
| Análise de latência | `latencia_media_ms` | [3.2](#32-vazão-e-latência) |
| Análise de perda de pacotes | `perda_pacotes_pct` | [3.2](#32-vazão-e-latência) |
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
acrescente `x`, `y`, `throughput_tcp_mbps` etc. e preencha. Nada mais.

Schema canônico completo:

```
bloco, ponto, andar, local, x, y, banda_ghz, rssi_dbm, snr_estimado_db,
canal, canal_melhor, qualidade_melhor_canal_pct, redes_vizinhas_mesmo_canal,
distancia_ao_ap, obstaculos, throughput_tcp_mbps, throughput_udp_mbps,
latencia_media_ms, perda_pacotes_pct
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

#### Lista concreta de coordenadas a medir

As descrições abaixo vêm do documento v2, que nomeou apenas os 6 pontos com obstáculo. Os
demais estão como ⬜ **a identificar** — recupere-os das anotações da campanha. Não invente.

**1º andar — 5 a 7 coordenadas**

| Medir | Ponto | Dist. AP | Referência |
|---|---|---|---|
| Fundo da sala **M102** | M-01 | 8,5 m | ✅ conhecida |
| Ponto a 1 m do AP (nº 1) | M-02 | 1,0 m | ⬜ a identificar — leitura de referência do modelo |
| Ponto a 1 m do AP (nº 2) | M-03 | 1,0 m | ⬜ a identificar — onde houve *band steering* p/ 5 GHz |
| Ponto a 4 m sem obstáculo | M-04 | 4,0 m | ⬜ a identificar |
| **Escada de incêndio** | M-05 | 6,0 m | ✅ conhecida — porta corta-fogo, 21,1 dB |
| Ponto de 5 GHz a 4 m c/ parede | M-18 | 4,0 m | ⬜ **confirmar se é o mesmo local do M-04** |
| Ponto de 5 GHz a 3 m | M-21 | 3,0 m | ⬜ **confirmar se coincide com algum acima** |

*Não medir separado:* M-19 e M-20 são os mesmos locais de M-02 e M-03.

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
*Fica de fora:* a zona cega do **M-22** — ver seção 7.2.

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

> **Por que 17 e não 29.** Comparando distância e obstáculo, o pareamento entre bandas é exato
> no Térreo (23↔6, 24↔7, 25↔8, 26↔9) e no Subsolo (27↔12, 28↔13, 29↔14, 30↔17). No 1º andar,
> 19↔2 e 20↔3 são claros, mas **M-18 e M-21 não têm par óbvio**. Confirme: se pareiam, são 17
> posições; se não, 19. Nas linhas pareadas do CSV, repita o mesmo `x`, `y`.

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
`(0, 0)` · `(L, 0)` · `(L, A)` · `(0, A)`. Meça só **L** e **A** de cada pavimento.

**Como medir**

1. Consiga a planta baixa de cada pavimento em imagem (`.png` ou `.jpg`). A secretaria ou a
   prefeitura do campus costuma ter; uma foto legível do projeto arquitetônico serve.
2. Defina **um referencial por pavimento**, sempre o mesmo:
   - origem `(0, 0)` no **canto inferior esquerdo** da planta;
   - `x` cresce para a direita, `y` cresce para cima;
   - unidade em **metros**.
3. Meça as dimensões reais externas do pavimento (largura × altura no plano da planta).
4. Para cada ponto de medição, registre `x` e `y` em metros nesse referencial. Trena a laser
   resolve; na falta dela, conte módulos construtivos (pilares, esquadrias) já cotados na planta.
5. Meça também a posição de **cada AP** no mesmo referencial.

> Se os pavimentos tiverem plantas diferentes, mantenha a origem no mesmo canto do prédio em
> todos, para que os mapas fiquem comparáveis entre andares.

**Como registrar**

No CSV, acrescente as colunas `x`, `y` (e `local`, se quiser o rótulo textual):

```csv
ponto,banda,rssi,d,obst,canal,melhor,pct,andar,livre,x,y,local
1,2.4,-60,8.5,"Parede, porta",1,6,35,1o,False,22.4,7.1,Fundo da M102
2,2.4,-30,1.0,Nenhum,6,6,15,1o,True,14.0,9.5,Sob o AP da M102
```

Na célula de configuração, preencha os três campos do bloco:

```python
"planta": DIR_DADOS / "planta_M_terreo.png",   # imagem da planta baixa
"dimensoes_m": (40.0, 25.0),                   # (largura, altura) REAIS em metros
"aps": {"AP-M1": (14.0, 9.5), "AP-M2": (31.0, 12.0)},
```

**Resultado.** Passam a ser gerados `fig_rssi_M_<banda>_<andar>.png`, além de SNR, throughput e
latência quando essas colunas existirem — com contornos destacados em −67 e −70 dBm e hachura
sobre a região fora do fecho convexo da amostragem. E em `saida/qgis/`, um par `.png` + `.pgw`
por métrica/banda/andar, mais o `pontos_M.csv` agora com geometria.

> **Atenção — `planta` e `aps` são únicos por bloco, não por andar.** Como o Bloco M tem 3
> pavimentos com plantas e posições de AP diferentes, isso não comporta o que você vai medir:
> os APs do Subsolo apareceriam desenhados também no mapa do Térreo. **Resolver antes de ir a
> campo.** Ver seção 7.1.

---

### 3.2 Vazão e latência

**Destrava:** Fase 6.2 (classificação cruzada completa), Fase 6.3 (confronto teoria × prática),
análises de latência e perda, e os heatmaps dessas métricas.

**Por que importa.** É a lacuna mais consequente do estudo. Sem vazão não se distingue um ponto
limitado por **propagação** de um ponto limitado por **disputa do meio** — e essa é exatamente a
distinção que a Fase 6.2 existe para fazer. Os dois casos geram a mesma queixa do usuário e
pedem intervenções opostas: um exige reposicionar AP, o outro exige replanejar canal. Hoje a
suspeita de congestionamento em 2,4 GHz se apoia só na qualidade de canal (20,4 % contra 94,3 %
em 5 GHz), que é indicador relativo, não medida de desempenho.

**Como medir** (não exige nova campanha completa; basta um subconjunto representativo de pontos)

- **Vazão** — `iperf3` contra um servidor na rede cabeada do campus:
  ```
  iperf3 -c <ip_do_servidor> -t 30            # TCP  -> throughput_tcp_mbps
  iperf3 -c <ip_do_servidor> -u -b 100M -t 30 # UDP  -> throughput_udp_mbps
  ```
  Anote a média dos 30 s. Rode nas duas bandas, no mesmo ponto e na mesma orientação do
  aparelho usada na medição de RSSI.
- **Latência e perda** — `ping` com 50 pacotes para o gateway:
  ```
  ping -n 50 <ip_do_gateway>     # Windows
  ```
  Registre a média em ms (`latencia_media_ms`) e o percentual de perda (`perda_pacotes_pct`).

**Como registrar**

```csv
...,throughput_tcp_mbps,throughput_udp_mbps,latencia_media_ms,perda_pacotes_pct
...,42.7,58.1,12.4,0.0
```

**Ajuste os limiares** se o seu ambiente pedir. Eles estão no topo do notebook, em `PARAMS`:

```python
"rssi_bom_dbm": -67.0,          # acima disso, sinal considerado bom
"throughput_baixo_mbps": 20.0,  # abaixo disso, vazão considerada baixa
```

**Resultado.** Tabela classificada por ponto nas 4 categorias (causa física / interferência ou
congestionamento / investigar / operação nominal), o scatter com os quadrantes coloridos, e o
gráfico de Shannon passa a confrontar capacidade teórica × vazão medida, destacando os pontos
que mais se afastam da tendência.

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
| **Alta** | Vazão e latência | subconjunto de pontos, `iperf3` + `ping` | Fases 6.2 e 6.3 completas |
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
| **Alta** | `planta` e `aps` por andar, não por bloco | **antes da campanha** — muda o formato do que você anota |
| Baixa | Suporte a zona cega (leitura sem RSSI) | antes de mapear o M-22 |
| Baixa | Cálculo rigoroso de SINR | só se coletar a lista completa de vizinhas |
| Baixa | Consumir `bssid` na análise | só se registrar BSSID |

---

## 7. Pendências do notebook (código)

Diferente das anteriores: estas não dependem de coleta. São limitações da implementação atual,
registradas para não serem descobertas tarde demais.

### 7.1 `planta` e `aps` são únicos por bloco — deveriam ser por andar

**Impacto: alto, e bloqueia o formato da coleta.** A configuração aceita hoje uma única imagem
de planta e um único dicionário de APs por bloco:

```python
"planta": DIR_DADOS / "planta_M.png",
"aps": {"AP-M1": (14.0, 9.5)},
```

O Bloco M tem **3 pavimentos**, com plantas distintas e APs em posições distintas. Na estrutura
atual, os APs do Subsolo apareceriam desenhados também no mapa do Térreo, e apenas uma das três
plantas entraria como fundo — as outras figuras sairiam com geometria correta, porém sem imagem
por baixo.

**Correção necessária:** trocar os dois campos por dicionários indexados por andar —
`{"Terreo": ..., "1o": ..., "Subsolo": ...}`. Não afeta nenhuma lógica de análise.

> **Resolva isto antes de ir a campo.** É o que define se você anota "os APs do Bloco M" ou
> "os APs de cada pavimento do Bloco M".

### 7.2 Zona cega não é representável

O **ponto 22** (Térreo, 5 GHz) não estabeleceu conexão e **não tem linha no CSV**. É informação
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

- [ ] Resolver a pendência 7.1 (`planta`/`aps` por andar) — define o formato da anotação
- [ ] Obter as **3 plantas baixas** em imagem (Térreo, 1º andar, Subsolo)
- [ ] Definir o referencial: origem `(0,0)` no **mesmo canto do prédio** em todos os pavimentos,
      `x` para a direita, `y` para cima, em metros

**Geometria**

- [ ] Largura `L` e altura `A` de cada pavimento — **3 pares de números**
- [ ] Coordenada de **cada AP**, por pavimento — estimados **6 a 7** no total

**Pontos já existentes** (para georreferenciar o que já foi medido)

- [ ] 1º andar: coordenadas de M-01 a M-05 — **5 pontos** (+ M-18 e M-21 se forem locais distintos)
- [ ] Térreo: coordenadas de M-06 a M-11 — **6 pontos**
- [ ] Subsolo: coordenadas de M-12 a M-17 — **6 pontos**
- [ ] Confirmar o pareamento entre bandas (ver quadro da seção 3.1)
- [ ] Preencher a coluna `local` dos 11 pontos marcados como ⬜ *a identificar*

**Pontos novos** (para o mapa cobrir o prédio e destravar o α de 5 GHz)

- [ ] Adensar até **15 a 25 pontos por pavimento**, distribuídos por circulação e salas
- [ ] Garantir leituras **sem obstáculo a 6, 10 e 15 m**, nas duas bandas, em cada pavimento
- [ ] Anotar `x`, `y` de cada ponto novo no mesmo referencial

**Medições por ponto** (ao menos num subconjunto representativo)

- [ ] RSSI nas duas bandas, mesma orientação do aparelho usada na campanha original
- [ ] Distância ao **AP associado** (não ao mais próximo)
- [ ] Obstáculos descritos em texto
- [ ] `iperf3` TCP e UDP → `throughput_tcp_mbps`, `throughput_udp_mbps`
- [ ] `ping` 50 pacotes → `latencia_media_ms`, `perda_pacotes_pct`
- [ ] Contagem de redes vizinhas no mesmo canal → `redes_vizinhas_mesmo_canal`
- [ ] BSSID do AP associado (opcional, mas resolve a ambiguidade de P13/P14)

**Metadados**

- [ ] Modelo do AP → `modelo_ap` na configuração
- [ ] Data da campanha → `data_campanha`

> **Uma campanha resolve tudo.** Coordenadas, adensamento da malha, distâncias intermediárias,
> vazão e latência são o mesmo trabalho de campo. Se for voltar ao Bloco M, faça os quatro na
> mesma ida — e aplique o mesmo protocolo desde o início no Bloco I, onde nada disso precisa
> ser remediado depois.
