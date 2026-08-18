# Limitacoes do estudo

Documento gerado automaticamente em 18/08/2026 17:45 a partir de dados/leituras.csv. Os numeros abaixo vem da execucao, nao de texto fixo.


## 1. Amostra unica por ponto, sem repeticao nem media

As 56 leituras correspondem a 56 combinacoes distintas de (predio, pavimento, banda, local), com **uma medicao por combinacao**. Nao ha repeticao temporal nem media, entao nao ha como separar variacao de curto prazo (fast fading, ocupacao do meio) do efeito que se quer medir. Todo intervalo de confianca reportado descreve a dispersao ENTRE pontos, nunca a repetibilidade de um ponto.


## 2. Altura de medicao nao controlada

A coluna altura_medicao_m esta vazia em **56 das 56 leituras** (100%). A campanha registrou o efeito uma unica vez, no ponto **M-02**:


> Anotado em campo como '< 1 m'. Em pe os valores chegavam proximos de -30 dBm; no chao, proximos de -45 dBm. Altura da medicao nao registrada.


Sao **15 dB de variacao produzidos por uma variavel que nao foi registrada**. Para comparacao: a perda atribuida a porta corta-fogo neste mesmo estudo e da ordem de 21 dB, e a diferenca entre os cenarios de alpha avaliados vale poucos dB ao longo de toda a faixa de distancias. Ou seja, **a variavel nao controlada excede varios dos efeitos que o estudo tenta medir**.


## 3. BSSID identifica o AP dominante, nao o AP associado

Os BSSIDs foram lidos da lista de varredura do aplicativo (aba de pontos de acesso), que mostra o **AP visivel dominante** no ponto. Nao ha registro de a qual AP o cliente estava efetivamente associado.


Consequencia direta: a expressao *sticky client* **nao e sustentavel por este dado**. O que se pode afirmar e que o AP mais forte na varredura era o indicado, nao que o aparelho estivesse preso a ele.


Cobertura de BSSID por predio:


| predio   |   leituras |   com_bssid |   pct |
|:---------|-----------:|------------:|------:|
| I        |         26 |          26 | 100   |
| M        |         30 |           5 |  16.7 |


## 4. O SINR calculado e um limite pessimista

O piso de ruido usado e **-95 dBm, adotado e nao medido**, uniforme para todos os pontos. Alem disso, tratar interferencia co-canal como ruido aditivo e conservador demais para Wi-Fi: em CSMA/CA a interferencia co-canal atua principalmente por **disputa de airtime** (o transmissor espera o meio ficar livre), e nao somando potencia ao denominador. A capacidade de Shannon derivada dai e teto teorico, jamais previsao de vazao.


## 5. Alpha reportado com 2 algarismos significativos

Pelos motivos das secoes 1 e 2: amostra unica, distancia anotada com aproximacao na origem, altura nao controlada e RSSI 802.11 variando tipicamente +-5 a 10 dB por fast fading. Reportar alpha = 2,62 sugere precisao de centesimos que a amostra nao sustenta; o pipeline reporta alpha ~= 2,6.


Amplitude dos intervalos de confianca obtidos nesta execucao:


| predio   |   banda | cenario   |   alpha |   ic95_inf |   ic95_sup |   n |   amplitude_ic |
|:---------|--------:|:----------|--------:|-----------:|-----------:|----:|---------------:|
| I        |     2.4 | A         |     1.9 |       1.07 |       2.81 |   8 |           1.74 |
| M        |     2.4 | A         |     3.3 |       1.91 |       4.62 |   9 |           2.71 |


Um IC de amplitude comparavel ao proprio valor de alpha confirma que o segundo algarismo ja e o limite do que a amostra sustenta.


## 6. Cobertura desigual entre os predios

| predio   |   leituras |   com_bssid |   xy_declarada |   dist_zero | mapa_ap   | fabricante_ap   |
|:---------|-----------:|------------:|---------------:|------------:|:----------|:----------------|
| I        |         26 |          26 |              0 |           4 | nao       | a confirmar     |
| M        |         30 |           5 |              0 |           0 | sim       | Ruckus Wireless |


A comparacao entre predios herda essas assimetrias. Onde um predio tem mapeamento de AP e o outro nao, a mesma analise nao roda dos dois lados, e a diferenca observada pode ser de **cobertura de dado**, nao de propagacao.


## 7. Equipamento nao totalmente identificado

- **Predio I**: fabricante **nao confirmado**. Os OUIs observados nao foram verificados contra a base do IEEE, e o pipeline nao os infere.

- **Predio M**: fabricante declarado (Ruckus Wireless), modelo nao registrado. Potencia de transmissao e ganho de antena variam entre modelos do mesmo fabricante, entao a ressalva de comparabilidade permanece aberta.


## 8. Transcricao de BSSID nao verificada na fonte

1 par(es) de BSSID diferem em poucos digitos sem cair no mesmo AP fisico. A hipotese de erro de transcricao **nao foi confirmada contra os prints originais do aplicativo**: ela e apenas a leitura mais provavel do padrao observado.


- predio M: e0:10:7f:3d:ea:78 (leitura [7]) vs e0:10:7f:7d:ea:79 (leitura [14]); candidato a erro: e0:10:7f:7d:ea:79
