# Relatorio de qualidade dos dados

Gerado automaticamente em 18/08/2026 17:45 a partir de `dados/leituras.csv`.

Este relatorio roda **antes** de qualquer analise. Nenhuma leitura e descartada pelo pipeline sem aparecer em alguma secao abaixo.


## 1. Contagem de leituras

| predio   | pavimento   |   banda |   leituras |
|:---------|:------------|--------:|-----------:|
| I        | Subsolo     |     2.4 |          5 |
| I        | Subsolo     |     5   |          4 |
| I        | Terreo      |     2.4 |          5 |
| I        | Terreo      |     5   |          3 |
| I        | 1o andar    |     2.4 |          5 |
| I        | 1o andar    |     5   |          4 |
| M        | Subsolo     |     2.4 |          6 |
| M        | Subsolo     |     5   |          4 |
| M        | Terreo      |     2.4 |          6 |
| M        | Terreo      |     5   |          4 |
| M        | 1o andar    |     2.4 |          5 |
| M        | 1o andar    |     5   |          5 |

**Total: 56 leituras.**


## 2. Campos ausentes por coluna

| coluna                 |   ausentes |   total |   pct | critica   |
|:-----------------------|-----------:|--------:|------:|:----------|
| altura_medicao_m       |         56 |      56 | 100   | SIM       |
| x_m                    |         32 |      56 |  57.1 | SIM       |
| y_m                    |         32 |      56 |  57.1 | SIM       |
| bssid_bruto            |         25 |      56 |  44.6 | SIM       |
| dist_ao_ap_dominante_m |         54 |      56 |  96.4 |           |
| dist_ap_conectado_m    |         53 |      56 |  94.6 |           |
| ap_dominante           |         53 |      56 |  94.6 |           |
| delta_pavimento        |         53 |      56 |  94.6 |           |
| ap_local               |         32 |      56 |  57.1 |           |
| dist_calc_2d_m         |         32 |      56 |  57.1 |           |
| dist_calc_3d_m         |         32 |      56 |  57.1 |           |
| divergencia_dist_m     |         32 |      56 |  57.1 |           |
| bssid                  |         25 |      56 |  44.6 |           |
| grupo_ap               |         25 |      56 |  44.6 |           |
| rssi_dbm               |          1 |      56 |   1.8 |           |
| canal_usado            |          1 |      56 |   1.8 |           |

> As colunas marcadas como criticas sustentam analises inteiras: `bssid_bruto` decide a dominancia de AP (cenarios B/D e perda de laje) e `x_m`/`y_m` decidem toda a geometria (cenarios C/D e mapas).


## 3. Origem da distancia — risco de circularidade

| predio   | dist_origem   |   leituras |
|:---------|:--------------|-----------:|
| I        | planta        |         26 |
| M        | planta        |         30 |

> **Nenhuma leitura com `dist_origem = 'estimada_app'`.** Nao ha risco de circularidade: a regressao nao recupera o modelo interno do aplicativo. As distancias declaradas como `planta` foram lidas do projeto arquitetonico, e sao independentes do RSSI medido.


## 4. BSSIDs suspeitos de erro de transcricao

| predio   | bssid_a           | leituras_a                   | bssid_b           | leituras_b                   |   hamming_nibbles | octetos_divergentes   | hipotese                                                    | bssid_anomalo     |
|:---------|:------------------|:-----------------------------|:------------------|:-----------------------------|------------------:|:----------------------|:------------------------------------------------------------|:------------------|
| I        | 00:e6:3a:5e:4e:a0 | [32]                         | 00:e6:3a:9e:4e:a0 | [46, 47]                     |                 1 | [4]                   | offset de radio 2.4/5 GHz no 4o octeto                      | nan               |
| I        | 3c:46:a1:66:33:30 | [37, 44]                     | 3c:46:a1:66:33:40 | [34, 36, 38, 39, 40, 41, 42] |                 1 | [6]                   | mesmo AP fisico (prefixo de 5 octetos, radio/SSID distinto) | nan               |
| I        | 3c:46:a1:66:33:30 | [37, 44]                     | 3c:46:a1:a6:33:40 | [50, 51, 52, 53, 54]         |                 2 | [4, 6]                | offset de radio 2.4/5 GHz no 4o octeto                      | 3c:46:a1:a6:33:40 |
| I        | 3c:46:a1:66:33:40 | [34, 36, 38, 39, 40, 41, 42] | 3c:46:a1:a6:33:40 | [50, 51, 52, 53, 54]         |                 1 | [4]                   | offset de radio 2.4/5 GHz no 4o octeto                      | 3c:46:a1:a6:33:40 |
| I        | c8:a6:08:43:20:a0 | [35]                         | c8:a6:08:83:20:a0 | [48, 49]                     |                 1 | [4]                   | offset de radio 2.4/5 GHz no 4o octeto                      | nan               |
| M        | e0:10:7f:3d:ea:78 | [7]                          | e0:10:7f:7d:ea:79 | [14]                         |                 2 | [4, 6]                | possivel erro de transcricao                                | e0:10:7f:7d:ea:79 |

