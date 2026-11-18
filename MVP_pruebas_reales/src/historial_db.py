# -*- coding: utf-8 -*-
"""
Guarda cada consulta + respuesta del agente, y el feedback (pulgar arriba/
abajo) que el comprador da despues. Version para las pruebas con usuarios
reales (MVP_pruebas_reales/).

Tiene la MISMA interfaz que MVP_Portal_Gamarrino/src/historial_db.py
(guardar_interaccion, guardar_feedback), asi agente.py se copia sin cambios.
Lo unico distinto es DONDE se guarda:

- Si existe la variable de entorno DATABASE_URL (cadena de conexion de
  Supabase), se guarda en Supabase. Es lo que se usa en Hugging Face Spaces,
  cuyo disco se borra en cada reinicio.
- Si no existe, se guarda en historial.db (SQLite, en la raiz de esta
  carpeta), igual que el MVP. Sirve para probar en la PC sin tocar la base real.

En Supabase las tablas llevan el prefijo "gamarrino_" para no chocar con otras
tablas que ya existan en el proyecto. Se crean solas la primera vez y se les
activa Row Level Security sin politicas: asi la API publica de Supabase (la
clave "anon") no puede leer las conversaciones; solo esta conexion directa,
con el usuario de la base, puede.

Si Supabase falla (red, credenciales), el agente igual responde: la falla se
escribe en el log (en Hugging Face: pestaña "Logs" del Space) y esa
interaccion recibe un id negativo, que guardar_feedback ignora.
"""
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# agente.py importa este modulo ANTES de su propio load_dotenv: hay que cargar el .env aqui.
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USA_SUPABASE = bool(DATABASE_URL)
RUTA_SQLITE = os.path.join(BASE_DIR, "historial.db")

# Version del agente que produjo cada respuesta (la evaluada frente a E5).
VERSION_AGENTE = "v7.4"  # v7.3 + nota de talla/precio y conversación que vuelve del mapa (prueba de uso, 18-nov)

T_INTERACCIONES = "gamarrino_interacciones" if USA_SUPABASE else "interacciones"
T_FEEDBACK = "gamarrino_feedback" if USA_SUPABASE else "feedback"


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(error: Exception, donde: str) -> None:
    print(f"[historial_db] ERROR en {donde}: {type(error).__name__}: {error}", file=sys.stderr, flush=True)


if USA_SUPABASE:
    import psycopg

    def _conectar():
        # prepare_threshold=None: el pooler de Supabase en modo transaccion no
        # admite sentencias preparadas.
        return psycopg.connect(DATABASE_URL, prepare_threshold=None, connect_timeout=10)

    def init_db():
        with _conectar() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {T_INTERACCIONES} (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp_utc TIMESTAMPTZ NOT NULL,
                    mensaje_usuario TEXT NOT NULL,
                    respuesta_agente TEXT NOT NULL,
                    version_agente TEXT NOT NULL
                )
                """
            )
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {T_FEEDBACK} (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    interaccion_id BIGINT NOT NULL UNIQUE REFERENCES {T_INTERACCIONES}(id),
                    util SMALLINT NOT NULL CHECK (util IN (0, 1)),
                    timestamp_utc TIMESTAMPTZ NOT NULL
                )
                """
            )
            conn.execute(f"ALTER TABLE {T_INTERACCIONES} ENABLE ROW LEVEL SECURITY")
            conn.execute(f"ALTER TABLE {T_FEEDBACK} ENABLE ROW LEVEL SECURITY")

    def _insertar_interaccion(session_id, mensaje, respuesta) -> int:
        with _conectar() as conn:
            fila = conn.execute(
                f"INSERT INTO {T_INTERACCIONES} "
                "(session_id, timestamp_utc, mensaje_usuario, respuesta_agente, version_agente) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (session_id, _ahora(), mensaje, respuesta, VERSION_AGENTE),
            ).fetchone()
            return fila[0]

    def _leer_conversacion(session_id):
        with _conectar() as conn:
            return conn.execute(
                f"SELECT i.mensaje_usuario, i.respuesta_agente, i.id, f.util FROM {T_INTERACCIONES} i "
                f"LEFT JOIN {T_FEEDBACK} f ON f.interaccion_id = i.id WHERE i.session_id = %s ORDER BY i.id",
                (session_id,),
            ).fetchall()

    def _upsert_feedback(interaccion_id, util) -> None:
        with _conectar() as conn:
            conn.execute(
                f"INSERT INTO {T_FEEDBACK} (interaccion_id, util, timestamp_utc) VALUES (%s, %s, %s) "
                "ON CONFLICT (interaccion_id) DO UPDATE SET util = EXCLUDED.util, timestamp_utc = EXCLUDED.timestamp_utc",
                (interaccion_id, util, _ahora()),
            )

