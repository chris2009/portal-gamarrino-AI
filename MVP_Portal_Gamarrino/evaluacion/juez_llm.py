# -*- coding: utf-8 -*-
"""
Juez LLM PROVISIONAL para pares consulta-tienda que no tienen etiqueta humana.

Por que existe: las etiquetas de E5 solo cubren las tiendas que propusieron sus
4 metodos. Cuando el agente muestra otra tienda, ese par no tiene etiqueta y el
Hit Rate queda como un rango (cota inferior / superior) con veredicto
INDETERMINADO. Este juez aplica los mismos criterios escritos que usaron los
etiquetadores humanos (Muestra_378_Evaluacion/CRITERIOS_ETIQUETADO.md) para dar
una estimacion puntual mientras el equipo etiqueta esos pares a mano.

Reglas de uso:
- Las etiquetas humanas SIEMPRE mandan: el juez solo cubre pares sin etiqueta humana.
- Su acuerdo con las etiquetas humanas se mide en validar_juez_llm.py (kappa).
- Cada par se juzga una sola vez y queda en etiquetas/juez_llm_cache.csv, asi
  corridas distintas usan la misma etiqueta para el mismo par.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd
from langchain_openai import ChatOpenAI

MODELO_JUEZ = "gpt-4o"
DIR_ETIQUETAS = Path(__file__).resolve().parent / "etiquetas"
RUTA_CACHE = DIR_ETIQUETAS / "juez_llm_cache.csv"
RUTA_CRITERIOS = Path(__file__).resolve().parents[2] / "Muestra_378_Evaluacion" / "CRITERIOS_ETIQUETADO.md"
COLUMNAS_CACHE = ["key", "consulta", "display_name", "relevante_SiNo", "modelo", "fecha"]

PROMPT_JUEZ = """Eres uno de los etiquetadores del equipo que evalua un buscador de tiendas del
Emporio de Gamarra (Lima). Decides si la tienda es relevante para la consulta del
comprador aplicando EXACTAMENTE estos criterios del equipo:

{criterios}

Consulta del comprador: {consulta}
Tienda: {display_name}
Categoria: {categories} | Subcategoria: {subcategory}

Responde SOLO "SI" o "NO"."""


def criterios() -> str:
    return RUTA_CRITERIOS.read_text(encoding="utf-8")


def juzgar_par(llm, texto_criterios: str, par: dict):
    """'SI' | 'NO' para un par, o None si la llamada falla (el par queda sin etiqueta)."""
    try:
        r = llm.invoke(PROMPT_JUEZ.format(
            criterios=texto_criterios, consulta=par["consulta"], display_name=par["display_name"],
            categories=par.get("categories", "") or "", subcategory=par.get("subcategory", "") or "",
        )).content.strip().upper()
    except Exception:
        return None
    return "SI" if r.startswith("S") else "NO"


def juzgar(pares: pd.DataFrame, modelo: str = MODELO_JUEZ, max_workers: int = 8) -> dict:
    """{key: 'SI' | 'NO'} para los pares de `pares` (columnas key, consulta, display_name,
    categories, subcategory). Usa la cache y solo llama al LLM por los pares nuevos."""
    DIR_ETIQUETAS.mkdir(exist_ok=True)
    cache = (pd.read_csv(RUTA_CACHE, encoding="utf-8-sig") if RUTA_CACHE.exists()
             else pd.DataFrame(columns=COLUMNAS_CACHE))
    cache = cache[cache["modelo"] == modelo]
    conocidas = dict(zip(cache["key"], cache["relevante_SiNo"]))
    nuevos = pares[~pares["key"].isin(conocidas.keys())].drop_duplicates("key").to_dict("records")
    if nuevos:
        llm, texto = ChatOpenAI(model=modelo, temperature=0), criterios()
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            etiquetas = list(ex.map(lambda p: juzgar_par(llm, texto, p), nuevos))
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filas = [{"key": p["key"], "consulta": p["consulta"], "display_name": p["display_name"],
                  "relevante_SiNo": e, "modelo": modelo, "fecha": ahora}
                 for p, e in zip(nuevos, etiquetas) if e is not None]
        if filas:
            pd.DataFrame(filas, columns=COLUMNAS_CACHE).to_csv(
                RUTA_CACHE, mode="a", header=not RUTA_CACHE.exists(), index=False, encoding="utf-8-sig")
            conocidas.update((f["key"], f["relevante_SiNo"]) for f in filas)
    return {k: conocidas[k] for k in pares["key"] if k in conocidas}
