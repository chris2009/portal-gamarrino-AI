# Construye el catálogo operativo de 438 tiendas a partir de los archivos de Portal Gamarrino
# (565 filas) y del scraping de Google Maps, y deja el conteo de cada paso en la hoja «resumen».
# Los archivos de entrada tienen datos de contacto y son privados (autorización solo académica):
# no están en este repositorio. El resultado público es MVP_Portal_Gamarrino/datos/catalogo_sin_contacto.csv.
# Se ejecuta desde la carpeta que contiene «Entregables/Base de Datos - Portal Gamarrino».

import re
import unicodedata
from pathlib import Path

import pandas as pd


BASE = Path("Entregables/Base de Datos - Portal Gamarrino")
OUT = BASE / "Catalogo Consolidado MVP"
PORTAL_FILE = BASE / "Tiendas-60_con_telefonos.xlsx"
MAPS_FILE = BASE / "gamarra.csv"


def present(value):
    return pd.notna(value) and str(value).strip() not in {"", "nan", "None"}


def normalize(value):
    if not present(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def phone_digits(value):
    if not present(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\D", "", str(value))


def extract(pattern, text):
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip(" .,-\"") if match else ""


def usable_commercial_name(value):
    """Reject address-like Google labels that are not credible business names."""
    if not present(value):
        return False
    text = normalize(value)
    return not re.match(r"^(piso|tienda|stand|local|interior|int)\b", text)


def extract_gallery(address):
    patterns = [
        r"(?:galer[ií]a|gal\.?|centro comercial|c\.?c\.?)\s*[\"']?([^,;]+)",
    ]
    for pattern in patterns:
        value = extract(pattern, address)
        if value:
            value = re.split(r"\b(?:piso|nivel|tda|tienda|stand|int\.?|interior)\b", value, flags=re.I)[0]
            return value.strip(" .,-\"")
    return ""


def extract_floor(address):
    patterns = [
        r"(?:piso|nivel)\s*[:#nro\.º°-]*\s*([a-z0-9]+)",
        r"\b(primer|segundo|tercer|cuarto|quinto|sexto|septimo|octavo|noveno|decimo)\s+piso\b",
        r"\b([1-9]|10)(?:ro|do|er|to|mo|vo|no)?\s+piso\b",
        r"\b(semis[oó]tano|s[oó]tano)\b",
    ]
    for pattern in patterns:
        value = extract(pattern, address)
        if value:
            return value
    return ""


def extract_stand(address):
    patterns = [
        r"(?:stand|tda\.?|tienda|local|int\.?|interior)\s*[:#nro\.º°-]*\s*([a-z0-9-]+)",
    ]
    for pattern in patterns:
        value = extract(pattern, address)
        if value:
            return value
    return ""


def location_match(portal_row, maps_row):
    gallery = normalize(portal_row["gallery"])
    floor = normalize(portal_row["floor"])
    stand = normalize(portal_row["stand"])
    parsed_gallery = maps_row["gallery_norm"]
    parsed_floor = normalize(maps_row["floor_parsed"])
    parsed_stand = normalize(maps_row["stand_parsed"])

    gallery_core = re.sub(r"\b(galeria|centro comercial|cc|c c)\b", " ", gallery)
    gallery_core = re.sub(r"\s+", " ", gallery_core).strip()
    parsed_gallery_core = re.sub(r"\b(galeria|centro comercial|cc|c c)\b", " ", parsed_gallery)
    parsed_gallery_core = re.sub(r"\s+", " ", parsed_gallery_core).strip()
    gallery_ok = bool(gallery_core and parsed_gallery_core) and (
        gallery_core == parsed_gallery_core
        or gallery_core in parsed_gallery_core
        or parsed_gallery_core in gallery_core
    )
    floor_ok = bool(floor) and floor == parsed_floor
    stand_ok = bool(stand) and stand == parsed_stand
    return gallery_ok, floor_ok, stand_ok


OUT.mkdir(parents=True, exist_ok=True)


def writable_output(filename):
    """Use an _actualizado copy when Windows has the workbook open."""
    path = OUT / filename
    if path.exists():
        try:
            with path.open("rb+"):
                pass
        except PermissionError:
            return path.with_name(f"{path.stem}_actualizado{path.suffix}")
    return path


portal = pd.read_excel(PORTAL_FILE, sheet_name="Tiendas")
maps = pd.read_csv(MAPS_FILE, dtype=str)

required_location = ["name", "gallery", "floor", "stand"]
portal["location_complete"] = portal[required_location].apply(
    lambda row: all(present(v) for v in row), axis=1
)
portal["semantic_complete"] = portal[["name", "categories", "subcategory", "tags", "description"]].apply(
    lambda row: all(present(v) for v in row), axis=1
)
portal["phone"] = portal["whatsapp"].map(phone_digits)
portal["whatsapp_available"] = portal["phone"].str.len().eq(9) & portal["phone"].str.startswith("9")
portal["source"] = "portal_gamarrino"
portal["portal_name"] = portal["name"]
portal["store_id"] = portal["id"]

base = portal.loc[portal["location_complete"]].copy()
base_columns = [
    "store_id", "portal_name", "categories", "subcategory", "tags", "description",
    "gallery", "floor", "aisle", "stand", "address", "phone", "whatsapp",
    "whatsapp_available", "portal_url", "google_maps_url", "is_active", "source",
    "location_complete", "semantic_complete",
]
base = base[base_columns]

maps["phone"] = maps["telefono"].map(phone_digits)
maps["address_raw"] = maps["direccion"].fillna("")
maps["address_norm"] = maps["address_raw"].map(normalize)
maps["commercial_name"] = maps["nombre"]
maps["google_category"] = maps["categoria"]
maps["gallery_parsed"] = maps["address_raw"].map(extract_gallery)
maps["floor_parsed"] = maps["address_raw"].map(extract_floor)
maps["stand_parsed"] = maps["address_raw"].map(extract_stand)
maps["gallery_norm"] = maps["gallery_parsed"].map(normalize)
maps["parse_status"] = maps[["gallery_parsed", "floor_parsed", "stand_parsed"]].apply(
    lambda row: "parsed_complete" if all(present(v) for v in row) else "parsed_partial", axis=1
)
maps["source"] = "google_maps"
maps_normalized = maps[[
    "place_id", "commercial_name", "google_category", "phone", "address_raw",
    "latitud", "longitud", "gallery_parsed", "floor_parsed", "stand_parsed",
    "parse_status", "source",
]].copy()

phone_to_maps = {}
for idx, value in maps["phone"].items():
    if value:
        phone_to_maps.setdefault(value, []).append(idx)

match_rows = []
selected_match = {}
for pidx, prow in base.iterrows():
    candidates = []
    phone = phone_digits(prow["phone"])
    for midx in phone_to_maps.get(phone, []):
        candidates.append((midx, "exact_phone", 100))

    location_candidates = []
    for midx, mrow in maps.iterrows():
        gallery_ok, floor_ok, stand_ok = location_match(prow, mrow)
        if gallery_ok and floor_ok and stand_ok:
            location_candidates.append((midx, "gallery_floor_stand", 95))

    # Location is the primary identity signal. A phone-only coincidence is
    # retained for review but never enriches a record automatically.
    if location_candidates:
        candidates = location_candidates

    unique_candidates = {midx: (method, score) for midx, method, score in candidates}
    decision = "no_match"
    chosen = None
    if len(unique_candidates) == 1:
        chosen, (method, score) = next(iter(unique_candidates.items()))
        if method == "gallery_floor_stand":
            decision = "auto_high_confidence"
            selected_match[pidx] = (chosen, method)
        else:
            decision = "manual_review_phone_only"
    elif len(unique_candidates) > 1:
        decision = "manual_review_multiple"

    if unique_candidates:
        for midx, (method, score) in unique_candidates.items():
            mrow = maps.loc[midx]
            match_rows.append({
                "store_id": prow["store_id"],
                "portal_name": prow["portal_name"],
                "portal_gallery": prow["gallery"],
                "portal_floor": prow["floor"],
                "portal_stand": prow["stand"],
                "place_id": mrow["place_id"],
                "commercial_name": mrow["commercial_name"],
                "google_category": mrow["google_category"],
                "google_phone": mrow["phone"],
                "google_address": mrow["address_raw"],
                "match_method": method,
                "match_score": score,
                "decision": decision,
            })
    else:
        match_rows.append({
            "store_id": prow["store_id"],
            "portal_name": prow["portal_name"],
            "portal_gallery": prow["gallery"],
            "portal_floor": prow["floor"],
            "portal_stand": prow["stand"],
            "place_id": "",
            "commercial_name": "",
            "google_category": "",
            "google_phone": "",
            "google_address": "",
            "match_method": "",
            "match_score": 0,
            "decision": "no_match",
        })

matches = pd.DataFrame(match_rows)
consolidated = base.copy()
consolidated["commercial_name"] = ""
consolidated["place_id"] = ""
consolidated["latitude"] = ""
consolidated["longitude"] = ""
consolidated["match_method"] = ""
consolidated["match_confidence"] = "none"
consolidated["enrichment_status"] = "not_enriched"
consolidated["phone_source"] = consolidated["phone"].map(lambda v: "portal_gamarrino" if present(v) else "")

for pidx, (midx, selected_method) in selected_match.items():
    mrow = maps.loc[midx]
    if usable_commercial_name(mrow["commercial_name"]):
        consolidated.at[pidx, "commercial_name"] = mrow["commercial_name"]
    consolidated.at[pidx, "place_id"] = mrow["place_id"]
    consolidated.at[pidx, "latitude"] = mrow["latitud"]
    consolidated.at[pidx, "longitude"] = mrow["longitud"]
    consolidated.at[pidx, "match_method"] = selected_method
    consolidated.at[pidx, "match_confidence"] = "high"
    consolidated.at[pidx, "enrichment_status"] = "auto_high_confidence"
    if not present(consolidated.at[pidx, "phone"]) and present(mrow["phone"]):
        consolidated.at[pidx, "phone"] = mrow["phone"]
        consolidated.at[pidx, "phone_source"] = "google_maps"

consolidated["display_name"] = consolidated.apply(
    lambda row: row["commercial_name"] if present(row["commercial_name"]) else row["portal_name"], axis=1
)
consolidated["rag_text"] = consolidated.apply(
    lambda row: (
        f"Nombre comercial: {row['commercial_name']}. " if present(row["commercial_name"]) else ""
    ) + (
        f"Oferta: {row['portal_name']}. Categoría: {row['categories']}. "
        f"Subcategoría: {row['subcategory']}. Etiquetas: {row['tags']}. "
        f"Descripción: {row['description']}. Ubicación: {row['gallery']}, "
        f"piso {row['floor']}, stand {row['stand']}."
    ), axis=1
)

# Put user-facing identity fields first so they are visible when opening Excel.
priority_columns = [
    "store_id", "display_name", "commercial_name", "portal_name", "categories",
    "subcategory", "tags", "description", "gallery", "floor", "aisle", "stand",
    "address", "phone", "phone_source", "whatsapp", "whatsapp_available",
    "portal_url", "google_maps_url", "place_id", "latitude", "longitude",
    "match_method", "match_confidence", "enrichment_status", "source",
    "is_active", "location_complete", "semantic_complete", "rag_text",
]
consolidated = consolidated[priority_columns]

summary = pd.DataFrame([
    {"metric": "Portal rows", "value": len(portal)},
    {"metric": "Portal location-complete rows", "value": len(base)},
    {"metric": "Google Maps rows", "value": len(maps)},
    {"metric": "Google parsed-complete rows", "value": int(maps["parse_status"].eq("parsed_complete").sum())},
    {"metric": "Automatic high-confidence matches", "value": len(selected_match)},
    {"metric": "Consolidated MVP rows", "value": len(consolidated)},
    {"metric": "Consolidated rows with phone", "value": int(consolidated["phone"].map(present).sum())},
])

with pd.ExcelWriter(writable_output("catalogo_portal_438_ubicacion_completa.xlsx"), engine="openpyxl") as writer:
    base.to_excel(writer, index=False, sheet_name="catalogo_438")
    summary.to_excel(writer, index=False, sheet_name="resumen")

with pd.ExcelWriter(writable_output("google_maps_normalizado.xlsx"), engine="openpyxl") as writer:
    maps_normalized.to_excel(writer, index=False, sheet_name="google_maps")
    summary.to_excel(writer, index=False, sheet_name="resumen")

with pd.ExcelWriter(writable_output("reporte_emparejamiento_portal_googlemaps.xlsx"), engine="openpyxl") as writer:
    matches.to_excel(writer, index=False, sheet_name="emparejamiento")
    summary.to_excel(writer, index=False, sheet_name="resumen")

consolidated_output = writable_output("catalogo_consolidado_mvp.xlsx")
with pd.ExcelWriter(consolidated_output, engine="openpyxl") as writer:
    consolidated.to_excel(writer, index=False, sheet_name="catalogo_mvp")
    summary.to_excel(writer, index=False, sheet_name="resumen")
    sheet = writer.book["catalogo_mvp"]
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 38
    sheet.column_dimensions["B"].width = 34
    sheet.column_dimensions["C"].width = 28
    sheet.column_dimensions["D"].width = 48

print(summary.to_string(index=False))
print(f"Consolidated output: {consolidated_output}")
