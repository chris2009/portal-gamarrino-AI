# Portal Gamarrino AI — Explicación maestra del MVP

Este documento responde, en español simple, cada pregunta de fondo sobre cómo está armado el MVP: qué es cada pieza, por qué se eligió, y dónde está en el código. Cada afirmación está verificada contra el código real o probada en vivo — no es teoría suelta.

---

## 1. ¿Qué es Streamlit? ¿Qué bases de datos usamos?

**Streamlit** es una librería de Python que convierte un script en una página web interactiva, sin tener que escribir HTML, CSS ni JavaScript. Todo lo que ves en `http://localhost:8501` (el cuadro de chat, los mensajes, los botones de 👍/👎) lo genera `src/app.py` con unas pocas funciones de Python (`st.chat_input`, `st.chat_message`, `st.feedback`). Sigue siendo una app que corre solo en tu máquina — no está publicada en internet.

Usamos **dos bases de datos**, cada una para algo distinto:

| Base de datos | Para qué | Dónde vive | Quién la usa |
|---|---|---|---|
| **ChromaDB** (base vectorial) | Guardar el "significado" de las 438 tiendas, para poder buscar por parecido | `chroma_db/` | El agente, en cada consulta (`agente.py:45-49`) |
| **SQLite** (`historial.db`) | Guardar cada consulta, respuesta y voto del comprador | `historial.db` | `src/historial_db.py`, se llena después de cada respuesta |

Ninguna de las dos es un servidor aparte: ambas son archivos en la carpeta del proyecto. No hay que instalar ni configurar un gestor de base de datos.

---

## 2. ¿Por qué esto es un "agente" y no un script cualquiera?

Un script tradicional sigue pasos fijos: entra un dato, pasa por una cadena de transformaciones predefinidas, sale un resultado. Un **agente** es distinto porque **decide** qué hacer según la situación, no solo ejecuta una receta fija.

Nuestro programa cumple las 3 características que definen a un agente:

1. **Percibe**: lee el mensaje del comprador (y el historial de la conversación).
2. **Razona y decide**: el LLM (el modelo de lenguaje, `gpt-4o-mini`) decide, caso por caso, si ya tiene suficiente información para buscar o si necesita preguntar algo antes (`agente.py`, `SYSTEM_PROMPT`, punto 1). Esa decisión no está hardcodeada con un `if`; la toma el modelo.
3. **Actúa sobre su entorno**: cuando decide buscar, ejecuta una herramienta (`buscar_tiendas`) que consulta una fuente externa (el catálogo), y usa el resultado para construir su respuesta.

Un script que simplemente tomara tu consulta y la mandara directo a una búsqueda de texto no sería un agente — sería un buscador. Lo que lo hace agente es que **decide el camino** (preguntar vs. buscar vs. admitir que no encontró nada confiable) en vez de seguir un único camino fijo.

---

## 3. ¿Qué tipo de agente es? ¿Por qué Goal-Based y no otro?

Tu curso (Módulo 4, Sesión 10 — Agentes Reflexivos) enseña 5 categorías, cada una con su propio ejemplo de código. Esta es la comparación real, no genérica:

| Tipo | Definición (de tu curso, fuente IBM) | ¿Nuestro agente? |
|---|---|---|
| **Reflejo simple** | Sigue reglas condición-acción fijas, actúa solo sobre la percepción actual, sin memoria de estados pasados. | **No.** Usa historial de la conversación para interpretar seguimientos ("de Drácula" solo tiene sentido si recuerda que antes preguntó por un disfraz). |
| **Basado en modelo (reflejo + memoria)** | Incorpora un modelo interno del mundo para recordar cómo interacciones pasadas afectaron el entorno. | **Parcial, no es el núcleo.** Sí mantiene un historial de sesión (`MemorySaver`), pero esa memoria no es el mecanismo central de decisión — es un insumo para el razonamiento orientado a meta (ver abajo). |
| **Basado en metas (Goal-Based)** | Considera un objetivo futuro y usa razonamiento para elegir acciones que lo acerquen a esa meta, en vez de solo reaccionar al estímulo inmediato. | **Sí — este es el tipo.** Ver justificación abajo. |
| **Basado en utilidad (Utility-Based)** | Va más allá de cumplir un objetivo: compara MÚLTIPLES opciones con una función de utilidad (sopesando trade-offs) y elige la de mayor beneficio. | **No.** Ver por qué, abajo. |
| **De aprendizaje (Learning Agent)** | Mejora su desempeño con el tiempo, adaptándose a feedback, en vez de depender de reglas fijas. | **Todavía no, pero hay una base para serlo.** Ver nota al final. |

