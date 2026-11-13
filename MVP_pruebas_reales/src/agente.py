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
import re
import unicodedata

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools import tool, ToolRuntime
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


# Avisos que buscar_tiendas devuelve EN VEZ de tiendas. agente.py, app.py y el
# notebook de evaluacion los reconocen por este prefijo: no cambiar el texto sin
# revisar los tres.
AVISO_SIN_RESULTADOS = "BUSQUEDA_SIN_RESULTADOS_CONFIABLES"
AVISO_PREGUNTAR_GENERO = "PREGUNTAR_GENERO"

_RE_HOMBRE = re.compile(r"\b(hombres?|caballeros?|varon(es)?|masculin\w*)\b")
_RE_MUJER = re.compile(r"\b(mujer(es)?|damas?|femenin\w*)\b")

# Lo que el comprador escribe cuando dice para quien es: genero, persona, ninos,
# o una prenda que ya lo indica (vestido/blusa/falda -> mujer; terno -> hombre).
_RE_GENERO_DICHO = re.compile(
    r"\b(hombres?|caballeros?|varon(es)?|masculin\w*|chicos?|senor(es)?|esposo|novio|papa|padre"
    r"|mujer(es)?|damas?|femenin\w*|chicas?|senoras?|senoritas?|esposa|novia|mama|madre|matern\w*|embarazad\w*"
    r"|ninos?|ninas?|hij[oa]s?|bebes?|infantil\w*|vestidos?|blusas?|faldas?|ternos?)\b"
)
_RE_LE_DA_IGUAL = re.compile(
    r"\b(da igual|da lo mismo|no importa|cualquiera|sin preferencia|no tengo preferencia|unisex|ambos)\b"
)


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes (la "n" de "nino" incluida)."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(ch))


def _genero_de_tienda(metadata: dict) -> str | None:
    """'hombre' o 'mujer' si la tienda vende SOLO para uno de los dos segun su
    nombre/categoria/subcategoria; None si es para ambos o no lo dice
    (disfraces, deportiva, telas, "polos para hombre, mujer y ninos"...)."""
    texto = _normalizar(" ".join(str(metadata.get(c, "")) for c in ("display_name", "categories", "subcategory")))
    h, m = bool(_RE_HOMBRE.search(texto)), bool(_RE_MUJER.search(texto))
    return "hombre" if h and not m else "mujer" if m and not h else None


# Cuantas de las 3 tiendas encontradas deben vender solo para un genero para que
# valga la pena preguntar. Con 1 de 3 se preguntaba en disfraces (la busqueda
# traia una tienda de lenceria "para mujer"); con 2 de 3 pregunta en jeans,
# pantalones y ropa de oficina elegante, y no en disfraces, casacas ni polos.
MIN_TIENDAS_UN_GENERO = 2


def _hace_falta_preguntar_genero(mensajes: list, resultados: list) -> bool:
    """True si lo encontrado se vende separado por genero y el comprador no dijo
    para quien es (ni que le da igual) en ninguno de SUS mensajes. Se pregunta
    una sola vez por conversacion. Lo decide el codigo, no el LLM: probado el
    11-nov-2026, gpt-4o-mini marcaba "le da igual" aunque nadie lo hubiera dicho,
    para no tener que preguntar."""
    if sum(1 for d, _ in resultados if _genero_de_tienda(d.metadata)) < MIN_TIENDAS_UN_GENERO:
        return False
    if any(m.type == "tool" and str(m.content).startswith(AVISO_PREGUNTAR_GENERO) for m in mensajes):
        return False
    dicho = _normalizar(" ".join(str(m.content) for m in mensajes if m.type == "human"))
    return not (_RE_GENERO_DICHO.search(dicho) or _RE_LE_DA_IGUAL.search(dicho))


