# -*- coding: utf-8 -*-
"""
Paso 2 del MVP: el agente que le habla al comprador.

Que hace: recibe la consulta en lenguaje natural, busca en ChromaDB (ya
indexado por 01_indexar_catalogo.py) las tiendas mas parecidas por
significado, y responde con el top-3 + explicacion + ubicacion. Usa
LangGraph para el flujo (decide cuando llamar a la herramienta de busqueda)
y memoria conversacional para recordar preferencias dentro de la misma
sesion (por ejemplo, si el usuario ya dijo "para hombre" y luego solo dice
"en negro", el agente no tiene que volver a preguntar el genero).

Este modulo no se corre solo: lo importa app.py (la interfaz).
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from guardrails_mvp import verificar_entrada, limpiar_salida, GuardrailBloqueado
from historial_db import guardar_interaccion

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

RUTA_CHROMA = os.path.join(BASE_DIR, "chroma_db")
COLECCION = "tiendas_gamarra_mvp"
MODELO_EMBEDDING = "text-embedding-3-small"
MODELO_CHAT = "gpt-4o-mini"
TOP_K = 3

# Umbral de relevancia minima (relevance score, no distancia) para considerar
# un resultado como match real. Calibrado con 4 consultas reales: "casaca de
# cuero para hombre" (match claro) dio 0.309; "disfraz para Halloween" (match
# razonable) dio 0.236; "sifraz para Halloween" (typo, resultado basura que el
# agente presentaba igual antes de este umbral) dio apenas 0.072. Es un corte
# empirico con poca evidencia, no una cifra cientifica: si el equipo ve falsos
# negativos o positivos al usar el agente, hay que recalibrarlo con mas datos.
UMBRAL_RELEVANCIA = 0.15

_embeddings = OpenAIEmbeddings(model=MODELO_EMBEDDING)
_vectorstore = Chroma(
    collection_name=COLECCION,
    embedding_function=_embeddings,
    persist_directory=RUTA_CHROMA,
)


@tool
def buscar_tiendas(consulta: str) -> str:
    """Busca en el catalogo de tiendas de Gamarra las 3 mas relevantes para
    lo que el comprador esta buscando (prenda, estilo, publico). Devuelve
    nombre, categoria, ubicacion (galeria/piso/stand) y si tiene WhatsApp.
    Si ningun resultado supera el umbral minimo de relevancia, devuelve un
    aviso en vez de tiendas (para que el agente pida mas detalle en lugar de
    presentar matches que en realidad son ruido)."""
    resultados = _vectorstore.similarity_search_with_relevance_scores(consulta, k=TOP_K)
    if not resultados or resultados[0][1] < UMBRAL_RELEVANCIA:
        return (
            "BUSQUEDA_SIN_RESULTADOS_CONFIABLES: ninguna tienda del catalogo "
            "coincide con suficiente confianza con esa consulta. No presentes "
            "estas tiendas como recomendacion. Pide al comprador que precise "
            "que prenda/articulo busca y para quien (hombre, mujer, nino/a)."
        )

    partes = []
    for i, (doc, score) in enumerate(resultados, 1):
        m = doc.metadata
        whatsapp = m["whatsapp"] if m.get("whatsapp_available") else "no disponible"
        partes.append(
            f"{i}. {m['display_name']} — {m['categories']} / {m['subcategory']}\n"
            f"   Ubicacion: {m['gallery']}, piso {m['floor']}, stand {m['stand']}\n"
            f"   WhatsApp: {whatsapp}\n"
            f"   Mapa: {m.get('google_maps_url', 'no disponible')}"
        )
    return "\n".join(partes)


SYSTEM_PROMPT = """Eres el asistente de Portal Gamarrino. Un comprador te describe
en lenguaje natural que prenda busca. Tu trabajo:

1. Antes de buscar, revisa si la consulta (sumando lo ya dicho en la conversacion)
   ya tiene AL MENOS UN atributo concreto ademas del tipo de prenda: color,
   talla, estilo, ocasion, o un personaje/tema si es un disfraz. Si lo tiene,
   busca directo (el genero no hace falta preguntarlo si se puede inferir de
   la prenda, ej. "vestido" sugiere mujer salvo que el comprador diga otra cosa).
   Si la consulta es generica y SIN ningun atributo diferenciador (ej. "busco
   un disfraz", "quiero ropa", "algo bonito", "busco un disfraz para Halloween"
   sin decir de que), haz UNA pregunta corta pidiendo ese detalle antes de buscar.