else:
    def _conectar():
        conn = sqlite3.connect(RUTA_SQLITE)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db():
        with _conectar() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {T_INTERACCIONES} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    mensaje_usuario TEXT NOT NULL,
                    respuesta_agente TEXT NOT NULL,
                    version_agente TEXT NOT NULL
                )
                """
            )
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {T_FEEDBACK} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interaccion_id INTEGER NOT NULL UNIQUE REFERENCES {T_INTERACCIONES}(id),
                    util INTEGER NOT NULL,
                    timestamp_utc TEXT NOT NULL
                )
                """
            )

    def _insertar_interaccion(session_id, mensaje, respuesta) -> int:
        with _conectar() as conn:
            cur = conn.execute(
                f"INSERT INTO {T_INTERACCIONES} "
                "(session_id, timestamp_utc, mensaje_usuario, respuesta_agente, version_agente) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, _ahora(), mensaje, respuesta, VERSION_AGENTE),
            )
            return cur.lastrowid

    def _leer_conversacion(session_id):
        with _conectar() as conn:
            return conn.execute(
                f"SELECT i.mensaje_usuario, i.respuesta_agente, i.id, f.util FROM {T_INTERACCIONES} i "
                f"LEFT JOIN {T_FEEDBACK} f ON f.interaccion_id = i.id WHERE i.session_id = ? ORDER BY i.id",
                (session_id,),
            ).fetchall()

    def _upsert_feedback(interaccion_id, util) -> None:
        with _conectar() as conn:
            conn.execute(
                f"INSERT INTO {T_FEEDBACK} (interaccion_id, util, timestamp_utc) VALUES (?, ?, ?) "
                "ON CONFLICT(interaccion_id) DO UPDATE SET util = excluded.util, timestamp_utc = excluded.timestamp_utc",
                (interaccion_id, util, _ahora()),
            )


def guardar_interaccion(session_id: str, mensaje: str, respuesta: str) -> int:
    """Guarda una consulta + respuesta y devuelve su id, para asociarle el
    feedback despues. Si la base falla, devuelve un id negativo unico (la app
    lo necesita como clave del widget de feedback) y deja el error en el log."""
    try:
        return _insertar_interaccion(session_id, mensaje, respuesta)
    except Exception as e:
        _log(e, "guardar_interaccion")
        return -time.time_ns()


def cargar_conversacion(session_id: str) -> list:
    """Devuelve [(mensaje, respuesta, interaccion_id, voto o None), ...] de una sesión,
    en orden. Lo usa app.py para recuperar la conversación si el celular reinicia la
    página al volver de «Ver en mapa» (prueba de uso, T3). Si la base falla, []."""
    try:
        return [tuple(f) for f in _leer_conversacion(session_id)]
    except Exception as e:
        _log(e, "cargar_conversacion")
        return []


def guardar_feedback(interaccion_id: int, util: int) -> None:
    """util: 1 = pulgar arriba, 0 = pulgar abajo (lo que devuelve
    st.feedback('thumbs')). Si el comprador cambia de voto, reemplaza el
    anterior: un voto final por interaccion."""
    if interaccion_id is None or interaccion_id < 0:
        return  # la interaccion no se pudo guardar: no hay a que asociar el voto
    try:
        _upsert_feedback(interaccion_id, util)
    except Exception as e:
        _log(e, "guardar_feedback")


try:
    init_db()
except Exception as e:  # sin base no se registra, pero la app arranca igual
    _log(e, "init_db")
