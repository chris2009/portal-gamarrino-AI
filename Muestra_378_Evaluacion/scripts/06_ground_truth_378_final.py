# -*- coding: utf-8 -*-
"""Ground truth final de las 2,299 filas (280 consultas distintas): 2,009
acuerdos directos pasada1=pasada2 + 290 resueltas por desempate. Luego Hit
Rate@3 de los 3 baselines, sin ponderar y ponderado por la muestra real de 378."""
import numpy as np
import pandas as pd

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

def norm(serie):
    s = serie.astype(str).str.strip().str.upper()
    return s.str[0].map({"S": "SI", "N": "NO"})

acuerdos = pd.read_csv(f"{BASE}/acuerdos_directos_378.csv")
desempate = pd.read_excel(f"{BASE}/hoja_desempate_378_290filas_ETIQUETADA.xlsx")
desempate["key"] = desempate["query_id"].astype(str) + "|" + desempate["store_id"].astype(str)
desempate["ground_truth_SiNo"] = norm(desempate["relevante_DESEMPATE_SiNo"])

gt = pd.concat([
    acuerdos[["key", "ground_truth_SiNo"]],
    desempate[["key", "ground_truth_SiNo"]],
], ignore_index=True)
print(f"Ground truth total: {len(gt)} filas (esperado 2299)")
print(f"Duplicadas: {gt['key'].duplicated().sum()}")
print(gt["ground_truth_SiNo"].value_counts())

relevancia = dict(zip(gt["key"], gt["ground_truth_SiNo"]))

candidatos = pd.read_excel(f"{BASE}/candidatos_por_metodo_378.xlsx")
candidatos["key"] = candidatos["query_id"].astype(str) + "|" + candidatos["store_id"].astype(str)
candidatos["relevante_GT"] = candidatos["key"].map(relevancia)
faltan = candidatos["relevante_GT"].isna().sum()
print(f"\nCandidatos sin match en ground truth: {faltan} / {len(candidatos)}")

mapa = pd.read_csv(f"{BASE}/mapa_muestra378_a_query_id.csv")

rng = np.random.default_rng(42)

print("\n=== SIN ponderar (280 consultas distintas) ===")
filas_sp = []
hits_dict = {}
for metodo, g in candidatos.groupby("metodo"):
    hits = g.groupby("query_id")["relevante_GT"].apply(lambda s: (s == "SI").any())
    hits_dict[metodo] = hits
    n = len(hits)
    hr = hits.mean()
    boot = np.array([hits.to_numpy()[rng.integers(0, n, n)].mean() for _ in range(1000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    filas_sp.append({"metodo": metodo, "n": n, "hit_rate_3": round(hr*100, 2),
                      "ic95_lo": round(lo*100, 2), "ic95_hi": round(hi*100, 2)})
    print(f"{metodo}: {hr*100:.2f}%  IC95=[{lo*100:.2f}%, {hi*100:.2f}%]")

print("\n=== PONDERADO (378, frecuencia real) ===")
filas_p = []
for metodo, hits in hits_dict.items():
    hits_df = hits.reset_index().rename(columns={"relevante_GT": "acierto"})
    exp = mapa.merge(hits_df, on="query_id", how="left")
    arr = exp["acierto"].dropna().to_numpy()
    n = len(arr)
    hr = arr.mean()
    boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(1000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    filas_p.append({"metodo": metodo, "n": n, "hit_rate_3": round(hr*100, 2),
                     "ic95_lo": round(lo*100, 2), "ic95_hi": round(hi*100, 2)})
    print(f"{metodo}: {hr*100:.2f}%  IC95=[{lo*100:.2f}%, {hi*100:.2f}%]")

orden = {"no_hacer_nada": 0, "lo_que_se_hace_hoy_categoria": 1, "modelo_simple_lexico": 2}
t1 = pd.DataFrame(filas_sp); t1["o"] = t1["metodo"].map(orden); t1 = t1.sort_values("o").drop(columns="o")
t2 = pd.DataFrame(filas_p); t2["o"] = t2["metodo"].map(orden); t2 = t2.sort_values("o").drop(columns="o")
t1.to_excel(f"{BASE}/hit_rate_378_FINAL_sin_ponderar.xlsx", index=False)
t2.to_excel(f"{BASE}/hit_rate_378_FINAL_ponderado.xlsx", index=False)

gt_out = candidatos.drop_duplicates(subset="key")[["key","query_id","consulta","store_id","display_name","relevante_GT"]]
gt_out.to_excel(f"{BASE}/ground_truth_378_FINAL.xlsx", index=False)
print(f"\nGuardado: ground_truth_378_FINAL.xlsx, hit_rate_378_FINAL_sin_ponderar.xlsx, hit_rate_378_FINAL_ponderado.xlsx")
