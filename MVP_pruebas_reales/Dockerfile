# Imagen para Hugging Face Spaces (SDK "docker"). La construye Hugging Face en
# sus servidores al subir esta carpeta; no hace falta construirla en la PC.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Hugging Face corre el contenedor con el usuario 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    ANONYMIZED_TELEMETRY=False
WORKDIR /home/user/app

# torch solo-CPU primero (la versión de PyPI trae CUDA y pesa varios GB más).
RUN pip install --user --index-url https://download.pytorch.org/whl/cpu torch==2.15.0
COPY --chown=user requirements.txt .
RUN pip install --user -r requirements.txt
# openai 3.42.0, la del .venv evaluado. guardrails-ai y litellm declaran openai<3,
# así que pip avisa del conflicto pero instala (igual que en la PC, donde funciona).
RUN pip install --user openai==3.42.0
# Guardrails AI manda métricas de uso a un servidor suyo (nombre del validador y si
# pasó; no los mensajes). Con usuarios reales, apagadas. No cambia las respuestas.
RUN printf 'enable_metrics=false\n' > /home/user/.guardrailsrc

COPY --chown=user . .
# chroma_db no se sube al Space (es público): se baja de un dataset privado con
# el secret HF_TOKEN, que Docker monta solo durante este paso.
RUN --mount=type=secret,id=HF_TOKEN,mode=0444,required=true python src/descargar_chroma.py
# Descarga los modelos de los guardrails ahora, no cuando entra el primer usuario.
RUN python src/precargar_modelos.py

EXPOSE 8501
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
