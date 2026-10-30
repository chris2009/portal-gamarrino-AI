# E5 explicado — Portal Gamarrino AI (Equipo 7)

## 1. Requerimientos del E5

El E5 es la entrega del jueves 29-oct-2026 (Canvas, un solo envío por equipo). Pide completar una plantilla fija (pptx) con 4 secciones:

1. **Plan de evaluación** — explicar cómo se va a medir si el modelo funciona, antes de medirlo (qué métrica, con qué datos, qué otros métodos más simples se usan de comparación).
2. **Baseline contra modelo v0** — una tabla comparando el modelo real contra 3 formas más simples de hacer lo mismo, para demostrar que vale la pena la complejidad.
3. **Model Card v0** — una ficha técnica de una página: qué es el modelo, para qué sirve, para qué no, con qué datos se probó, qué limitaciones tiene.
4. **Registro de 3 riesgos** — 3 cosas que podrían salir mal, con su mitigación y una señal de alerta concreta.

Entrega: la plantilla llena, exportada a PDF, más un enlace a un repositorio con el código.

---

## 2. Pasos para completarlo

### Paso 1 — Piloto chico (42 consultas)
Se armó un primer pipeline con las 50 consultas reales que ya teníamos a mano (quedaron 42 después de limpiar vacías y duplicadas). Se corrieron 3 métodos simples sobre el catálogo de 438 tiendas: al azar, filtro por categoría, y búsqueda léxica (por palabras).

### Paso 2 — Intento de atajo con IA como juez (falló)
Para no etiquetar todo a mano, se probó que Claude (la IA) juzgara qué tienda era relevante para cada consulta, validando sus respuestas contra una muestra chica etiquetada por un humano. **No pasó la validación** (ver Kappa en el glosario): la IA y el humano solo coincidían en el nivel que exige la rúbrica el 51,5% de las veces, muy por debajo del 80% mínimo. Se descartó el atajo.

### Paso 3 — Etiquetado humano real, con problemas y correcciones
Se volvió al plan original: que personas reales etiquetaran. Pasó lo siguiente, en orden:
- Dos personas (Jhomar y Hugo) etiquetaron las 361 consultas-tienda de la muestra chica, cada uno por separado.
- El primer cálculo de acuerdo entre ellos salió mal por un error de formato (uno escribió "SÍ" con tilde, el sistema no lo reconocía) — se corrigió y se repitió el cálculo.
- El acuerdo bruto entre Jhomar y Hugo fue **86,7%**; el kappa de Cohen de esa misma comparación fue **0,629** (verificado cruzando `ground_truth_361_FINAL.xlsx` contra `desacuerdos_jhomar_vs_hugo.xlsx`: coinciden exacto, 48/48 filas en desacuerdo). El 0,629 queda por debajo del umbral de 0,80 de la rúbrica — esto confirmó que el problema no era la IA, sino que el criterio de "relevante" tiene ambigüedad real para ciertas consultas (estilos de moda, tallas, etc.).
- Se escribieron **10 reglas de etiquetado** (documento `CRITERIOS_ETIQUETADO.md`), basadas en los casos reales de desacuerdo, para que las 4 personas del equipo etiquetaran con el mismo criterio.

### Paso 4 — Escalamiento a la muestra real (378 consultas)
El plan pre-registrado del equipo pedía una muestra de 378 consultas (no 42), sacada con un método estadístico específico de un archivo de 4.000 consultas reales. Se generó esa muestra, y las 4 personas del equipo etiquetaron en rondas (con un primer intento que resultó no ser realmente independiente — se detectó y se corrigió repitiendo el etiquetado a ciegas de verdad). El acuerdo bruto final (reevaluación ciega real, confirmado corriendo `scripts/04_kappa_378_reevaluado.py`) dio **87,4%**; el kappa de Cohen de esa misma ronda — que descuenta lo que coincidiría solo por azar — dio **0,627**. El "62,7%" que esta sección mencionaba en versiones anteriores era en realidad el kappa, no el acuerdo bruto: son dos números distintos de la misma comparación, y hay que reportarlos por separado. El 0,627 queda por debajo del umbral de 0,80 que exige la rúbrica, consistente con el hallazgo anterior.

### Paso 5 — Modelo v0 real (embeddings)
Con la clave de OpenAI configurada, se generaron los vectores semánticos (ver "embeddings" en el glosario) del catálogo completo y de las 280 consultas distintas, y se calculó qué tiendas eran más parecidas en significado a cada consulta. El modelo propuso muchas tiendas nuevas que los métodos simples no habían tocado, así que se etiquetaron también esos pares nuevos, con un segundo acuerdo entre evaluadores mucho mejor (confirmado corriendo `scripts/08_kappa_nuevos_v0.py`): acuerdo bruto 93-94%, kappa de Cohen 0,86-0,88 — el "86-88%" mencionado en versiones anteriores era el kappa, no el acuerdo bruto. De cualquier forma, ambos números confirman que las coincidencias de este modelo son mucho más claras que en la muestra general.

