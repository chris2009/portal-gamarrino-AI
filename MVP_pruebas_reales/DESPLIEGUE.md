# Despliegue de Portal Gamarrino AI para pruebas con usuarios reales

Documento único del despliegue: qué se publicó, cómo funciona, qué se hizo (y por qué) y cómo
se mantiene. Hecho el 12-nov-2026.

---

## 1. Qué está publicado

| Pieza | Dónde | Visibilidad | Para qué |
|---|---|---|---|
| **App para probadores** | https://chris1803-portal-gamarrino-ai.hf.space | Pública, con contraseña (`APP_PASSWORD`) | El enlace que se comparte |
| Space (código + build) | https://huggingface.co/spaces/Chris1803/portal-gamarrino-ai | Público | Hugging Face construye y corre la app desde aquí |
| Dataset de tiendas (`chroma_db`) | https://huggingface.co/datasets/Chris1803/portal-gamarrino-chroma | **Privado** | Las 438 tiendas (con 37 WhatsApp); solo el build lo descarga |
| Conversaciones y votos 👍/👎 | Supabase, proyecto `agente_gamarrino` | Privado (RLS) | Registro durable de cada consulta, respuesta y voto |
| Trazas paso a paso | LangSmith, proyecto `portal-gamarrino-pruebas-reales` | Privado | Ver qué buscó el agente, qué recibió, tiempos y costo |
| Código fuente | GitHub `portal-gamarrino-AI`, carpeta `MVP_pruebas_reales/` | Público | Historia del código (sin `.env` ni `chroma_db`) |

**Qué enlace se comparte con los probadores: siempre el `.hf.space`.**

| Enlace | Qué muestra | Para quién |
|---|---|---|
| `https://chris1803-portal-gamarrino-ai.hf.space` | Solo la app, a pantalla completa, sin nada de Hugging Face | **Probadores** (junto con la contraseña) |
| `https://huggingface.co/spaces/Chris1803/portal-gamarrino-ai` | La app dentro de la página de Hugging Face: encabezado, pestañas *App / Files / Community / Settings*, botón *Logs*, y el código a un clic | El equipo, para administrar |

El segundo deja ver el código y los archivos del Space; no tiene nada secreto, pero distrae y no
es lo que debe ver un comprador.

```
                    ┌────────────────────── Hugging Face Space (Docker) ──────────────────────┐
 Probador ──HTTPS──▶│ Streamlit (src/app.py) ──▶ agente v7.1 (src/agente.py + guardrails)     │
 (navegador)        │        │                        │             │                          │
                    └────────┼────────────────────────┼─────────────┼──────────────────────────┘
                             │                        │             │
                             ▼                        ▼             ▼
                  Supabase (Postgres)          OpenAI API      LangSmith
                  conversaciones + votos       gpt-4o-mini,    trazas
                                               embeddings

 Al construir la imagen (no en cada visita):  dataset privado ──HF_TOKEN──▶ chroma_db dentro de la imagen
```

---

## 2. Las dos carpetas: quién es quién

```
Entregable 29-10/                          (repo de GitHub)
├── MVP_Portal_Gamarrino/   ← EL LABORATORIO: aquí se mejora y se EVALÚA el agente
│   ├── src/agente.py, src/guardrails_mvp.py     ← ÚNICO lugar donde se editan
│   ├── src/app.py                                 interfaz local (localhost:8501)
│   ├── chroma_db/                                 índice de tiendas (fuente)
│   └── evaluacion/                                notebook vs E5 (el 67,5 %)
│
└── MVP_pruebas_reales/     ← LA VITRINA: lo que usan los probadores en internet
    ├── src/agente.py, src/guardrails_mvp.py     ← COPIAS (las trae publicar.py; no se editan)
    ├── src/app.py                               ← interfaz pública (contraseña, foto, ejemplos)
    ├── src/historial_db.py                      ← guarda en Supabase; VERSION_AGENTE
    ├── src/descargar_chroma.py, precargar_modelos.py, Dockerfile, requirements.txt
    ├── publicar.py                              ← publica en Hugging Face con un comando
    └── DESPLIEGUE.md                            ← este documento
```

**Regla de oro:**

- **¿Vas a mejorar el agente?** (cómo busca, el prompt, los guardrails): se edita en
  `MVP_Portal_Gamarrino/src/`. Ahí está el notebook que lo mide frente a E5; si se editara solo
  en `MVP_pruebas_reales`, los probadores usarían un agente que nadie evaluó y el 67,5 % de la
  defensa ya no lo describiría.
