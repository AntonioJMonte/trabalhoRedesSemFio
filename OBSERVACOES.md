# Observações — estado do projeto e o que falta coletar

> Documento de acompanhamento. Reescrito em **18/08/2026**, após a refatoração que moveu
> todo o pipeline do notebook para `src/` e unificou os dois CSVs em `dados/leituras.csv`.
> A versão anterior descrevia a arquitetura antiga e não vale mais.

Para instruções de execução e arquitetura, veja [README.md](README.md).
Para o estado dos dados a cada execução, veja `saidas/relatorio_qualidade.md`, que é
**gerado automaticamente** e sempre reflete o CSV atual — este documento explica o *porquê*,
aquele traz os *números*.

---

## 1. Situação atual

**56 leituras**, IDs 1 a 56, dois prédios, três pavimentos, duas bandas.

| Cobertura de dado | Situação |
|---|---|
| RSSI | 55 de 56 (o M-22 é zona cega em 5 GHz — a ausência **é** o dado) |
| Distância de campo | 56 de 56, todas com `dist_origem = "planta"` |
| BSSID | **31 de 56** |
| Coordenadas `x_m`/`y_m` | **24 de 56**, e todas derivadas de "Abaixo do APn" |
| Altura de medição | **0 de 56** |

**O que roda hoje**

| Análise | Situação |
|---|---|
| Canais — descasamento, reuso, qualidade relativa | ✅ executável |
| Path loss cenário A | ⚠️ 2 de 4 combinações (só 2,4 GHz) |
| Atenuação por obstáculo | ⚠️ 2 de 4 combinações |
| Path loss cenários B/D (dominância) | ❌ falta BSSID completo |
| Path loss cenários C/D (geometria 3D) | ❌ falta `x_m`/`y_m` |
| Perda de laje | ❌ 1 par utilizável no M, mínimo 3 |
| Mapas de calor interpolados | ❌ 2 posições distintas por pavimento |

**Verificação de regressão: passa integralmente.** α = 2,60 (esperado 2,62), R² = 0,906
(esperado 0,91), n = 9, descasamento M 2,4 GHz = 76,5 % (esperado 76 %), L_obstáculo da
porta corta-fogo = 21,1 dB. Se algum desses divergir numa execução futura, o problema é de
parsing ou de mapeamento de coluna — **não é descoberta**.

---

## 2. O que mudou na refatoração de 18/08/2026

| Antes | Agora |
|---|---|
| Notebook de 40 células com toda a lógica inline | 11 módulos em `src/`; o notebook só orquestra |
| Dois CSVs com schemas diferentes | `dados/leituras.csv`, schema único, 56 linhas |
| `andar` como texto (`"1o"`, `"Terreo"`) | `pavimento` inteiro (`1`, `0`, `-1`) |
| Exclusão de pontos por ID, declarada à mão | Critério objetivo de dominância de AP, calculado em runtime |
| Distância única por leitura | `dist_campo_m` + `dist_calc_3d_m` lado a lado |
| BSSID não coletado | 31 BSSIDs transcritos e consumidos por 3 análises |
| Colunas de vazão/latência no schema | Removidas — ver seção 4.5 |
| α reportado com 2 casas decimais | 2 **algarismos significativos**, com IC 95 % |
| Estimativas retornavam `float` ou `dict` | `Resultado(valor, ic, n, status, motivo)` |
| Ponto 22 ausente do CSV | Presente, com `rssi_dbm` vazio — zona cega é resultado |

**A exclusão dos pontos 13 e 14 deixou de ser uma lista.** Ela agora cai fora sozinha, por
evidência de BSSID: o ponto 13 tem OUI `84:18:3a`, estranho aos APs Ruckus do prédio M
(classificado `ap_nao_mapeado`), e o 14 tem `7d` no 4º octeto, fora do vocabulário
`3c`/`3d`/`3e`/`3f` observado no prédio (classificado `suspeito`). O resultado numérico é o
mesmo de antes — a diferença é que agora ele é **derivado**, e um leitor pode contestar o
critério em vez de ter que aceitar a lista.

