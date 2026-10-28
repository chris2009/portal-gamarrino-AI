# Criterios de etiquetado — Equipo 7 (Portal Gamarrino AI)

Pregunta base para cada fila: **¿de verdad le serviría a un comprador real ir a esa tienda, aunque la consulta no use las mismas palabras?**

Estas reglas salen de los 48 desacuerdos reales que tuvimos entre Jhomar y Hugo en las 361 filas anteriores. Úsenlas los 4 de la misma forma — no importa si son estrictos o flexibles, lo que rompe el kappa es que cada quien use un criterio distinto.

---

### 1. Género no especificado en la consulta
Si la consulta no dice "para hombre" o "para mujer", y la tienda vende lo pedido aunque sea solo para un género → **Sí**.
*Ejemplo real: "Polos básicos" (sin género) → tienda de ropa casual y deportiva para mujer = Sí.*

### 2. Característica específica que la tienda no confirma
Si la consulta menciona un material, corte, estampado, talla o color concreto (cuero, cuadros, oversize, manga larga tres cuartos, bootcut...) y el nombre/categoría/subcategoría de la tienda **no lo menciona ni lo sugiere** → **No**. No asumir que una tienda genérica ("ropa casual para hombre") tiene esa prenda específica solo porque vende ropa en general.
*Ejemplos reales: "chaqueta de cuero hombre" → "Tienda de ropa casual para hombre" (no menciona cuero) = No. "Busco blusa de cuadros" → "Tienda de vestidos y tops para mujer" (no menciona cuadros) = No.*

### 3. Estilo o tendencia de moda
Si la consulta nombra un estilo (streetwear, yk2, gótico, vintage, old money, shoujo, alternativa) → cuenta **Sí** solo si el nombre, categoría o tags de la tienda mencionan ese estilo o un sinónimo claro. "Ropa urbana" o "ropa casual" sola **no basta** para streetwear/yk2.
*Ejemplo real: "ropa streetwear y yk2" → "Tienda de Ropa Urbana y Denim Streetwear" (dice "Streetwear" en el nombre) = Sí. → "Tienda de jeans y ropa casual para mujer" (no lo dice) = No.*

### 4. El comprador pide exactitud explícita
Si la consulta dice "exactamente X", "nada más que X", "no quiero ver opciones" → no cuentan tiendas genéricas de la misma categoría amplia que no confirman ese corte/modelo exacto.
*Ejemplo real: "no quiero ver opciones, quiero jean bootcut, exactamente jean bootcut" → "Tienda de jeans para mujer" (genérica, no dice bootcut) = No.*

### 5. El destinatario de la prenda debe coincidir
Si la consulta es para una persona adulta y la tienda es específicamente infantil (o viceversa), **no cuenta** aunque compartan palabras clave como "fiesta" o "bautizo".
*Ejemplo real: "vestido... para una madrina de bautizo" (adulta) → "Vestidos de Fiesta y Bautizo para Niña" = No, aunque comparte la palabra "bautizo".*

### 6. Ante la duda, No
Si después de aplicar las reglas 1-5 todavía hay duda razonable, se marca **No**. Es mejor subestimar relevancia que inflarla — así lo pide la rúbrica (el "Plan B honesto" penaliza inflar resultados, no ser estrictos).

### 7. Consulta sin ningún producto mencionado (solo género o edad)
Si la consulta es solo una palabra de género o edad ("Hombre", "Mujer", "niños") sin mencionar ninguna prenda o categoría → **No**. No hay información suficiente para decidir — esto es candidato a que el agente pregunte "¿qué tipo de ropa buscas?" en vez de adivinar (ver la idea de preguntas de aclaración ya anotada en el backlog).
*Ejemplo real: "Hombre" (sola, sin prenda) → cualquier tienda de ropa de hombre = No.*

### 8. Pide un servicio, no un producto
Si la consulta pide un servicio (sastre, modista, arreglos, lavandería) y la tienda solo vende prendas ya hechas sin confirmar que ofrece ese servicio → **No**.
*Ejemplo real: "Sastre para ternos" → "Tienda de ternos y trajes de vestir" (vende ternos hechos, no confirma servicio de sastrería) = No.*

### 9. Pide galerías o ubicaciones, no una tienda puntual
Si la consulta pregunta por galerías completas ("galerías de ropa para hombre") en vez de una prenda o tienda específica → **No**. El formato de top-3 tiendas no resuelve directamente esa necesidad; es una consulta fuera del alcance de este tipo de respuesta.
*Ejemplo real: "Galerías de ropa para hombre" → tiendas individuales de ropa de hombre = No (aunque vendan ropa de hombre, no responden "qué galerías").*

### 10. Réplicas, "exportación" u otra procedencia/calidad no confirmada
Si la consulta pide específicamente productos de réplica, de "exportación" u otra característica de procedencia/calidad, y la tienda no lo confirma en su nombre/categoría → **No**.
*Ejemplo real: "Polos réplica a1" → "Tienda de polos básicos y camiseros" (no confirma que venda réplicas de marca) = No.*
*Nota aparte: las solicitudes de réplicas de marca son además un tema ético/legal (propiedad intelectual) a anotar en el registro de riesgos del E5, no solo un tema de etiquetado.*