- **¿Vas a cambiar la página pública?** (textos, foto, ejemplos, contraseña, base de datos):
  se edita en `MVP_pruebas_reales/`. El MVP no se toca.
- **`MVP_Portal_Gamarrino` no desaparece ni queda viejo**: sigue siendo la versión evaluada, la que
  corres en local para desarrollar y la que se presenta en la defensa. `MVP_pruebas_reales` solo
  la envuelve para internet.

Las copias del agente en `MVP_pruebas_reales/src/` existen para poder probar la vitrina en la PC
y para que Hugging Face las reciba; `publicar.py` las reemplaza siempre por las del MVP antes de
subir, así nunca se desincronizan.

### Qué cambia la vitrina frente al MVP

| Archivo | Frente al MVP | Por qué |
|---|---|---|
| `src/agente.py`, `src/guardrails_mvp.py` | Idénticos | Lo que prueban los usuarios es lo que se evaluó |
| `src/historial_db.py` | Guarda en Supabase si existe `DATABASE_URL` (si no, en `historial.db` como el MVP); anota `VERSION_AGENTE` en cada respuesta | El disco del Space se borra en cada reinicio |
| `src/app.py` | Contraseña, barra lateral (foto, cómo funciona, 4 ejemplos, "Nuevo chat", aviso de privacidad); sin burbuja de bienvenida | Abrirlo a desconocidos sin que gasten la cuenta de OpenAI, y que se entienda sin explicación |
| `Dockerfile`, `requirements.txt` | Nuevos | Receta de la imagen, con las mismas versiones del `.venv` evaluado |
| `src/descargar_chroma.py` | Nuevo | Baja `chroma_db` del dataset privado durante el build |
| `src/precargar_modelos.py` | Nuevo | Baja los modelos de los guardrails durante el build, no con el primer usuario |
| `assets/gamarra.jpg`, `.streamlit/config.toml` | Nuevos | Foto de la barra lateral y color rojo de los botones |

---

## 3. Qué ejecuta Hugging Face

En Hugging Face **no hay una consola donde se escriban comandos**. Lo que ejecuta está escrito en
dos archivos de esta carpeta, y lo corre solo cada vez que se sube un cambio:

1. **`README.md` (las líneas entre `---` al inicio)** le dice qué es: `sdk: docker` (construir con
   el `Dockerfile`) y `app_port: 8501` (el puerto donde escucha la app).
2. **`Dockerfile`**: la receta, paso por paso.

### 3.1 Construcción de la imagen (build)

| # | Comando del `Dockerfile` | Qué hace | ¿Se repite en cada publicación? |
|---|---|---|---|
| 1 | `FROM python:3.12-slim` | Parte de un Linux mínimo con Python 3.12 | No (caché) |
| 2 | `RUN useradd -m -u 1000 user` + `USER user` | Crea el usuario con el que Hugging Face corre los Spaces | No |
| 3 | `ENV HF_HOME=… ANONYMIZED_TELEMETRY=False` | Dónde guardar los modelos; apaga la telemetría de Chroma | No |
| 4 | `RUN pip install … torch==2.15.0` (índice CPU) | PyTorch solo-CPU (la versión normal trae CUDA y pesa varios GB más) | No |
| 5 | `RUN pip install -r requirements.txt` | LangChain, Chroma, Guardrails, spaCy + `en_core_web_lg`, Streamlit, psycopg… | Solo si cambia `requirements.txt` |
| 6 | `RUN pip install openai==3.42.0` | La versión del `.venv` evaluado (ver bitácora, problema 3) | Solo si cambia lo anterior |
| 7 | `RUN printf 'enable_metrics=false' > ~/.guardrailsrc` | Apaga la telemetría de Guardrails AI | Solo si cambia lo anterior |
| 8 | `COPY . .` | Copia el código | **Sí** |
| 9 | `RUN --mount=type=secret,id=HF_TOKEN … python src/descargar_chroma.py` | Baja `chroma_db` del dataset privado con el secret `HF_TOKEN` (montado solo en este paso; no queda en la imagen) | Sí |
| 10 | `RUN python src/precargar_modelos.py` | Baja los modelos de los guardrails (jailbreak, GLiNER) | Sí |

La primera construcción tardó unos 4 minutos; las siguientes, 1–2 minutos, porque los pasos 1–7
quedan en caché.

### 3.2 Arranque (cada vez que el Space se enciende)

```
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
```