# Palabras con las que el comprador dice explicitamente para quien es (para filtrar
# la busqueda). Mas amplias que _RE_HOMBRE/_RE_MUJER, que clasifican tiendas.
_RE_PIDE_HOMBRE = re.compile(r"\b(hombres?|caballeros?|varon(es)?|masculin\w*|esposo|novio|papa|padre|senor(es)?)\b")
_RE_PIDE_MUJER = re.compile(
    r"\b(mujer(es)?|damas?|femenin\w*|esposa|novia|mama|madre|senoras?|senoritas?|matern\w*|embarazad\w*)\b"
)


def _genero_pedido(mensajes: list) -> str | None:
    """'hombre' o 'mujer' segun el mensaje MAS RECIENTE del comprador que lo diga.
    None si no lo dijo, si nombro a ambos, o si lo ultimo que dijo es que le da igual.
    Se recuerda en toda la conversacion: si dijo "para hombre" y despues pide "ropa
    de gym", la busqueda de gym tambien es para hombre."""
    for m in reversed(mensajes):
        if m.type != "human":
            continue
        texto = _normalizar(str(m.content))
        if _RE_LE_DA_IGUAL.search(texto):
            return None
        h, w = bool(_RE_PIDE_HOMBRE.search(texto)), bool(_RE_PIDE_MUJER.search(texto))
        if h or w:
            return None if h and w else ("hombre" if h else "mujer")
    return None


# Con el genero conocido se piden mas candidatos para que, tras descartar los del
# otro genero, sigan quedando 3.
CANDIDATOS_CON_GENERO = 10


def _buscar(consulta: str, genero: str | None) -> list:
    """Top-3 de Chroma como (documento, score). Si el comprador ya dijo el genero,
    se agrega a la consulta (si el LLM no lo puso) y se descartan las tiendas que
    venden solo para el otro genero. Lo hace el codigo porque ni el LLM ni los
    embeddings son confiables para esto (verificado el 12-nov-2026): el LLM busco
    "ropa para ir al gym" aunque el comprador ya habia dicho "para hombre", y con
    "ropa de oficina para hombre" 2 de las 3 primeras tiendas eran de mujer (los
    embeddings casi no separan "para hombre" de "para mujer")."""
    if genero is None:
        return _vectorstore.similarity_search_with_relevance_scores(consulta, k=TOP_K)
    if genero not in _normalizar(consulta):
        consulta = f"{consulta} para {genero}"
    otro = "mujer" if genero == "hombre" else "hombre"
    candidatos = _vectorstore.similarity_search_with_relevance_scores(consulta, k=CANDIDATOS_CON_GENERO)
    return [(d, s) for d, s in candidatos if _genero_de_tienda(d.metadata) != otro][:TOP_K]