> Sinalizado todo par com distancia de Hamming (em nibbles) <= 2 que a regra de agrupamento do predio separa em APs distintos. **Apenas os 1 par(es) classificados como erro de transcricao marcam a leitura como suspeita**; os demais indicam que a regra de agrupamento daquele predio precisa de revisao, nao que o dado esteja errado.


### Grupos candidatos de AP fisico — predio I

O mapeamento `bssid_para_ap` deste predio esta vazio: a regra de agrupamento confirmada para outro predio **nao foi assumida aqui**. Confira os grupos abaixo e preencha `config/predios.py` manualmente.

| grupo             | bssids            | oui      | leituras                     | pavimentos   | bandas   | locais                                                                               |
|:------------------|:------------------|:---------|:-----------------------------|:-------------|:---------|:-------------------------------------------------------------------------------------|
| 00:e6:3a:5e:4e:a0 | 00:e6:3a:5e:4e:a0 | 00:e6:3a | [32]                         | [1]          | ['2.4']  | Abaixo do AP2                                                                        |
| 00:e6:3a:8a:81:70 | 00:e6:3a:8a:81:70 | 00:e6:3a | [56]                         | [-1]         | ['5']    | Canto da Biblioteca                                                                  |
| 00:e6:3a:9e:4e:a0 | 00:e6:3a:9e:4e:a0 | 00:e6:3a | [46, 47]                     | [1]          | ['5']    | Abaixo do AP2; Fundo do corredor                                                     |
| 3c:46:a1:66:33:30 | 3c:46:a1:66:33:30 | 3c:46:a1 | [37, 44]                     | [-1, 0]      | ['2.4']  | Abaixo do AP2; Canto da Biblioteca                                                   |
| 3c:46:a1:66:33:40 | 3c:46:a1:66:33:40 | 3c:46:a1 | [34, 36, 38, 39, 40, 41, 42] | [-1, 0, 1]   | ['2.4']  | Abaixo do AP1; Entrada; Entrada/Bebedouro; Escada; Fundo do Terreo; Janela/Bebedouro |
| 3c:46:a1:a6:33:40 | 3c:46:a1:a6:33:40 | 3c:46:a1 | [50, 51, 52, 53, 54]         | [-1, 0]      | ['5']    | Abaixo do AP1; Abaixo do AP2; Entrada/Bebedouro; Fundo do Terreo                     |
| 70:47:77:74:84:10 | 70:47:77:74:84:10 | 70:47:77 | [31]                         | [1]          | ['2.4']  | Fundo do corredor                                                                    |
| 70:47:77:75:2a:a0 | 70:47:77:75:2a:a0 | 70:47:77 | [33]                         | [1]          | ['2.4']  | Abaixo do AP1                                                                        |
| 70:47:77:b4:55:60 | 70:47:77:b4:55:60 | 70:47:77 | [55]                         | [-1]         | ['5']    | Abaixo do AP2                                                                        |
| c8:a6:08:43:20:a0 | c8:a6:08:43:20:a0 | c8:a6:08 | [35]                         | [1]          | ['2.4']  | Escada                                                                               |
| c8:a6:08:44:3b:70 | c8:a6:08:44:3b:70 | c8:a6:08 | [43, 45]                     | [-1]         | ['2.4']  | Abaixo do AP2; Escada                                                                |
| c8:a6:08:83:20:a0 | c8:a6:08:83:20:a0 | c8:a6:08 | [48, 49]                     | [1]          | ['5']    | Abaixo do AP1; Janela/Bebedouro                                                      |

## 5. Leituras sem RSSI

| ponto_id   | predio   |   pavimento |   banda | local   | obs_campo                                                                                                                                       |
|:-----------|:---------|------------:|--------:|:--------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| M-22       | M        |           1 |       5 | Escada  | Sem conexao em 5 GHz na escada: nao foi possivel identificar associacao com nenhum AP, provavelmente por distancia ou interferencia. Zona cega. |

## 6. Leituras com distancia de campo <= 0

| ponto_id   | predio   |   pavimento |   banda |   dist_campo_m | local         | obs_campo                                                                                                                                                                                                                                                                                               |
|:-----------|:---------|------------:|--------:|---------------:|:--------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| I-32       | I        |           1 |     2.4 |              0 | Abaixo do AP2 | Distancia anotada em campo como 0 m (medicao diretamente sob o AP).                                                                                                                                                                                                                                     |
| I-43       | I        |          -1 |     2.4 |              0 | Abaixo do AP2 | Distancia anotada em campo como 0 m (medicao diretamente sob o AP). Reclassificado como SEM obstaculo em 18/08/2026: a medicao foi feita diretamente sob o AP, sem nada interposto no caminho do enlace; as prateleiras de metal estao no entorno do ponto. Anotacao original em obstaculos_registrado. |
| I-47       | I        |           1 |     5   |              0 | Abaixo do AP2 | Distancia anotada em campo como 0 m (medicao diretamente sob o AP).                                                                                                                                                                                                                                     |
| I-55       | I        |          -1 |     5   |              0 | Abaixo do AP2 | Distancia anotada em campo como 0 m (medicao diretamente sob o AP). Reclassificado como SEM obstaculo em 18/08/2026: mesmo criterio do ponto 43. Anotacao original em obstaculos_registrado.                                                                                                            |

