# -*- coding: utf-8 -*-
"""
Paso 3 del MVP: la interfaz web. Un chat simple donde el comprador escribe
su consulta y el agente (agente.py) responde con el top-3 de tiendas.
Cada respuesta del agente lleva botones de pulgar arriba/abajo (st.feedback)
que guardan el feedback en historial.db, asociado a esa interaccion exacta
(ver historial_db.py).

Para correrlo: streamlit run src/app.py (desde la carpeta MVP_Portal_Gamarrino)
"""
import uuid
import streamlit as st
from agente import responder
from historial_db import guardar_feedback

st.set_page_config(page_title="Portal Gamarrino AI", page_icon="\U0001F6CD", layout="centered")
st.title("Portal Gamarrino AI")
st.caption("Describe la prenda que buscas y te recomiendo 3 tiendas de Gamarra.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "historial" not in st.session_state:
    st.session_state.historial = []  # lista de (rol, texto, interaccion_id)

if "feedback_guardado" not in st.session_state:
    st.session_state.feedback_guardado = {}  # interaccion_id -> ultimo valor ya guardado


def _mostrar_feedback(interaccion_id: int) -> None:
    valor = st.feedback("thumbs", key=f"fb_{interaccion_id}")
    if valor is not None and st.session_state.feedback_guardado.get(interaccion_id) != valor:
        guardar_feedback(interaccion_id, valor)
        st.session_state.feedback_guardado[interaccion_id] = valor


for rol, texto, interaccion_id in st.session_state.historial:
    with st.chat_message(rol):
        st.markdown(texto)
        if rol == "assistant" and interaccion_id is not None:
            _mostrar_feedback(interaccion_id)

consulta = st.chat_input("Ej: busco un vestido de fiesta corto negro en talla M")

if consulta:
    st.session_state.historial.append(("user", consulta, None))
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en Gamarra..."):
            respuesta, interaccion_id = responder(consulta, st.session_state.session_id)
        st.markdown(respuesta)
        _mostrar_feedback(interaccion_id)
    st.session_state.historial.append(("assistant", respuesta, interaccion_id))
