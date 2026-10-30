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
└── src/
    ├── 01_indexar_catalogo.py  # paso 1: carga las 438 tiendas en ChromaDB (correr 1 vez)
    ├── guardrails_mvp.py       # guardrails de entrada y salida (ver seccion abajo)
    ├── historial_db.py         # guarda cada interaccion y su feedback en historial.db
    ├── agente.py               # paso 2: el agente LangGraph (herramienta de busqueda + memoria + guardrails)
    └── app.py                  # paso 3: interfaz de chat (Streamlit, con botones de feedback)
```

## Persistencia y feedback

**Memoria a corto plazo (short-term):** `MemorySaver` de LangGraph — el historial de la conversación activa, indexado por `session_id`. Vive solo en RAM: se pierde al reiniciar el proceso. No es un registro durable, y no hace falta que lo sea: es memoria de UNA conversación.

**Memoria a largo plazo (long-term):**

- **ChromaDB** (`chroma_db/`): el conocimiento persistente del catálogo (el embedding de las 438 tiendas). Se calcula una vez y se reutiliza siempre.
- **`historial.db`** (SQLite, `src/historial_db.py`): registro permanente de cada consulta + respuesta + voto. A diferencia de ChromaDB, el agente no lo vuelve a leer durante la conversación — es almacenamiento para análisis, no memoria que el agente consuma en vivo.

**Feedback**: cada respuesta del agente muestra botones de 👍/👎 (`st.feedback("thumbs")` de Streamlit), ligados a esa interacción exacta en `historial.db`.

Para revisar lo guardado:
```powershell
python -c "import sqlite3; c=sqlite3.connect('historial.db'); [print(r) for r in c.execute('SELECT * FROM interacciones')]"
```

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
            relevancia (LLM barato)                     sin PHONE_NUMBER
                                                          ni PERSON)
```

| Capa | Que hace | Estado |
|---|---|---|
| Seguridad (`DetectJailbreak`) | Bloquea intentos de hackear el prompt. Corre 100% local (3 modelos descargados con `post_install`). | Activa. **Limitacion verificada:** el modelo esta entrenado sobre todo en ingles — no detecto 2 de 2 intentos de jailbreak en español en las pruebas. |
| Relevancia | Mantiene la conversacion en "ropa/tiendas de Gamarra"; usa el historial de la sesion para no bloquear respuestas cortas de seguimiento ("De Dracula", "talla M"). | Activa |
| Tool safeguards | `buscar_tiendas` es de solo lectura, sin escritura ni accion irreversible -> riesgo bajo, no necesita pausa. | Evaluado, no necesita guard |
| PII (`GuardrailsPII`, `on_fail="fix"`) | Sanea email / DNI / tarjeta en la respuesta. Excluye a proposito `PHONE_NUMBER` (el WhatsApp de la tienda es dato de negocio que SI debe mostrarse) y `PERSON` (el detector de nombres confundia listas tipo "hombre, mujer o nino?" con nombres propios). | Activa |
| Moderacion (`BiasCheck`) | Revisa lenguaje sesgado en la respuesta. | **Pendiente** — requiere TensorFlow, que falla por el limite de rutas largas de Windows. Una vez corrido `Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1` (PowerShell como Administrador), se instala con `pip install guardrails-ai-bias-check` y se agrega en `guardrails_mvp.py`. |

Detalle completo de cada capa y por que va donde va: `src/guardrails_mvp.py`.

## Cómo correrlo (PowerShell)

```powershell
cd "D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\MVP_Portal_Gamarrino"
.\.venv\Scripts\Activate.ps1          # activa el entorno virtual (venv)
python src\01_indexar_catalogo.py     # solo la primera vez, o si cambia el catalogo
streamlit run src\app.py              # abre el chat en http://localhost:8501
```

Para salir del venv: `deactivate`.

Si PowerShell bloquea la activación con un error de "execution policy", correr una
vez (en esa misma sesión): `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
y luego repetir `.\.venv\Scripts\Activate.ps1`.

## Estado actual

- Catálogo: 438 tiendas indexadas en ChromaDB.
- Búsqueda: filtra por umbral de relevancia, corrige typos, pide detalle cuando falta.
- Guardrails: seguridad + relevancia activos en entrada; PII activo en salida; moderación pendiente.
- Persistencia: cada consulta + respuesta + feedback queda en `historial.db`.
- Observabilidad: trazas a LangSmith si se activa la API key.
- Interfaz: chat funcionando en `localhost:8501`.
- Pendiente: fotos de tienda (H4), autenticación, despliegue más allá de local.