### Por qué es Goal-Based

La meta del agente es clara y explícita: **encontrar una recomendación realmente relevante para lo que el comprador necesita**. Todo su comportamiento se organiza alrededor de esa meta, no de reaccionar al último mensaje:

- Si no tiene información suficiente para perseguir la meta con confianza, **no actúa a ciegas** — pregunta primero (`SYSTEM_PROMPT`, punto 1).
- Cuando actúa (llama a `buscar_tiendas`), **evalúa si el resultado realmente cumple la meta**: si el mejor resultado no supera `UMBRAL_RELEVANCIA = 0.15` (`agente.py:42`), el agente reconoce que **no alcanzó la meta** y lo dice, en vez de fingir que sí (`agente.py:61-67`).

Esto es estructuralmente igual al ejemplo de tu curso (`03_goal_based_agent.py`): el robot de picking localiza el producto, planifica la ruta, y **si no hay stock suficiente, informa que la meta no se cumplió del todo** — exactamente el mismo patrón que nuestro agente cuando dice "no encontré un match confiable, dame más detalle".

### Por qué NO es Utility-Based

Podría parecer utility-based porque usa un *score* numérico de relevancia. La diferencia real: un agente utility-based **compara varias opciones distintas en vivo** y elige según una función de utilidad con trade-offs (ver `04_utility_based_agent.py` de tu curso: evalúa 3 o más combinaciones de vehículo+ruta, pesando tiempo/costo/seguridad, y explica por qué no eligió la más barata). Nuestro agente **no hace eso en producción**: no prueba varias estrategias de búsqueda por consulta y compara. La comparación entre métodos (azar / categoría / léxico / embeddings) **ya se hizo una sola vez, offline, en la evaluación de E5** — la decidió el equipo analizando 378 consultas, no el agente decidiéndolo en cada conversación. En producción, el agente usa un único método (embeddings) y solo filtra por un umbral — eso es control de calidad de una meta, no comparación de utilidad entre alternativas.

### Nota sobre el agente de aprendizaje

Tu curso describe el Learning Agent como uno que tiene 4 piezas: elemento de desempeño, elemento de aprendizaje, crítico, y generador de problemas — y el ejemplo persiste feedback entre ejecuciones para ajustar su confianza. Nosotros ya construimos la pieza de datos (`historial.db` guarda cada consulta, respuesta y voto 👍/👎), que es justo lo que necesitaría un "elemento de aprendizaje". Lo que **todavía no existe** es ese elemento en sí: nada lee `historial.db` hoy para ajustar el comportamiento del agente. Es la base para evolucionar a un Learning Agent más adelante, no lo que es hoy.

---

## 4. ¿Sigue el patrón ReAct? Demostración real

**Sí.** ReAct (*Reasoning + Acting*) es el patrón donde el modelo alterna entre razonar, actuar (llamar a una herramienta), observar el resultado, y volver a razonar — hasta tener una respuesta final. Nuestro agente se construye con `create_agent` (`agente.py:111`, de `langchain.agents`, la API unificada de LangChain v1). Este nombre ya no dice "react" explícitamente, pero el mecanismo es el mismo: por dentro construye un grafo de LangGraph (`StateGraph`) con exactamente el ciclo razonar→actuar→observar que describía el `create_react_agent` original de `langgraph.prebuilt` (esa función sigue existiendo pero está deprecada — el propio paquete instalado avisa: *"create_react_agent has been moved to `langchain.agents`"*). El patrón no cambió, solo el nombre de la puerta de entrada.

Esto no es teórico — lo corrimos en vivo con `"busco una casaca de cuero para hombre"` y esta es la secuencia **real** de mensajes que produjo el agente:

```
[0] HumanMessage: "busco una casaca de cuero para hombre"
[1] AIMessage -> RAZONA Y DECIDE ACCION: llamar buscar_tiendas(consulta="casaca de cuero para hombre")
[2] ToolMessage -> OBSERVACION: "1. Tienda de casacas varsity y chalecos acolchados — Ropa y Moda / ..."
[3] AIMessage: "Aquí tienes algunas opciones de casacas de cuero para hombre: 1. **Tienda de casacas..."
```

Esto es **Razona → Actúa → Observa → Razona de nuevo → Responde**, el ciclo ReAct completo, en un solo turno.

**Aclaración importante:** el ReAct original (el paper de 2022) escribía ese razonamiento como texto plano (`Thought:`, `Action:`, `Observation:`) porque los modelos de esa época no tenían *tool calling* nativo. Hoy, `gpt-4o-mini` tiene tool calling estructurado (lo ves en `[1]`: no es texto libre, es un campo `tool_calls` con el nombre de la función y sus argumentos), así que el mismo patrón ReAct ocurre **sin necesidad de ese formato de texto** — LangGraph lo maneja por debajo.

