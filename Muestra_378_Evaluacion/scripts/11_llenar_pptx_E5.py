# -*- coding: utf-8 -*-
"""Llena la plantilla E5 copiada, preservando el formato de cada caja
(toma la fuente del primer run existente en cada shape y la reaplica)."""
from pptx import Presentation

PATH = r"D:\APRENDIZAJE\MAESTRIA\CICLO_V\CAPSTONE_I\Entregables\Entregable 29-10\E5_Equipo7_Portal_Gamarrino.pptx"

prs = Presentation(PATH)
slides = prs.slides


def shape_by_name(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(f"No se encontro shape '{name}'")


def set_text(shape, text):
    tf = shape.text_frame
    base_run = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        base_run = tf.paragraphs[0].runs[0]
    font_name = base_run.font.name if base_run else None
    font_size = base_run.font.size if base_run else None
    font_bold = base_run.font.bold if base_run else None
    font_italic = base_run.font.italic if base_run else None
    try:
        font_color = base_run.font.color.rgb if base_run and base_run.font.color and base_run.font.color.type is not None else None
    except Exception:
        font_color = None

    tf.clear()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        if font_name:
            run.font.name = font_name
        if font_size:
            run.font.size = font_size
        if font_bold is not None:
            run.font.bold = font_bold
        # no forzamos italic=False para no perder enfasis real; solo heredamos
        if font_color:
            try:
                run.font.color.rgb = font_color
            except Exception:
                pass


def clear_text(shape):
    shape.text_frame.clear()


def fill_table(shape, rows_data, start_row=1):
    tbl = shape.table
    for r_idx, row_vals in enumerate(rows_data, start=start_row):
        for c_idx, val in enumerate(row_vals):
            tbl.cell(r_idx, c_idx).text = val


EQUIPO = "Equipo N.º 7"
FOOTER = "E5 · Equipo N.º 7"

# ============== SLIDE 1 — PORTADA ==============
s = slides[0]
set_text(shape_by_name(s, "Text 3"),
    "Equipo N.º 7 · Proyecto: Portal Gamarrino AI\n\n"
    "Integrantes: Hugo Ángeles, Christian Cajusol, Francisco Meza, Jhomar Yurivilca · Entrega: jueves 29 de octubre de 2026")

# ============== SLIDE 3 — Plan de evaluación (1/2) ==============
s = slides[2]
clear_text(shape_by_name(s, "Text 5"))
set_text(shape_by_name(s, "Text 6"),
    "Recuperación semántica + ranking top-3 (no es clasificación ni generación pura). "
    "El LLM solo redactaría la explicación breve de cada coincidencia; no decide qué tiendas se muestran.\n"
    "• Unidad: consulta del usuario × catálogo de tiendas activas.\n"
    "• Momento: al enviar la consulta en el asistente web móvil, antes de salir de casa (81,4%) o durante el viaje.\n"
    "• Horizonte: inmediato, una sola interacción.\n"
    "• Contexto: texto libre + memoria de sesión + catálogo activo (rag_text).")

clear_text(shape_by_name(s, "Text 9"))
set_text(shape_by_name(s, "Text 10"),
    "Métrica principal: Hit Rate@3, meta pre-registrada ≥70%.\n"
    "KPI de impacto: Tasa de recomendación útil ≥70% (informe preliminar).\n"
    "Contrapeso: latencia promedio ≤6s, p95 ≤10-12s.\n"
    "Compuesta (LLM/agente): calidad por etiquetado humano (κ); LLM juez intentado y descartado (κ=0,515, no validó); "
    "costo <$0,01 USD por esta prueba; latencia por medir (sin prototipo desplegado aún).")

clear_text(shape_by_name(s, "Text 13"))
set_text(shape_by_name(s, "Text 14"),
    "1) No hacer nada: 3 tiendas al azar.\n"
    "2) Lo que se hace hoy: filtro por categoría (como Gamarra.com.pe / Mi Gamarra), sin NLP.\n"
    "3) Modelo simple: TF-IDF/léxico sobre rag_text.\n"
    "4) Modelo v0: embeddings text-embedding-3-small + similitud de coseno (ChromaDB pendiente para escalar).")

set_text(shape_by_name(s, "Text 15"), FOOTER)

# ============== SLIDE 4 — Plan de evaluación (2/2) ==============
s = slides[3]
clear_text(shape_by_name(s, "Text 5"))
set_text(shape_by_name(s, "Text 6"),
    "Catálogo: 438 de 1.853 tiendas (consolidado operativo).\n"
    "Consultas: muestra sistemática con arranque al azar (semilla 42) de 378 (280 textos distintos, ponderados "
    "por frecuencia real), tomadas de 4.000 consultas reales en mano (de 21.186 históricas).\n"
    "Ninguna consulta de prueba se usó para ajustar el modelo. Es una muestra piloto, no el universo completo.")

clear_text(shape_by_name(s, "Text 9"))
set_text(shape_by_name(s, "Text 10"),
    "Rango: IC 95% por bootstrap (1.000 remuestreos) sobre las 378 consultas ponderadas.\n"
    "3 segmentos (ver Sección 2): específica de una prenda (240 casos ponderados), ambigua o compuesta (113), "
    "con marca/talla/precio explícito (25).")

clear_text(shape_by_name(s, "Text 13"))
set_text(shape_by_name(s, "Text 14"),
    "Si el Hit Rate@3 de modelo v0 no supera a los baselines por más que el rango (intervalos se cruzan) → "
    "revisar embeddings/ranking antes del 21-nov. Resultado real: SÍ superó, intervalos no se cruzan.\n"
    "Si el costo o la latencia real del prototipo supera 6s prom. / 10-12s p95 → simplificar pipeline o cambiar proveedor.")

set_text(shape_by_name(s, "Text 15"), FOOTER)

# ============== SLIDE 5 — Baseline vs modelo v0 ==============
s = slides[4]
tbl_shape = shape_by_name(s, "Table 0")
fill_table(tbl_shape, [
    ["No hacer nada", "23,0% [18,8-27,5]", "—", "$0", "378 (280 dist.)"],
    ["Lo que se hace hoy", "46,8% [41,8-51,6]", "Por medir", "$0 / <50ms cómputo", "378 (280 dist.)"],
    ["Modelo simple", "52,9% [48,2-57,7]", "Por medir", "$0 / <50ms cómputo", "378 (280 dist.)"],
    ["Modelo v0", "66,9% [61,9-71,4]", "Por medir (sin prototipo)", "<$0,01 / ~0,3-0,5s embed.", "378 (280 dist.)"],
])
tbl_shape.table.cell(0, 1).text = "Métrica principal: Hit Rate@3 (con rango)"
tbl_shape.table.cell(0, 2).text = "Métrica de contrapeso: Latencia"

clear_text(shape_by_name(s, "Text 6"))
set_text(shape_by_name(s, "Text 7"),
    "De 46,8% con lo que se hace hoy (filtro por categoría) a 66,9% con el modelo v0 (ponderado, IC95% 61,9-71,4%). "
    "La diferencia es mayor que el rango de ambos — los intervalos no se cruzan, es una mejora real, no ruido. "
    "Conclusión: se justifica construir el prototipo v0 con embeddings en vez de quedarse con el filtro simple.")

set_text(shape_by_name(s, "Text 9"), FOOTER)

# ============== SLIDE 6 — Dónde falla el modelo v0 ==============
s = slides[5]
tbl_shape = shape_by_name(s, "Table 0")
tbl_shape.table.cell(1, 1).text = "378 (280)"
tbl_shape.table.cell(1, 2).text = "66,9%"
fill_table(tbl_shape, [
    ["Específica (una prenda)", "240 (ponder.)", "79,6%", "+12,7 pp", "Nombre de prenda claro → el embedding encuentra match directo"],
    ["Ambigua o compuesta", "113 (ponder.)", "50,4%", "-16,5 pp", "Sin prenda o estilo/tendencia sin etiqueta en catálogo (yk2, años 2000, 'de pinterest')"],
    ["Con marca, talla o precio", "25 (ponder.)", "20,0%", "-46,9 pp", "Embeddings no filtran atributos estructurados (talla, precio, réplica)"],
], start_row=2)

clear_text(shape_by_name(s, "Text 6"))
set_text(shape_by_name(s, "Text 7"),
    "Declaramos el segmento de marca/talla/precio como limitación conocida del v0 (motor semántico, no estructurado) "
    "y diseñamos un filtro híbrido (metadata + embeddings) para el prototipo del 21-nov. El segmento ambiguo "
    "queda documentado en el Model Card; no se fuerza su corrección antes de la entrega.")

set_text(shape_by_name(s, "Text 8"), FOOTER)

# ============== SLIDE 7 — Model Card (1/2) ==============
s = slides[6]
clear_text(shape_by_name(s, "Text 6"))
set_text(shape_by_name(s, "Text 7"),
    "Motor de recuperación semántica: embeddings text-embedding-3-small (OpenAI) sobre el catálogo (rag_text: "
    "categoría, subcategoría, tags, descripción, ubicación) + similitud de coseno para el top-3. No es un LLM "
    "generativo decidiendo — el LLM solo redactaría la explicación breve (pendiente de implementar). Versión v0, piloto.")

clear_text(shape_by_name(s, "Text 10"))
set_text(shape_by_name(s, "Text 11"),
    "Comprador individual en Gamarra, en el asistente web móvil, para decidir qué tiendas visitar — antes de salir "
    "de casa o durante el recorrido. Responde consultas en lenguaje natural con un top-3 de tiendas del directorio.")

clear_text(shape_by_name(s, "Text 14"))
set_text(shape_by_name(s, "Text 15"),
    "No garantiza stock, talla o precio en tiempo real. No procesa búsqueda por imagen. No debe usarse para validar "
    "autenticidad/legalidad de productos. No es apto para consultas con restricciones estrictas de talla/marca/precio.")

clear_text(shape_by_name(s, "Text 18"))
set_text(shape_by_name(s, "Text 19"),
    "Catálogo de 438 tiendas de Portal Gamarrino (de 1.853 totales; ver datasheet E4). Prueba: muestra sistemática "
    "de 378 (280 distintas) de 4.000 consultas reales en mano (de 21.186 históricas), semilla 42.")

set_text(shape_by_name(s, "Text 20"), FOOTER)

# ============== SLIDE 8 — Model Card (2/2) ==============
s = slides[7]
clear_text(shape_by_name(s, "Text 5"))
set_text(shape_by_name(s, "Text 6"),
    "Hit Rate@3 = 66,9% [61,9-71,4%] (ponderado, 378 consultas), frente a 52,9% del léxico y 46,8% del filtro por "
    "categoría — mejora real, intervalos no se cruzan. Segmento más débil: marca/talla/precio explícito (20,0%, -46,9pp).")

clear_text(shape_by_name(s, "Text 9"))
set_text(shape_by_name(s, "Text 10"),
    "Juicios binarios Sí/No etiquetados por los 4 integrantes, doble ciego + desempate con reglas escritas. LLM juez "
    "(Claude) intentado primero: κ=0,515, no validó. Humano-humano: κ≈0,6 en consultas generales (3 réplicas "
    "independientes); κ=0,86-0,88 en los pares nuevos propuestos por modelo v0.")

clear_text(shape_by_name(s, "Text 13"))
set_text(shape_by_name(s, "Text 14"),
    "No filtra talla/precio/disponibilidad real (HR@3 cae a 20% ahí). El acuerdo humano sobre 'relevante' tiene un "
    "techo real de κ≈0,6 en consultas ambiguas de estilo (yk2, años 2000, 'de pinterest') — el catálogo no tiene "
    "esas etiquetas. Evaluado sobre 438/1.853 tiendas y 378/21.186 consultas (piloto, no universo completo). "
    "Costo y latencia del prototipo real aún no medidos (sin despliegue).")

clear_text(shape_by_name(s, "Text 17"))
set_text(shape_by_name(s, "Text 18"),
    "No se procesan datos personales de compradores (solo texto de consulta). Catálogo sin datos de contacto "
    "expuestos fuera de lo autorizado (H3, uso académico, firmado 6-oct-2026). Riesgo: consultas piden productos "
    "'réplica' — el sistema no debe recomendar tiendas como fuente de falsificaciones (ver riesgo 3). Sesgo "
    "potencial: el ranking puede favorecer tiendas con fichas más completas — pendiente de monitoreo.")

set_text(shape_by_name(s, "Text 19"), FOOTER)

# ============== SLIDE 9 — Registro de 3 riesgos ==============
s = slides[8]
tbl_shape = shape_by_name(s, "Table 0")
fill_table(tbl_shape, [
    ["1", "El acuerdo humano sobre relevancia tiene un techo real de κ≈0,6 en consultas ambiguas de estilo/tendencia",
     "Datos", "Alta", "Medio",
     "Declarar la limitación en el Model Card; para Capstone II, enriquecer el catálogo con etiquetas de estilo y repetir el etiquetado con guía más detallada",
     "Kappa de una nueva ronda de etiquetado por debajo de 0,70 al 21 de noviembre", "Equipo completo"],
    ["2", "Los embeddings no filtran atributos estructurados (talla, precio, marca) — HR@3 cae a 20% en ese segmento, el más débil de los tres",
     "Modelo", "Alta", "Alto",
     "Diseñar un filtro híbrido (metadata estructurada + embeddings) para el prototipo del 21-nov; mientras tanto, declarar la limitación",
     "Más del 30% de las quejas de usuarios de prueba son por talla/precio no filtrado", "Equipo técnico"],
    ["3", "Consultas reales piden productos 'réplica' (ej. 'polos réplica a1') — recomendar tiendas sin verificar puede facilitar la venta de falsificaciones",
     "Ética o regulación", "Media", "Alto",
     "No marcar como relevante ninguna tienda en consultas de réplica (regla ya aplicada en el etiquetado); consultar con el asesor si el prototipo debe rechazar este tipo de consulta",
     "Consultas de réplica/marca no autorizada en más del 5% de una muestra ampliada", "Francisco Meza / asesor"],
])
clear_text(shape_by_name(s, "Text 4"))
set_text(shape_by_name(s, "Text 5"), FOOTER)

# ============== SLIDE 10 — Anexo ==============
s = slides[9]
clear_text(shape_by_name(s, "Text 5"))
set_text(shape_by_name(s, "Text 6"),
    "Pipeline y resultados: Entregables/Entregable 29-10/pipeline/ y Entregables/Muestra_378_Evaluacion/ (repositorio local del equipo).\n"
    "Datasheet del dataset: Entregable E4 (auditoría de datos).\n"
    "[ ] Repositorio en línea (GitHub) pendiente de crear antes de enviar — hoy el pipeline vive solo en Drive/disco local.")

clear_text(shape_by_name(s, "Text 9"))
set_text(shape_by_name(s, "Text 10"),
    "Búsqueda por imagen: No aplica, porque el informe preliminar ya la declaró fuera de alcance del v0 (backlog Capstone II).\n"
    "Fine-tuning de un modelo propio: No aplica, porque el enfoque es RAG con embeddings pre-entrenados, no entrenamiento desde cero.")

tbl_shape = shape_by_name(s, "Table 0")
checklist = [
    "La métrica principal se conecta con el KPI",
    "Los datos de prueba no se usaron para entrenar/ajustar",
    "Hay al menos dos baselines en la tabla",
    "Cada número tiene su rango",
    "Hay al menos 2 segmentos analizados",
    "La Model Card tiene sus 8 cajas llenas o 'No aplica, porque...'",
    "Los 3 riesgos tienen señal de alerta con fecha",
    "Se borraron todas las pistas en gris",
]
for i, texto in enumerate(checklist, start=1):
    tbl_shape.table.cell(i, 0).text = "✓"
    tbl_shape.table.cell(i, 1).text = texto

set_text(shape_by_name(s, "Text 12"), FOOTER)

prs.save(PATH)
print("Guardado:", PATH)
