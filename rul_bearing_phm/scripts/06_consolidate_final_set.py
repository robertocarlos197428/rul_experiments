# 06_consolidate_final_set.py
# Ruta de lectura : data/raw/FEMTO/** y data/interim/FEMTO/corrected_data/**
# Ruta de salida  : data/processed/FEMTO/**, experiments/exp006_..., results/exp006_...
# Ensambla el set final FEMTO en processed transfiriendo archivos INTEGROS
# (copia byte a byte verificada con sha256, sin tocar ni modificar contenido),
# con precedencia interim > raw y validacion en modo solo-lectura.
# Cierra la auditoria con manifest completed/failed.

import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# --- Rutas centralizadas -------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]

RAW_FEMTO       = BASE_DIR / "data" / "raw" / "FEMTO"
INTERIM_CORR    = BASE_DIR / "data" / "interim" / "FEMTO" / "corrected_data"
PROCESSED_FEMTO = BASE_DIR / "data" / "processed" / "FEMTO"

EXP_ID  = "exp006_consolidate_final_set"
EXP_DIR = BASE_DIR / "experiments" / EXP_ID
RES_DIR = BASE_DIR / "results" / EXP_ID
LOG_DIR = RES_DIR / "logs"
TAB_DIR = RES_DIR / "tables"

for carpeta in (PROCESSED_FEMTO, EXP_DIR, LOG_DIR, TAB_DIR):
    carpeta.mkdir(parents=True, exist_ok=True)

# --- Parámetros técnicos ---------------------------------------------------------
FS_HZ             = 25600.0  # frecuencia de muestreo
FILAS_POR_ARCHIVO = 2560     # 0.1 s por registro
# Etiquetas internas de trabajo (solo en memoria, nunca se escriben a disco):
COLUMNAS_INTERNAS = ["hour", "minute", "second", "microsecond",
                     "acc_horizontal", "acc_vertical"]

