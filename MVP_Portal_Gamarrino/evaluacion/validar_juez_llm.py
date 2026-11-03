# -*- coding: utf-8 -*-
"""
Mide cuanto coincide el juez LLM (juez_llm.py) con las etiquetas humanas finales de E5.

Usa los pares "nuevos" del modelo v0 de E5: son del mismo tipo que los que muestra
el agente (candidatos de un buscador semantico) y tienen etiqueta humana final
(acuerdo directo de la doble etiquetacion o desempate). Muestra estratificada de
300 pares, semilla 42. Como referencia calcula tambien el kappa entre los dos
etiquetadores humanos sobre esos mismos pares.

Uso (desde MVP_Portal_Gamarrino/):  python evaluacion/validar_juez_llm.py [modelo ...]
Guarda etiquetas/validacion_juez_llm.csv (detalle) y validacion_juez_llm_resumen.json.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI.parent / ".env")
sys.path.insert(0, str(AQUI))
import juez_llm  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

DIR_E5 = AQUI.parents[1] / "Muestra_378_Evaluacion"
N_VALIDACION, SEMILLA = 300, 42


def norm(serie):
    return serie.astype(str).str.strip().str.upper().str[0].map({"S": "SI", "N": "NO"})


def kappa(a, b):
    a, b = pd.Series(list(a)), pd.Series(list(b))
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in ("SI", "NO"))
    return (po - pe) / (1 - pe)


def pares_validacion():
    hojas, humanos = [], []
    for mitad in ("A", "B"):
        c1 = pd.read_excel(DIR_E5 / f"NUEVOS_v0_MITAD_{mitad}_copia1_ETIQUETADA.xlsx")
        c2 = pd.read_excel(DIR_E5 / f"NUEVOS_v0_MITAD_{mitad}_copia2_ETIQUETADA.xlsx")
        for c in (c1, c2):
            c["key"] = c["query_id"].astype(str) + "|" + c["store_id"].astype(str)
        hojas.append(c1)
        humanos.append(c1[["key"]].assign(h1=norm(c1["relevante_SiNo"])).merge(
            c2[["key"]].assign(h2=norm(c2["relevante_SiNo"])), on="key"))
    pares = pd.concat(hojas, ignore_index=True)
    final = pd.read_csv(DIR_E5 / "acuerdos_directos_nuevos_v0.csv")
    final = dict(zip(final["key"], norm(final["ground_truth_SiNo"])))
    des = pd.read_excel(DIR_E5 / "hoja_desempate_nuevos_v0_41filas_ETIQUETADA.xlsx")
    final.update(zip(des["key"], norm(des["relevante_DESEMPATE_SiNo"])))
    pares["humano"] = pares["key"].map(final)
    pares = pares.dropna(subset=["humano"]).drop_duplicates("key")
    return pares, pd.concat(humanos, ignore_index=True).dropna()


def main(modelos):
    pares, humanos = pares_validacion()
    muestra = pd.concat([g.sample(round(N_VALIDACION * len(g) / len(pares)), random_state=SEMILLA)
                         for _, g in pares.groupby("humano")], ignore_index=True)
    texto = juez_llm.criterios()
    resumen = {"pares_validacion": len(muestra), "proporcion_SI_humano": round((muestra["humano"] == "SI").mean(), 3),
               "kappa_entre_humanos_mismos_pares": round(kappa(humanos["h1"], humanos["h2"]), 3), "modelos": {}}
    for modelo in modelos:
        llm = ChatOpenAI(model=modelo, temperature=0)
        with ThreadPoolExecutor(max_workers=8) as ex:
            muestra[modelo] = list(ex.map(lambda p: juez_llm.juzgar_par(llm, texto, p), muestra.to_dict("records")))
        ok = muestra[muestra[modelo].notna()]
        resumen["modelos"][modelo] = {
            "kappa_vs_etiqueta_humana_final": round(kappa(ok["humano"], ok[modelo]), 3),
            "acuerdo": round((ok["humano"] == ok[modelo]).mean(), 3),
            "juez_SI_humano_NO": int(((ok[modelo] == "SI") & (ok["humano"] == "NO")).sum()),
            "juez_NO_humano_SI": int(((ok[modelo] == "NO") & (ok["humano"] == "SI")).sum()),
            "fallos_de_llamada": int(muestra[modelo].isna().sum()),
        }
    juez_llm.DIR_ETIQUETAS.mkdir(exist_ok=True)
    muestra[["key", "consulta", "display_name", "categories", "subcategory", "humano", *modelos]].to_csv(
        juez_llm.DIR_ETIQUETAS / "validacion_juez_llm.csv", index=False, encoding="utf-8-sig")
    (juez_llm.DIR_ETIQUETAS / "validacion_juez_llm_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:] or [juez_llm.MODELO_JUEZ])
