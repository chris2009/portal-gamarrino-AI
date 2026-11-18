# -*- coding: utf-8 -*-
"""
Interfaz para las pruebas con usuarios reales (MVP_pruebas_reales/).

Es el mismo chat de MVP_Portal_Gamarrino/src/app.py (el agente v7 y la
pregunta "¿Te sirvieron estas recomendaciones?" con 👍/👎 solo bajo
respuestas con tiendas), mas lo necesario para abrirlo a probadores:

- Contraseña de acceso (variable APP_PASSWORD): solo entran los probadores,
  y nadie mas gasta la cuenta de OpenAI. Si no esta definida, no se pide.
- Barra lateral con foto de Gamarra, que hace el agente, consultas de ejemplo
  (un clic las envia al chat), aviso de privacidad y boton "Nuevo chat".
- Sin burbuja de bienvenida: el agente no la ve (no esta en su memoria) y, si el
  comprador escribe "hola...", saluda de nuevo y se veian dos presentaciones.
  Lo que decia la bienvenida va en el subtitulo.
- Mientras el agente responde, botones y caja de texto quedan desactivados: en
  las pruebas reales del 13 y 14-nov, volver a hacer clic en un ejemplo durante
  la espera (~7 s) cortaba la respuesta y mandaba la misma consulta otra vez
  (hasta 3 veces en 5 segundos).
- La conversación sobrevive a «Ver en mapa»: en la prueba de uso (T3, 14-nov), al
  volver de Google Maps el celular recargó la página y el chat empezó de cero. El
  identificador de la sesión va en la URL (?s=...) con una firma derivada de la
  contraseña (&k=...), así que al recargar se recupera la conversación desde la base
  sin volver a pedir la contraseña; sin la firma correcta, se pide de nuevo.

Para correrlo: streamlit run src/app.py (desde la carpeta MVP_pruebas_reales)
"""
import hashlib
import hmac
import os
import re
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
FOTO = BASE_DIR / "assets" / "gamarra.jpg"

st.set_page_config(
    page_title="Portal Gamarrino AI",
    page_icon="\U0001F6CD",
    layout="centered",
    initial_sidebar_state="expanded",
)

SUBTITULO = (
    "Cuéntame qué prenda, disfraz o estilo buscas y te recomiendo 3 tiendas de Gamarra, "
    "con su galería, piso y stand."
)
EJEMPLOS = ["Polos básicos", "Jeans para mujer", "Ropa deportiva para hombre", "Vestido de fiesta"]
AVISO_PRIVACIDAD = (
    "Esta es una prueba académica de la Maestría en Ciencia de Datos e IA de UTEC. "
    "Tus mensajes, las respuestas y tus votos 👍/👎 se guardan sin tu nombre (en Supabase "
    "y en LangSmith, la herramienta con la que analizamos el agente) para mejorarlo. "
    "No escribas datos personales."
)
PREGUNTA_FEEDBACK = "**¿Te sirvieron estas recomendaciones?**"
CONFIRMACION = {
    1: ("¡Gracias! Registramos que estas recomendaciones te sirvieron.", "\U0001F44D"),
    0: ("Gracias por avisarnos. Lo usaremos para mejorar las recomendaciones.", "\U0001F44E"),
}


# --- Sesión en la URL (ver docstring) ------------------------------------------------
def _firma(sid: str) -> str:
    clave = os.environ.get("APP_PASSWORD", "")
    return hmac.new(clave.encode("utf-8"), sid.encode("utf-8"), hashlib.sha256).hexdigest()[:16] if clave else ""


def _sesion_de_url() -> str | None:
    """El session_id de la URL, solo si es un uuid y trae la firma correcta."""
    sid, firma = st.query_params.get("s", ""), st.query_params.get("k", "")
    if re.fullmatch(r"[0-9a-f-]{36}", sid) and hmac.compare_digest(firma, _firma(sid)):
        return sid
    return None


# --- Acceso con contraseña -------------------------------------------------------
def _acceso_permitido() -> bool:
    clave = os.environ.get("APP_PASSWORD", "")
    if not clave or st.session_state.get("acceso_ok"):
        return True
    if _sesion_de_url():  # misma sesión, recargada (p. ej., al volver del mapa)
        st.session_state.acceso_ok = True
        return True
    st.title("Portal Gamarrino AI")
    st.caption("Prueba con usuarios · ingresa la contraseña que te dio el equipo")
    intento = st.text_input("Contraseña", type="password")
    if intento:
        if hmac.compare_digest(intento.encode("utf-8"), clave.encode("utf-8")):
            st.session_state.acceso_ok = True
            st.rerun()
        st.error("Contraseña incorrecta.")
    return False


if not _acceso_permitido():
    st.stop()

# El agente se importa despues del acceso: carga los modelos de los guardrails (unos segundos la primera vez).
with st.spinner("Preparando el asistente..."):
    from agente import responder_detallado
    from historial_db import cargar_conversacion, guardar_feedback


