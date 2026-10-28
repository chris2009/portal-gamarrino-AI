# -*- coding: utf-8 -*-
"""Modelo v0 sobre las 280 consultas distintas de la muestra de 378.
Reusa los embeddings del catalogo (438 tiendas) ya generados antes."""
import re
import numpy as np
import pandas as pd
import requests
from sklearn.metrics.pairwise import cosine_similarity

ENV_PATH = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\.env"
PIPE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline"
BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"
RUTA_CATALOGO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\Catalogo Consolidado MVP\catalogo_consolidado_mvp.xlsx"

with open(ENV_PATH, "r", encoding="utf-8") as f:
    m = re.search(r'OPENAI_API_KEY\s*=\s*(\S+)', f.read())
API_KEY = m.group(1).strip().strip('"').strip("'")

MODEL = "text-embedding-3-small"
TOP_K = 3


def embed(textos, batch_size=100):
    vectores = []
    for i in range(0, len(textos), batch_size):
        lote = textos[i:i+batch_size]
        resp = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "input": lote},
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Error OpenAI API ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        vectores.extend([d["embedding"] for d in data["data"]])
        print(f"  Embebidos {min(i+batch_size, len(textos))}/{len(textos)}")
    return np.array(vectores)


catalogo = pd.read_excel(RUTA_CATALOGO)
store_ids_guardados = pd.read_csv(f"{PIPE}/emb_catalogo_store_ids.csv")
assert list(catalogo["store_id"]) == list(store_ids_guardados["store_id"]), "El catalogo cambio de orden, hay que regenerar embeddings del catalogo"
emb_catalogo = np.load(f"{PIPE}/emb_catalogo.npy")
print(f"Catalogo reusado: {emb_catalogo.shape}")

queries = pd.read_excel(f"{BASE}/consultas_distintas_para_etiquetar.xlsx")[["query_id", "consulta"]]
print(f"Consultas a embeber: {len(queries)}")
emb_queries = embed(queries["consulta"].tolist())

sim = cosine_similarity(emb_queries, emb_catalogo)

resultados = []
for i, (_, q) in enumerate(queries.iterrows()):
    orden = np.argsort(-sim[i])[:TOP_K]
    for rank, pos in enumerate(orden, 1):
        resultados.append({
            "query_id": q["query_id"], "consulta": q["consulta"], "metodo": "modelo_v0", "rank": rank,
            "store_id": catalogo.iloc[pos]["store_id"],
            "display_name": catalogo.iloc[pos]["display_name"],
            "categories": catalogo.iloc[pos]["categories"],
            "subcategory": catalogo.iloc[pos]["subcategory"],
            "gallery": catalogo.iloc[pos]["gallery"],
            "floor": catalogo.iloc[pos]["floor"],
            "stand": catalogo.iloc[pos]["stand"],
            "score_similitud": round(float(sim[i, pos]), 4),
        })

df = pd.DataFrame(resultados)
df.to_excel(f"{BASE}/candidatos_modelo_v0_378.xlsx", index=False)
print(f"\nGuardado: candidatos_modelo_v0_378.xlsx ({len(df)} filas)")

np.save(f"{BASE}/emb_queries_378.npy", emb_queries)
queries[["query_id"]].to_csv(f"{BASE}/emb_queries_378_ids.csv", index=False)

gt = pd.read_excel(f"{BASE}/ground_truth_378_FINAL.xlsx")
gt_keys = set(gt["key"])
df["key"] = df["query_id"].astype(str) + "|" + df["store_id"].astype(str)
cubiertos = df["key"].isin(gt_keys).sum()
print(f"\nCobertura: {cubiertos}/{len(df)} pares ya tienen etiqueta")
print(f"Pares NUEVOS sin etiqueta: {len(df) - cubiertos}")
nuevos = df[~df["key"].isin(gt_keys)].drop_duplicates(subset="key")
if len(nuevos):
    nuevos.to_excel(f"{BASE}/pares_nuevos_modelo_v0_378_SIN_ETIQUETAR.xlsx", index=False)
    print(f"Guardado: pares_nuevos_modelo_v0_378_SIN_ETIQUETAR.xlsx ({len(nuevos)} filas)")
