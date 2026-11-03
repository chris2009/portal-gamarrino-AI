# -*- coding: utf-8 -*-
"""
Consolida el doble etiquetado humano de los pares del agente (mismo protocolo que E5).

1. Lee PARES_AGENTE_MITAD_{A,B}_copia{1,2}_ETIQUETADA.xlsx de esta carpeta.
2. Calcula el kappa entre las dos copias de cada mitad.
3. Acuerdos -> etiqueta final. Desacuerdos -> hoja_desempate_agente.xlsx, para que
   un tercer integrante decida (columna relevante_DESEMPATE_SiNo) y la guarde como
   hoja_desempate_agente_ETIQUETADA.xlsx; al volver a correr este script se incorporan.
4. Escribe etiquetas_humanas_agente.csv, que el notebook carga como cuarta fuente de
   etiquetas humanas (por encima del juez LLM).

Uso (desde MVP_Portal_Gamarrino/):  python evaluacion/etiquetas/consolidar_etiquetas_humanas.py
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent


def norm(serie):
    return serie.astype(str).str.strip().str.upper().str[0].map({"S": "SI", "N": "NO"})


def kappa(a, b):
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in ("SI", "NO"))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    unidas = []
    for mitad in ("A", "B"):
        rutas = [AQUI / f"PARES_AGENTE_MITAD_{mitad}_copia{c}_ETIQUETADA.xlsx" for c in (1, 2)]
        if not all(r.exists() for r in rutas):
            print(f"MITAD_{mitad}: faltan copias etiquetadas, se omite")
            continue
        c1, c2 = (pd.read_excel(r) for r in rutas)
        for c in (c1, c2):
            c["key"] = c["query_id"].astype(str) + "|" + c["store_id"].astype(str)
            c["relevante_SiNo"] = norm(c["relevante_SiNo"])
        m = c1.merge(c2[["key", "relevante_SiNo"]], on="key", suffixes=("_c1", "_c2")).dropna(
            subset=["relevante_SiNo_c1", "relevante_SiNo_c2"])
        print(f"MITAD_{mitad}: {len(m)} pares con ambas etiquetas | kappa = {kappa(m.relevante_SiNo_c1, m.relevante_SiNo_c2):.3f}")
        unidas.append(m)
    if not unidas:
        return
    m = pd.concat(unidas, ignore_index=True)
    acuerdo = m[m.relevante_SiNo_c1 == m.relevante_SiNo_c2]
    final = dict(zip(acuerdo["key"], acuerdo["relevante_SiNo_c1"]))
    fuente = {k: "acuerdo_directo" for k in final}

    desacuerdo = m[m.relevante_SiNo_c1 != m.relevante_SiNo_c2]
    ruta_des = AQUI / "hoja_desempate_agente_ETIQUETADA.xlsx"
    if ruta_des.exists():
        des = pd.read_excel(ruta_des)
        des["relevante_DESEMPATE_SiNo"] = norm(des["relevante_DESEMPATE_SiNo"])
        resueltos = des.dropna(subset=["relevante_DESEMPATE_SiNo"])
        final.update(zip(resueltos["key"], resueltos["relevante_DESEMPATE_SiNo"]))
        fuente.update({k: "desempate" for k in resueltos["key"]})
    pendientes = desacuerdo[~desacuerdo["key"].isin(final.keys())]
    if len(pendientes):
        hoja = pendientes.rename(columns={"relevante_SiNo_c1": "copia1_dijo", "relevante_SiNo_c2": "copia2_dijo"})
        hoja = hoja[["key", "query_id", "consulta", "store_id", "display_name", "categories", "subcategory",
                     "gallery", "floor", "stand", "copia1_dijo", "copia2_dijo"]].assign(relevante_DESEMPATE_SiNo="")
        hoja.to_excel(AQUI / "hoja_desempate_agente.xlsx", index=False)

    pd.DataFrame({"key": list(final), "relevante_SiNo": list(final.values()),
                  "fuente": [fuente[k] for k in final]}).to_csv(
        AQUI / "etiquetas_humanas_agente.csv", index=False, encoding="utf-8-sig")
    print(f"Etiquetas finales: {len(final)} (acuerdo directo {len(acuerdo)}, desempate {sum(v == 'desempate' for v in fuente.values())})"
          f" | desacuerdos sin desempatar: {len(pendientes)}"
          + (" -> hoja_desempate_agente.xlsx" if len(pendientes) else ""))


if __name__ == "__main__":
    main()
