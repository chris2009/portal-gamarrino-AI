# -*- coding: utf-8 -*-
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

def norm(serie):
    s = serie.astype(str).str.strip().str.upper()
    return s.str[0].map({"S": "SI", "N": "NO"})

for mitad in ["A", "B"]:
    c1 = pd.read_excel(f"{BASE}/NUEVOS_v0_MITAD_{mitad}_copia1_ETIQUETADA.xlsx")
    c2 = pd.read_excel(f"{BASE}/NUEVOS_v0_MITAD_{mitad}_copia2_ETIQUETADA.xlsx")
    for df in (c1, c2):
        df["key"] = df["query_id"].astype(str) + "|" + df["store_id"].astype(str)
        df["lbl"] = norm(df["relevante_SiNo"])
    print(f"Mitad {mitad}: copia1={len(c1)} (sin completar {c1['lbl'].isna().sum()}), copia2={len(c2)} (sin completar {c2['lbl'].isna().sum()})")

    m = c1[["key", "lbl"]].merge(c2[["key", "lbl"]], on="key", suffixes=("_1", "_2"))
    acuerdo = (m["lbl_1"] == m["lbl_2"]).mean()
    kappa = cohen_kappa_score(m["lbl_1"], m["lbl_2"], labels=["SI", "NO"])
    print(f"  Filas comparadas: {len(m)} | Acuerdo: {acuerdo*100:.1f}% | Kappa: {kappa:.3f} -> {'CUMPLE' if kappa>=0.80 else 'NO CUMPLE'}")
    print(" ", confusion_matrix(m["lbl_1"], m["lbl_2"], labels=["SI","NO"]).tolist())
    desac = (m["lbl_1"] != m["lbl_2"]).sum()
    print(f"  Desacuerdos: {desac}\n")