---

## 3. Como o pipeline trata a ausência de dado

Quatro garantias, para que nada vire erro silencioso:

1. **Nenhum valor é arbitrado.** Coluna vazia gera aviso e a leitura sai daquela análise —
   nunca entra com um valor padrão.
2. **Nenhuma estimativa sem medida de confiança.** Toda função devolve
   `Resultado(valor, ic, n, status, motivo)`. Onde a amostra não sustenta, o resultado
   declarado é a impossibilidade, com o motivo por escrito.
3. **Nenhuma exclusão silenciosa.** Tudo que é filtrado aparece em
   `saidas/relatorio_qualidade.md`.
4. **Ausência não interrompe.** O pipeline roda até o fim com o que existir.

E três recusas deliberadas, que **não** devem ser "consertadas" afrouxando parâmetro:

- **Menos de 5 pontos → não há α.** (`PARAMS["min_pontos_ajuste"]`)
- **Menos de 3 distâncias distintas → não há α**, por mais pontos que existam.
  Sem alavanca em distância, o α descreve a dispersão da amostra, não a perda de percurso.
- **Menos de 3 pares → não há perda de laje.** Um único par não é estimativa.

---

## 4. Pendências de campo, por prioridade

### 4.1 Coordenadas `x_m` / `y_m` — a pendência nº 1

**Destrava:** mapas de calor interpolados, GeoTIFF para o QGIS, cenários C e D do path loss,
e o termo de correção por distância da perda de laje.

Hoje só 24 leituras têm coordenada, e todas são de pontos rotulados "Abaixo do APn" — ou
seja, estão sobre os próprios APs. Isso dá **2 posições distintas por pavimento**, e as duas
são os APs. Interpolar entre elas não produz mapa de cobertura.

**Não dá para deduzir do texto.** As descrições não fecham com as distâncias anotadas:

> **M-11, "Meio (entre os dois APs)", `dist_campo_m` = 2 m.** O ponto médio entre AP1 e AP2
> fica a **8,32 m** de cada um.

O mesmo vale para "Entrada" a 3 m e "Sala entre AP1 e AP2" a 4 m. Ou as distâncias são a um
AP diferente do rótulo, ou os rótulos são aproximados. Colocar esses pontos no mapa por
dedução geraria uma superfície bonita e falsa.

**O que fazer.** O arquivo `saidas/coordenadas_a_levantar.csv` já lista as **23 posições**
que faltam, com as leituras e a distância de cada uma, e as colunas `x_m`/`y_m` em branco.

| Referência para preencher | Valor |
|---|---|
| Origem | eixo 06 (`x = 0`), eixo A (`y = 0`) |
| Envoltória | 30,08 × 19,99 m |
| AP1 | (7,40 ; 9,55) |
| AP2 | (24,05 ; 9,55) |
| Distância entre APs | 16,65 m |
| Pé-direito | 3,40 m |

As posições dos APs são **idênticas nos dois prédios e nos três pavimentos** (confirmado em
18/08/2026), e já estão em `GEOMETRIA_PADRAO`.

**Como medir.** Não se mede "a coordenada" — medem-se duas distâncias perpendiculares. Com
trena a laser: encoste na parede de referência de `x` e meça até o ponto (é o `x`); repita na
parede perpendicular (é o `y`). Dois disparos por ponto. Se a planta for cotada, dá para ler
direto contando módulos construtivos.

**Precisão de ±0,5 m basta.** A variação de RSSI por orientação do aparelho no mesmo ponto
chegou a **15 dB** nesta campanha (M-02, em pé versus no chão). Meio metro de incerteza
posicional é irrelevante perto disso.

### 4.2 BSSID nas 25 leituras restantes

**Destrava:** cenários B e D do path loss, perda de laje, mapa de reuso de canal.

31 de 56 leituras têm BSSID. As que faltam são quase todas do prédio M — só 5 leituras do M
foram transcritas (7, 8, 12, 13, 14), contra 26 do prédio I.

