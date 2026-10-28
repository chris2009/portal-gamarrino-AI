# -*- coding: utf-8 -*-
"""Clasifica las 280 consultas distintas en 3 segmentos (heuristica por
palabras clave, documentada) y calcula Hit Rate@3 de modelo_v0 por segmento,
ponderado por la frecuencia real en la muestra de 378."""
import re
import unicodedata
import numpy as np
import pandas as pd

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

def norm(txt):
    txt = str(txt).strip().lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    return txt

PALABRAS_AMBIGUAS = [
    "pinterest", "2000", "yk2", "y2k", "old money", "shoujo", "alternativ",
    "tendencia", "sobrio", "algo para", "algo asi", "como para", "no se",
]
PALABRAS_MARCA_TALLA_PRECIO = [
    "talla", "precio", "soles", "s/.", "s/ ", "costo", "barato", "barata",
    "caro", "cara", "replica", "exportacion", "original", "de marca",
    "marca ", " xs", " xl", " xxl",
]
PRENDAS = [
    "polo", "vestid", "jean", "pantalon", "casaca", "terno", "blusa",
    "camisa", "falda", "short", "buzo", "chompa", "chaleco", "saco",
    "blazer", "bano", "bikini", "conjunto", "tela", "poncho", "abrigo",
    "sueter", "medias", "pijama", "overol", "mono", "enterizo", "top",
    "leggin", "capa", "bolero", "traje", "canguro", "gorra", "bividi",
    "polera", "camiseta", "ropa interior", "zapat", "calzad",
]

def clasificar(texto_norm, n_palabras):
    if any(p in texto_norm for p in PALABRAS_MARCA_TALLA_PRECIO) or re.search(r"\d", texto_norm):
        return "Con marca, talla o precio"
    tiene_prenda = any(p in texto_norm for p in PRENDAS)
    es_vaga = any(p in texto_norm for p in PALABRAS_AMBIGUAS)
    es_compuesta = (" y " in texto_norm and sum(texto_norm.count(p) for p in PRENDAS) == 0 is False and
                    sum(1 for p in PRENDAS if p in texto_norm) >= 2)
    if not tiene_prenda or es_vaga or es_compuesta:
        return "Ambigua o compuesta"
    return "Especifica (una prenda)"

q = pd.read_excel(f"{BASE}/consultas_distintas_para_etiquetar.xlsx")
q["texto_norm"] = q["consulta"].apply(norm)
q["n_palabras"] = q["texto_norm"].str.split().apply(len)
q["segmento"] = q.apply(lambda r: clasificar(r["texto_norm"], r["n_palabras"]), axis=1)

print(q["segmento"].value_counts())
print()
for seg in q["segmento"].unique():
    print(f"--- {seg} (muestras) ---")
    print(q[q["segmento"]==seg]["consulta"].head(6).tolist())
    print()

q[["query_id","consulta","segmento"]].to_csv(f"{BASE}/segmentos_280.csv", index=False, encoding="utf-8-sig")

# ahora Hit Rate@3 de modelo_v0 por segmento, ponderado por frecuencia real (378)
gt = {}
for src in ["ground_truth_378_FINAL.xlsx"]:
    pass
import json

# reconstruir relevancia (igual que antes)
gt_3 = pd.read_excel(f"{BASE}/ground_truth_378_FINAL.xlsx")
relevancia = dict(zip(gt_3["key"], gt_3["relevante_GT"]))
acuerdos_v0 = pd.read_csv(f"{BASE}/acuerdos_directos_nuevos_v0.csv")
relevancia.update(dict(zip(acuerdos_v0["key"], acuerdos_v0["ground_truth_SiNo"])))
desempate_v0 = pd.read_excel(f"{BASE}/hoja_desempate_nuevos_v0_41filas_ETIQUETADA.xlsx")
desempate_v0["lbl"] = desempate_v0["relevante_DESEMPATE_SiNo"].astype(str).str.strip().str.upper().str[0].map({"S":"SI","N":"NO"})
relevancia.update(dict(zip(desempate_v0["key"], desempate_v0["lbl"])))

cand_v0 = pd.read_excel(f"{BASE}/candidatos_modelo_v0_378.xlsx")
cand_v0["key"] = cand_v0["query_id"].astype(str) + "|" + cand_v0["store_id"].astype(str)
cand_v0["relevante_GT"] = cand_v0["key"].map(relevancia)

hits = cand_v0.groupby("query_id")["relevante_GT"].apply(lambda s: (s=="SI").any())
hits_df = hits.reset_index().rename(columns={"relevante_GT":"acierto"})
hits_df = hits_df.merge(q[["query_id","segmento"]], on="query_id", how="left")

mapa = pd.read_csv(f"{BASE}/mapa_muestra378_a_query_id.csv")
exp = mapa.merge(hits_df, on="query_id", how="left")

print("\n=== Hit Rate@3 modelo_v0 por segmento (ponderado, 378) ===")
total_hr = exp["acierto"].mean()
rng = np.random.default_rng(42)
filas = []
for seg, g in exp.groupby("segmento"):
    arr = g["acierto"].to_numpy()
    n = len(arr)
    hr = arr.mean()
    boot = np.array([arr[rng.integers(0,n,n)].mean() for _ in range(1000)])
    lo,hi = np.percentile(boot,[2.5,97.5])
    dif = (hr-total_hr)*100
    filas.append({"segmento":seg, "n_casos_378": n, "hit_rate_3": round(hr*100,1),
                   "ic95_lo": round(lo*100,1), "ic95_hi": round(hi*100,1), "diferencia_vs_total_pp": round(dif,1)})
    print(f"{seg}: n={n}, HR@3={hr*100:.1f}% [{lo*100:.1f}-{hi*100:.1f}], total={total_hr*100:.1f}%, dif={dif:+.1f}pp")

print(f"\nTOTAL: n={len(exp)}, HR@3={total_hr*100:.1f}%")
pd.DataFrame(filas).to_excel(f"{BASE}/segmentos_hitrate_modelo_v0.xlsx", index=False)
