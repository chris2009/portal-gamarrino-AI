# E5 — Borrador de contenido (para pasar a la plantilla pptx)

Equipo 7 · Portal Gamarrino AI · Entrega: jueves 29-oct-2026
Pista usada en todas las cajas: **LLM / agente** (no ML clásico).

---

## SECCIÓN 1 · PLAN DE EVALUACIÓN

### 1 · Problema de ML
En el fondo es una tarea de **recuperación semántica + ranking** (retrieval & ranking), no de clasificación ni de generación pura: dada una consulta en lenguaje natural, el sistema recupera del catálogo las tiendas semánticamente más cercanas y arma un top-3. El LLM se usa solo después, para redactar la explicación breve de cada coincidencia — no decide qué tiendas se muestran.

- **Unidad de predicción:** consulta del usuario × catálogo de tiendas activas.
- **Momento de la decisión:** cuando el usuario envía su consulta en el asistente web móvil — típicamente antes de salir de casa (81,4 % de los casos) o durante el viaje.
- **Horizonte:** inmediato, una sola interacción (no hay predicción a futuro como en el caso de cobranza).
- **Contexto disponible al decidir:** texto libre de la consulta, memoria conversacional de la sesión (preferencias mencionadas antes) y el catálogo activo (`rag_text`: categoría, subcategoría, tags, descripción, ubicación).

### 2 · Métrica ↔ KPI
- **Métrica principal:** Hit Rate@3 (Success@3) — % de consultas donde al menos una de las 3 tiendas recomendadas es relevante, según etiquetado de dos evaluadores (kappa de Cohen ≥ 0,80). Umbral pre-registrado: **≥ 70 %**.
- **Por qué esta métrica:** refleja directamente si el usuario encuentra lo que buscaba entre las 3 opciones mostradas — es el mecanismo central del producto.
- **KPI de impacto:** Tasa de recomendación útil (consultas con al menos una tienda considerada útil / total evaluadas) ≥ 70 %, definido en el informe preliminar.
- **Métrica de contrapeso:** latencia promedio ≤ 6 s, p95 ≤ 10-12 s (guardarraíl técnico) — ganar relevancia a costa de respuestas lentas rompe la promesa de "antes de salir de casa".
- **Costo por caso:** `[ ]` — pendiente de estimar (llamadas a embeddings + LLM por consulta). Obligatorio para LLM/agente, hay que completarlo antes de entregar.

### 3 · Baselines
Cuatro filas, consistentes con la Opción A ya decidida por el equipo (sin depender del agente de producción de Abraham):

1. **No hacer nada:** selección aleatoria de 3 tiendas activas del catálogo.
2. **Lo que se hace hoy** (mapa de alternativas, A2): filtro por categoría fija, replicando el mecanismo de los directorios existentes (Gamarra.com.pe, Mi Gamarra) — el usuario elige una categoría y recibe una lista, sin comprensión de lenguaje natural.
3. **Modelo simple:** baseline léxico (coincidencia de palabras clave / TF-IDF sobre `rag_text`), ya mencionado en el informe preliminar como punto de comparación planeado para el E5.
4. **Modelo v0:** pipeline real del equipo — `text-embedding-3-small` + ChromaDB + lógica de ranking.

### 4 · Con qué datos se prueba
- **Conjunto de prueba (ahora):** el piloto que ya está en mano — 50 consultas reales (parte del histórico de 21,186) evaluadas sobre las 60 tiendas de la muestra aleatoria (ampliable al catálogo consolidado de 438). Se declara explícitamente como **ensayo del protocolo**, no como la muestra probabilística definitiva de 378 consultas / 319 tiendas, que sigue pendiente de Portal Gamarrino.
- **Corte respecto al desarrollo:** ninguna de las 50 consultas reales se usó para construir ejemplos del prompt ni para ajustar el umbral de similitud — se reservan solo para medir.
- **Nota de honestidad (regla de la rúbrica):** se deja escrito en la plantilla que es una muestra piloto pequeña y no representativa (CAL-6 aún no resuelto), no un resultado generalizable al universo de 21,186 consultas.

### 5 · Un rango y dónde falla
- **Rango:** intervalo de confianza del 95 % por bootstrap (remuestreo, 1000 repeticiones) sobre las 50 consultas. Con una muestra tan chica, el rango va a salir amplio — se declara así, no se oculta.
- **Segmentos para el análisis de error** (tipos de consulta, pista LLM/agente):
  a. Consultas específicas de una sola prenda (p. ej. "jean azul").
  b. Consultas ambiguas o compuestas (p. ej. "algo para una fiesta").
  c. Consultas con marca, talla o precio mencionado explícitamente.

### 6 · Criterio de decisión
- Si el Hit Rate@3 del modelo v0 no supera al baseline léxico por más que el rango (intervalos se cruzan), se revisa el modelo de embeddings o la lógica de ranking antes del 21 de noviembre, en vez de escalar directo a las 378 consultas.
- Si la latencia promedio supera 6 s o el p95 supera 10-12 s por consulta, se evalúa simplificar el pipeline o cambiar de proveedor de embeddings/LLM antes de seguir.

---

*(Pendiente: Sección 2 — Baseline vs. modelo v0 [requiere correr el pipeline], Sección 3 — Model Card v0, Sección 4 — Registro de 3 riesgos, Anexo.)*