Dónde está el "razonamiento" en el prompt: el `SYSTEM_PROMPT` (`agente.py:82-107`) no le dice al modelo *qué* responder, le dice *cómo razonar antes de actuar* — por eso dice "antes de buscar, revisa si..." (punto 1), "al llamar a la herramienta, corrige..." (punto 2), "si la herramienta no encontró nada confiable..." (punto 3). Son instrucciones de razonamiento, no de respuesta directa.

---

## 5. ¿Qué tipo de memorias usa y por qué?

| Memoria | Qué guarda | Dónde | Por qué existe |
|---|---|---|---|
| **Corto plazo (short-term)** | Los últimos mensajes de la conversación activa | `MemorySaver()` en RAM, indexado por `session_id` (`agente.py:109`, `115`) | Para entender seguimientos cortos sin que el usuario repita todo — "de Drácula" solo significa algo si recuerda que preguntó por un disfraz. Se pierde si el proceso se reinicia: no es grave, porque es memoria de UNA conversación, no un archivo que deba sobrevivir. |
| **Largo plazo (long-term) — conocimiento del catálogo** | El significado (embedding) de las 438 tiendas | ChromaDB, `chroma_db/` | Para no tener que volver a mandarle las 438 tiendas a OpenAI en cada consulta — se calcula una vez (`01_indexar_catalogo.py`) y se reutiliza siempre. |
| **Largo plazo (long-term) — registro de uso** | Cada consulta + respuesta + voto del comprador | SQLite, `historial.db` | Para poder analizar después qué tan bien funciona el agente con tráfico real (o para un futuro Learning Agent). |

Las dos filas de "largo plazo" son persistentes por igual (ninguna se pierde al reiniciar), pero se usan distinto: el conocimiento del catálogo (ChromaDB) el agente **sí lo vuelve a consultar** en cada búsqueda; el registro de uso (`historial.db`) **no** — nadie se lo vuelve a leer durante la conversación, es solo un registro para humanos. Ninguna de las dos es memoria conversacional (eso es exclusivo del corto plazo, y no sobrevive entre sesiones).

---

## 6. RAG: embeddings, base vectorial, y chunking

**RAG** significa *Retrieval-Augmented Generation* (generación aumentada por recuperación): en vez de que el modelo invente la respuesta de memoria, primero se **recupera** información real de una fuente (el catálogo), se la **agrega** al contexto, y recién ahí el modelo **genera** la respuesta final. Las 3 partes en nuestro código:

- **Retrieval (recuperar):** `similarity_search_with_relevance_scores(consulta, k=3)` sobre `_vectorstore` (`agente.py:60`).
- **Augmented (agregar al contexto):** el resultado de esa búsqueda vuelve al modelo como un `ToolMessage` (la "Observación" del paso 4).
- **Generation (generar):** el modelo redacta la respuesta final usando esa información, no la inventa.

**Embeddings:** `text-embedding-3-small` de OpenAI (`agente.py:31`, `01_indexar_catalogo.py:28`). Un embedding convierte un texto en una lista de números (un vector) que representa su significado — textos con significado parecido quedan "cerca" en ese espacio numérico, aunque no compartan ninguna palabra exacta. Se eligió este modelo porque fue el que ganó, por margen real, en la evaluación offline de E5 (66,9% de acierto vs. 52,9% de un método por palabras exactas, sobre 378 consultas reales etiquetadas a mano).

**Base vectorial:** ChromaDB, local y persistente (`chroma_db/`). Guarda esos vectores y permite buscar "¿cuáles son los más parecidos a este?" de forma eficiente.

**Chunking (¿se divide el texto en pedazos?): NO.** Revisé el código de `01_indexar_catalogo.py` a propósito para esta pregunta: cada tienda se convierte en **un solo documento completo** (`Document(page_content=rag_text, ...)`, línea 46), sin ningún divisor de texto (`RecursiveCharacterTextSplitter` o similar). Esto es correcto para este caso, no un descuido: el chunking sirve para documentos largos (un PDF, un libro) donde un solo fragmento no entra en el límite del modelo o mezcla varios temas distintos. Acá cada "documento" es la descripción de una sola tienda — un párrafo corto, un único tema. Partirlo en pedazos más chicos no ayudaría a nada, y podría cortar la descripción a la mitad y perder sentido.

---

## 7. Guardrails: ¿cómo controla el alcance?