Registre na coluna `bssid_bruto`, no formato do aplicativo. O pipeline normaliza separador e
caixa sozinho.

### 4.3 Distâncias intermediárias — o α de 5 GHz

**Destrava:** α em 5 GHz nos dois prédios, e a fragilidade do α de 2,4 GHz.

Não é coluna faltando: é **cobertura amostral**.

| Problema | Diagnóstico da execução |
|---|---|
| α em 5 GHz não estimável (M) | as 9 leituras sem obstáculo estão em apenas **2 distâncias** (1 m e 3 m); o mínimo é 3 |
| α em 5 GHz inconsistente (I) | R² = 0,03 — a distância explica 3 % da variação do RSSI |
| α de 2,4 GHz frágil | pouquíssimas leituras livres além de 4 m |

**O que medir:** leituras **sem obstáculo** a **6, 10 e 15 m**, nas duas bandas, em cada
pavimento. É a mesma recomendação para os três problemas.

> As guardas que produzem esses bloqueios são parametrizadas em `PARAMS`.
> **Não as afrouxe para "destravar" a análise** — elas existem para impedir que um α sem
> sustentação amostral seja reportado como se fosse medida.

### 4.4 Redes vizinhas → SINR real

Hoje o pipeline calcula **SNR**, não SINR. O piso de ruído é **−95 dBm, adotado e não
medido**, uniforme para todos os pontos.

Varredura passiva resolve, sem nova campanha completa: em cada ponto, registre a lista de
redes vizinhas com SSID, canal e RSSI. Para o cálculo rigoroso: converter cada vizinha de dBm
para mW e **somar em potência linear** (dBm não se soma), ponderar pelo fator de sobreposição
espectral, e aplicar `SINR = S / (I + N)`.

### 4.5 ~~Vazão e latência~~ — REMOVIDO

<!-- REMOVIDO: vazão/latência não medidas -->

> **Estas medições não foram realizadas e foram removidas do escopo.** O pipeline não possui
> mais módulo, coluna nem célula de vazão, latência ou perda de pacotes.
>
> Consequência metodológica que permanece registrada: sem vazão não se distingue um ponto
> limitado por **propagação** de um ponto limitado por **disputa do meio**. A suspeita de
> congestionamento em 2,4 GHz se apoia apenas na camada de canal (descasamento e
> `pct_melhor_canal`), que é indicador relativo, não medida de desempenho.

### 4.6 Fabricante do prédio I

`PREDIOS["I"]["fabricante_ap"]` está `None` de propósito. Os OUIs observados no prédio I são
`00:e6:3a`, `3c:46:a1`, `70:47:77` e `c8:a6:08` — quatro distintos, contra um único
(`e0:10:7f`, Ruckus) no prédio M. **Não inferir sem consultar a base do IEEE.** Enquanto
estiver `None`, a ressalva de comparabilidade entre os prédios permanece aberta.

### 4.7 Semântica de `pct_melhor_canal`

A coluna tem duas leituras possíveis — qualidade do melhor canal, ou ocupação dele — e o
pipeline a trata **apenas como métrica relativa comparativa**, emitindo aviso.

Indício a favor de "qualidade": em 5 GHz o valor é quase sempre 100, e em 2,4 GHz varia de 0
a 52. Banda limpa dando 100 é coerente com qualidade e incoerente com ocupação. Não fecha a
questão — **defina no relatório antes de citar qualquer valor absoluto**.

---

## 5. Achados que pedem decisão sua

### 5.1 Os pontos 15, 16 e 22 têm duas distâncias anotadas

A planilha de campo traz, para esses três, `"6 m (dist real), 15 m (do AP conectado)"` e
equivalentes. O CSV antigo gravava **a do AP conectado**; o novo grava a real em
`dist_campo_m` e preserva a outra em `dist_ap_conectado_m`.

**Isso move o α do prédio M em 2,4 GHz de 2,6 para 3,3.** As duas versões ficam calculáveis —
o cenário histórico usa a antiga, o cenário A usa a nova — mas **a escolha precisa estar
declarada no texto do relatório**, porque muda o resultado principal.

