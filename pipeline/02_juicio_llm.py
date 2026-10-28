# -*- coding: utf-8 -*-
"""
E5 - Portal Gamarrino AI
Etiquetas de relevancia hechas por Claude como "LLM juez" (metodo explicitamente
permitido por la pista del E5: "calidad (rubrica humana con kappa, o LLM juez
validado)"). Criterio usado: "le serviria al comprador ir a ver esa tienda,
aunque no use las mismas palabras que la consulta?" - aplicado consulta por
consulta, tienda por tienda, leyendo nombre/categoria/subcategoria.

Estas etiquetas NO reemplazan la validacion humana: se genera ademas una
muestra para que UNA persona del equipo las revise a ciegas y se calcule el
kappa LLM-vs-humano antes de usarlas como definitivas.
"""
import pandas as pd
import numpy as np

RUTA_HOJA = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\hoja_etiquetado.xlsx"
RUTA_CANDIDATOS = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\candidatos_por_metodo.xlsx"

# (query_id, store_id) -> "Si" / "No", juicio de Claude como LLM juez
JUICIOS = {
    ("Q01","01b90bd5"):"No", ("Q01","024e53e2"):"No", ("Q01","14607ab9"):"No", ("Q01","7841916c"):"No",
    ("Q01","8eb0d23e"):"No", ("Q01","b97d8982"):"No", ("Q01","e59e79f1"):"No", ("Q01","fe0af07f"):"No",
    ("Q02","024e53e2"):"No", ("Q02","1fd91804"):"No", ("Q02","2ab05cac"):"No", ("Q02","2b5fab83"):"No",
    ("Q02","8f3e6f4b"):"No", ("Q02","b97d8982"):"No", ("Q02","da6976c6"):"No", ("Q02","fe0af07f"):"No",
    ("Q03","0eceaf4e"):"No", ("Q03","3a1b1d60"):"No", ("Q03","4407bb11"):"No", ("Q03","4b4bc8fb"):"No",
    ("Q03","b76cc8fb"):"No", ("Q03","fee10aac"):"No",
    ("Q04","0047436b"):"No", ("Q04","024e53e2"):"No", ("Q04","2b5fab83"):"No", ("Q04","46bc9ed8"):"No",
    ("Q04","6965ce2a"):"No", ("Q04","b97d8982"):"No", ("Q04","cc7d3a92"):"No", ("Q04","f50a4954"):"No",
    ("Q04","fe0af07f"):"No",
    ("Q05","3a1b1d60"):"No", ("Q05","425e3af0"):"Si", ("Q05","4407bb11"):"No", ("Q05","496e1665"):"Si",
    ("Q05","4d8093fd"):"Si", ("Q05","89f97bc8"):"No", ("Q05","8c1caa00"):"No", ("Q05","b76cc8fb"):"No",
    ("Q05","e6897d59"):"No",
    ("Q06","4753bf01"):"No", ("Q06","4825c5de"):"No", ("Q06","54ca792b"):"No", ("Q06","776da559"):"No",
    ("Q06","7c4570b3"):"No", ("Q06","94bc7d65"):"No", ("Q06","aa9ecd0a"):"No", ("Q06","d3a8252a"):"No",
    ("Q06","fe0af07f"):"No",
    ("Q07","02d8c26e"):"No", ("Q07","18744db9"):"Si", ("Q07","35f1b02b"):"No", ("Q07","54ca792b"):"No",
    ("Q07","649b5e89"):"No", ("Q07","725909f4"):"No", ("Q07","9b1881cf"):"No", ("Q07","a9f698e1"):"No",
    ("Q07","c4b6e5f6"):"No",
    ("Q08","18744db9"):"No", ("Q08","19701c36"):"No", ("Q08","30caa422"):"Si", ("Q08","3d224756"):"No",
    ("Q08","425e3af0"):"No", ("Q08","447563b9"):"No", ("Q08","9b1881cf"):"No", ("Q08","a445e1d7"):"No",
    ("Q08","f7c2ea3f"):"Si",
    ("Q09","18744db9"):"No", ("Q09","19701c36"):"No", ("Q09","30caa422"):"Si", ("Q09","3728bc2a"):"No",
    ("Q09","3fbb19c4"):"No", ("Q09","447563b9"):"No", ("Q09","9b1881cf"):"No", ("Q09","de45dc09"):"No",
    ("Q09","f7c2ea3f"):"Si",
    ("Q10","2b5fab83"):"No", ("Q10","3038ffec"):"Si", ("Q10","3e2be70a"):"Si", ("Q10","3f8c19ad"):"No",
    ("Q10","5bae871a"):"No", ("Q10","6965ce2a"):"No", ("Q10","aec87c4e"):"Si", ("Q10","dd9d99dd"):"No",
    ("Q10","e6897d59"):"Si",
    ("Q11","1a2788b3"):"No", ("Q11","2b28f75f"):"No", ("Q11","3038ffec"):"Si", ("Q11","3e2be70a"):"Si",
    ("Q11","3fbb19c4"):"No", ("Q11","5414ffb2"):"No", ("Q11","5b442e72"):"No", ("Q11","be53d67d"):"No",
    ("Q12","0267943a"):"No", ("Q12","19701c36"):"No", ("Q12","197c9757"):"No", ("Q12","7e393811"):"No",
    ("Q12","9b1881cf"):"No", ("Q12","aa9ecd0a"):"No", ("Q12","d32fa0f1"):"No", ("Q12","da6c30ae"):"No",
    ("Q12","f7c2ea3f"):"Si",
    ("Q13","0a75e156"):"No", ("Q13","26e54c4e"):"No", ("Q13","4825c5de"):"No", ("Q13","70bbbd8b"):"No",
    ("Q13","776da559"):"No", ("Q13","7e86d2bb"):"No", ("Q13","cc7d3a92"):"No", ("Q13","cf8be804"):"No",
    ("Q13","e15b2de7"):"No",
    ("Q14","15e90439"):"Si", ("Q14","776da559"):"No", ("Q14","8ca4e1e6"):"No", ("Q14","94bc7d65"):"No",
    ("Q14","9d1bb34c"):"No", ("Q14","a445e1d7"):"Si", ("Q14","c9ed7802"):"No", ("Q14","e6897d59"):"No",
    ("Q14","f9396fcc"):"No",
    ("Q15","15e90439"):"Si", ("Q15","2f12fcb3"):"No", ("Q15","5c77a333"):"No", ("Q15","8ca4e1e6"):"No",
    ("Q15","a445e1d7"):"Si", ("Q15","a8aabf07"):"No", ("Q15","acc2823a"):"No", ("Q15","b5a03b85"):"No",
    ("Q15","ffd89a61"):"Si",
    ("Q16","184ff5b2"):"Si", ("Q16","19701c36"):"No", ("Q16","53b2a624"):"No", ("Q16","649b5e89"):"No",
    ("Q16","8e05d55c"):"No", ("Q16","9b1881cf"):"No", ("Q16","da6c30ae"):"No", ("Q16","f7c2ea3f"):"No",
    ("Q16","f8aab63d"):"No",
    ("Q17","18744db9"):"Si", ("Q17","2cdc730f"):"No", ("Q17","3e08c6e2"):"No", ("Q17","447563b9"):"Si",
    ("Q17","4b4bc8fb"):"No", ("Q17","4e9070da"):"No", ("Q17","9b1881cf"):"No", ("Q17","ae712e1b"):"No",
    ("Q17","f4a1d66e"):"No",
    ("Q18","3f8c19ad"):"Si", ("Q18","4407bb11"):"Si", ("Q18","79e538b1"):"No", ("Q18","7ab05db5"):"Si",
    ("Q18","83def9f5"):"No", ("Q18","8f3e6f4b"):"Si", ("Q18","cee0f342"):"Si", ("Q18","dfdacef1"):"Si",
    ("Q19","184ff5b2"):"No", ("Q19","2268e0c8"):"No", ("Q19","51891c75"):"Si", ("Q19","9570b38a"):"No",
    ("Q19","9b1881cf"):"No", ("Q19","9bc953bc"):"No", ("Q19","bb5362e0"):"No", ("Q19","d9a494ef"):"Si",
    ("Q20","1e5b2c5a"):"No", ("Q20","42a2e728"):"Si", ("Q20","476f095d"):"Si", ("Q20","617c5379"):"Si",
    ("Q20","6ac5ad8a"):"Si", ("Q20","b43b54fd"):"Si", ("Q20","b76cc8fb"):"Si", ("Q20","e1e89c7b"):"Si",
    ("Q20","f89ce831"):"No",
    ("Q21","11b9dfe8"):"No", ("Q21","184ff5b2"):"No", ("Q21","3e08c6e2"):"No", ("Q21","7e86d2bb"):"No",
    ("Q21","83def9f5"):"No", ("Q21","9369ead5"):"No", ("Q21","cc293357"):"No", ("Q21","d81c773b"):"No",
    ("Q21","f4a1d66e"):"No",
    ("Q22","15122e06"):"No", ("Q22","7e3b18f5"):"Si", ("Q22","8c9661f2"):"No", ("Q22","acc2823a"):"Si",
    ("Q22","b5a03b85"):"No", ("Q22","b9c25455"):"Si", ("Q22","cc9db888"):"No", ("Q22","d3a5966e"):"No",
    ("Q22","fc43af36"):"No",
    ("Q23","01b90bd5"):"No", ("Q23","024e53e2"):"No", ("Q23","2cb49942"):"No", ("Q23","7841916c"):"No",
    ("Q23","b5a03b85"):"No", ("Q23","b97d8982"):"No", ("Q23","e59e79f1"):"No", ("Q23","e7bcb290"):"No",
    ("Q23","fe0af07f"):"No",
    ("Q24","011e2f04"):"Si", ("Q24","1fd91804"):"Si", ("Q24","377aca54"):"No", ("Q24","390ebdca"):"No",
    ("Q24","7e3b18f5"):"No", ("Q24","94bc7d65"):"No", ("Q24","b9c25455"):"No", ("Q24","dfffbcb4"):"Si",
    ("Q25","617c5379"):"No", ("Q25","6ac5ad8a"):"No", ("Q25","7c73af4e"):"Si", ("Q25","8eb0d23e"):"No",
    ("Q25","ae712e1b"):"No", ("Q25","b43b54fd"):"No", ("Q25","ba6378b2"):"Si", ("Q25","da6976c6"):"Si",
    ("Q25","f13013c7"):"No",
    ("Q26","5b442e72"):"No", ("Q26","66e1aa47"):"No", ("Q26","6965ce2a"):"No", ("Q26","8b631a4c"):"No",
    ("Q26","8e05d55c"):"No", ("Q26","d842c75f"):"No", ("Q26","e7050d4e"):"No", ("Q26","e7106922"):"No",
    ("Q26","f0b1b25f"):"No",
    ("Q27","3a1b1d60"):"No", ("Q27","4407bb11"):"No", ("Q27","758c1b6a"):"No", ("Q27","b76cc8fb"):"No",
    ("Q27","dc21cfbe"):"No", ("Q27","e7106922"):"No",
    ("Q28","19701c36"):"No", ("Q28","2b5fab83"):"No", ("Q28","40f4ad7f"):"No", ("Q28","4a8e8227"):"No",
    ("Q28","6965ce2a"):"No", ("Q28","9b1881cf"):"No", ("Q28","ad431736"):"No", ("Q28","b56be78d"):"No",
    ("Q28","f6a9363c"):"No",
    ("Q29","184ff5b2"):"No", ("Q29","2b28f75f"):"No", ("Q29","9b1881cf"):"No", ("Q29","9faab9fc"):"No",
    ("Q29","a8aabf07"):"No", ("Q29","b56be78d"):"No", ("Q29","f50a4954"):"No", ("Q29","f9396fcc"):"No",
    ("Q30","5dbcae27"):"Si", ("Q30","6ac5ad8a"):"Si", ("Q30","7c73af4e"):"Si", ("Q30","919e0db8"):"Si",
    ("Q30","b1a5cf96"):"No", ("Q30","b43b54fd"):"Si", ("Q30","b76cc8fb"):"Si", ("Q30","e1fb581b"):"No",
    ("Q31","024e53e2"):"Si", ("Q31","2268e0c8"):"Si", ("Q31","3a1b1d60"):"No", ("Q31","4407bb11"):"Si",
    ("Q31","a187d538"):"No", ("Q31","b76cc8fb"):"No", ("Q31","ba201714"):"Si", ("Q31","e15b2de7"):"No",
    ("Q31","f9396fcc"):"No",
    ("Q32","21f647c6"):"No", ("Q32","2cb49942"):"No", ("Q32","4a2f3092"):"No", ("Q32","70ae47fe"):"No",
    ("Q32","aa9ecd0a"):"No", ("Q32","b56be78d"):"No", ("Q32","da6c30ae"):"No", ("Q32","f7c2ea3f"):"No",
    ("Q32","f97cbc23"):"No",
    ("Q33","202c6c58"):"No", ("Q33","35c5c8e3"):"No", ("Q33","496e1665"):"No", ("Q33","5b442e72"):"No",
    ("Q33","b1c0de5e"):"No", ("Q33","da6976c6"):"Si", ("Q33","edfefd19"):"No", ("Q33","fb60c411"):"No",
    ("Q33","fbf758ac"):"No",
    ("Q34","024e53e2"):"No", ("Q34","2b5fab83"):"No", ("Q34","6965ce2a"):"No", ("Q34","89e0bb5b"):"No",
    ("Q34","b97d8982"):"No", ("Q34","da6976c6"):"Si", ("Q34","da6c30ae"):"No", ("Q34","f6e34195"):"No",
    ("Q34","fe0af07f"):"No",
    ("Q35","31d603fc"):"No", ("Q35","6965ce2a"):"No", ("Q35","776da559"):"Si", ("Q35","94bc7d65"):"Si",
    ("Q35","9b1881cf"):"No", ("Q35","b3932072"):"No", ("Q35","dc21cfbe"):"No", ("Q35","dfdacef1"):"No",
    ("Q35","ed388025"):"No",
    ("Q36","0a7476ee"):"Si", ("Q36","4e9070da"):"No", ("Q36","515807f6"):"No", ("Q36","6f694ae1"):"No",
    ("Q36","7e3b18f5"):"No", ("Q36","80aa31a7"):"Si", ("Q36","8ddc75d3"):"Si", ("Q36","dc7a1306"):"Si",
    ("Q37","19701c36"):"No", ("Q37","39a2b6c5"):"No", ("Q37","9b1881cf"):"No", ("Q37","aa9ecd0a"):"No",
    ("Q37","b75df5ba"):"No", ("Q37","c17408b1"):"No", ("Q37","cc293357"):"No", ("Q37","f81e316f"):"No",
    ("Q37","fb60c411"):"No",
    ("Q38","184ff5b2"):"Si", ("Q38","3728bc2a"):"No", ("Q38","5bae871a"):"No", ("Q38","776da559"):"No",
    ("Q38","9b1881cf"):"No", ("Q38","b9c25455"):"No", ("Q38","f9396fcc"):"No", ("Q38","f97cbc23"):"No",
    ("Q39","0f0d993e"):"No", ("Q39","184ff5b2"):"No", ("Q39","1e5b2c5a"):"No", ("Q39","2b5fab83"):"No",
    ("Q39","3b42fd7f"):"No", ("Q39","776da559"):"Si", ("Q39","94bc7d65"):"Si", ("Q39","9b1881cf"):"No",
    ("Q39","f9396fcc"):"No",
    ("Q40","5c5467bc"):"No", ("Q40","6965ce2a"):"No", ("Q40","8b631a4c"):"No", ("Q40","b97d8982"):"No",
    ("Q40","cbcd3549"):"No", ("Q40","e0649dc4"):"Si", ("Q40","e6f40937"):"Si", ("Q40","e7050d4e"):"No",
    ("Q40","f4a1d66e"):"No",
    ("Q41","150dd5b7"):"No", ("Q41","1a2788b3"):"No", ("Q41","2eb63e03"):"No", ("Q41","54ca792b"):"No",
    ("Q41","b97d8982"):"No", ("Q41","db79a085"):"Si", ("Q41","dc7a1306"):"Si", ("Q41","f6fc2930"):"No",
    ("Q41","fe0af07f"):"No",
    ("Q42","25755efa"):"No", ("Q42","31d603fc"):"No", ("Q42","4753bf01"):"No", ("Q42","5d42d8d4"):"Si",
    ("Q42","6131bc64"):"No", ("Q42","7e56b2d1"):"No", ("Q42","b75df5ba"):"Si", ("Q42","de45dc09"):"No",
}

