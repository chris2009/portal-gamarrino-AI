# -*- coding: utf-8 -*-
"""
Genera la muestra probabilistica de 378 consultas pre-registrada en el informe
preliminar (linea 731: "muestreo sistematico con arranque al azar", sobre las
4,000 consultas en mano). Preserva la frecuencia real (no deduplica antes de
muestrear) para que el Hit Rate@3 final pese cada tipo de consulta como
realmente la escriben los usuarios. Luego separa los textos DISTINTOS dentro
de esa muestra, porque repetir la misma etiqueta para el mismo texto exacto
no aporta nada nuevo: se etiqueta una sola vez y se reusa el resultado para
las repeticiones al calcular la metrica final.
"""
import re
import unicodedata
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RUTA_POOL = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\consultas x 4000.xlsx"
RUTA_CATALOGO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\Catalogo Consolidado MVP\catalogo_consolidado_mvp.xlsx"
OUT = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

SEED = 42
N_MUESTRA = 378
TOP_K = 3


def normalizar(texto):
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"\s+", " ", texto)
    return texto


pool = pd.read_excel(RUTA_POOL)
pool["consulta"] = pool["consulta"].astype(str).str.strip()
N = len(pool)

k = N / N_MUESTRA
rng = np.random.default_rng(SEED)
r = rng.uniform(0, k)
idx = sorted({int(r + i * k) for i in range(N_MUESTRA)})
# por si el redondeo deja menos de 378 unicos (no deberia con este N/n), completar
faltan = N_MUESTRA - len(idx)
if faltan > 0:
    restantes = [i for i in range(N) if i not in set(idx)]
    extra = rng.choice(restantes, size=faltan, replace=False)
    idx = sorted(set(idx) | set(extra.tolist()))

muestra = pool.iloc[idx].reset_index(drop=False).rename(columns={"index": "indice_original_4000"})
muestra["texto_normalizado"] = muestra["consulta"].apply(normalizar)
muestra["muestra_id"] = ["M{:03d}".format(i + 1) for i in range(len(muestra))]

print(f"Metodo: sistematico con arranque al azar, seed={SEED}, k={k:.3f}")
print(f"Poblacion (consultas x 4000.xlsx): {N} filas")
print(f"Muestra generada: {len(muestra)} filas (objetivo: {N_MUESTRA})")

muestra_out = muestra[["muestra_id", "indice_original_4000", "consulta", "texto_normalizado"]]
muestra_out.to_excel(f"{OUT}/muestra_378_consultas.xlsx", index=False)
print(f"Guardado: {OUT}/muestra_378_consultas.xlsx")

# textos distintos dentro de la muestra de 378, con su frecuencia real (peso para la metrica final)
distintos = (
    muestra.groupby("texto_normalizado")
    .agg(consulta=("consulta", "first"), frecuencia_en_muestra_378=("consulta", "size"))
    .reset_index()
    .sort_values("frecuencia_en_muestra_378", ascending=False)
    .reset_index(drop=True)
)
distintos["query_id"] = ["Q{:03d}".format(i + 1) for i in range(len(distintos))]
distintos = distintos[["query_id", "consulta", "texto_normalizado", "frecuencia_en_muestra_378"]]
distintos.to_excel(f"{OUT}/consultas_distintas_para_etiquetar.xlsx", index=False)
print(f"Textos distintos a etiquetar: {len(distintos)} (de {len(muestra)} muestreadas)")
print(f"Guardado: {OUT}/consultas_distintas_para_etiquetar.xlsx")

# mapa muestra_id -> query_id, para reconstruir el Hit Rate@3 ponderado despues
mapa = muestra[["muestra_id", "texto_normalizado"]].merge(
    distintos[["query_id", "texto_normalizado"]], on="texto_normalizado", how="left"
)[["muestra_id", "query_id"]]
mapa.to_csv(f"{OUT}/mapa_muestra378_a_query_id.csv", index=False, encoding="utf-8-sig")
print(f"Guardado: {OUT}/mapa_muestra378_a_query_id.csv (para expandir la metrica final)")

# --- generar candidatos de los 3 baselines sobre estos textos distintos ---
catalogo = pd.read_excel(RUTA_CATALOGO)
catalogo["categoria_texto"] = catalogo["categories"].fillna("") + " " + catalogo["subcategory"].fillna("")

queries = distintos.rename(columns={"consulta": "texto"})[["query_id", "texto"]]


def topk_random(catalogo, queries, k=TOP_K, seed=SEED):
    rng = np.random.default_rng(seed)
    store_ids = catalogo["store_id"].to_numpy()
    filas = []
    for _, q in queries.iterrows():
        elegidos = rng.choice(store_ids, size=k, replace=False)
        for rank, sid in enumerate(elegidos, 1):
            filas.append({"query_id": q["query_id"], "metodo": "no_hacer_nada", "rank": rank, "store_id": sid})
    return pd.DataFrame(filas)


def topk_similitud(catalogo, queries, columna, metodo, k=TOP_K):
    vec = TfidfVectorizer()
    m_cat = vec.fit_transform(catalogo[columna].fillna(""))
    m_q = vec.transform(queries["texto"])
    sim = cosine_similarity(m_q, m_cat)
    filas = []
    for i, (_, q) in enumerate(queries.iterrows()):
        orden = np.argsort(-sim[i])[:k]
        for rank, pos in enumerate(orden, 1):
            filas.append({
                "query_id": q["query_id"], "metodo": metodo, "rank": rank,
                "store_id": catalogo.iloc[pos]["store_id"],
                "score_similitud": round(float(sim[i, pos]), 4),
            })
    return pd.DataFrame(filas)


r_random = topk_random(catalogo, queries)
r_categoria = topk_similitud(catalogo, queries, "categoria_texto", "lo_que_se_hace_hoy_categoria")
r_lexico = topk_similitud(catalogo, queries, "rag_text", "modelo_simple_lexico")

candidatos = pd.concat([r_random, r_categoria, r_lexico], ignore_index=True)
candidatos = candidatos.merge(
    catalogo[["store_id", "display_name", "categories", "subcategory", "gallery", "floor", "stand"]],
    on="store_id", how="left",
)
candidatos = candidatos.merge(queries, on="query_id", how="left").rename(columns={"texto": "consulta"})
candidatos.to_excel(f"{OUT}/candidatos_por_metodo_378.xlsx", index=False)
print(f"Guardado: {OUT}/candidatos_por_metodo_378.xlsx ({len(candidatos)} filas)")

candidatos["metodos_que_la_proponen"] = candidatos.groupby(["query_id", "store_id"])["metodo"].transform(
    lambda s: ", ".join(sorted(set(s)))
)
union = candidatos.drop_duplicates(subset=["query_id", "store_id"]).copy()
hoja = union.drop_duplicates(subset=["query_id", "store_id"])[
    ["query_id", "consulta", "store_id", "display_name", "categories", "subcategory",
     "gallery", "floor", "stand", "metodos_que_la_proponen"]
].sort_values(["query_id", "store_id"])
hoja["relevante_SiNo"] = ""
hoja.to_excel(f"{OUT}/hoja_etiquetado_378.xlsx", index=False)
print(f"Guardado: {OUT}/hoja_etiquetado_378.xlsx ({len(hoja)} filas unicas consulta-tienda por etiquetar)")