Al entrar un probador con la contraseña correcta, `app.py` importa el agente (carga los modelos
desde la imagen, unos segundos) y desde ahí cada mensaje sigue el mismo camino que en el MVP.

### 3.3 Dónde ver lo que pasa

- **Logs**: en la página del Space, botón **Logs** (arriba, junto al estado). Pestaña *Build* para
  la construcción y *Container* para la app corriendo; ahí aparecen los errores.
- **Estado**: *Building* → *Running*. Si dice *Build error* o *Runtime error*, el log dice por qué.
- **Settings del Space**: *Variables and secrets*, *Pause* (apagarlo), *Factory rebuild*
  (reconstruir desde cero), visibilidad.

---

## 4. Cómo se publica un cambio

Todos los comandos se corren en la PC, desde la carpeta `Entregable 29-10`, con el `.venv` del MVP
(no hace falta otro entorno). La sesión de Hugging Face ya quedó iniciada en la PC; si algún día
se pierde: `MVP_Portal_Gamarrino/.venv/Scripts/python.exe -m huggingface_hub.cli.hf auth login`.

### Caso A: mejoraste el agente

```bash
# 1. Editar MVP_Portal_Gamarrino/src/agente.py (o guardrails_mvp.py)
# 2. Volver a correr el notebook de evaluación (MVP_Portal_Gamarrino/evaluacion/) y revisar el %
# 3. Subir VERSION_AGENTE en MVP_pruebas_reales/src/historial_db.py (ej. "v7.1" -> "v7.2")
# 4. Ver qué se publicaría y publicar:
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --revisar
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py -m "v7.2: qué cambió"
# 5. Guardar en GitHub
git add MVP_Portal_Gamarrino MVP_pruebas_reales && git commit -m "v7.2: qué cambió" && git push
```

`publicar.py` copia solo el agente del MVP a la vitrina; si olvidaste el paso 3, se detiene y lo pide.

### Caso B: cambiaste la página pública

```bash
# 1. Editar MVP_pruebas_reales/src/app.py (o la foto, los textos…)
# 2. (Opcional) probar en la PC: ver sección 6
# 3. Publicar y guardar en GitHub
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py -m "interfaz: qué cambió"
git add MVP_pruebas_reales && git commit -m "interfaz: qué cambió" && git push
```

### Caso C: cambiaron las tiendas (se reindexó `chroma_db` en el MVP)

```bash
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --chroma -m "tiendas actualizadas"
```

Sube `chroma_db` al dataset privado y reconstruye el Space. `chroma_db` nunca va a GitHub ni al
Space público.

### Caso D: cambiaste un secreto

Los secretos se cambian en la web: *Settings → Variables and secrets → (el nombre) → Replace*.

- `OPENAI_API_KEY`, `DATABASE_URL`, `APP_PASSWORD`, `LANGSMITH_*`: los usa la app **mientras corre**.
  Al guardarlos, Hugging Face reinicia el Space solo; no hay que hacer nada más.
- `HF_TOKEN`: solo se usa **al construir** (para bajar `chroma_db`). Un reinicio no lo prueba; hay
  que reconstruir desde cero (*Factory rebuild*, botón en *Settings*, o por comando):

```bash
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --reconstruir
```

Por dentro es una llamada a la API de Hugging Face (la herramienta `hf` de la terminal no trae un
comando para reiniciar Spaces):

```bash
MVP_Portal_Gamarrino/.venv/Scripts/python.exe -c "from huggingface_hub import HfApi; HfApi().restart_space('Chris1803/portal-gamarrino-ai', factory_reboot=True)"
```

### Qué muestra `publicar.py`

```
1. Agente: se trae desde MVP_Portal_Gamarrino/src (ahí se edita y se evalúa)
   agente.py: copiado
2. Versión del agente
   publicada: v7.1 | local: v7.2 | el agente cambió respecto de lo publicado: sí
4. Código -> Space Chris1803/portal-gamarrino-ai
   subido
5. Build en Hugging Face (1-2 min; unos 4 si cambia requirements.txt)
   [00 min] RUNNING_BUILDING
   [01 min] RUNNING
   En línea: https://chris1803-portal-gamarrino-ai.hf.space (health 200 ok)
```

Mientras se construye la versión nueva, la anterior sigue atendiendo (`RUNNING_BUILDING`).

---

## 5. Variables y secretos

Ninguno está en GitHub ni en el Space público. En la PC viven en `MVP_pruebas_reales/.env`
(ignorado por git); en Hugging Face, en *Settings → Variables and secrets* (se ven los nombres,
nunca los valores).

