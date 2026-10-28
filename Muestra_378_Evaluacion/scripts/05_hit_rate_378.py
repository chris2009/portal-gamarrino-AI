# -*- coding: utf-8 -*-
"""Hit Rate@3 sobre la muestra de 378 (3 baselines), usando el etiquetado
recien completado por el equipo, ponderado por la frecuencia real de cada
texto distinto dentro de la muestra sistematica de 378."""
import numpy as np
import pandas as pd

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

etiquetas = pd.read_excel(f"{BASE}/hoja_etiquetado_378_ETIQUETADA.xlsx")
candidatos = pd.read_excel(f"{BASE}/candidatos_por_metodo_378.xlsx")
mapa = pd.read_csv(f"{BASE}/mapa_muestra378_a_query_id.csv")  # muestra_id -> query_id (280 distintas -> 378 con peso)

etiquetas["key"] = etiquetas["query_id"].astype(str) + "|" + etiquetas["store_id"].astype(str)
etiquetas["lbl"] = etiquetas["relevante_SiNo"].astype(str).str.strip().str.upper().str[0].map({"S": "SI", "N": "NO"})

candidatos["key"] = candidatos["query_id"].astype(str) + "|" + candidatos["store_id"].astype(str)
rel = dict(zip(etiquetas["key"], etiquetas["lbl"]))
candidatos["relevante_GT"] = candidatos["key"].map(rel)

faltan = candidatos["relevante_GT"].isna().sum()
print(f"Pares de candidatos sin match en el etiquetado: {faltan} / {len(candidatos)}")

# acierto por query_id (de las 280 distintas)
acierto_por_query = {}
for metodo, g in candidatos.groupby("metodo"):
    hits = g.groupby("query_id")["relevante_GT"].apply(lambda s: (s == "SI").any())
    acierto_por_query[metodo] = hits

print(f"\nTotal consultas distintas evaluadas: {candidatos['query_id'].nunique()} / 280 esperadas\n")

rng = np.random.default_rng(42)
print("=== SIN ponderar (una vez cada texto distinto, 280 consultas) ===")
filas_sinpond = []
for metodo, hits in acierto_por_query.items():
    n = len(hits)
    hr = hits.mean()
    boot = np.array([hits.to_numpy()[rng.integers(0, n, n)].mean() for _ in range(1000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    filas_sinpond.append({"metodo": metodo, "n_queries": n, "hit_rate_3": round(hr * 100, 2),
                           "ic95_lo": round(lo * 100, 2), "ic95_hi": round(hi * 100, 2)})
    print(f"{metodo}: {hr*100:.2f}%  IC95=[{lo*100:.2f}%, {hi*100:.2f}%]  (n={n})")

print("\n=== PONDERADO por frecuencia real en la muestra de 378 ===")
filas_pond = []
for metodo, hits in acierto_por_query.items():
    hits_df = hits.reset_index().rename(columns={"relevante_GT": "acierto"})
    expandido = mapa.merge(hits_df, on="query_id", how="left")
    faltan_exp = expandido["acierto"].isna().sum()
    if faltan_exp:
        print(f"  ATENCION {metodo}: {faltan_exp} filas de la muestra 378 sin match")
    arr = expandido["acierto"].dropna().to_numpy()
    n = len(arr)
    hr = arr.mean()
    boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(1000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    filas_pond.append({"metodo": metodo, "n_consultas_378": n, "hit_rate_3": round(hr * 100, 2),
                        "ic95_lo": round(lo * 100, 2), "ic95_hi": round(hi * 100, 2)})
    print(f"{metodo}: {hr*100:.2f}%  IC95=[{lo*100:.2f}%, {hi*100:.2f}%]  (n={n})")

orden = {"no_hacer_nada": 0, "lo_que_se_hace_hoy_categoria": 1, "modelo_simple_lexico": 2}
t1 = pd.DataFrame(filas_sinpond); t1["orden"] = t1["metodo"].map(orden); t1 = t1.sort_values("orden").drop(columns="orden")
t2 = pd.DataFrame(filas_pond); t2["orden"] = t2["metodo"].map(orden); t2 = t2.sort_values("orden").drop(columns="orden")
t1.to_excel(f"{BASE}/hit_rate_378_sin_ponderar.xlsx", index=False)
t2.to_excel(f"{BASE}/hit_rate_378_ponderado.xlsx", index=False)
print(f"\nGuardado: hit_rate_378_sin_ponderar.xlsx y hit_rate_378_ponderado.xlsx")
