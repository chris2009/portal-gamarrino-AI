# -*- coding: utf-8 -*-
"""
Paso 3 del MVP: la interfaz web. Un chat simple donde el comprador escribe
su consulta y el agente (agente.py) responde con el top-3 de tiendas.
Las respuestas que traen tiendas recomendadas llevan la pregunta "¿Te
sirvieron estas recomendaciones?" con botones de pulgar arriba/abajo
(st.feedback); los saludos, repreguntas y bloqueos no la llevan. Al votar se
muestra una confirmacion (aviso flotante + mensaje fijo bajo la respuesta) y
el voto se guarda en historial.db, asociado a esa interaccion exacta (ver
historial_db.py).

Para correrlo: streamlit run src/app.py (desde la carpeta MVP_Portal_Gamarrino)
"""
import uuid
import streamlit as st
from agente import responder_detallado
from historial_db import guardar_feedback

st.set_page_config(page_title="Portal Gamarrino AI", page_icon="\U0001F6CD", layout="centered")
st.title("Portal Gamarrino AI")
st.caption("Describe la prenda que buscas y te recomiendo 3 tiendas de Gamarra.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "historial" not in st.session_state:
    st.session_state.historial = []  # lista de (rol, texto, interaccion_id, trajo_tiendas)

if "feedback_guardado" not in st.session_state:
    st.session_state.feedback_guardado = {}  # interaccion_id -> ultimo valor ya guardado

PREGUNTA_FEEDBACK = "**¿Te sirvieron estas recomendaciones?**"
CONFIRMACION = {
    1: ("¡Gracias! Registramos que estas recomendaciones te sirvieron.", "\U0001F44D"),
    0: ("Gracias por avisarnos. Lo usaremos para mejorar las recomendaciones.", "\U0001F44E"),
}


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

consulta = st.chat_input("Ej: busco un disfraz para Halloween de Vampiro en talla M")

if consulta:
    st.session_state.historial.append(("user", consulta, None, False))
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en Gamarra..."):
            respuesta, interaccion_id, trajo_tiendas = responder_detallado(
                consulta, st.session_state.session_id
            )
        st.markdown(respuesta)
        if trajo_tiendas:
            _mostrar_feedback(interaccion_id)
    st.session_state.historial.append(("assistant", respuesta, interaccion_id, trajo_tiendas))