### 5.2 A regra de agrupamento de BSSID do prédio M não vale no prédio I

No prédio M, BSSIDs que compartilham os **5 primeiros octetos** são o mesmo AP físico (o
último octeto varia por rádio/SSID). Confirmado.

No prédio I o padrão é outro: o **4º octeto difere em +0x40** entre os rádios de 2,4 e 5 GHz
do mesmo equipamento. Verificado em 4 pares, todos separando limpo por banda:

| 2,4 GHz | 5 GHz |
|---|---|
| `00:e6:3a:5e:4e:a0` | `00:e6:3a:9e:4e:a0` |
| `3c:46:a1:66:33:40` | `3c:46:a1:a6:33:40` |
| `c8:a6:08:43:20:a0` | `c8:a6:08:83:20:a0` |

Por isso `PREDIOS["I"]["bssid_para_ap"]` está **vazio** e a regra conservadora (BSSID
inteiro) está em vigor. O relatório de qualidade emite os **12 grupos candidatos** a cada
execução. Confira e preencha `config/predios.py` à mão — o pipeline não assume por você.

### 5.3 A data do prédio I na planilha é 07/08/2026

A configuração antiga registrava a campanha do prédio I como 16/08/2026. A planilha de campo
traz **07/08/2026** em todas as linhas, inclusive as do I. Adotei o que está na planilha.
Vale conferir se foi preenchimento por arrasto na coluna de data.

### 5.4 Um único BSSID domina o prédio I inteiro

`3c:46:a1:66:33:40` aparece como AP dominante em 7 leituras, nos **três pavimentos**
(subsolo, térreo e 1º andar). Isso é o que produz os 15 pares de laje do prédio I — e também
o que os torna suspeitos: se um mesmo AP é o mais forte em todo o edifício, ou ele está muito
bem posicionado, ou os demais estão subdimensionados. Vale investigar em campo.

### 5.5 Descasamento de canal de 100 % em 5 GHz

Nos dois prédios, **todas** as leituras de 5 GHz têm `canal_usado != canal_melhor`. Em 2,4 GHz
o descasamento é alto mas não total (M 76 %, I 93 %).

100 % nos dois prédios é forte demais para ser só ausência de gerenciamento adaptativo.
Suspeita: artefato de como o aplicativo define "melhor canal" em 5 GHz, onde há dezenas de
canais e muitos ficam vazios. **Não afirme a conclusão de campus sem entender o critério do
app** — a hipótese está sustentada em 2,4 GHz, que é onde o dado é interpretável.

---

## 6. Plantas do prédio M — já disponíveis

Projeto arquitetônico executivo da UFCA (2019, arq. Louise Buarque de Gusmão Barbosa,
escala **1:75**), cobrindo os três pavimentos da campanha:

| Prancha | Título no projeto | `pavimento` no CSV |
|---|---|---|
| `01/13` | PLANTA-BAIXA — **1º PAVIMENTO** — SUBSOLO | `-1` |
| `02/13` | PLANTA-BAIXA — **2º PAVIMENTO** — TÉRREO | `0` |
| `03/13` | PLANTA-BAIXA — **3º PAVIMENTO** — 1º andar | `1` |

> ⚠️ **A numeração de pavimento do projeto não é a da campanha.** O que a campanha chama de
> "1º andar" é o **3º pavimento** na planta.

**O que as plantas resolvem**

- **Salas nomeadas:** `M01`–`M05` no subsolo, `M101`–`M105` no 1º andar. Localiza o M-01
  ("fundo da M102") e confirma que a M102 é do 1º andar, não a M02 do subsolo.
- **Escadas** identificáveis nos três pavimentos — localiza M-05, M-10 e M-16.
- **Corroboração do obstáculo:** o Quadro de Esquadrias lista a **P7, porta corta-fogo,
  100×210 cm, em "Escadas"** — é o obstáculo dos 21,1 dB do M-05, confirmado pelo projeto.

**O que as plantas NÃO resolvem:** a posição dos APs (elas são arquitetônicas; APs estariam
no projeto de cabeamento estruturado) e as 23 posições de medição da seção 4.1.

