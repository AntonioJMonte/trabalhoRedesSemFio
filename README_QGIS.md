# Georreferenciamento no QGIS — Mapa de Cobertura Wi-Fi

Gerado em 16/08/2026 19:14 pelo notebook das Fases 5 e 6.
Blocos exportados: M.
Formato de raster adotado: **PNG + world file .pgw (rasterio ausente neste ambiente)**.

O sistema de referência é **local, em metros**, com origem no canto da planta
(x cresce para a direita, y cresce para cima). Não há CRS geográfico associado:
trabalhe em um projeto sem projeção ou defina um CRS cartesiano genérico.

## 1. Georreferenciar a planta baixa

1. `Camada > Georreferenciador`.
2. Abra a imagem da planta.
3. Marque no mínimo 4 pontos de controle, preferencialmente os cantos do pavimento.
4. Para cada ponto, informe a coordenada local em metros. Para uma planta de
   L x A metros, os cantos são `(0, 0)`, `(L, 0)`, `(L, A)` e `(0, A)`,
   com `(0, 0)` no canto inferior esquerdo.
5. Tipo de transformação: **Linear** (ou Helmert). Reamostragem: vizinho mais próximo.
   Deixe o CRS em branco ou use um cartesiano genérico.
6. Execute. A planta passa a ocupar exatamente o retângulo `0..L` por `0..A`.

## 2. Importar a camada de pontos

1. `Camada > Adicionar camada > Adicionar camada de texto delimitado`.
2. Arquivo: `pontos_<bloco>.csv`.
3. Formato: CSV. Geometria: **coordenadas de ponto**, campo X = `x`, campo Y = `y`.
4. CRS: o mesmo usado no passo 1.
5. Estilize por `rssi_dbm` com gradação graduada, paleta RdYlGn, para reproduzir a
   leitura dos heatmaps.

> Se a coluna `x`/`y` do CSV estiver vazia, a camada carrega como tabela sem geometria.
> É o caso de qualquer bloco cuja campanha só registrou a localização como texto.

## 3. Carregar os rasters interpolados

- **GeoTIFF**: `Camada > Adicionar camada > Adicionar camada raster` e selecione o `.tif`.
  A transformação afim já está embutida; o raster cai sobre a planta.
- **PNG + `.pgw`**: mantenha o `.png` e o `.pgw` **no mesmo diretório e com o mesmo nome
  base**. Adicione o `.png` como camada raster — o QGIS lê o world file automaticamente
  e aplica a mesma transformação.

Estilize com `Propriedades > Simbologia > Banda simples falsa-cor`, paleta RdYlGn,
e reduza a opacidade para ~65% de modo que a planta permaneça visível por baixo.

## 4. Conferência

Sobreponha a camada de pontos ao raster: cada ponto medido deve cair sobre a região do
raster com o valor correspondente. Divergência indica erro de georreferenciamento no
passo 1 — refaça os pontos de controle.

## Arquivos gerados

- `pontos_M.csv`
