# Instrucciones del proyecto — Portal Gamarrino AI (MVP)

## Regla fija: cero contradicciones entre documentos

Los mismos hechos están descritos en varios archivos a la vez (`README.md`,
`EXPLICACION_MAESTRA_MVP.md`, `MVP_ARQUITECTURA_Y_TECNOLOGIAS.md` (que desde
el 29-oct-2026 incluye el diagrama, ver sección "Compilar..." más abajo),
`Documentacion_MVP_Latex/diagrama_arquitectura.dot`, `agent_profile_card.html`).
Editar uno sin revisar los demás ya causó una
contradicción real (README decía que el filtro de PII "sanea nombre de
persona" cuando en realidad se excluyó `PERSON` a propósito por un bug).
**No vuelve a pasar.**

Antes de dar por terminada CUALQUIER tarea que toque uno de los hechos de
esta tabla, correr un grep de ese termino sobre `*.{md,html,dot}` **de forma
recursiva** (el `.dot` vive un nivel abajo, en `Documentacion_MVP_Latex/`,
que está en `.gitignore` pero igual debe mantenerse sincronizado a mano) y
revisar cada resultado, no solo el archivo que se estaba editando:

| Hecho compartido | Aparece en |
|---|---|
| `UMBRAL_RELEVANCIA = 0.15` y las consultas de calibración | MVP_ARQUITECTURA (sección 2 y 7), EXPLICACION (sección 3), agent_profile_card (Tools) |
| Entidades del filtro PII y por qué se excluyen `PHONE_NUMBER`/`PERSON` | README, MVP_ARQUITECTURA (secciones 4 y 5), Documentacion_MVP_Latex/diagrama_arquitectura.dot, agent_profile_card |
| Límite de `DetectJailbreak` en español (2 de 2 / 0 de 2) | README, MVP_ARQUITECTURA (sección 5), agent_profile_card |
| Hit Rate@3 (23,0 / 46,8 / 52,9 / 66,9%, IC95, segmentos 79,6%/20,0%) | EXPLICACION (sección 8), MVP_ARQUITECTURA (sección 7), agent_profile_card |
| Memoria corto/largo plazo (qué va en cada categoría) | README, EXPLICACION (sección 5), agent_profile_card |
| Tipo de agente (Goal-Based) y por qué | EXPLICACION (sección 3), agent_profile_card (tag) |
| El flujo del diagrama (nodos, flechas) | MVP_ARQUITECTURA_Y_TECNOLOGIAS.md sección 4 (Mermaid) y Documentacion_MVP_Latex/diagrama_arquitectura.dot (Graphviz) — dos fuentes separadas, no se generan una de la otra |
| Nombre de la función que construye el agente (`create_agent` de `langchain.agents`; ya NO `create_react_agent`, que quedó deprecada en `langgraph.prebuilt`) | `agente.py` (import + llamada), MVP_ARQUITECTURA (secciones 2 y 4), EXPLICACION (secciones 4 y 9) |
| Referencias `archivo.py:linea` | Cualquier doc que cite una línea de código — si el código se edita y mueve líneas, hay que re-verificar, no asumir que la cita sigue siendo correcta |

Si agregas un hecho nuevo que se repite en más de un archivo, agrégalo a
esta tabla.

Después de corregir cualquier cosa de esta lista: recompilar el PDF (ver
sección siguiente).

## Compilar la documentación a PDF

Este proyecto tiene un PDF compilado (`Documentacion_MVP.pdf`) que junta estos
`.md` en un solo documento, en este orden:

1. `README.md`
2. `EXPLICACION_MAESTRA_MVP.md`
3. `MVP_ARQUITECTURA_Y_TECNOLOGIAS.md` (incluye el diagrama de arquitectura
   en su sección 4 — `DIAGRAMA_ARQUITECTURA.md` existió como archivo
   separado hasta el 29-oct-2026, cuando se fusionó aquí porque repetía lo
   mismo que la sección 4 en otro formato)

**El script, sus archivos de soporte (`.dot`, `.tex`) y el PDF resultante
viven en `Documentacion_MVP_Latex/`, y esa carpeta entera está en
`.gitignore` desde el 29-oct-2026 (decisión explícita del usuario): al repo
solo suben los `.md` fuente, no el PDF compilado ni el pipeline LaTeX que lo
genera.**

**Regla fija: cada vez que edites, mejores o corrijas cualquiera de esos 3
archivos, vuelve a compilar el PDF antes de terminar la tarea.** No hace
falta que el usuario lo pida cada vez — es parte de terminar el trabajo.

Comando (desde `MVP_Portal_Gamarrino/`):
```bash
python Documentacion_MVP_Latex/compilar_documentacion.py
```

Las rutas dentro del script son relativas a su propia ubicación (no al
directorio desde donde se invoque), así que funciona igual si se corre con
la ruta completa. El PDF queda en `Documentacion_MVP_Latex/Documentacion_MVP.pdf`.

### Qué hace el script

1. Renderiza `Documentacion_MVP_Latex/diagrama_arquitectura.dot` (Graphviz) a imagen.
2. Arma una copia temporal combinada de los 3 `.md`, con esa imagen en vez
   del bloque ` ```mermaid ` dentro de `MVP_ARQUITECTURA_Y_TECNOLOGIAS.md`
   (el .md original no se toca — sigue teniendo el Mermaid real para que se
   vea en Obsidian/GitHub).
3. Compila esa copia a PDF con `pandoc` + `xelatex`.

### Si agregas un nuevo archivo .md al proyecto

Agrégalo a la lista `ARCHIVOS_MD` en `Documentacion_MVP_Latex/compilar_documentacion.py`,
en el orden en que debería aparecer en el PDF.

### Si el diagrama de arquitectura cambia

El Mermaid dentro de la sección 4 de `MVP_ARQUITECTURA_Y_TECNOLOGIAS.md` y
el Graphviz en `Documentacion_MVP_Latex/diagrama_arquitectura.dot` son dos fuentes separadas — no se
generan una de la otra. Si el flujo de la arquitectura cambia, hay que
actualizar las **dos** a mano para que el PDF no quede desincronizado del
diagrama que se ve en Obsidian/GitHub.

### Por qué Graphviz y no Mermaid para el PDF

La forma estándar de renderizar Mermaid a imagen es `mermaid-cli` via
`npx @mermaid-js/mermaid-cli`, pero eso descarga y ejecuta un paquete de
internet al vuelo — el sandbox de este entorno bloquea esa acción por
seguridad. Graphviz (`dot`) ya estaba instalado localmente en este equipo,
así que se usa esa ruta en su lugar. Si en una sesión futura `npx` deja de
estar bloqueado, se podría simplificar todo esto a un solo origen (el
Mermaid), pero mientras tanto hay que mantener los dos archivos sincronizados
a mano.

### Notas de la fuente/LaTeX (por si hay que tocar `Documentacion_MVP_Latex/pdf_header.tex`)

- El monofont es `DejaVu Sans Mono`, no Consolas ni Calibri: las fuentes
  comerciales de Microsoft traen bits de restricción de incrustación que
  hacen que `xdvipdfmx` marque el PDF resultante como "protegido" para
  lectores estrictos (aunque se abra sin pedir clave — se verificó que no
  hay ningún diccionario `/Encrypt` real en el archivo).
- Evitar spans de código inline (una sola palabra entre backticks) de más de
  ~45 caracteres sin espacios en los `.md` — LaTeX no les hace salto de
  línea y se salen del margen de la página. Si hace falta mostrar algo así,
  usar un bloque de código (```) en vez de código inline, o acortar la
  mención.