| Nombre | Tipo en HF | Qué es |
|---|---|---|
| `OPENAI_API_KEY` | Secret | Clave de OpenAI (agente, embeddings, clasificador de relevancia) |
| `DATABASE_URL` | Secret | Conexión a Supabase: *Connect → Transaction pooler*, puerto 6543 |
| `APP_PASSWORD` | Secret | Contraseña que se da a los probadores |
| `HF_TOKEN` | Secret | Token **de solo lectura** (`space-gamarrino-lectura-chroma`) para bajar el dataset privado en el build. No es el token de la PC, que sí escribe (lo usa `publicar.py`) |
| `LANGSMITH_API_KEY` | Secret | Clave de LangSmith |
| `LANGSMITH_TRACING` | Variable | `true` |
| `LANGSMITH_PROJECT` | Variable | `portal-gamarrino-pruebas-reales` (aparte de las trazas de desarrollo) |

`.env.example` tiene la plantilla. Para cambiar un secreto en Hugging Face: *Settings → Variables
and secrets → (el nombre) → Replace*; el Space se reinicia solo.

---

## 6. Probar la vitrina en la PC

```bash
cd MVP_pruebas_reales
../MVP_Portal_Gamarrino/.venv/Scripts/python.exe -m streamlit run src/app.py
```

Ojo: con `DATABASE_URL` en el `.env`, lo que pruebes en la PC **se guarda en el Supabase real**,
mezclado con los probadores. Para no ensuciarlo, pon `#` delante de la línea `DATABASE_URL` del
`.env` mientras pruebas (se guarda en `historial.db` local) y quítalo al terminar.

---

## 7. Ver los resultados

**Supabase** (*Table Editor* o *SQL Editor*):

```sql
-- conversaciones con su voto (si lo hubo)
select i.id, i.session_id, i.timestamp_utc at time zone 'America/Lima' as hora_lima,
       i.mensaje_usuario, i.respuesta_agente, i.version_agente, f.util
from gamarrino_interacciones i
left join gamarrino_feedback f on f.interaccion_id = i.id
order by i.id;

-- votos por versión del agente
select i.version_agente, count(*) as votos, round(100.0 * avg(f.util), 1) as pct_utiles
from gamarrino_feedback f join gamarrino_interacciones i on i.id = f.interaccion_id
group by 1 order by 1;
```

Las filas `v7` (ids 2–4) son la primera prueba propia, del 12-nov; las de probadores salen como `v7.1`.

**LangSmith**: proyecto `portal-gamarrino-pruebas-reales` → cada conversación con sus búsquedas
(`buscar_tiendas`), lo que devolvieron, la respuesta, tiempos y tokens.

---

## 8. Bitácora: qué se hizo y qué problemas hubo

Todo el 12-nov-2026.

1. **Elección de plataforma.** Vercel no sirve (es para páginas web y funciones cortas; el agente
   es un proceso Python que carga ~2,6 GB de modelos). Se eligió Hugging Face Spaces (Docker) +
   Supabase (ya había cuenta). Se creó esta carpeta para no tocar el MVP evaluado.
2. **Supabase.** Proyecto `agente_gamarrino`, región Americas. *Data API* desactivada y *Automatically
   expose new tables* desactivado (la app se conecta directo a Postgres; así nadie puede leer las
   tablas por la API pública); *automatic RLS* activado. Primer intento de conexión: `password
   authentication failed` → la contraseña del `.env` no era la del proyecto; se reseteó en
   *Project Settings → Database* y funcionó. Prueba completa: tablas creadas, inserción, cambio de
   voto (queda uno por respuesta), RLS activo, filas de prueba borradas.
3. **Hugging Face.** El `hf.exe` del `.venv` no arranca ("Fatal error in launcher"): el `.venv` se
   creó cuando la carpeta estaba en otra ruta y el `.exe` apunta a la vieja. Solución: llamar la
   herramienta a través de Python (`python -m huggingface_hub.cli.hf …`).
4. **`chroma_db` en un dataset privado.** Un Space público deja descargar todos sus archivos aunque
   la app pida contraseña, y `chroma_db` trae los datos de las 438 tiendas (37 con WhatsApp), que en
   GitHub están excluidos. Se subió a un dataset privado y el build lo descarga con `HF_TOKEN`
   (verificado byte a byte). El código sí es público (ya lo era en GitHub).