> Anotadas em campo como 0 m (medicao diretamente sob o AP). `log10(0)` e indefinido, entao essas leituras **saem de toda regressao** — o pipeline nao as normaliza para d0 em silencio. Recoletar com a distancia horizontal real ao AP resolveria.


## 7. Divergencia entre distancia de campo e geometria 3D

Limite de reporte: **3 m**.

_(nenhuma divergencia acima do limite — ou geometria indisponivel)_

### 7b. Leituras com DUAS distancias anotadas em campo

| ponto_id   | predio   |   pavimento |   banda |   dist_campo_m |   dist_ap_conectado_m |   rssi_dbm | local   |
|:-----------|:---------|------------:|--------:|---------------:|----------------------:|-----------:|:--------|
| M-15       | M        |          -1 |     2.4 |              6 |                    15 |        -60 | Entrada |
| M-16       | M        |          -1 |     2.4 |              8 |                    18 |        -68 | Escada  |
| M-22       | M        |           1 |     5   |              8 |                    18 |        nan | Escada  |

> A campanha anotou distancia real **e** distancia ao AP dominante. `dist_campo_m` recebe a real (lida da planta); a outra fica em `dist_ap_conectado_m`. A escolha muda o alpha de forma material e esta reportada na tabela comparativa de cenarios.


## 8. Executabilidade das analises

Esta e a lista objetiva do que precisa ser recoletado em campo.

| analise                                        | situacao                | motivo                                                                                                                                 | o_que_falta_coletar                                                                                                           |
|:-----------------------------------------------|:------------------------|:---------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------|
| 1. Path loss — cenario A (distancia de campo)  | executavel com ressalva | estimado em 2 de 4 combinacoes; sem estimativa em: I 5 GHz, M 5 GHz                                                                    | leituras sem obstaculo em distancias intermediarias (6, 10 e 15 m), sobretudo em 5 GHz, onde ha apenas 2 distancias distintas |
| 2. Path loss — cenarios B/D (dominancia de AP) | bloqueada               | estimado em 0 de 8 combinacoes; cobertura de bssid_bruto parcial (M: 5/30); mapa de AP vazio em: I                                     | BSSID em TODAS as leituras (faltam 25 de 56) e confirmacao manual dos grupos de AP dos predios sem mapa                       |
| 3. Path loss — cenarios C/D (geometria 3D)     | bloqueada               | estimado em 0 de 8 combinacoes; x/y so sao conhecidos onde o local e 'Abaixo do APn' (I: 12/26, M: 12/30)                              | x_m e y_m lidos em planta para TODOS os pontos (duas distancias perpendiculares por ponto; precisao de +-0,5 m basta)         |
| 4. Perda de laje                               | bloqueada               | minimo de 3 pares utilizaveis por combinacao; obtido — I 2.4 GHz: 15, I 5 GHz: 6, M 2.4 GHz: 1, M 5 GHz: 0                             | BSSID em todas as leituras, para achar o mesmo AP fisico visto de pavimentos diferentes; e x/y, para descontar a distancia    |
| 5. Atenuacao por obstaculo                     | executavel com ressalva | calculada em 2 de 4 combinacoes; 3 ponto(s) com L <= 0, sinalizados e nao recategorizados                                              | alpha valido em 5 GHz — hoje sem alavanca em distancia — para estender o calculo aquela banda                                 |
| 6. Canais (descasamento, reuso, qualidade)     | executavel              | descasamento calculado em 12 grupos predio x banda x pavimento; reuso identificavel apenas onde ha BSSID                               | definicao explicita da semantica de pct_melhor_canal; BSSID completo para fechar o mapa de reuso de canal                     |
| 7. Mapas de calor por pavimento                | bloqueada               | 12 mapa(s) gerado(s), 0 com superficie interpolada; os demais saem como scatter porque ha menos de 4 posicoes distintas com coordenada | x/y de todos os pontos e as imagens de planta por pavimento                                                                   |

---


## Avisos de semantica

- SEMANTICA PENDENTE: 'pct_melhor_canal' tem interpretacao ambigua (qualidade do melhor canal vs. ocupacao do melhor canal). O pipeline a trata APENAS como metrica relativa comparativa, nunca como grandeza fisica. Defina explicitamente no relatorio antes de citar qualquer valor absoluto.

- Os BSSIDs identificam o **AP dominante** na varredura, nao o AP ao qual o cliente estava associado. Nenhuma conclusao sobre associacao de cliente pode ser tirada deste dado.
