# -*- coding: utf-8 -*-
"""
Genera las hojas de etiquetado humano (doble ciego) de los pares consulta-tienda del
agente que no tienen etiqueta humana, con el mismo formato y protocolo que E5:

- Los pares se reparten en dos mitades (A y B) por consulta, para que las tiendas de
  una misma consulta las juzgue la misma pareja de etiquetadores.
- Cada mitad sale en dos copias identicas (copia1, copia2): cada integrante etiqueta
  su copia SIN ver la del otro ni la etiqueta del juez LLM.
- Se etiqueta la columna relevante_SiNo con SI / NO siguiendo
  Muestra_378_Evaluacion/CRITERIOS_ETIQUETADO.md, y se guarda como
  <nombre>_ETIQUETADA.xlsx en esta misma carpeta.
- Despues: python evaluacion/etiquetas/consolidar_etiquetas_humanas.py

Uso (desde MVP_Portal_Gamarrino/):
    python evaluacion/etiquetas/generar_hojas_etiquetado.py evaluacion/resultados/<corrida>.xlsx
"""
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
COLUMNAS = ["query_id", "consulta", "store_id", "display_name", "categories", "subcategory",
            "gallery", "floor", "stand", "relevante_SiNo"]


def main(ruta_corrida):
    pares = pd.read_excel(ruta_corrida, "pares_sin_etiqueta").drop_duplicates("key")
    pares["relevante_SiNo"] = ""
    consultas = sorted(pares["query_id"].unique())
    mitad_a = set(consultas[::2])
    for nombre, filtro in (("A", pares["query_id"].isin(mitad_a)), ("B", ~pares["query_id"].isin(mitad_a))):
        hoja = pares.loc[filtro, COLUMNAS].sort_values(["query_id", "display_name"])
        for copia in (1, 2):
            destino = AQUI / f"PARES_AGENTE_MITAD_{nombre}_copia{copia}.xlsx"
            hoja.to_excel(destino, index=False)
        print(f"MITAD_{nombre}: {len(hoja)} pares, {hoja.query_id.nunique()} consultas -> copia1 y copia2")
    print(f"Total: {len(pares)} pares sin etiqueta humana (de {Path(ruta_corrida).name})")


if __name__ == "__main__":
    main(sys.argv[1])