def _nueva_sesion(sid: str | None = None) -> None:
    """Sin sid: conversación nueva. Con sid (vino en la URL): la recupera de la base."""
    st.session_state.session_id = sid or str(uuid.uuid4())
    st.session_state.historial = []        # lista de (rol, texto, interaccion_id, trajo_tiendas)
    st.session_state.feedback_guardado = {}  # interaccion_id -> ultimo valor ya guardado
    for mensaje, respuesta, interaccion_id, voto in (cargar_conversacion(sid) if sid else []):
        # trajo tiendas = la respuesta tiene ubicación; así vuelve a salir el voto
        trajo = "stand" in respuesta.lower() and "piso" in respuesta.lower()
        st.session_state.historial += [("user", mensaje, None, False),
                                       ("assistant", respuesta, interaccion_id, trajo)]
        if voto is not None:
            st.session_state.feedback_guardado[interaccion_id] = voto
            st.session_state[f"fb_{interaccion_id}"] = voto
    st.query_params["s"] = st.session_state.session_id
    st.query_params["k"] = _firma(st.session_state.session_id)


if "session_id" not in st.session_state:
    _nueva_sesion(_sesion_de_url())

# Mientras el agente responde, la interfaz queda bloqueada (ver docstring).
st.session_state.setdefault("procesando", False)
if st.session_state.procesando and "pendiente" not in st.session_state:
    st.session_state.procesando = False  # una corrida anterior se corto a medias: desbloquear


def _enviar(texto: str | None = None) -> None:
    """Callback de los botones de ejemplo (texto) y de la caja de texto (lee
    "entrada"). Corre ANTES de que Streamlit vuelva a dibujar la pagina, asi la
    corrida que responde ya dibuja todo desactivado."""
    texto = texto if texto is not None else st.session_state.get("entrada")
    if texto and not st.session_state.procesando:
        st.session_state.pendiente = texto
        st.session_state.procesando = True


# --- Barra lateral ---------------------------------------------------------------
with st.sidebar:
    if FOTO.exists():
        st.image(str(FOTO), width="stretch")
    st.markdown("### Portal Gamarrino AI")
    st.caption("Tu asistente para encontrar tiendas en Gamarra")
    st.markdown("**Dónde**  \nEmporio Comercial de Gamarra, La Victoria, Lima")
    st.markdown(
        "**Cómo funciona**  \nEscribe lo que buscas, como lo dirías en la calle. "
        "Si hace falta, te pregunto si es para hombre o para mujer."
    )
    st.markdown("**Prueba con**")
    for ejemplo in EJEMPLOS:
        st.button(ejemplo, key=f"ej_{ejemplo}", width="stretch", disabled=st.session_state.procesando,
                  on_click=_enviar, args=(ejemplo,))
    st.divider()
    if st.button("Nuevo chat", icon=":material/refresh:", width="stretch",
                 disabled=st.session_state.procesando):
        _nueva_sesion()
        st.rerun()
    st.caption(AVISO_PRIVACIDAD)


# --- Chat --------------------------------------------------------------------------
# Encabezado fijo: título y subtítulo quedan arriba aunque la conversación se alargue.
# Streamlit le pone la clase .st-key-encabezado al contenedor con key="encabezado",
# pero lo envuelve en un stLayoutWrapper de su mismo alto, y un "sticky" no puede
# salirse de su padre: lo que se fija es ese envoltorio (verificado con capturas de
# Edge, 17-nov). Queda justo debajo de la franja superior de Streamlit (la del menú
# ⋮, 3.75rem en la versión 1.66), que se pinta de blanco para que el chat no se vea
# pasar por detrás. Tema claro fijo en .streamlit/config.toml.
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { background-color: #ffffff; }
    div[data-testid="stLayoutWrapper"]:has(> .st-key-encabezado) {
        position: sticky;
        top: 3.75rem;
        z-index: 990;
        background-color: #ffffff;
    }
    .st-key-encabezado {
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #eeeeee;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
with st.container(key="encabezado"):
    st.title("Portal Gamarrino AI")
    st.caption(SUBTITULO)


def _mostrar_feedback(interaccion_id: int) -> None:
    st.markdown(PREGUNTA_FEEDBACK)
    valor = st.feedback("thumbs", key=f"fb_{interaccion_id}")  # 1 = pulgar arriba, 0 = abajo
    if valor is not None and st.session_state.feedback_guardado.get(interaccion_id) != valor:
        guardar_feedback(interaccion_id, valor)
        st.session_state.feedback_guardado[interaccion_id] = valor
        st.toast("¡Gracias por tu opinión!", icon="✅")
    if valor is not None:
        texto, icono = CONFIRMACION[valor]
        (st.success if valor == 1 else st.info)(texto, icon=icono)


for rol, texto, interaccion_id, trajo_tiendas in st.session_state.historial:
    with st.chat_message(rol):
        st.markdown(texto)
        if rol == "assistant" and trajo_tiendas:
            _mostrar_feedback(interaccion_id)

st.chat_input("Ej: busco un disfraz para Halloween de Vampiro en talla M", key="entrada",
              on_submit=_enviar, disabled=st.session_state.procesando)
consulta = st.session_state.pop("pendiente", None)  # la dejo _enviar (caja de texto o ejemplo)

if consulta:
    st.session_state.historial.append(("user", consulta, None, False))
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en Gamarra..."):
            try:
                respuesta, interaccion_id, trajo_tiendas = responder_detallado(
                    consulta, st.session_state.session_id
                )
                # al historial antes de dibujar nada: si un clic (p. ej. un voto) corta
                # esta corrida, la respuesta igual aparece en la siguiente
                st.session_state.historial.append(("assistant", respuesta, interaccion_id, trajo_tiendas))
            finally:
                st.session_state.procesando = False
    st.rerun()  # redibuja desde el historial (respuesta + feedback) con todo reactivado
