# -*- coding: utf-8 -*-
"""
Paso 1 del MVP: indexar las 438 tiendas del catalogo consolidado en una base
de datos vectorial (ChromaDB), usando el mismo modelo de embeddings que ya
se valido en E5 (text-embedding-3-small, OpenAI) porque fue el que gano
claramente a los otros 3 metodos (66.9% vs 52.9% del lexico).

Esto se corre normalmente una sola vez, o cada vez que cambie el catalogo.
Es seguro volver a correrlo: borra la coleccion anterior antes de reconstruirla,
asi que nunca duplica tiendas. El resultado queda guardado en disco (carpeta
chroma_db/), y el agente (agente.py) solo lee de ahi: no vuelve a llamar a
OpenAI para las tiendas en cada consulta.
"""
import os
import chromadb
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

RUTA_CATALOGO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Base de Datos - Portal Gamarrino\Catalogo Consolidado MVP\catalogo_consolidado_mvp.xlsx"
RUTA_CHROMA = os.path.join(BASE_DIR, "chroma_db")
COLECCION = "tiendas_gamarra_mvp"
MODELO_EMBEDDING = "text-embedding-3-small"

# Hace el script idempotente: sin esto, cada vez que se vuelve a correr
# Chroma.from_documents() SUMA las tiendas de nuevo en vez de reemplazarlas
# (porque no se le pasan ids fijos, genera uuids nuevos cada vez). Sin este
# borrado previo, correr el script dos veces deja 876 tiendas en vez de 438.
_cliente = chromadb.PersistentClient(path=RUTA_CHROMA)
try:
    _cliente.delete_collection(COLECCION)
    print(f"Coleccion '{COLECCION}' existente borrada, se reconstruye desde cero.")
except Exception:
    pass  # no existia todavia (primera corrida)

catalogo = pd.read_excel(RUTA_CATALOGO)
print(f"Catalogo: {len(catalogo)} tiendas")

documentos = []
for _, tienda in catalogo.iterrows():
    doc = Document(
        page_content=str(tienda["rag_text"]),
        metadata={
            "store_id": str(tienda["store_id"]),
            "display_name": str(tienda["display_name"]),
            "categories": str(tienda["categories"]),
            "subcategory": str(tienda["subcategory"]),
            "gallery": str(tienda["gallery"]),
            "floor": str(tienda["floor"]),
            "stand": str(tienda["stand"]),
            "whatsapp": str(tienda["whatsapp"]) if pd.notna(tienda["whatsapp"]) else "",
            "whatsapp_available": bool(tienda["whatsapp_available"]),
            "google_maps_url": str(tienda["google_maps_url"]) if pd.notna(tienda["google_maps_url"]) else "",
        },
    )
    documentos.append(doc)

embeddings = OpenAIEmbeddings(model=MODELO_EMBEDDING)

print(f"Generando embeddings y guardando en {RUTA_CHROMA} ...")
vectorstore = Chroma.from_documents(
    documents=documentos,
    embedding=embeddings,
    collection_name=COLECCION,
    persist_directory=RUTA_CHROMA,
)

print(f"Listo: {vectorstore._collection.count()} tiendas indexadas en la coleccion '{COLECCION}'")