### Paso 6 — Resultado final y análisis de errores
Con todo el etiquetado reconciliado, se calculó el resultado final de los 4 métodos, y se clasificaron las 280 consultas en 3 grupos (específica, ambigua, con marca/talla/precio) para ver en cuál falla más el modelo v0.

### Paso 7 — Armado del entregable
Se llenó la plantilla oficial (pptx) con todo el contenido, se creó un repositorio privado de GitHub con el código (excluyendo la clave de API y los datos de contacto reales de las tiendas, por la autorización académica firmada con Portal Gamarrino), y se dejó todo documentado.

---

## 3. Glosario

| Término | Qué significa |
|---|---|
| **Baseline** | Una forma simple de resolver el problema, usada como punto de comparación. Si el modelo "de verdad" no le gana al baseline, no vale la pena usarlo. |
| **Hit Rate@3** (o HR@3) | De todas las consultas probadas, en qué porcentaje al menos UNA de las 3 tiendas recomendadas era la correcta. Es la nota final del modelo. |
| **Léxico** | Búsqueda que compara palabras exactas (si la consulta dice "jean" busca tiendas que digan "jean" en su descripción). No entiende significado, solo coincidencia de texto. |
| **Embeddings** | Convertir un texto en una lista de números que representa su *significado*. Así, "ropa streetwear" y "moda urbana" pueden salir "parecidos" aunque no compartan ninguna palabra — a diferencia del léxico. |
| **Ground truth** | El "examen con respuestas correctas": las etiquetas Sí/No que dice un humano, contra las que se mide si el modelo acertó o no. |
| **Kappa de Cohen (κ)** | Mide si dos personas que etiquetaron por separado están de acuerdo, descontando lo que coincidirían solo por casualidad. No mide si el modelo funciona — mide si las etiquetas (el examen) son confiables. La rúbrica exige κ≥0,80. |
| **IC95% / intervalo de confianza** | Un rango que dice "el resultado real probablemente está entre estos dos números". Rangos angostos = medición confiable; rangos anchos = medición con mucha incertidumbre (normalmente porque la muestra es chica). |
| **pp (puntos porcentuales)** | La diferencia directa entre dos porcentajes. Si un método da 50% y otro 66%, la diferencia es "16 pp", no "16%" (eso evita confusión cuando se habla de porcentajes de porcentajes). |
| **Ponderado** | Pesar cada consulta según qué tan seguido la hacen los usuarios reales. Si "Vestidos" se pregunta mucho más que "ropa gótica", el resultado ponderado le da más peso a "Vestidos" — refleja mejor la experiencia real. |
| **Bootstrap** | Una técnica estadística que repite el cálculo miles de veces tomando muestras al azar de los mismos datos, para ver cuánto varía el resultado y así construir el intervalo de confianza. |
| **Muestreo sistemático con arranque al azar** | Forma de elegir una muestra: se calcula un intervalo fijo (por ejemplo, "cada 10 consultas") y se empieza a contar desde un punto al azar, tomando una de cada intervalo. Es reproducible (misma semilla = misma muestra) y representativo. |
| **Doble ciego** | Que dos personas etiqueten lo mismo sin ver la respuesta de la otra ni ninguna respuesta previa — así la comparación (el kappa) es real y no una copia. |
| **Desempate / reconciliación** | Cuando dos evaluadores no coinciden en una fila, una tercera persona decide con las reglas escritas, para cerrar esa fila del ground truth. |

---

## 4. Qué se obtuvo — interpretación de los resultados

### Tabla final (378 consultas, ponderado por frecuencia real)

| Método | Hit Rate@3 | Intervalo de confianza |
|---|---|---|
| No hacer nada (azar) | 23,0% | 18,8% – 27,5% |
| Lo que se hace hoy (filtro por categoría) | 46,8% | 41,8% – 51,6% |
| Modelo simple (léxico) | 52,9% | 48,2% – 57,7% |
| **Modelo v0 (embeddings) — el nuestro** | **66,9%** | **61,9% – 71,4%** |

**Lectura:** el modelo v0 le gana claramente a los otros tres. La diferencia con el segundo mejor (léxico, 52,9%) es de **14 puntos porcentuales**, y los intervalos de confianza no se tocan (61,9% vs. 57,7%) — eso quiere decir que la mejora es real, no es ruido de la muestra. Se justifica construir el prototipo con embeddings en vez de quedarse con un filtro simple.

### Dónde falla el modelo v0 (análisis por tipo de consulta)