@tool
def buscar_tiendas(consulta: str, runtime: ToolRuntime) -> str:
    """Busca en el catalogo de tiendas de Gamarra las 3 mas relevantes para
    lo que el comprador esta buscando (prenda, estilo, publico). Devuelve
    nombre, categoria, ubicacion (galeria/piso/stand) y si tiene WhatsApp.
    Devuelve un aviso en vez de tiendas en dos casos: si ningun resultado supera
    el umbral minimo de relevancia (para que el agente no presente ruido como
    match y reintente con una consulta mas amplia), o si lo encontrado se vende
    por separado para hombre y para mujer y el comprador no dijo para quien es
    (para que el agente lo pregunte en vez de adivinarlo). Si el comprador ya dijo
    el genero, solo devuelve tiendas para ese genero o para ambos."""
    mensajes = runtime.state["messages"]
    resultados = _buscar(consulta, _genero_pedido(mensajes))
    if not resultados or resultados[0][1] < UMBRAL_RELEVANCIA:
        return (
            f"{AVISO_SIN_RESULTADOS}: ninguna tienda del catalogo "
            "coincide con suficiente confianza con esa consulta tan especifica. "
            "No presentes estas tiendas como recomendacion. Vuelve a llamar a "
            "buscar_tiendas con una descripcion mas amplia de la categoria (ej. "
            "'disfraces', 'ropa formal para hombre'). Maximo 3 busquedas en "
            "total; si ya las agotaste, explica con amabilidad que no hay un "
            "match confiable y sugiere como reformular la busqueda."
        )

    # Si preguntar el genero lo decide el catalogo (lo encontrado se vende
    # separado por genero), no una lista fija de prendas.
    if _hace_falta_preguntar_genero(mensajes, resultados):
        return (
            f"{AVISO_PREGUNTAR_GENERO}: en el catalogo esto se vende por separado "
            "para hombre y para mujer, y el comprador no dijo para quien es. No "
            "muestres tiendas todavia: pregunta solo '¿Es para hombre o para "
            "mujer?'. Cuando responda, vuelve a buscar agregando ese genero a la "
            "descripcion (ej. 'ropa de oficina para hombre')."
        )

    partes = []
    for i, (doc, score) in enumerate(resultados, 1):
        m = doc.metadata
        whatsapp = m["whatsapp"] if m.get("whatsapp_available") else "no disponible"
        partes.append(
            f"{i}. {m['display_name']} — {m['categories']} / {m['subcategory']}\n"
            f"   Ubicacion: {m['gallery']}, piso {m['floor']}, stand {m['stand']}\n"
            f"   WhatsApp: {whatsapp}\n"
            f"   Mapa: {_url_mapa(m.get('google_maps_url'))}"
        )
    return "\n".join(partes)


