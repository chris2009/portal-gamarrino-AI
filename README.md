# Portal Gamarrino AI

Motor de recomendación semántica para compradores de Gamarra: a partir de una consulta en lenguaje natural, recupera y rankea el top-3 de tiendas más relevantes del directorio de Portal Gamarrino.

**Capstone Project I · UTEC Posgrado · Equipo 7**
Christian Cajusol · Hugo Ángeles Chávez · Francisco Meza Medel · Jhomar Yurivilca Gómez
Asesor: Vicente Machaca

> ⚠️ Repositorio privado. El catálogo de tiendas y las consultas de usuarios están autorizados por Portal Gamarrino **únicamente para uso académico durante el proyecto** (declaración jurada firmada el 6-oct-2026), no para distribución pública.

## Qué es esto

Este repo contiene el pipeline de evaluación offline construido para el entregable **E5 (Plan de evaluación, baseline vs. modelo v0, Model Card v0 y registro de riesgos)**. Compara 4 formas de recomendar tiendas:

1. **No hacer nada** — selección al azar.
2. **Lo que se hace hoy** — filtro por categoría (como el directorio actual de Gamarra.com.pe).
3. **Modelo simple** — búsqueda léxica (TF-IDF) sobre la descripción de cada tienda.
4. **Modelo v0** — embeddings (`text-embedding-3-small`, OpenAI) + similitud de coseno.

## Resultado principal

Sobre una muestra de 378 consultas reales (muestreo sistemático con arranque al azar, semilla 42; 280 textos distintos), con etiquetas de relevancia hechas por los 4 integrantes del equipo (doble ciego + desempate):

| Método | Hit Rate@3 (ponderado) | IC 95% |
|---|---|---|
| No hacer nada | 23,0% | [18,8%, 27,5%] |
| Lo que se hace hoy (categoría) | 46,8% | [41,8%, 51,6%] |
| Modelo simple (léxico) | 52,9% | [48,2%, 57,7%] |
| **Modelo v0 (embeddings)** | **66,9%** | **[61,9%, 71,4%]** |

El modelo v0 supera a los baselines por más que el rango de error (los intervalos no se cruzan) — mejora real, no ruido. Falla más en consultas con marca/talla/precio explícito (20,0% de acierto) que en consultas con una prenda específica (79,6%); el detalle está en el Model Card.

## Estructura del repo

```
Entregable 29-10/              <- raíz de este repo
├── README.md
├── .gitignore
├── E5_Equipo7_Portal_Gamarrino.pptx   # Entregable final (plantilla llena)
├── E5_Equipo7_Portal_Gamarrino.pdf    # Mismo archivo, exportado para Canvas
├── E5_borrador.md                     # Borrador en texto del plan de evaluación
├── pipeline/
│   ├── 01_baselines.py                # Catálogo + consultas piloto (42) + 3 baselines
│   ├── 02_juicio_llm.py                # Intento de LLM-juez (descartado, κ=0,515)
│   └── 03_validar_kappa.py             # Validación del LLM-juez contra etiquetas humanas
└── Muestra_378_Evaluacion/
    ├── CRITERIOS_ETIQUETADO.md         # 10 reglas de etiquetado, con ejemplos reales
    ├── consultas_distintas_para_etiquetar.xlsx
    ├── segmentos_280.csv                # Clasificación de consultas por segmento
    ├── ground_truth_378_FINAL.xlsx      # Etiquetas finales reconciliadas
    ├── TABLA_FINAL_378_4metodos_ponderado.xlsx
    └── scripts/
        ├── 01_muestra_378.py                # Muestreo sistemático de 378 consultas
        ├── 02_split_4_pedazos.py            # Reparto para doble etiquetado
        ├── 03_kappa_378_pasada2.py           # Primer intento de validación (descartado)
        ├── 04_kappa_378_reevaluado.py        # Kappa real humano-humano (κ=0,627)
        ├── 05_hit_rate_378.py                # Hit Rate@3 de los 3 baselines
        ├── 06_ground_truth_378_final.py      # Ground truth reconciliado (acuerdo + desempate)
        ├── 07_modelo_v0_378.py               # Embeddings + top-3 del modelo v0
        ├── 08_kappa_nuevos_v0.py             # Kappa sobre los pares nuevos de modelo v0
        ├── 09_tabla_final_378_4metodos.py    # Tabla final de los 4 métodos
        ├── 10_segmentos.py                   # Clasificación y Hit Rate@3 por segmento
        └── 11_llenar_pptx_E5.py              # Llena la plantilla pptx con los resultados
```

> Nota: el catálogo de tiendas y las consultas crudas (`Base de Datos - Portal Gamarrino/`) viven **fuera** de esta carpeta, en `Entregables/`, y no se suben — ver `.gitignore`.

## Cómo reproducirlo

Requiere Python 3 con `pandas`, `scikit-learn`, `openpyxl`, `requests`, `python-pptx`.

1. Crear un archivo `.env` (NO versionado) con `OPENAI_API_KEY=...` en esta misma carpeta (`Entregable 29-10/`).
2. Correr los scripts de `pipeline/` en orden (01 → 03).
3. Correr los scripts de `Muestra_378_Evaluacion/scripts/` en orden (01 → 11).

Cada script indica en su docstring qué hace y qué archivo genera. El etiquetado humano (los archivos `*_ETIQUETADA.xlsx`) no se puede regenerar automáticamente — es trabajo manual del equipo.

## Metodología de etiquetado

El ground truth de relevancia se construyó con etiquetado humano doble ciego (no con un LLM-juez: se intentó, validó mal — κ=0,515 — y se descartó). El acuerdo humano-humano real está documentado en `CRITERIOS_ETIQUETADO.md` junto con las 10 reglas usadas para resolver casos ambiguos, cada una con un ejemplo real del catálogo.

## Licencia / uso de datos

Datos del catálogo y consultas de Portal Gamarrino, autorizados solo para uso académico (ver `informe-preliminar.tex`, sección "Autorización del dueño de los datos"). No redistribuir.
