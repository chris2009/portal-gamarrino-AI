# Portal Gamarrino AI — MVP

El agente real (no la evaluación offline de E5, que está en `Muestra_378_Evaluacion/`, dentro de este mismo repo).
Arquitectura: embeddings (OpenAI `text-embedding-3-small`) + ChromaDB + LangGraph
+ memoria conversacional, tal como se decidió en las asesorías del equipo.

## Estructura

```
MVP_Portal_Gamarrino/
├── .env                        # OPENAI_API_KEY + LANGSMITH_* (no se sube a git)
├── requirements.txt
├── chroma_db/                  # base vectorial persistida (se genera, no se sube)
├── historial.db                # SQLite: consultas + respuestas + feedback (se genera, no se sube)
├── src/
│   ├── 01_indexar_catalogo.py  # paso 1: carga las 438 tiendas en ChromaDB (correr 1 vez)
│   ├── guardrails_mvp.py       # guardrails de entrada y salida (ver seccion abajo)
│   ├── historial_db.py         # guarda cada interaccion y su feedback en historial.db
│   ├── agente.py               # paso 2: el agente LangGraph (herramienta de busqueda + memoria + guardrails)
│   └── app.py                  # paso 3: interfaz de chat (Streamlit, con botones de feedback)
└── evaluacion/
    ├── evaluacion_agente_vs_E5.ipynb  # agente real vs. Hit Rate@3 de E5 (ver seccion Evaluacion)
    ├── juez_llm.py             # juez LLM provisional para pares sin etiqueta humana
    ├── validar_juez_llm.py     # mide su acuerdo (kappa) con las etiquetas humanas de E5
    ├── etiquetas/              # hojas de doble ciego, consolidacion y cache del juez
    └── resultados/             # xlsx + grafico por corrida y registro_corridas.csv
```

## Persistencia y feedback

**Memoria a corto plazo (short-term):** `MemorySaver` de LangGraph — el historial de la conversación activa, indexado por `session_id`. Vive solo en RAM: se pierde al reiniciar el proceso. No es un registro durable, y no hace falta que lo sea: es memoria de UNA conversación.

**Memoria a largo plazo (long-term):**

- **ChromaDB** (`chroma_db/`): el conocimiento persistente del catálogo (el embedding de las 438 tiendas). Se calcula una vez y se reutiliza siempre.
- **`historial.db`** (SQLite, `src/historial_db.py`): registro permanente de cada consulta + respuesta + voto. A diferencia de ChromaDB, el agente no lo vuelve a leer durante la conversación — es almacenamiento para análisis, no memoria que el agente consuma en vivo.

**Feedback**: cada respuesta del agente muestra botones de 👍/👎 (`st.feedback("thumbs")` de Streamlit), ligados a esa interacción exacta en `historial.db`.

Para revisar lo guardado (consultas, respuestas y su voto si lo tienen):
```powershell
python -c "import sqlite3; c=sqlite3.connect('historial.db'); [print(r) for r in c.execute('SELECT i.id, i.mensaje_usuario, i.respuesta_agente, f.util FROM interacciones i LEFT JOIN feedback f ON f.interaccion_id = i.id')]"
```
(`f.util` sale `None` si todavía no votó, `1` si fue 👍, `0` si fue 👎 — y es el voto final, no uno por cada vez que cambió de opinión.)

Esto sirve para construir, mas adelante, un set de evaluacion con trafico real
(la misma logica que las 378 consultas de E5, pero con feedback explicito del
usuario en vez de etiquetado manual del equipo).

## Trazabilidad (LangSmith)