| Tipo de consulta | n sin ponderar (de 280) | Hit Rate@3 | IC95% | Diferencia vs. el total* |
|---|---|---|---|---|
| Específica (una prenda clara, ej. "vestidos") | 150 | 79,6% | [74,6% – 84,6%] | +12,7 pp |
| Ambigua o compuesta (ej. "ropa de pinterest", "yk2") | 105 | 50,4% | [41,6% – 60,2%] | -16,5 pp |
| Con marca, talla o precio explícito | 25 | 20,0% | [4,0% – 36,0%] | -46,9 pp |

\* La "diferencia vs. el total" es un número puntual (resta simple entre dos porcentajes); no tiene su propio intervalo de confianza.

**Lectura:** el modelo funciona muy bien cuando el comprador nombra una prenda clara. Funciona peor en consultas vagas de estilo/tendencia (el catálogo no tiene esas etiquetas). Y funciona **mal** cuando el comprador pide una talla, un precio o una marca específica — eso es esperable: los embeddings entienden significado, no filtran datos exactos como un número de talla. Esa es la limitación más importante a declarar, y la base del riesgo #2 del registro. **Ojo con ese último segmento:** son solo 25 consultas (ponderado y sin ponderar coinciden — ninguna se repite en la muestra) y su intervalo de confianza es muy ancho, de 4,0% a 36,0% (32 puntos porcentuales de rango). El 20,0% es un indicio real, no una cifra firme — con una muestra tan chica el resultado real podría ser bastante distinto.

### Conclusión general
El experimento cumplió su propósito: demostró con evidencia (no con intuición) que vale la pena construir el prototipo con el motor semántico, identificó exactamente en qué tipo de consultas hay que reforzarlo (filtro estructurado para talla/precio/marca), y dejó un proceso de etiquetado y una metodología documentada y reproducible para cuando se repita con las 378 consultas definitivas de Portal Gamarrino.

---

## 5. Detalles metodológicos adicionales

### 5.1 Cómo se generó el documento de las 378 consultas, paso a paso

Script usado: `Muestra_378_Evaluacion/scripts/01_muestra_378.py`. Proceso exacto:

1. Se tomó el archivo de 4.000 consultas reales que ya teníamos, y se sacó una muestra de 378 con un método estadístico (muestreo sistemático con arranque al azar, semilla fija 42, reproducible).
2. De esas 378, quedaron 280 textos distintos (sin repetir).
3. Se cargó el catálogo de 438 tiendas.
4. Para cada una de las 280 consultas, se corrieron 3 métodos distintos — azar, filtro por categoría, búsqueda léxica — y cada uno, por su cuenta, eligió sus 3 tiendas top ("top-3") según su propio criterio (ver glosario: léxico y categoría comparan palabras; azar no compara nada).
5. Esos resultados se guardaron en un Excel (`candidatos_por_metodo_378.xlsx`): una fila por cada tienda que cada método propuso.
6. Se armó un segundo Excel, uniendo en una sola fila las tiendas que se repetían entre métodos (para no pedirle al equipo que etiquete la misma tienda dos veces), con una columna extra de referencia (`metodos_que_la_proponen`) que debía anotar qué método(s) la habían propuesto. Ese segundo archivo (`hoja_etiquetado_378.xlsx`) fue el que se repartió para etiquetar a mano.

La columna `metodos_que_la_proponen` era solo informativa para el equipo durante el etiquetado (se borró antes de etiquetar). El Hit Rate@3 de cada método (46,8% / 52,9% / 66,9%) se calculó directamente de `candidatos_por_metodo_378.xlsx` (el archivo con una fila por cada método, sin deduplicar) cruzado con las etiquetas humanas por consulta-tienda — no depende de esa columna.

### 5.2 Cómo se calcularon los intervalos de confianza (bootstrap)

Para cada método hay un array de aciertos: un 1 si esa consulta tuvo al menos una tienda relevante en el top-3, un 0 si no (378 valores en la versión ponderada). El proceso, llamado **bootstrap no paramétrico**:

1. De ese array, se saca una muestra al azar **del mismo tamaño**, pero **con reemplazo** (la misma consulta puede salir elegida más de una vez, o ninguna).
2. Se calcula el Hit Rate@3 de esa muestra simulada.
3. Se repite 1.000 veces → quedan 1.000 resultados distintos, todos plausibles dado lo observado.
4. El intervalo de confianza al 95% es: se corta el 2,5% más bajo y el 2,5% más alto de esos 1.000 resultados; lo que queda en el medio es el rango reportado.

Código exacto (semilla fija = 42, para que sea reproducible):
```python
rng = np.random.default_rng(42)
boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(1000)])
lo, hi = np.percentile(boot, [2.5, 97.5])
```

Es una técnica estándar para estimar incertidumbre sin asumir ninguna fórmula teórica — remuestrea los datos que ya se tienen muchas veces y mide cuánto varía el resultado.
