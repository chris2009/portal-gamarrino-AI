# -*- coding: utf-8 -*-
"""Tabla final de los 4 metodos sobre la muestra de 378 consultas.
modelo_v0: 195 ya cubiertos por el ground truth de los 3 baselines + 604
acuerdos directos + 41 resueltos por desempate = 840 total."""
import numpy as np
import pandas as pd

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

def norm(serie):
    s = serie.astype(str).str.strip().str.upper()
    return s.str[0].map({"S": "SI", "N": "NO"})

gt_3baselines = pd.read_excel(f"{BASE}/ground_truth_378_FINAL.xlsx")  # tiene 'key' y 'relevante_GT'
relevancia = dict(zip(gt_3baselines["key"], gt_3baselines["relevante_GT"]))

acuerdos_v0 = pd.read_csv(f"{BASE}/acuerdos_directos_nuevos_v0.csv")
relevancia.update(dict(zip(acuerdos_v0["key"], acuerdos_v0["ground_truth_SiNo"])))

desempate_v0 = pd.read_excel(f"{BASE}/hoja_desempate_nuevos_v0_41filas_ETIQUETADA.xlsx")
desempate_v0["lbl"] = norm(desempate_v0["relevante_DESEMPATE_SiNo"])
relevancia.update(dict(zip(desempate_v0["key"], desempate_v0["lbl"])))

candidatos_v0 = pd.read_excel(f"{BASE}/candidatos_modelo_v0_378.xlsx")
candidatos_v0["key"] = candidatos_v0["query_id"].astype(str) + "|" + candidatos_v0["store_id"].astype(str)
candidatos_v0["relevante_GT"] = candidatos_v0["key"].map(relevancia)
faltan = candidatos_v0["relevante_GT"].isna().sum()
print(f"modelo_v0: pares sin ground truth: {faltan} / {len(candidatos_v0)}")

candidatos_base = pd.read_excel(f"{BASE}/candidatos_por_metodo_378.xlsx")
candidatos_base["key"] = candidatos_base["query_id"].astype(str) + "|" + candidatos_base["store_id"].astype(str)
candidatos_base["relevante_GT"] = candidatos_base["key"].map(relevancia)

todos = pd.concat([
    candidatos_base[["query_id", "metodo", "relevante_GT"]],
    candidatos_v0[["query_id", "metodo", "relevante_GT"]],
], ignore_index=True)

mapa = pd.read_csv(f"{BASE}/mapa_muestra378_a_query_id.csv")
rng = np.random.default_rng(42)

print("\n=== SIN ponderar (por consulta distinta) ===")
filas_sp, filas_p = [], []
for metodo, g in todos.groupby("metodo"):
    hits = g.groupby("query_id")["relevante_GT"].apply(lambda s: (s == "SI").any())
    n = len(hits)
    hr = hits.mean()
    boot = np.array([hits.to_numpy()[rng.integers(0, n, n)].mean() for _ in range(1000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    filas_sp.append({"metodo": metodo, "n": n, "hit_rate_3": round(hr*100, 2),
                      "ic95_lo": round(lo*100, 2), "ic95_hi": round(hi*100, 2)})
    print(f"{metodo}: {hr*100:.2f}%  IC95=[{lo*100:.2f}%, {hi*100:.2f}%]  (n={n})")

    hits_df = hits.reset_index().rename(columns={"relevante_GT": "acierto"})
    exp = mapa.merge(hits_df, on="query_id", how="left")
    faltan_exp = exp["acierto"].isna().sum()
    arr = exp["acierto"].dropna().to_numpy()
    n2 = len(arr)
    hr2 = arr.mean()
    boot2 = np.array([arr[rng.integers(0, n2, n2)].mean() for _ in range(1000)])
    lo2, hi2 = np.percentile(boot2, [2.5, 97.5])
    filas_p.append({"metodo": metodo, "n": n2, "hit_rate_3": round(hr2*100, 2),
                     "ic95_lo": round(lo2*100, 2), "ic95_hi": round(hi2*100, 2)})

print("\n=== PONDERADO (378, frecuencia real) ===")
orden = {"no_hacer_nada": 0, "lo_que_se_hace_hoy_categoria": 1, "modelo_simple_lexico": 2, "modelo_v0": 3}
t1 = pd.DataFrame(filas_sp); t1["o"] = t1["metodo"].map(orden); t1 = t1.sort_values("o").drop(columns="o")
t2 = pd.DataFrame(filas_p); t2["o"] = t2["metodo"].map(orden); t2 = t2.sort_values("o").drop(columns="o")
print(t2.to_string(index=False))

print("\n=== TABLA SIN PONDERAR ===")
print(t1.to_string(index=False))

t1.to_excel(f"{BASE}/TABLA_FINAL_378_4metodos_sin_ponderar.xlsx", index=False)
t2.to_excel(f"{BASE}/TABLA_FINAL_378_4metodos_ponderado.xlsx", index=False)
print(f"\nGuardado: TABLA_FINAL_378_4metodos_sin_ponderar.xlsx y _ponderado.xlsx")