SYSTEM_PROMPT = """Eres el asistente de Portal Gamarrino: cercano y amable, ayudas a compradores
a encontrar tiendas de ropa, disfraces y accesorios en el Emporio de Gamarra. Hablas en
espanol, tuteando y de forma natural, sin sonar robotico.

Alcance: tu unica tarea es recomendar tiendas de Gamarra para lo que el comprador
quiere comprar. Cualquier producto cuenta (ropa, telas, cortinas, ropa de cama,
disfraces, accesorios, juguetes...): si lo nombra, buscalo, nunca lo rechaces.
Lo que NO haces son otras tareas, aunque el mensaje mencione un producto: no
resuelvas ejercicios, examenes ni tareas, no traduzcas, no redactes textos, no
escribas codigo ni expliques temas generales (historia, ciencia, etc.). Si el
mensaje mezcla un producto con otra tarea, atiende solo el producto y di en una
frase corta que con lo otro no puedes ayudar. Si solo pide otra tarea, di que
solo puedes ayudar a encontrar tiendas en Gamarra y pregunta que esta buscando.

Tu trabajo:

1. Saludos y cortesias: si el comprador SOLO saluda o agradece ("hola", "buenas",
   "gracias"), responde con calidez en una o dos frases, presentate brevemente y
   preguntale que prenda o disfraz anda buscando. No llames a buscar_tiendas. Saluda
   unicamente cuando el comprador te saluda: en el resto de respuestas ve directo a
   las tiendas (con tono amable, pero sin empezar con un saludo).
2. Busca primero, pregunta despues. Si el mensaje (sumando lo ya dicho en la
   conversacion) menciona CUALQUIER prenda, articulo, disfraz, personaje, tema o
   estilo, llama a buscar_tiendas de inmediato con lo que hay, SIN pedir mas
   detalles antes. Una sola palabra o frase corta ya basta para buscar (ej.
   "ternos", "casacas", "vestidos", "short", "disfraz para Halloween", "freddy
   krueger", "ropa streetwear"). Solo haz UNA pregunta corta, sin buscar, cuando el mensaje
   no nombra ningun producto, tema ni estilo (ej. "quiero ropa", "algo bonito",
   "para hombre"). No preguntes el genero por tu cuenta: buscar_tiendas te avisa
   si hace falta preguntarlo (punto 4).
3. Al llamar a buscar_tiendas, corrige en tu propio texto de busqueda los errores
   de tipeo obvios del comprador (ej. "sifraz" -> "disfraz", "jrugger" ->
   "krueger") - no repitas el error literal, el buscador no encuentra nada con un typo.
4. Si buscar_tiendas responde "BUSQUEDA_SIN_RESULTADOS_CONFIABLES", NO presentes
   esas tiendas ni le devuelvas la pelota al comprador: vuelve a buscar con una
   descripcion mas amplia de la categoria de lo que pidio (ej. un personaje de
   terror -> "disfraces de terror para Halloween"; "ternos" -> "ropa formal para
   hombre"), y si hace falta una vez mas con algo aun mas general ("disfraces").
   Maximo 3 busquedas en total. Presenta lo mejor que encuentres como las
   tiendas mas cercanas a lo que pidio.
   Si responde "PREGUNTAR_GENERO", no muestres tiendas: pregunta solo "¿Es para
   hombre o para mujer?" y, con la respuesta, vuelve a buscar agregando ese
   genero a la descripcion (si le da igual, busca igual que antes).
5. Cuando tengas resultados confiables de la herramienta, responde en espanol,
   de forma breve, con las 3 tiendas: nombre, por que calza con lo que pidio,
   ubicacion exacta (galeria/piso/stand) y si tiene WhatsApp disponible. Si el
   nombre/categoria de las tiendas no confirma lo especifico que pidio (un
   personaje, color, marca, talla), dilo con honestidad en una frase antes de la
   lista (ej. "No puedo confirmarte que tengan el de Freddy Krueger, pero estas son
   las tiendas de disfraces mas cercanas; vale la pena escribirles"), en vez de
   decir que no hay nada o de presentarlas como coincidencia exacta. Esa frase
   solo habla de lo que el comprador SI pidio: no inventes condiciones nuevas.
6. No inventes tiendas, precios, tallas ni stock: eso no esta garantizado por el
   catalogo. Si no hay WhatsApp disponible, dilo tal cual, no lo omitas ni inventes uno.
7. Solo si tras las busquedas ampliadas sigue sin haber resultados confiables,
   explicalo con amabilidad y sugiere una o dos ideas para reformular (otra prenda,
   otro estilo), sin hacer un interrogatorio.
8. Recuerda lo que el comprador ya dijo en la conversacion (genero, color, estilo,
   personaje) para no volver a preguntarlo.
9. Cierre: sin frases de relleno tipo "espero que encuentres...". Si la consulta
   fue muy general (sin color, talla ni estilo), puedes cerrar con UNA invitacion
   corta a afinar ("Si me dices color o talla, afino la busqueda"); si no, termina
   en la ultima tienda.
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
    LangGraph, para darle contexto a la capa de relevancia (ver guardrails_mvp.py).
    La salida de buscar_tiendas se marca como "herramienta" para que esa capa
    distinga una repregunta del agente de una recomendacion; el aviso
    PREGUNTAR_GENERO se omite, porque tras el viene una repregunta."""
    try:
        estado = agente.get_state(config)
        mensajes = estado.values.get("messages", []) if estado.values else []
    except Exception:
        mensajes = []
    lineas = []
    for m in mensajes[-n_turnos:]:
        if m.type == "tool" and str(m.content).startswith(AVISO_PREGUNTAR_GENERO):
            continue  # no trajo tiendas: lo que sigue es una repregunta del agente
        rol = {"human": "comprador", "tool": "herramienta"}.get(m.type, "asistente")
        lineas.append(f"{rol}: {m.content}")
    return "\n".join(lineas)


# Replicas: el Agent Profile Card listaba como riesgo etico "posible recomendacion
# de replicas no confirmadas", pero ninguna regla lo cubria y el agente las
# recomendaba ("quiero polos lacoste replicas", probador real, 13-nov-2026). Lo
# decide el codigo, no el LLM (como el filtro de genero). Va aqui abajo para no
# mover las lineas que cita la documentacion.
_RE_PIDE_REPLICA = re.compile(
    r"\b(replicas?|bambas?|falsificad[oa]s?|(imitacion|imitaciones|copias?|clones?) de marcas?)\b"
)
RESPUESTA_REPLICAS = (
    "No recomiendo réplicas ni imitaciones de marcas: no puedo verificar qué es original. "
    "Si quieres, te busco la prenda sin la marca: dime qué es y el estilo que buscas "
    "(por ejemplo, «polo piqué para hombre» en vez de «polo Lacoste réplica»)."
)