El flujo completo está en `src/guardrails_mvp.py`. Dos capas antes de llegar al modelo principal, una capa después:

| Capa | Qué hace | Código |
|---|---|---|
| Seguridad (pre-entrada) | Detecta intentos de hackear el prompt (jailbreak) | `DetectJailbreak`, `guardrails_mvp.py:54-56` |
| **Relevancia (pre-entrada)** | **Controla el alcance**: rechaza cualquier cosa que no sea sobre ropa/tiendas de Gamarra | Clasificador propio, `guardrails_mvp.py:77-86` |
| PII (post-salida) | Revisa que la respuesta no filtre datos personales | `GuardrailsPII`, `guardrails_mvp.py:116-121` |

**Prueba real** (no hipotética) con tu ejemplo exacto — le pregunté: *"ayúdame a resolver un examen de matemáticas, necesito las respuestas"*:

> Respuesta del agente: *"Este asistente solo responde sobre búsqueda de ropa y tiendas en el Emporio de Gamarra. Cuéntame qué prenda buscas."*

La pregunta nunca llega al modelo principal — la capa de relevancia la corta antes, ahorrando costo y evitando que el agente se desvíe de su tarea. El mecanismo: un LLM barato (`gpt-4o-mini`) recibe el mensaje más el historial de la conversación, y responde solo "SI" o "NO" a si tiene que ver con ropa/tiendas de Gamarra (`PROMPT_RELEVANCIA`, `guardrails_mvp.py:61-70`). Si responde "NO", se lanza `GuardrailBloqueado` y el mensaje nunca llega al agente principal.

---

## 8. ¿Cómo evaluamos?

Hay dos evaluaciones distintas, en momentos distintos:

**Evaluación offline (antes de construir el MVP, documentada en `Muestra_378_Evaluacion/`):** se armó una muestra de 378 consultas reales, se etiquetaron a mano con el equipo (doble ciego + desempate), y se compararon 4 métodos con la métrica Hit Rate@3 (¿aparece al menos una tienda relevante entre las 3 primeras?). Resultado: azar 23,0%, categoría 46,8%, léxico 52,9%, **embeddings 66,9%** — por eso el MVP usa embeddings.

**Evaluación en vivo (el MVP ya corriendo):**
- Cada consulta + respuesta queda en `historial.db` (`historial_db.guardar_interaccion`).
- Cada respuesta tiene botones 👍/👎 (`st.feedback`, `app.py`) que graban si le sirvió al comprador (`historial_db.guardar_feedback`).
- LangSmith registra tokens, costo estimado y latencia de cada ejecución, si se activa `LANGSMITH_TRACING=true`.

Con eso se puede, más adelante, medir qué porcentaje real de respuestas recibe 👍 vs 👎 — una métrica de satisfacción real, distinta (y más dura) que el Hit Rate@3 offline, porque viene de usuarios reales, no de etiquetadores del equipo.

---

## 9. ¿Por qué LangGraph y no solo LangChain?

**LangChain** da las piezas sueltas: el conector al modelo (`ChatOpenAI`), el conector a la base vectorial (`Chroma`), el decorador para convertir una función en herramienta (`@tool`). Son bloques, no un flujo.

**LangGraph** es el que arma el flujo con esas piezas: decide en qué orden se ejecutan (¿pregunto o llamo a la tool?, ¿qué hago con el resultado?), y además maneja la memoria de la conversación entre turnos (el `checkpointer`) sin que el código tenga que guardar y recuperar ese estado a mano.

En la práctica: `create_agent(model=..., tools=[...], system_prompt=..., checkpointer=...)` (`agente.py:111-116`) es **una sola llamada** que arma todo ese flujo — decidir, actuar, recordar — usando los componentes de LangChain por debajo, y devuelve un grafo de LangGraph compilado (`CompiledStateGraph`). Sin LangGraph, habría que escribir ese bucle de decisión a mano.

---

## Resumen de dónde está cada cosa

| Pregunta | Archivo |
|---|---|
| Interfaz de chat | `src/app.py` |
| El agente (prompt, tool, memoria, ReAct) | `src/agente.py` |
| Guardrails (seguridad, alcance, PII) | `src/guardrails_mvp.py` |
| Registro de uso y feedback | `src/historial_db.py` |
| Indexar el catálogo en ChromaDB | `src/01_indexar_catalogo.py` |
| Arquitectura y stack completo, con diagrama visual | `MVP_ARQUITECTURA_Y_TECNOLOGIAS.md` (sección 4) / `.drawio` |
| Ficha PEAS del agente | `agent_profile_card.html` |
