# Instância local da Overpass API (São Luís - MA)

Usada pelo experimento do TCC (`bonding.services.external_integrations`,
Seção 3.2) para eliminar a dependência de espelhos públicos compartilhados
(`overpass-api.de`, `overpass.kumi.systems`, `overpass.openstreetmap.ru`),
que estavam sujeitos a sobrecarga e a limites de uso automatizado.

## Como foi gerada

1. Download do extrato do Brasil inteiro (Geofabrik, sem rate-limit, download
   direto por arquivo):
   ```
   curl -L -o osm_data/brazil-latest.osm.pbf \
     https://download.geofabrik.de/south-america/brazil-latest.osm.pbf
   ```
2. Recorte para uma caixa delimitadora ao redor de São Luís (-2.5300,
   -44.3028), grande o suficiente para cobrir o raio de busca de 100km usado
   pela aplicação (`RADIUS_KM` em `run_date_experiment.py`):
   `(-45.40, -3.60) a (-43.20, -1.40)` — ver `scripts/crop_sao_luis.py`
   (requer `pip install osmium`). Mantém nós dentro da caixa; mantém vias
   apenas quando todos os nós referenciados também estão dentro da caixa
   (evita referências quebradas sem precisar do `osmium-tool` em C++).
3. Resultado: `osm_data/sao-luis.osm.bz2`, usado pela imagem Docker
   `wiktorn/overpass-api` em modo `init`.

## Como rodar

```
docker compose --profile overpass up -d overpass
```

A primeira subida importa o arquivo (`OVERPASS_MODE=init`) e pode levar
alguns minutos; depois disso o container fica servindo a API normalmente em
`http://localhost:12345/api/interpreter`, sem buscar atualizações externas
(não há `OVERPASS_DIFF_URL` configurado — é um retrato estático dos dados no
momento do download, o que é intencional para reprodutibilidade do
experimento).

Para reconstruir do zero (ex.: atualizar os dados), remova o conteúdo de
`osm_data/` (exceto o `.osm.bz2` fonte) e suba o container de novo, ou gere
um novo `sao-luis.osm.bz2` a partir de um extrato mais recente do Geofabrik.
