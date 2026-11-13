# -*- coding: utf-8 -*-
"""
Descarga chroma_db/ (las 438 tiendas) desde un dataset PRIVADO de Hugging Face
mientras se construye la imagen del Space.

Por que: un Space publico deja descargar todos sus archivos desde la pestaña
"Files", aunque la app pida contraseña. chroma_db tiene los datos de las
tiendas de Portal Gamarrino (incluidos sus WhatsApp), asi que NO se sube al
Space: vive en el dataset privado y solo el build lo baja.

El token (de solo lectura) es el secret HF_TOKEN del Space. El Dockerfile lo
monta en /run/secrets/HF_TOKEN solo durante este paso; no queda en la imagen.
"""
import os
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download

REPO_CHROMA = "Chris1803/portal-gamarrino-chroma"
DESTINO = Path(__file__).resolve().parent.parent / "chroma_db"

archivo_token = Path("/run/secrets/HF_TOKEN")
token = archivo_token.read_text().strip() if archivo_token.exists() else os.environ.get("HF_TOKEN")

snapshot_download(
    repo_id=REPO_CHROMA,
    repo_type="dataset",
    local_dir=DESTINO,
    token=token,
    ignore_patterns=[".gitattributes", "README.md"],
)
shutil.rmtree(DESTINO / ".cache", ignore_errors=True)  # metadatos de la descarga, Chroma no los usa

if not (DESTINO / "chroma.sqlite3").exists():
    raise SystemExit(f"chroma_db incompleto: falta chroma.sqlite3 en {DESTINO}")
print(f"chroma_db descargado de {REPO_CHROMA}: {sorted(p.name for p in DESTINO.iterdir())}")
