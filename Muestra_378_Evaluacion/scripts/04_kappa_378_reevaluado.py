# -*- coding: utf-8 -*-
"""Compara Pasada 1 (hoja_etiquetado_378_ETIQUETADA.xlsx) vs Pasada 2 real
(los 4 PEDAZO_*_REEVALUADO.xlsx, ahora presuntamente ciegos)."""
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
    ("PEDAZO_1_de_4_REEVALUADO.xlsx", "Christian"),
    ("PEDAZO_2_de_4_REEVALUADO.xlsx", "Hugo"),
    ("PEDAZO_3_de_4_REEVALUADO.xlsx", "Jhomar"),
    ("PEDAZO_4_de_4_REEVALUADO.xlsx", "Francisco"),
]

frames = []
for fname, persona in piezas:
    df = pd.read_excel(f"{BASE}/{fname}")
    df["key"] = df["query_id"].astype(str) + "|" + df["store_id"].astype(str)
    df["lbl"] = norm(df["relevante_SiNo"])
    df["persona_pasada2"] = persona
    faltan = df["lbl"].isna().sum()
    print(f"{fname} ({persona}): {len(df)} filas, sin completar: {faltan}")
    frames.append(df[["key", "query_id", "consulta", "store_id", "display_name",
                       "categories", "subcategory", "gallery", "floor", "stand",
                       "lbl", "persona_pasada2"]])

pass2 = pd.concat(frames, ignore_index=True)
print(f"\nTotal pasada2: {len(pass2)}, duplicadas: {pass2['key'].duplicated().sum()}")

m = pass1[["key", "lbl"]].rename(columns={"lbl": "lbl_p1"}).merge(
    pass2.rename(columns={"lbl": "lbl_p2"}), on="key", how="outer"
)
sin_match = m[m["lbl_p1"].isna() | m["lbl_p2"].isna()]
print(f"Sin match: {len(sin_match)}")

m_ok = m.dropna(subset=["lbl_p1", "lbl_p2"])
acuerdo = (m_ok["lbl_p1"] == m_ok["lbl_p2"]).mean()
kappa = cohen_kappa_score(m_ok["lbl_p1"], m_ok["lbl_p2"], labels=["SI", "NO"])
print(f"\n=== GLOBAL ===")
print(f"Filas comparadas: {len(m_ok)}")
print(f"Acuerdo: {acuerdo*100:.1f}%")
print(f"Kappa: {kappa:.3f} -> {'CUMPLE' if kappa>=0.80 else 'NO CUMPLE'} (umbral 0.80)")
print(confusion_matrix(m_ok["lbl_p1"], m_ok["lbl_p2"], labels=["SI","NO"]))

print("\n=== Por persona (pasada 2) ===")
for persona in ["Christian","Hugo","Jhomar","Francisco"]:
    sub = m_ok[m_ok["persona_pasada2"] == persona]
    if not len(sub):
        continue
    k = cohen_kappa_score(sub["lbl_p1"], sub["lbl_p2"], labels=["SI","NO"])
    a = (sub["lbl_p1"] == sub["lbl_p2"]).mean()
    print(f"{persona}: n={len(sub)}, acuerdo={a*100:.1f}%, kappa={k:.3f}")

dis = m_ok[m_ok["lbl_p1"] != m_ok["lbl_p2"]].copy()
dis.to_excel(f"{BASE}/desacuerdos_pasada1_vs_reevaluado.xlsx", index=False)
print(f"\nDesacuerdos: {len(dis)} / {len(m_ok)} -> desacuerdos_pasada1_vs_reevaluado.xlsx")

acuerdos = m_ok[m_ok["lbl_p1"] == m_ok["lbl_p2"]][["key","lbl_p1"]].rename(columns={"lbl_p1":"ground_truth_SiNo"})
acuerdos.to_csv(f"{BASE}/acuerdos_directos_378.csv", index=False)
print(f"Acuerdos directos: {len(acuerdos)} -> acuerdos_directos_378.csv")
