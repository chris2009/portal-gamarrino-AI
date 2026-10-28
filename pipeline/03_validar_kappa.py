# -*- coding: utf-8 -*-
"""
E5 - Portal Gamarrino AI
Compara las 84 etiquetas humanas (muestra_validacion_humana_completada.xlsx)
contra el juicio de Claude (juicio_llm_claude.xlsx) y calcula el kappa de
Cohen, para decidir si el LLM juez queda validado (umbral de la rubrica: 0.80).
"""
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

RUTA_HUMANO = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\muestra_validacion_humana_completada.xlsx"
RUTA_LLM = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\juicio_llm_claude.xlsx"

humano = pd.read_excel(RUTA_HUMANO)
humano["relevante_SiNo"] = humano["relevante_SiNo"].str.strip().str.upper().replace({"SI": "Si", "NO": "No"})

llm = pd.read_excel(RUTA_LLM)[["query_id", "store_id_corto", "relevante_LLM", "consulta", "display_name"]]

comparado = humano.merge(llm, on=["query_id", "store_id_corto"], how="left", suffixes=("", "_llm"))

faltan = comparado["relevante_LLM"].isna().sum()
if faltan:
    print(f"ATENCION: {faltan} filas de la muestra humana no hicieron match con el juicio LLM")

y_humano = comparado["relevante_SiNo"]
y_llm = comparado["relevante_LLM"]

acuerdo = (y_humano == y_llm).mean()
kappa = cohen_kappa_score(y_humano, y_llm)

print(f"Filas comparadas: {len(comparado)}")
print(f"Acuerdo simple (% filas iguales): {acuerdo*100:.1f}%")
print(f"Kappa de Cohen (LLM juez Claude vs. humano): {kappa:.3f}")
print(f"Umbral de la rubrica: 0.80 -> {'CUMPLE' if kappa >= 0.80 else 'NO CUMPLE'}")

print("\nMatriz de confusion (filas=humano, columnas=LLM):")
labels = ["Si", "No"]
cm = confusion_matrix(y_humano, y_llm, labels=labels)
print(pd.DataFrame(cm, index=[f"humano_{l}" for l in labels], columns=[f"llm_{l}" for l in labels]))

print("\nDesacuerdos:")
desacuerdos = comparado[y_humano != y_llm][["query_id", "consulta", "display_name", "relevante_SiNo", "relevante_LLM"]]
print(desacuerdos.to_string(index=False))

desacuerdos.to_excel(r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\desacuerdos_llm_vs_humano.xlsx", index=False)
