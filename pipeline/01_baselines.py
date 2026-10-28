# -*- coding: utf-8 -*-
"""
E5 - Portal Gamarrino AI
Corre los 3 baselines que NO requieren API externa (random, filtro por
categoria, lexico/TF-IDF) sobre las 50 consultas reales y el catalogo de
438 tiendas. Genera una hoja de etiquetado para que dos evaluadores marquen
relevancia (Si/No) por cada tienda candidata.

El cuarto metodo (Modelo v0 = text-embedding-3-small) queda pendiente:
requiere una OPENAI_API_KEY que todavia no esta configurada en este entorno.
Ver 02_modelo_v0.py para ese paso, una vez se tenga la clave.
"""
import re
import unicodedata
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RUTA_CATALOGO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\Catalogo Consolidado MVP\catalogo_consolidado_mvp.xlsx"
RUTA_CONSULTAS = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\Consultas Usuarios Portal Gamarrino (50 consultas reales).md"
RUTA_SALIDA_CANDIDATOS = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\candidatos_por_metodo.xlsx"
RUTA_SALIDA_ETIQUETADO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\hoja_etiquetado.xlsx"

SEED = 42
TOP_K = 3

# Consultas que no son de busqueda de producto: se excluyen del set de evaluacion
QUERIES_FUERA_DE_ALCANCE = {"como mando fotos"}


def normalizar(texto):
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def cargar_consultas(ruta_md):
    """Parsea la lista numerada del .md y deja solo consultas de busqueda, sin duplicados exactos."""
    filas = []
    with open(ruta_md, "r", encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"^\s*(\d+)\.\s+(.*\S)\s*$", linea)
            if not m:
                continue
            idx, texto = m.group(1), m.group(2).strip()
            filas.append({"orden_original": int(idx), "texto": texto})

    df = pd.DataFrame(filas)
    df["texto_normalizado"] = df["texto"].apply(normalizar)

    # fuera de alcance: vacias o no son busqueda de producto
    df = df[df["texto_normalizado"] != ""]
    df = df[df["texto_normalizado"] != "(vacio)"]
    df = df[~df["texto_normalizado"].isin(QUERIES_FUERA_DE_ALCANCE)]

    # duplicados exactos (texto igual tras normalizar) -> conservar solo la primera aparicion
    antes = len(df)
    df = df.drop_duplicates(subset="texto_normalizado", keep="first").reset_index(drop=True)
    print(f"Consultas: {antes} tras limpiar vacias/fuera-de-alcance -> {len(df)} distintas tras quitar duplicados exactos")

    df["query_id"] = ["Q{:02d}".format(i + 1) for i in range(len(df))]
    return df[["query_id", "orden_original", "texto"]]


def cargar_catalogo(ruta_xlsx):
    df = pd.read_excel(ruta_xlsx)
    df["categoria_texto"] = (df["categories"].fillna("") + " " + df["subcategory"].fillna(""))
    return df


def topk_random(catalogo, queries, k=TOP_K, seed=SEED):
    rng = np.random.default_rng(seed)
    resultados = []
    store_ids = catalogo["store_id"].to_numpy()
    for _, q in queries.iterrows():
        elegidos = rng.choice(store_ids, size=k, replace=False)
        for rank, sid in enumerate(elegidos, 1):
            resultados.append({"query_id": q["query_id"], "metodo": "no_hacer_nada", "rank": rank, "store_id": sid})
    return pd.DataFrame(resultados)


def topk_por_similitud(catalogo, queries, columna_texto, metodo_nombre, k=TOP_K):
    vectorizer = TfidfVectorizer()
    matriz_catalogo = vectorizer.fit_transform(catalogo[columna_texto].fillna(""))
    matriz_queries = vectorizer.transform(queries["texto"])
    sim = cosine_similarity(matriz_queries, matriz_catalogo)

    resultados = []
    for i, (_, q) in enumerate(queries.iterrows()):
        orden = np.argsort(-sim[i])[:k]
        for rank, pos in enumerate(orden, 1):
            resultados.append({
                "query_id": q["query_id"],
                "metodo": metodo_nombre,
                "rank": rank,
                "store_id": catalogo.iloc[pos]["store_id"],
                "score_similitud": round(float(sim[i, pos]), 4),
            })
    return pd.DataFrame(resultados)


def main():
    catalogo = cargar_catalogo(RUTA_CATALOGO)
    queries = cargar_consultas(RUTA_CONSULTAS)

    print(f"Catalogo: {len(catalogo)} tiendas")
    print(f"Consultas a evaluar: {len(queries)}")

    r_random = topk_random(catalogo, queries)
    r_categoria = topk_por_similitud(catalogo, queries, "categoria_texto", "lo_que_se_hace_hoy_categoria")
    r_lexico = topk_por_similitud(catalogo, queries, "rag_text", "modelo_simple_lexico")

    candidatos = pd.concat([r_random, r_categoria, r_lexico], ignore_index=True)
    candidatos = candidatos.merge(
        catalogo[["store_id", "display_name", "categories", "subcategory", "gallery", "floor", "stand"]],
        on="store_id", how="left",
    )
    candidatos = candidatos.merge(queries[["query_id", "texto"]], on="query_id", how="left")
    candidatos = candidatos.rename(columns={"texto": "consulta"})

    columnas_orden = ["query_id", "consulta", "metodo", "rank", "store_id", "display_name",
                       "categories", "subcategory", "gallery", "floor", "stand", "score_similitud"]
    candidatos = candidatos[[c for c in columnas_orden if c in candidatos.columns]]
    candidatos.to_excel(RUTA_SALIDA_CANDIDATOS, index=False)
    print(f"Guardado: {RUTA_SALIDA_CANDIDATOS} ({len(candidatos)} filas)")

    # Hoja de etiquetado: union de tiendas candidatas por consulta (sin duplicar
    # la misma tienda si aparece en mas de un metodo para la misma consulta),
    # con dos columnas en blanco para que dos evaluadores marquen Si/No.
    union = candidatos.drop_duplicates(subset=["query_id", "store_id"]).copy()
    union = union.sort_values(["query_id", "store_id"])
    union["relevante_evaluador1_SiNo"] = ""
    union["relevante_evaluador2_SiNo"] = ""
    union["metodos_que_la_proponen"] = union.groupby(["query_id", "store_id"])["metodo"].transform(
        lambda s: ", ".join(sorted(set(s)))
    )
    hoja = union.drop_duplicates(subset=["query_id", "store_id"])[
        ["query_id", "consulta", "store_id", "display_name", "categories", "subcategory",
         "gallery", "floor", "stand", "metodos_que_la_proponen",
         "relevante_evaluador1_SiNo", "relevante_evaluador2_SiNo"]
    ]
    hoja.to_excel(RUTA_SALIDA_ETIQUETADO, index=False)
    print(f"Guardado: {RUTA_SALIDA_ETIQUETADO} ({len(hoja)} filas unicas consulta-tienda para etiquetar)")

    queries.to_csv(RUTA_SALIDA_CANDIDATOS.replace(".xlsx", "") + "_queries_limpias.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
