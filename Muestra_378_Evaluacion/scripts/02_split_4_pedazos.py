# -*- coding: utf-8 -*-
"""Parte la hoja de 378 en 4 pedazos en blanco (por query_id completo, no por
fila suelta) para una SEGUNDA pasada independiente -- se suma a la que ya
esta hecha (hoja_etiquetado_378_ETIQUETADA.xlsx) para poder sacar kappa."""
import numpy as np
import pandas as pd

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

candidatos = pd.read_excel(f"{BASE}/candidatos_por_metodo_378.xlsx")

union = candidatos.drop_duplicates(subset=["query_id", "store_id"]).copy()
union["metodos_que_la_proponen"] = union.groupby(["query_id", "store_id"])["metodo"].transform(
    lambda s: ", ".join(sorted(set(s)))
)
hoja = union.drop_duplicates(subset=["query_id", "store_id"])[
    ["query_id", "consulta", "store_id", "display_name", "categories", "subcategory",
     "gallery", "floor", "stand", "metodos_que_la_proponen"]
].sort_values(["query_id", "store_id"]).reset_index(drop=True)

queries_ordenadas = sorted(hoja["query_id"].unique(), key=lambda q: int(q[1:]))
n = len(queries_ordenadas)
rng = np.random.default_rng(7)
shuffled = queries_ordenadas.copy()
rng.shuffle(shuffled)
grupos = np.array_split(shuffled, 4)

print(f"Total consultas distintas: {n} -> 4 grupos de aprox {n//4} cada uno")

for i, grupo in enumerate(grupos, 1):
    pedazo = hoja[hoja["query_id"].isin(set(grupo))].drop(columns=["metodos_que_la_proponen"]).copy()
    pedazo["relevante_SiNo"] = ""
    pedazo = pedazo.sort_values(["query_id", "store_id"])
    out_path = f"{BASE}/PEDAZO_{i}_de_4.xlsx"
    pedazo.to_excel(out_path, index=False)
    print(f"PEDAZO_{i}_de_4.xlsx: {len(grupo)} consultas, {len(pedazo)} filas")
