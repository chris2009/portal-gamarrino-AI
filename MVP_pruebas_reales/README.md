---
title: Portal Gamarrino AI
emoji: 🛍️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
short_description: Te recomienda 3 tiendas de Gamarra para lo que buscas
---

# Portal Gamarrino AI — pruebas con usuarios reales

Asistente que recomienda 3 tiendas del Emporio Comercial de Gamarra (Lima) para la prenda que
busca el comprador, con su galería, piso, stand y WhatsApp. Proyecto de capstone de la Maestría
en Ciencia de Datos e IA de UTEC (Equipo 7).

Esta carpeta es la versión publicada en Hugging Face Spaces para que la usen compradores reales.
El agente es el mismo que se evaluó frente al buscador de E5 (67,5 % de Hit Rate@3 con juez LLM):
`src/agente.py` y `src/guardrails_mvp.py` son copias idénticas de `MVP_Portal_Gamarrino/src/`.
En el registro las respuestas quedan como `v7.3`: v7 más cuatro correcciones encontradas con
probadores (feedback solo bajo respuestas con tiendas, rechazo de réplicas, enlaces de mapa con
La Victoria, Lima, sin frases de relleno al cierre); el 67,5 % no cambia.

- App: https://chris1803-portal-gamarrino-ai.hf.space (pide contraseña)
- Conversaciones y votos: Supabase · Trazas: LangSmith · Tiendas (`chroma_db`): dataset privado

**Todo el despliegue (qué hay, qué ejecuta Hugging Face, cómo publicar cambios, secretos,
problemas resueltos, costos): [DESPLIEGUE.md](DESPLIEGUE.md).**

Publicar un cambio, desde la carpeta `Entregable 29-10`:

```bash
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --revisar   # qué cambiaría
MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py -m "qué cambió"
```

El agente se edita solo en `MVP_Portal_Gamarrino/src/` (ahí se evalúa); `publicar.py` lo trae.