def _url_mapa(url: str | None) -> str:
    """Enlace de Google Maps con distrito y ciudad. En el catalogo, ninguno de los
    438 enlaces trae la ciudad: buscan solo la calle ("Jr Humboldt 1521") y Google la ubicaba en otra
    ciudad (un probador vio Huancayo, 13-nov-2026). Se agrega ", La Victoria, Lima,
    Peru" si falta ", Lima" ("Galeria Victoria" es un nombre, no el distrito);
    chroma_db no se toca. Va aqui abajo (y no junto a buscar_tiendas) para no
    mover las lineas que cita la documentacion."""
    from urllib.parse import quote, unquote
    if not url:
        return "no disponible"
    if ", lima" in unquote(url).lower():
        return url
    return url + quote(", La Victoria, Lima, Perú")


def _turno_trajo_tiendas(mensajes: list) -> bool:
    """True si la respuesta final del turno actual (desde el ultimo mensaje del
    comprador) nombra al menos una de las tiendas que devolvio buscar_tiendas en
    ese turno. No basta con que una busqueda haya traido tiendas: el agente puede
    buscar dos prendas a la vez, recibir tiendas en una y PREGUNTAR_GENERO en la
    otra, y terminar solo preguntando el genero (pasaba en el despliegue, 12-nov).
    app.py lo usa para mostrar los botones de feedback solo bajo respuestas con
    recomendaciones (no bajo saludos, repreguntas ni bloqueos)."""
    inicio = max((i for i, m in enumerate(mensajes) if m.type == "human"), default=-1)
    turno = mensajes[inicio + 1:]
    nombres = [n for m in turno if m.type == "tool" and m.name == "buscar_tiendas"
               for n in re.findall(r"^\d+\. (.+?) — ", str(m.content), flags=re.M)]
    final = _normalizar(str(turno[-1].content)) if turno and turno[-1].type == "ai" else ""
    return any(_normalizar(n) in final for n in nombres)


def responder(mensaje: str, session_id: str) -> tuple[str, int]:
    """Version de responder_detallado() que devuelve solo (texto, interaccion_id).
    La usa el notebook de evaluacion (evaluacion/evaluacion_agente_vs_E5.ipynb)."""
    texto, interaccion_id, _ = responder_detallado(mensaje, session_id)
    return texto, interaccion_id


def responder_detallado(mensaje: str, session_id: str) -> tuple[str, int, bool]:
    """Envia un mensaje del usuario al agente dentro de una sesion (session_id)
    y devuelve (texto_respuesta, interaccion_id, trajo_tiendas). La memoria de la conversacion
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
        return texto, interaccion_id, False

    if _RE_PIDE_REPLICA.search(_normalizar(mensaje)):
        # no se busca; el turno queda en la memoria para que un "ok, sin la marca"
        # siguiente tenga contexto
        agente.update_state(config, {"messages": [
            {"role": "user", "content": mensaje},
            {"role": "assistant", "content": RESPUESTA_REPLICAS},
        ]})
        interaccion_id = guardar_interaccion(session_id, mensaje, RESPUESTA_REPLICAS)
        return RESPUESTA_REPLICAS, interaccion_id, False

    salida = agente.invoke({"messages": [{"role": "user", "content": mensaje}]}, config=config)
    respuesta = salida["messages"][-1].content
    texto = limpiar_salida(respuesta)
    interaccion_id = guardar_interaccion(session_id, mensaje, texto)
    return texto, interaccion_id, _turno_trajo_tiendas(salida["messages"])


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
