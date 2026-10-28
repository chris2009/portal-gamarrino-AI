# -*- coding: utf-8 -*-
"""Compara la Pasada 1 (hoja_etiquetado_378_ETIQUETADA.xlsx, ya mezclada) con
la Pasada 2 (los 4 pedazos, cada uno de una persona distinta), calcula kappa
global y por pedazo, y deja listas las filas en desacuerdo."""
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

BASE = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\Muestra_378_Evaluacion"

def norm(serie):
    s = serie.astype(str).str.strip().str.upper()
    return s.str[0].map({"S": "SI", "N": "NO"})

pass1 = pd.read_excel(f"{BASE}/hoja_etiquetado_378_ETIQUETADA.xlsx")
pass1["key"] = pass1["query_id"].astype(str) + "|" + pass1["store_id"].astype(str)
pass1["lbl"] = norm(pass1["relevante_SiNo"])

piezas = [
    ("PEDAZO_1_de_4_ETIQUETADO.xlsx", "Christian"),
    ("PEDAZO_2_de_4_ETIQUETADO.xlsx", "Hugo"),
    ("PEDAZO_3_de_4_ETIQUETADO.xlsx", "Jhomar"),
    ("PEDAZO_4_de_4_ETIQUETADO.xlsx", "Francisco"),
]

pass2_frames = []
for fname, persona in piezas:
    df = pd.read_excel(f"{BASE}/{fname}")
    df["key"] = df["query_id"].astype(str) + "|" + df["store_id"].astype(str)
    df["lbl"] = norm(df["relevante_SiNo"])
    df["persona_pasada2"] = persona
    faltan = df["lbl"].isna().sum()
    print(f"{fname} ({persona}): {len(df)} filas, sin completar: {faltan}")
    pass2_frames.append(df[["key", "query_id", "consulta", "store_id", "display_name",
                             "categories", "subcategory", "gallery", "floor", "stand",
                             "lbl", "persona_pasada2"]])

pass2 = pd.concat(pass2_frames, ignore_index=True)
print(f"\nTotal pasada 2: {len(pass2)} filas, {pass2['key'].duplicated().sum()} duplicadas")

m = pass1[["key", "lbl"]].rename(columns={"lbl": "lbl_pasada1"}).merge(
    pass2, on="key", how="outer", suffixes=("", "")
).rename(columns={"lbl": "lbl_pasada2"})

sin_match = m[m["lbl_pasada1"].isna() | m["lbl_pasada2"].isna()]
print(f"Filas sin match entre pasada1 y pasada2: {len(sin_match)}")

m_ok = m.dropna(subset=["lbl_pasada1", "lbl_pasada2"])
print(f"\nFilas comparadas: {len(m_ok)}")
acuerdo = (m_ok["lbl_pasada1"] == m_ok["lbl_pasada2"]).mean()
kappa = cohen_kappa_score(m_ok["lbl_pasada1"], m_ok["lbl_pasada2"], labels=["SI", "NO"])
print(f"ACUERDO GLOBAL pasada1 vs pasada2: {acuerdo*100:.1f}%")
print(f"KAPPA GLOBAL: {kappa:.3f} -> {'CUMPLE' if kappa >= 0.80 else 'NO CUMPLE'} (umbral 0.80)")
print(confusion_matrix(m_ok["lbl_pasada1"], m_ok["lbl_pasada2"], labels=["SI", "NO"]))

print("\n=== Kappa por pedazo (persona de la pasada 2) ===")
for persona in ["Christian", "Hugo", "Jhomar", "Francisco"]:
    sub = m_ok[m_ok["persona_pasada2"] == persona]
    if len(sub) == 0:
        continue
    k = cohen_kappa_score(sub["lbl_pasada1"], sub["lbl_pasada2"], labels=["SI", "NO"])
    a = (sub["lbl_pasada1"] == sub["lbl_pasada2"]).mean()
    print(f"{persona}: n={len(sub)}, acuerdo={a*100:.1f}%, kappa={k:.3f}")

dis = m_ok[m_ok["lbl_pasada1"] != m_ok["lbl_pasada2"]].copy()
dis.to_excel(f"{BASE}/desacuerdos_pasada1_vs_pasada2.xlsx", index=False)
print(f"\nDesacuerdos guardados: {len(dis)} filas -> desacuerdos_pasada1_vs_pasada2.xlsx")

acuerdos = m_ok[m_ok["lbl_pasada1"] == m_ok["lbl_pasada2"]][["key", "lbl_pasada1"]].rename(columns={"lbl_pasada1": "ground_truth_SiNo"})
acuerdos.to_csv(f"{BASE}/acuerdos_directos_378.csv", index=False)
print(f"Acuerdos directos: {len(acuerdos)} filas -> acuerdos_directos_378.csv")