# --- Logging dual -----------------------------------------------------------------
logger = logging.getLogger(EXP_ID)
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
_h_consola = logging.StreamHandler(sys.stdout)
_h_consola.setFormatter(_fmt)
_h_archivo = logging.FileHandler(LOG_DIR / f"{EXP_ID}.log", encoding="utf-8")
_h_archivo.setFormatter(_fmt)
logger.addHandler(_h_consola)
logger.addHandler(_h_archivo)


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def detectar_delimitador(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        linea = f.readline()
    for sep in (",", ";", "\t"):
        if linea.count(sep) == len(COLUMNAS_INTERNAS) - 1:
            return sep
    if len(linea.split()) == len(COLUMNAS_INTERNAS):
        return r"\s+"
    raise ValueError(f"Delimitador no reconocido en {ruta.name}")


def validar_solo_lectura(ruta, t_prev_fin):
    """Checks de integridad sin escribir nada. Devuelve (errores, t_fin)."""
    errores = []
    sep = detectar_delimitador(ruta)
    engine = "python" if sep == r"\s+" else "c"
    df = pd.read_csv(ruta, sep=sep, header=None, names=COLUMNAS_INTERNAS, engine=engine)
    for col in COLUMNAS_INTERNAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if len(df) != FILAS_POR_ARCHIVO:
        errores.append(f"{ruta.name}: {len(df)} filas (esperadas {FILAS_POR_ARCHIVO})")
    if df.isnull().any().any():
        errores.append(f"{ruta.name}: nulos o valores no numéricos")
    t_abs = ((df["hour"] * 3600 + df["minute"] * 60 + df["second"]) * 1_000_000
             + df["microsecond"]).astype("int64")
    if len(df) > 1 and not (t_abs.diff().dropna() > 0).all():
        errores.append(f"{ruta.name}: timestamps no monótonos dentro del archivo")
    if t_prev_fin is not None and len(t_abs) > 0 and t_abs.iloc[0] <= t_prev_fin:
        errores.append(f"{ruta.name}: inicio no posterior al fin del archivo previo")
    t_fin = int(t_abs.iloc[-1]) if len(df) else None
    return errores, t_fin


def construir_lookup_interim():
    lookup = {}
    if INTERIM_CORR.exists():
        for ruta in INTERIM_CORR.rglob("*.csv"):
            partes = ruta.relative_to(INTERIM_CORR).parts
            if len(partes) == 3:
                lookup[(partes[0].lower(), partes[1].lower(), partes[2].lower())] = ruta
    return lookup


def volcar_yaml(datos, ruta):
    lineas = []
    for k, v in datos.items():
        if isinstance(v, (list, dict)):
            lineas.append(f"{k}: {json.dumps(v)}")
        elif isinstance(v, bool):
            lineas.append(f"{k}: {str(v).lower()}")
        else:
            lineas.append(f"{k}: {v}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    lookup = construir_lookup_interim()
    logger.info(f"Archivos corregidos detectados en interim: {len(lookup)}")

    resumen, archivos_manifest, descartados = [], [], []

    for set_dir in sorted([p for p in RAW_FEMTO.iterdir() if p.is_dir()]):
        for bearing_dir in sorted([p for p in set_dir.iterdir() if p.is_dir()]):
            archivos = sorted(bearing_dir.glob("acc_*.csv"))
            if not archivos:
                continue
            t_prev_fin = None
            for f in archivos:
                clave = (set_dir.name.lower(), bearing_dir.name.lower(), f.name.lower())
                origen = "interim" if clave in lookup else "raw"
                fuente = lookup.get(clave, f)
                if origen == "interim":
                    logger.info(f"  {bearing_dir.name}/{f.name}: usando versión corregida de interim")

                errores, t_fin = validar_solo_lectura(fuente, t_prev_fin)
                if errores:
                    for e in errores:
                        logger.warning(f"{set_dir.name}/{bearing_dir.name}: {e}")
                    descartados.append(f"{set_dir.name}/{bearing_dir.name}/{f.name}")
                    archivos_manifest.append({"set": set_dir.name, "rodamiento": bearing_dir.name,
                                              "archivo": f.name, "origen": origen,
                                              "sha256": None, "estado": "failed",
                                              "errores": errores})
                    resumen.append({"set": set_dir.name, "rodamiento": bearing_dir.name,
                                    "archivo": f.name, "origen": origen,
                                    "filas": None, "sha256": None, "estado": "failed"})
                    continue

                t_prev_fin = t_fin
                dest = PROCESSED_FEMTO / set_dir.name / bearing_dir.name / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fuente, dest)                      # transferencia íntegra
                hash_src, hash_dst = sha256(fuente), sha256(dest)
                if hash_src != hash_dst:
                    logger.error(f"{f.name}: hash no coincide tras la copia")
                    descartados.append(f"{set_dir.name}/{bearing_dir.name}/{f.name}")
                    estado = "failed"
                else:
                    estado = "completed"
                    logger.info(f"{set_dir.name}/{bearing_dir.name}/{f.name}: OK "
                                f"(origen={origen}, sha256={hash_src[:12]}...)")

                archivos_manifest.append({"set": set_dir.name, "rodamiento": bearing_dir.name,
                                          "archivo": f.name, "origen": origen,
                                          "sha256": hash_src, "estado": estado, "errores": []})
                resumen.append({"set": set_dir.name, "rodamiento": bearing_dir.name,
                                "archivo": f.name, "origen": origen,
                                "filas": FILAS_POR_ARCHIVO, "sha256": hash_src, "estado": estado})

    # --- Artefactos de gobernanza ----------------------------------------------------
    pd.DataFrame(resumen).to_csv(TAB_DIR / "consolidation_summary.csv", index=False)

    estado_global = "completed" if not descartados else "failed"
    n_interim = sum(1 for a in archivos_manifest if a["origen"] == "interim")

    volcar_yaml({
        "experimento": EXP_ID,
        "script": "06_consolidate_final_set.py",
        "regla_suprema": "los archivos solo se transfieren integros; nunca se modifican",
        "operacion": "copia_byte_a_byte_verificada_sha256",
        "fs_hz": FS_HZ,
        "filas_por_archivo": FILAS_POR_ARCHIVO,
        "columnas_internas_memoria": COLUMNAS_INTERNAS,
        "ruta_raw": str(RAW_FEMTO),
        "ruta_interim": str(INTERIM_CORR),
        "ruta_processed": str(PROCESSED_FEMTO),
        "modificacion_raw": False,
        "eliminacion_archivos": False,
    }, EXP_DIR / "config.yaml")

    (EXP_DIR / "notes.md").write_text(
        f"# notes.md — {EXP_ID}\n\n"
        f"Generado: {datetime.now().isoformat(timespec='seconds')}\n\n"
        "## Objetivo\nEnsamblar el set final FEMTO en data/processed mediante transferencia "
        "íntegra (interim > raw), cerrando la etapa de auditoría.\n\n"
        f"## Observaciones automáticas\n- Archivos procesados: {len(archivos_manifest)}\n"
        f"- Versiones corregidas usadas (interim): {n_interim}\n"
        f"- Descartados: {', '.join(descartados) if descartados else 'ninguno'}\n\n"
        "## Notas humanas\n(pendientes de revisión)\n",
        encoding="utf-8")

    manifest = {
        "experimento": EXP_ID,
        "estado": estado_global,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "inputs": {"raw": str(RAW_FEMTO), "interim": str(INTERIM_CORR)},
        "outputs": {"processed": str(PROCESSED_FEMTO),
                    "summary": str((TAB_DIR / "consolidation_summary.csv").relative_to(BASE_DIR))},
        "metricas": {"archivos_total": len(archivos_manifest),
                     "archivos_ok": len(archivos_manifest) - len(descartados),
                     "archivos_failed": len(descartados),
                     "versiones_interim_usadas": n_interim},
        "archivos": archivos_manifest,
        "archivos_descartados": descartados,
    }
    (EXP_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"Manifest generado. Estado global: {estado_global}")
    logger.info(f"EXP006 finalizado {'correctamente' if estado_global == 'completed' else 'con fallos'}.")
    return 0 if estado_global == "completed" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception(f"EXP006 falló: {e}")
        (EXP_DIR / "manifest.json").write_text(json.dumps(
            {"experimento": EXP_ID, "estado": "failed",
             "timestamp": datetime.now().isoformat(timespec="seconds"),
             "error": str(e)}, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(1)