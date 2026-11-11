#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recorta o extrato do Brasil (Geofabrik) para uma caixa delimitadora ao
redor de Sao Luis - MA, grande o suficiente para cobrir o raio de busca real
usado pela aplicacao (RADIUS_KM = 100 em run_date_experiment.py), nao so o
centro da cidade. Ver docs/overpass-local.md.

Mantem nos dentro da bbox; mantem ways apenas se TODOS os nos referenciados
tambem estiverem dentro da bbox (evita referencias quebradas sem precisar de
um segundo passo / osmium-tool em C++). Suficiente para o caso de uso: a
maioria dos amenity=cafe/restaurant/bar/etc. no OSM sao mapeados como nos
(pontos), nao como poligonos.

Uso:
    pip install osmium
    python scripts/crop_sao_luis.py
Le osm_data/brazil-latest.osm.pbf e escreve osm_data/sao-luis.osm.bz2.
"""
import os
import time

import osmium

# Sao Luis-MA fica em aprox. (-2.5300, -44.3028). RADIUS_KM=100 ~ 0.9-1.0 grau
# de margem; usamos uma caixa ainda mais generosa por seguranca.
MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = -45.40, -3.60, -43.20, -1.40

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(_BASE, "osm_data", "brazil-latest.osm.pbf")
DST = os.path.join(_BASE, "osm_data", "sao-luis.osm.bz2")


class CropHandler(osmium.SimpleHandler):
    def __init__(self, writer):
        super().__init__()
        self.writer = writer
        self.kept_node_ids = set()
        self.n_nodes_seen = 0
        self.n_nodes_kept = 0
        self.n_ways_seen = 0
        self.n_ways_kept = 0

    def node(self, n):
        self.n_nodes_seen += 1
        if n.location.valid():
            lon, lat = n.location.lon, n.location.lat
            if MIN_LON <= lon <= MAX_LON and MIN_LAT <= lat <= MAX_LAT:
                self.writer.add_node(n)
                self.kept_node_ids.add(n.id)
                self.n_nodes_kept += 1

    def way(self, w):
        self.n_ways_seen += 1
        if w.tags and all(nd.ref in self.kept_node_ids for nd in w.nodes):
            self.writer.add_way(w)
            self.n_ways_kept += 1


def main():
    if not os.path.exists(SRC):
        raise SystemExit(
            f"Nao encontrado: {SRC}\n"
            "Baixe primeiro: curl -L -o osm_data/brazil-latest.osm.pbf "
            "https://download.geofabrik.de/south-america/brazil-latest.osm.pbf"
        )
    t0 = time.time()
    writer = osmium.SimpleWriter(DST)
    handler = CropHandler(writer)
    print(f"Lendo {SRC} e recortando para bbox ({MIN_LON},{MIN_LAT},{MAX_LON},{MAX_LAT})...")
    handler.apply_file(SRC, locations=False)
    writer.close()
    dt = time.time() - t0
    print(f"Concluido em {dt:.1f}s -> {DST}")
    print(f"Nos: {handler.n_nodes_kept}/{handler.n_nodes_seen} mantidos")
    print(f"Ways: {handler.n_ways_kept}/{handler.n_ways_seen} mantidos")


if __name__ == "__main__":
    main()