# Casos borderline documentados aparte, para que el humano les preste mas atencion
NOTAS = {
    ("Q28","ad431736"): "Tienda dice explicitamente 'Old Money' pero su subcategoria es 'Ropa para hombre'; la consulta pide mujer. Se marco No por genero, pero el match de estilo es el unico en todo el catalogo.",
    ("Q31","024e53e2"): "Consulta exige 'exactamente bootcut'; el catalogo no tiene dato de corte. Se marco Si por ser jeans de mujer generico (mismo criterio usado en Q40).",
    ("Q32","*"): "Consulta 'es para mujer' es una aclaracion de contexto, no trae producto propio: no evaluable de forma aislada.",
}


def main():
    hoja = pd.read_excel(RUTA_HOJA)
    # los juicios se armaron mirando el store_id truncado a 8 caracteres (como se volco en el .txt de lectura)
    hoja["store_id_corto"] = hoja["store_id"].str[:8]
    hoja["relevante_LLM"] = hoja.apply(lambda r: JUICIOS.get((r["query_id"], r["store_id_corto"]), "SIN_JUICIO"), axis=1)

    faltantes = hoja[hoja["relevante_LLM"] == "SIN_JUICIO"]
    if len(faltantes):
        print("ATENCION: filas sin juicio asignado:")
        print(faltantes[["query_id", "store_id", "consulta", "display_name"]])
    else:
        print(f"OK: {len(hoja)} filas con juicio LLM asignado, {len(JUICIOS)} juicios en el diccionario")

    hoja["nota_borderline"] = hoja.apply(
        lambda r: NOTAS.get((r["query_id"], r["store_id_corto"]), ""), axis=1
    )
    hoja.to_excel(r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\juicio_llm_claude.xlsx", index=False)

    total_si = (hoja["relevante_LLM"] == "Si").sum()
    print(f"Total Si: {total_si} / {len(hoja)} ({total_si/len(hoja)*100:.1f}%)")

    # ---- Hit Rate@3 por metodo usando el juicio LLM como ground truth ----
    candidatos = pd.read_excel(RUTA_CANDIDATOS)
    candidatos["store_id_corto"] = candidatos["store_id"].str[:8]
    relevancia = dict(zip(zip(hoja["query_id"], hoja["store_id_corto"]), hoja["relevante_LLM"]))

    resultados = []
    for metodo, g in candidatos.groupby("metodo"):
        por_query = g.groupby("query_id")
        aciertos = 0
        total_queries = 0
        for qid, gq in por_query:
            total_queries += 1
            relevantes = [relevancia.get((qid, sid), "No") for sid in gq["store_id_corto"]]
            if "Si" in relevantes:
                aciertos += 1
        hit_rate = aciertos / total_queries
        resultados.append({"metodo": metodo, "aciertos": aciertos, "total_consultas": total_queries,
                            "hit_rate_at_3": round(hit_rate, 4)})

    tabla = pd.DataFrame(resultados).sort_values("hit_rate_at_3", ascending=False)
    print("\n=== Hit Rate@3 por metodo (ground truth = LLM juez Claude, SIN validar todavia) ===")
    print(tabla.to_string(index=False))
    tabla.to_excel(r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\hit_rate_preliminar.xlsx", index=False)

    # ---- Muestra de validacion humana: ~1-2 pares por consulta, ciego ----
    rng = np.random.default_rng(7)
    partes = []
    for qid, g in hoja.groupby("query_id"):
        n = 2 if len(g) > 4 else 1
        partes.append(g.sample(n=min(n, len(g)), random_state=7))
    muestra = pd.concat(partes).sort_values(["query_id", "store_id"])
    muestra_ciega = muestra.drop(columns=["relevante_LLM", "nota_borderline", "relevante_evaluador1_SiNo", "relevante_evaluador2_SiNo"]).copy()
    muestra_ciega["relevante_SiNo"] = ""
    muestra_ciega.to_excel(r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\pipeline\muestra_validacion_humana.xlsx", index=False)
    print(f"\nMuestra de validacion (ciega, sin mis respuestas): {len(muestra_ciega)} filas -> muestra_validacion_humana.xlsx")


if __name__ == "__main__":
    main()
