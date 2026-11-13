# -*- coding: utf-8 -*-
"""
Publica MVP_pruebas_reales/ en Hugging Face con un solo comando, sin copiar nada a mano.

Uso (desde la carpeta "Entregable 29-10"):

    MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --revisar
        Solo muestra qué cambiaría. No copia ni sube nada.

    MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py -m "qué cambió"
        Publica el código (agente + interfaz) y espera a que el Space quede en línea.

    MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --chroma -m "..."
        Además sube chroma_db (las tiendas) al dataset privado y reconstruye el Space.

    MVP_Portal_Gamarrino/.venv/Scripts/python.exe MVP_pruebas_reales/publicar.py --reconstruir
        No sube nada: reconstruye el Space desde cero (Factory rebuild) y espera. Sirve
        tras cambiar un secret que se usa al construir (HF_TOKEN). Tarda 4-5 min.

Qué hace, en orden (explicado en DESPLIEGUE.md, sección 4):
1. Trae agente.py y guardrails_mvp.py desde MVP_Portal_Gamarrino/src, que es donde se
   editan y se evalúan. Las copias de esta carpeta no se editan a mano.
2. Si el agente cambió respecto de lo publicado y VERSION_AGENTE (src/historial_db.py)
   sigue igual, se detiene: hay que subir la versión para distinguir en Supabase las
   respuestas de antes y de después del cambio.
3. Con --chroma: copia chroma_db del MVP y lo sube al dataset privado.
4. Sube esta carpeta al Space, sin .env, historial.db, chroma_db, __pycache__ ni este script.
5. Espera el build de Hugging Face y dice si quedó en línea; si falla, muestra el log.

Necesita la sesión de Hugging Face iniciada en la PC (se hace una sola vez):
    MVP_Portal_Gamarrino/.venv/Scripts/python.exe -m huggingface_hub.cli.hf auth login
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import time
from fnmatch import fnmatch
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

import requests
from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError

AQUI = Path(__file__).resolve().parent
MVP = AQUI.parent / "MVP_Portal_Gamarrino"
SPACE = "Chris1803/portal-gamarrino-ai"
DATASET = "Chris1803/portal-gamarrino-chroma"
URL_APP = "https://chris1803-portal-gamarrino-ai.hf.space"
ARCHIVOS_AGENTE = ["agente.py", "guardrails_mvp.py"]
NO_SUBIR = [".env", "historial.db", "chroma_db/*", "__pycache__/*", "*/__pycache__/*", "*.pyc", "publicar.py"]
ESTADOS_FINALES = {"RUNNING", "BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR", "NO_APP_FILE", "STOPPED", "PAUSED"}

api = HfApi()


def _version(texto: str) -> str:
    m = re.search(r'^VERSION_AGENTE = "([^"]+)"', texto, flags=re.M)
    return m.group(1) if m else "?"


def _publicado(ruta: str) -> bytes | None:
    """Contenido actual de un archivo en el Space (None si no existe)."""
    try:
        return Path(hf_hub_download(SPACE, ruta, repo_type="space")).read_bytes()
    except EntryNotFoundError:
        return None


def _archivos_locales() -> list[str]:
    rutas = (p.relative_to(AQUI).as_posix() for p in AQUI.rglob("*") if p.is_file())
    return sorted(r for r in rutas if not any(fnmatch(r, patron) for patron in NO_SUBIR))


def _logs(tipo: str, ultimas: int = 40, segundos: int = 20) -> str:
    lineas, fin = [], time.time() + segundos
    try:
        with requests.get(f"https://huggingface.co/api/spaces/{SPACE}/logs/{tipo}",
                          headers={"Authorization": f"Bearer {get_token()}"}, stream=True, timeout=segundos) as r:
            for raw in r.iter_lines(decode_unicode=True):
                if raw and raw.startswith("data:"):
                    try:
                        lineas.append(json.loads(raw[5:]).get("data", "").rstrip())
                    except ValueError:
                        lineas.append(raw[5:])
                if time.time() > fin:
                    break
    except requests.RequestException:
        pass  # el stream de logs queda abierto; se corta por tiempo
    return "\n".join(lineas[-ultimas:])


def paso1_traer_agente(revisar: bool) -> None:
    print(f"1. Agente: se trae desde {MVP.name}/src (ahí se edita y se evalúa)")
    for nombre in ARCHIVOS_AGENTE:
        origen, destino = MVP / "src" / nombre, AQUI / "src" / nombre
        if filecmp.cmp(origen, destino, shallow=False):
            print(f"   {nombre}: idéntico")
        elif revisar:
            print(f"   {nombre}: DISTINTO (se copiaría)")
        else:
            shutil.copy2(origen, destino)
            print(f"   {nombre}: copiado")


def paso2_revisar_version() -> None:
    print("2. Versión del agente")
    agente_cambio = any(_publicado(f"src/{n}") != (MVP / "src" / n).read_bytes() for n in ARCHIVOS_AGENTE)
    local = _version((AQUI / "src" / "historial_db.py").read_text(encoding="utf-8"))
    remoto_bytes = _publicado("src/historial_db.py")
    remoto = _version(remoto_bytes.decode("utf-8")) if remoto_bytes else "?"
    print(f"   publicada: {remoto} | local: {local} | el agente cambió respecto de lo publicado: "
          f"{'sí' if agente_cambio else 'no'}")
    if agente_cambio and local == remoto:
        sys.exit(f"   ALTO: el agente cambió y VERSION_AGENTE sigue en \"{local}\". Súbela en "
                 "MVP_pruebas_reales/src/historial_db.py (ej. v7.2) y vuelve a correr este script.")


def paso3_subir_chroma(revisar: bool) -> bool:
    print("3. chroma_db (tiendas) -> dataset privado")
    origen, destino = MVP / "chroma_db", AQUI / "chroma_db"
    if revisar:
        print(f"   se copiaría {origen} y se subiría a {DATASET}")
        return False
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino)
    antes = api.dataset_info(DATASET).sha
    api.upload_folder(repo_id=DATASET, repo_type="dataset", folder_path=destino,
                      delete_patterns=["*"],  # borra del dataset lo que ya no existe (.gitattributes se respeta)
                      commit_message="chroma_db actualizado desde MVP_Portal_Gamarrino")
    cambio = api.dataset_info(DATASET).sha != antes
    print(f"   {'subido' if cambio else 'sin cambios: el dataset ya tenía este chroma_db'}")
    return cambio


def paso4_subir_codigo(revisar: bool, mensaje: str) -> bool:
    print(f"4. Código -> Space {SPACE}")
    archivos = _archivos_locales()
    if revisar:
        distintos = [r for r in archivos if _publicado(r) != (AQUI / r).read_bytes()]
        print(f"   se subirían {len(distintos)} archivo(s) distinto(s): {distintos or 'ninguno'}")
        return False
    dockerfile = AQUI / "Dockerfile"
    if b"\r\n" in dockerfile.read_bytes():
        # git en Windows puede devolverlo con CRLF; los RUN los ejecuta Linux y el \r los rompe
        dockerfile.write_bytes(dockerfile.read_bytes().replace(b"\r\n", b"\n"))
        print("   Dockerfile pasado a finales de línea LF")
    antes = api.space_info(SPACE).sha
    api.upload_folder(repo_id=SPACE, repo_type="space", folder_path=AQUI,
                      ignore_patterns=NO_SUBIR, commit_message=mensaje)
    cambio = api.space_info(SPACE).sha != antes
    print(f"   {'subido' if cambio else 'sin cambios: el Space ya tenía este código'}")
    return cambio


def paso5_esperar_build() -> None:
    print("5. Build en Hugging Face (1-2 min; unos 4 si cambia requirements.txt)")
    t0 = time.time()
    while api.get_space_runtime(SPACE).stage == "RUNNING" and time.time() - t0 < 180:
        time.sleep(5)  # esperar a que Hugging Face tome el commit nuevo
    previo = None
    while time.time() - t0 < 45 * 60:
        estado = api.get_space_runtime(SPACE).stage
        if estado != previo:
            print(f"   [{int(time.time() - t0) // 60:02d} min] {estado}", flush=True)
            previo = estado
        if estado in ESTADOS_FINALES:
            break
        time.sleep(15)
    if previo == "RUNNING":
        salud = requests.get(f"{URL_APP}/_stcore/health", timeout=30)
        print(f"   En línea: {URL_APP} (health {salud.status_code} {salud.text.strip()})")
    else:
        tipo = "build" if previo == "BUILD_ERROR" else "run"
        print(f"   FALLÓ ({previo}). Final del log de {tipo}:\n{_logs(tipo)}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica MVP_pruebas_reales en Hugging Face.")
    parser.add_argument("--revisar", action="store_true", help="solo muestra qué cambiaría; no sube nada")
    parser.add_argument("--chroma", action="store_true", help="sube también chroma_db al dataset privado")
    parser.add_argument("-m", "--mensaje", default="Actualización desde publicar.py",
                        help="descripción del cambio (queda en el historial del Space)")
    parser.add_argument("--reconstruir", action="store_true",
                        help="no sube nada: reconstruye el Space desde cero (tras cambiar HF_TOKEN)")
    args = parser.parse_args()
    if not get_token():
        sys.exit("No hay sesión de Hugging Face. Corre una vez:\n"
                 "  MVP_Portal_Gamarrino/.venv/Scripts/python.exe -m huggingface_hub.cli.hf auth login")

    if args.reconstruir:
        # Reiniciar no basta: HF_TOKEN solo se usa al construir. Factory rebuild = build sin caché.
        api.restart_space(SPACE, factory_reboot=True)
        print("Factory rebuild lanzado (sin caché: 4-5 min)")
        paso5_esperar_build()
        return

    paso1_traer_agente(args.revisar)
    paso2_revisar_version()
    cambio_chroma = paso3_subir_chroma(args.revisar) if args.chroma else False
    cambio_codigo = paso4_subir_codigo(args.revisar, args.mensaje)
    if args.revisar:
        return
    if cambio_chroma and not cambio_codigo:
        # el código no cambió, así que no hay build automático: hay que reconstruir para bajar chroma_db
        api.restart_space(SPACE, factory_reboot=True)
    if cambio_chroma or cambio_codigo:
        paso5_esperar_build()
    else:
        print("Nada que publicar: el Space ya está al día.")


if __name__ == "__main__":
    main()