2. Al llamar a buscar_tiendas, corrige en tu propio texto de busqueda los errores
   de tipeo obvios del comprador (ej. si escribio "sifraz", busca "disfraz") -
   no repitas el error literal, el buscador no encuentra nada con un typo.
3. Si buscar_tiendas responde "BUSQUEDA_SIN_RESULTADOS_CONFIABLES", NO presentes
   esas tiendas como recomendacion. Explica brevemente que no encontraste un
   match confiable y pide el detalle que falta (que prenda exacta, para quien).
4. Cuando tengas resultados confiables de la herramienta, responde en espanol,
   de forma breve, con las 3 tiendas: nombre, por que calza con lo que pidio,
   ubicacion exacta (galeria/piso/stand) y si tiene WhatsApp disponible. Sin
   frase de cierre tipo "espero que encuentres..." - termina en la ultima tienda.
5. No inventes tiendas, precios, tallas ni stock: eso no esta garantizado por el
   catalogo. Si no hay WhatsApp disponible, dilo tal cual, no lo omitas ni inventes uno.
6. Recuerda lo que el comprador ya dijo en la conversacion (genero, color, estilo,
   personaje) para no volver a preguntarlo.
"""

_checkpointer = MemorySaver()

agente = create_agent(
    model=ChatOpenAI(model=MODELO_CHAT, temperature=0),
    tools=[buscar_tiendas],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


def _historial_reciente(config: dict, n_turnos: int = 4) -> str:
    """Lee los ultimos N mensajes de ESTA sesion desde el checkpointer de
    LangGraph, para darle contexto a la capa de relevancia (ver guardrails_mvp.py)."""
    try:
        estado = agente.get_state(config)
        mensajes = estado.values.get("messages", []) if estado.values else []
    except Exception:
        mensajes = []
    lineas = []
    for m in mensajes[-n_turnos:]:
        rol = "comprador" if m.type == "human" else "asistente"
        lineas.append(f"{rol}: {m.content}")
    return "\n".join(lineas)


def responder(mensaje: str, session_id: str) -> tuple[str, int]:
    """Envia un mensaje del usuario al agente dentro de una sesion (session_id)
    y devuelve (texto_respuesta, interaccion_id). La memoria de la conversacion
    (para seguimientos dentro de la sesion) se guarda en RAM via el checkpointer
    de LangGraph; por separado, CADA interaccion (incluida una bloqueada por un
    guardrail) se guarda de forma durable en historial.db junto con su id, para
    poder asociarle feedback despues (ver historial_db.py y app.py).

    Antes de llamar al agente corre los guardrails de entrada (seguridad +
    relevancia); despues de la respuesta corre el guardrail de salida (PII).
    Ver guardrails_mvp.py para el detalle de cada capa."""
    config = {"configurable": {"thread_id": session_id}}

    try:
        historial = _historial_reciente(config)
        verificar_entrada(mensaje, historial)
    except GuardrailBloqueado as e:
        texto = str(e)
        interaccion_id = guardar_interaccion(session_id, mensaje, texto)
        return texto, interaccion_id

    salida = agente.invoke({"messages": [{"role": "user", "content": mensaje}]}, config=config)
    respuesta = salida["messages"][-1].content
    texto = limpiar_salida(respuesta)
    interaccion_id = guardar_interaccion(session_id, mensaje, texto)
    return texto, interaccion_id


if __name__ == "__main__":
    # prueba rapida por consola, sin interfaz
    sesion = "prueba-consola"
    print("Agente Portal Gamarrino (escribe 'salir' para terminar)\n")
    while True:
        texto = input("Tu: ").strip()
        if texto.lower() in {"salir", "exit"}:
            break
        texto_respuesta, _ = responder(texto, sesion)
        print("Agente:", texto_respuesta, "\n")
