# -*- coding: utf-8 -*-
"""
Guarda cada consulta + respuesta del agente, y el feedback (pulgar arriba/
abajo) que el comprador da despues, en una base de datos SQLite local
(historial.db, en la raiz del proyecto).

Antes de este archivo, NADA se guardaba de forma durable: la memoria de
LangGraph (MemorySaver) vive solo en RAM y se pierde al reiniciar el
proceso - es literalmente lo que dice su propia documentacion ("solo para
debugging/testing, no para produccion").

Para que sirve esto: (a) tener un registro real de que preguntan los
compradores y si las respuestas les sirvieron, y (b) mas adelante, usar ese
feedback real para construir un set de evaluacion con trafico real (parecido
a lo que se hizo para E5 con las 378 consultas historicas, pero esta vez con
feedback explicito del usuario en vez de etiquetado manual del equipo).
"""
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_DB = os.path.join(BASE_DIR, "historial.db")


def _conectar():
    conn = sqlite3.connect(RUTA_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                mensaje_usuario TEXT NOT NULL,
                respuesta_agente TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaccion_id INTEGER NOT NULL REFERENCES interacciones(id),
                util INTEGER NOT NULL,
                timestamp_utc TEXT NOT NULL
            )
            """
        )


def guardar_interaccion(session_id: str, mensaje: str, respuesta: str) -> int:
    """Guarda una consulta + respuesta y devuelve el id para poder
    asociarle feedback despues."""
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO interacciones (session_id, timestamp_utc, mensaje_usuario, respuesta_agente) "
            "VALUES (?, ?, ?, ?)",
            (session_id, datetime.now(timezone.utc).isoformat(), mensaje, respuesta),
        )
        return cur.lastrowid


def guardar_feedback(interaccion_id: int, util: int) -> None:
    """util: 1 = pulgar arriba, 0 = pulgar abajo (mismo criterio que
    devuelve el widget st.feedback('thumbs') de Streamlit)."""
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO feedback (interaccion_id, util, timestamp_utc) VALUES (?, ?, ?)",
            (interaccion_id, util, datetime.now(timezone.utc).isoformat()),
        )


init_db()