Activa el registro de cada ejecucion (tokens, costo estimado en USD, latencia
por paso) sin tocar el codigo: solo completa `LANGSMITH_API_KEY` en el `.env`
(las otras 2 variables ya estan listas). Mismo patron que la guia
`CONECTAR_LANGSMITH.md` del curso (Modulo 5, Sesion 12).
Despues de activarla, ve las trazas en [smith.langchain.com](https://smith.langchain.com),
proyecto `mvp-portal-gamarrino`.

## Guardrails

Arquitectura (taxonomia de capas de OpenAI, la misma del curso en el
ejercicio `e4-guardrails-en-capas`, Modulo 3, Sesion 07):

```
usuario -> [guard_entrada] -> agente (LLM + tool) -> [guard_salida] -> usuario
            DetectJailbreak                            GuardrailsPII (fix,
            filtro de patrones (ES/EN)                  sin PHONE_NUMBER
            relevancia (LLM barato)                       ni PERSON)
```

| Capa | Que hace | Estado |
|---|---|---|
| Seguridad (`DetectJailbreak`) | Bloquea intentos de hackear el prompt. Corre 100% local (3 modelos descargados con `post_install`). | Activa. **Limitacion verificada:** el modelo esta entrenado sobre todo en ingles — no detecto 2 de 2 intentos de jailbreak en español en las pruebas. Para cubrirlo se añadió un filtro determinista de patrones de inyección (ES/EN) en `guardrails_mvp.py`: es heurístico, no una garantía. |
| Relevancia | Mantiene la conversacion en "ropa/tiendas de Gamarra"; usa el historial de la sesion para no bloquear respuestas cortas de seguimiento ("De Dracula", "talla M"). Desde el 31-oct-2026 los saludos puros, los mensajes de hasta 3 palabras y la respuesta a una repregunta del agente pasan por reglas deterministas, sin el clasificador LLM, que los bloqueaba por error (40 de sus 47 bloqueos en la evaluacion de 378 consultas reales contra E5). | Activa |
| Tool safeguards | `buscar_tiendas` es de solo lectura, sin escritura ni accion irreversible -> riesgo bajo, no necesita pausa. | Evaluado, no necesita guard |
| PII (`GuardrailsPII`, `on_fail="fix"`) | Sanea email / DNI / tarjeta en la respuesta. Excluye a proposito `PHONE_NUMBER` (el WhatsApp de la tienda es dato de negocio que SI debe mostrarse) y `PERSON` (el detector de nombres confundia listas tipo "hombre, mujer o nino?" con nombres propios). | Activa |
| Moderacion (`BiasCheck`) | Revisa lenguaje sesgado en la respuesta. | **Pendiente** — requiere TensorFlow, que falla por el limite de rutas largas de Windows. Una vez corrido `Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1` (PowerShell como Administrador), se instala con `pip install guardrails-ai-bias-check` y se agrega en `guardrails_mvp.py`. |

Detalle completo de cada capa y por que va donde va: `src/guardrails_mvp.py`.

## Cómo correrlo (PowerShell)

```powershell
cd "D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\MVP_Portal_Gamarrino"
.\.venv\Scripts\Activate.ps1          # activa el entorno virtual (venv)
python src\01_indexar_catalogo.py     # solo la primera vez, o si cambia el catalogo
streamlit run src\app.py              # abre el chat en http://localhost:8501
```

Para salir del venv: `deactivate`.

Si PowerShell bloquea la activación con un error de "execution policy", correr una
vez (en esa misma sesión): `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
y luego repetir `.\.venv\Scripts\Activate.ps1`.

## Evaluación frente a E5 (`evaluacion/`)

`evaluacion/evaluacion_agente_vs_E5.ipynb` le toma al agente real el mismo examen que a E5: las consultas de
`Muestra_378_Evaluacion/` con sus etiquetas humanas. Compara su Hit Rate@3 con el 66,9 % del modelo v0, que el
notebook lee de `TABLA_FINAL_378_4metodos_ponderado.xlsx` y reproduce desde las etiquetas antes de empezar.

```powershell
jupyter lab evaluacion/evaluacion_agente_vs_E5.ipynb      # kernel: "Python (Portal Gamarrino .venv)"
```

- Parámetros (sección 3 del notebook): `N_MUESTRA` (filas a sortear; `None` = las 378), `SEMILLA` (`None` = muestra
  nueva; un entero repite una corrida), `USAR_JUEZ_LLM`, `MAX_WORKERS`.
- Corrida completa sin abrir JupyterLab (~7 min):
  `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=gamarrino --ExecutePreprocessor.timeout=-1 evaluacion/resultados/ejecucion_378_completas_v4_guardrail_juez.ipynb`
- Cada corrida deja en `evaluacion/resultados/` un xlsx (detalle, top-3, pares sin etiqueta), un gráfico y una fila
  en `registro_corridas.csv`.
- Abrir el notebook en un solo editor a la vez (JupyterLab o VS Code): una copia vieja abierta en el otro editor
  sobrescribe los cambios al guardarse.

Cómo se puntúa: M1 es el primer turno; M2 agrega un seguimiento neutro cuando el agente repregunta (es la medida
comparable con E5). Si el agente muestra una tienda que ningún método de E5 propuso, ese par no tiene etiqueta humana
y el resultado se da como rango (cota inferior: sin etiqueta = No; superior: sin etiqueta = Sí), más una estimación
puntual provisional con un juez LLM (`evaluacion/juez_llm.py`: gpt-4o con `CRITERIOS_ETIQUETADO.md`). El juez coincide
con la etiqueta humana final en 75 % de los pares (κ = 0,486; entre dos humanos κ = 0,872), medido con
`validar_juez_llm.py`. Las etiquetas humanas siempre mandan sobre las del juez.

Resultado de referencia (31-oct-2026, 378 filas, versión v4 del agente):

| Medida | Hit Rate@3 | Veredicto |
|---|---|---|
| Modelo v0 de E5 (misma muestra) | 66,9 % | — |
| Agente M2, solo etiquetas humanas | 60,6 % – 86,8 % | Indeterminado |
| Agente M2, estimación con juez LLM (provisional) | 65,9 % (IC 95 % 61,1 – 70,6) | Se cubre |

Diferencia pareada con E5 usando el juez: −1,1 pp (IC 95 % −4,0 a +2,1). El guardrail de relevancia bloquea 6 de las
378 consultas (antes del arreglo, 47). Las corridas de las 09:40 y 09:41 del 31-oct (0,0 %) fallaron por un error del
notebook ya corregido: no son resultados.

Para cerrar el número oficial falta etiquetar a mano 308 pares, con el mismo protocolo de E5:

1. `evaluacion/etiquetas/PARES_AGENTE_MITAD_{A,B}_copia{1,2}.xlsx` (generadas con `generar_hojas_etiquetado.py`):
   cada mitad la etiquetan dos personas por separado y guardan su copia como `*_ETIQUETADA.xlsx`.
2. `python evaluacion/etiquetas/consolidar_etiquetas_humanas.py`: calcula κ, aplica los acuerdos, arma la hoja de
   desempate y deja `etiquetas_humanas_agente.csv`.
3. Volver a correr el notebook con `N_MUESTRA = None`: esas etiquetas reemplazan a las del juez.

## Estado actual

- Catálogo: 438 tiendas indexadas en ChromaDB.
- Búsqueda: busca primero (pregunta solo si no se nombra ningún producto), filtra por umbral de relevancia, corrige typos y, si nada supera el umbral, reintenta con una consulta más amplia (hasta 3 búsquedas).
- Guardrails: seguridad + relevancia activos en entrada; PII activo en salida; moderación pendiente.
- Persistencia: cada consulta + respuesta + feedback queda en `historial.db`.
- Observabilidad: trazas a LangSmith si se activa la API key.
- Interfaz: chat funcionando en `localhost:8501`.
- Evaluación vs. E5 (31-oct, 378 consultas): 65,9 % con juez LLM provisional frente a 66,9 % de E5 (se cubre); el número oficial espera el etiquetado humano de 308 pares (ver sección Evaluación).
- Pendiente: fotos de tienda (H4), autenticación, despliegue más allá de local.