**Para usar como fundo dos mapas**, recorte só o desenho e salve como
`dados/planta_M_subsolo.png`, `dados/planta_M_terreo.png`, `dados/planta_M_1andar.png` — os
caminhos já estão declarados em `config/predios.py`. Ausência não quebra: o mapa sai sem
fundo e a caixa de texto registra `planta = indisponivel`.

---

## 7. Checklist de campo consolidado

Em ordem de retorno por esforço:

- [ ] **`x_m` / `y_m` das 23 posições** de `saidas/coordenadas_a_levantar.csv`
      → destrava mapas interpolados, GeoTIFF, cenários C/D e o desconto de distância da laje
- [ ] **BSSID das 25 leituras sem** — prioridade no prédio M, que só tem 5
      → destrava cenários B/D, perda de laje e reuso de canal
- [ ] **Leituras sem obstáculo a 6, 10 e 15 m**, nas duas bandas, em cada pavimento
      → destrava α em 5 GHz e reforça o de 2,4 GHz
- [ ] **Altura de medição** de cada ponto, em metros
      → remove a variável não controlada de 15 dB
- [ ] **Repetição**: 3 leituras por ponto, para poder reportar média e desvio
      → hoje toda estimativa é de amostra única
- [ ] **Lista de redes vizinhas** (SSID, canal, RSSI) por ponto
      → destrava SINR real no lugar de SNR
- [ ] **Modelo exato do AP** (não só o fabricante), nos dois prédios
- [ ] **Confirmar o fabricante do prédio I** via OUI na base do IEEE
- [ ] **Plantas do prédio I**, equivalentes às do M

Regras ao acrescentar dado:

- Coluna com nome canônico passa direto — abra `dados/leituras.csv` e preencha.
- `dist_origem` deve ser `medida`, `planta`, `estimada_app` ou `desconhecida`.
  **Se o valor veio da coluna "Distância" do aplicativo, marque `estimada_app`** — ela é
  derivada do RSSI por um modelo interno, e o pipeline a exclui de toda regressão para não
  recuperar o α do app em vez do α do prédio.
- Não invente coordenadas a partir da descrição textual do local.

---

## 8. Como verificar que destravou

Depois de acrescentar dado, rode o pipeline e confira, nesta ordem:

```bash
.venv/Scripts/python.exe -c "from src.pipeline import rodar; S = rodar(); print(S['verificacao'])"
```

1. **A verificação de regressão continua passando?** Se não, o dado novo quebrou o parsing —
   corrija antes de olhar qualquer resultado.
2. **`saidas/relatorio_qualidade.md`, seção 8** — a análise que você queria destravar saiu de
   `bloqueada`?
3. **`saidas/limitacoes.md`** — as limitações se atualizam sozinhas a partir dos dados.

---

## 9. Ambiente

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

`pandas`, `numpy`, `scipy`, `matplotlib`, `rasterio`, `tabulate`, `ipykernel`, `nbconvert`.
`rasterio` só é necessário para o GeoTIFF — sem ele o pipeline roda e avisa.

---

## 10. Pendências de código

- [ ] **SINR rigoroso** — depende da lista de vizinhas (seção 4.4). Hoje só há SNR sobre piso
      de ruído adotado.
- [ ] **Zona cega no mapa** — o M-22 aparece hoje apenas como ausência. Representá-lo como
      região explicitamente descoberta pede um marcador próprio na figura.
- [ ] **Mapas de SNR** — a infraestrutura de `heatmap.rodar()` aceita qualquer métrica por
      parâmetro; só falta chamar para `snr_estimado_db` depois que houver coordenadas.
- [x] ~~`planta` e `aps` únicos por bloco~~ — resolvido: `GEOMETRIA_PADRAO` + `plantas` por pavimento
- [x] ~~`bssid` carregado mas não consumido~~ — resolvido: consumido por dominância, laje e reuso
- [x] ~~Exclusão de pontos por ID~~ — resolvido: critério objetivo de dominância em runtime