5. **Plan PRO.** Crear el Space dio `402 Payment Required`: desde 2026 los Spaces Docker en CPU
   basic exigen la suscripción PRO (9 USD/mes); solo los Spaces estáticos siguen gratis. Se
   descartó Azure (la suscripción de UTEC del curso de Data Engineering estaba deshabilitada) y se
   tomó PRO.
6. **Build 1 falló**: conflicto de versiones. El `.venv` evaluado tiene `openai 3.42.0`, pero
   `guardrails-ai 0.10.2` y `litellm` declaran `openai<3`. En la PC pip lo instaló igual (con aviso)
   y funciona; en Docker, pip se niega a resolverlo. Solución: instalar todo lo demás y luego
   `openai==3.42.0` en un paso aparte (paso 6 del build), igual que quedó la PC.
7. **Modelo de spaCy faltante** (detectado antes de que fallara): el detector de datos personales
   usa `en_core_web_lg`, que estaba en el `.venv` pero no en `requirements.txt`; sin él habría
   fallado con el primer usuario. Se agregó.
8. **Telemetría de Guardrails.** El log del build mostró que Guardrails AI intenta mandar métricas
   de uso a un servidor suyo (nombre del validador y si pasó; no los mensajes). Se apagó
   (paso 7 del build). En la PC tampoco llega nada: ese servidor no responde.
9. **Primera prueba real (ids 2–4 en Supabase)** encontró dos fallas:
   - **Saludo doble**: la app mostraba una burbuja de bienvenida que el agente no ve (no está en su
     memoria); al escribir "hola…" el agente se presentaba otra vez. Se quitó la burbuja; su texto
     pasó al subtítulo. Solo existía en la vitrina.
   - **"¿Te sirvieron estas recomendaciones?" bajo "¿Es para hombre o para mujer?"**: la regla daba
     por hecho que hubo recomendación si *alguna* búsqueda del turno trajo tiendas; el agente puede
     buscar dos prendas a la vez y recibir tiendas en una y la pregunta de género en otra. Ahora
     el feedback sale solo si la respuesta **nombra** una tienda encontrada (`_turno_trajo_tiendas`
     en `agente.py`). El error también estaba en el MVP: se corrigió allí y se copió. No cambia
     recomendaciones ni la evaluación (el notebook no usa ese valor). Desde aquí, `VERSION_AGENTE = "v7.1"`.
10. **LangSmith.** Se había dejado apagado en el Space para no mandar los mensajes de los
    probadores a otro servicio; se activó con un proyecto aparte y el aviso de privacidad de la app
    lo dice.
11. **`publicar.py` y este documento**, para que publicar sea un solo comando y no dependa de
    recordar pasos.
12. **13-nov: `HF_TOKEN` de solo lectura.** Al crear el Space se había puesto en `HF_TOKEN` el token
    principal de la cuenta (con permiso de escritura sobre todo), cuando el Space solo necesita leer
    el dataset. Se creó el token `space-gamarrino-lectura-chroma` (*Access Tokens → Create new token
    → Fine-grained*, preset *Custom* o *Read-Only*: la pantalla ya no muestra la lista de permisos
    directamente) y se reemplazó el secret. Verificado con `publicar.py --reconstruir`: el build bajó
    `chroma_db` con el token nuevo y la app quedó en línea.

---

## 9. Costos

| Servicio | Plan | Costo |
|---|---|---|
| Hugging Face | PRO | 9 USD/mes (cubre el Space en CPU basic: 2 vCPU, 16 GB) |
| Supabase | Gratis | 0 (se pausa tras 7 días sin actividad; se reactiva con un clic) |
| OpenAI | Crédito prepagado (10 USD) | Cada consulta usa `gpt-4o-mini` + embeddings: centavos por conversación. El crédito es el tope: si se agota, el agente deja de responder hasta recargar |
| LangSmith | El que ya se usaba en desarrollo | — |

---

## 10. Pendientes y al terminar las pruebas

**Pendientes:**
- Confirmar con Portal Gamarrino que se pueden mostrar los WhatsApp de las tiendas a probadores.
- Confirmar el origen y los derechos de `assets/gamarra.jpg`.

**Al terminar:**
1. *Settings → Pause* en el Space (o ponerlo privado).
2. Exportar los resultados de Supabase (*Table Editor → Export to CSV*) para el informe.
3. Cancelar Hugging Face PRO si no se seguirá usando.
4. Regenerar o borrar los tokens usados (Hugging Face, y la contraseña de la base de Supabase).
