import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURACION FINAL ---
RAW_PATH = Path(r"escribe aqui tu ruta")
XJTU_PATH = RAW_PATH / "XJTU-SY"
FEMTO_PATH = RAW_PATH / "FEMTO"

PATTERN_FEMTO = re.compile(r"^acc_\d+\.csv$", re.IGNORECASE)
PATTERN_XJTU = re.compile(r"^\d+\.csv$", re.IGNORECASE)

CSV_SALIDA = RAW_PATH / "resumen_bearings.csv"
PNG_SALIDA = RAW_PATH / "resumen_bearings.png"

def formatear_hhmm(total_segundos):
    h = int(total_segundos // 3600)
    m = int((total_segundos % 3600) // 60)
    s = int(total_segundos % 60)
    hhmmss = f"{h:02d}:{m:02d}:{s:02d}"
    hhmm = f"{h:02d}:{m:02d}"
    return hhmmss, hhmm

def analizar_bearing(carpeta_bearing: Path, dataset_label: str, tipo: str):
    archivos = [f for f in carpeta_bearing.iterdir() if f.is_file()]
    archivos_csv = [f for f in archivos if f.suffix.lower() == ".csv"]
    cantidad = len(archivos_csv)
    if cantidad == 0:
        return None

    pattern = PATTERN_FEMTO if tipo == "FEMTO" else PATTERN_XJTU
    invalidos = [f.name for f in archivos_csv if not pattern.match(f.name)]
    if invalidos:
        print(f"[ADVERTENCIA] {carpeta_bearing.name}: {len(invalidos)} no cumplen patron {pattern.pattern}")

    total_segundos = cantidad * 10 if tipo == "FEMTO" else cantidad * 60
    hhmmss, hhmm = formatear_hhmm(total_segundos)
    
    print(f"[OK] {dataset_label} | {carpeta_bearing.name} -> {cantidad} csv -> {hhmm}")

    return {
        "Dataset": dataset_label,
        "Nombre de Bearing": carpeta_bearing.name,
        "Cantidad de archivos en bearing": cantidad,
        "Tiempo HH:MM:SS": hhmmss,
        "Tiempo HH:MM": hhmm,
        "Tiempo": hhmm,
    }

def main():
    print(f"RAW: {RAW_PATH}")
    print(f"Existe XJTU-SY? {XJTU_PATH.exists()} - {XJTU_PATH}")
    print(f"Existe FEMTO? {FEMTO_PATH.exists()} - {FEMTO_PATH}")

    if XJTU_PATH.exists():
        print("\nContenido XJTU-SY:")
        for d in XJTU_PATH.iterdir():
            if d.is_dir():
                print(f"  - {d.name}")
                for sd in d.iterdir():
                    if sd.is_dir():
                        print(f"      -> {sd.name}")

    resultados = []

    # FEMTO
    print("\n--- FEMTO ---")
    if FEMTO_PATH.exists():
        for bf in FEMTO_PATH.rglob("Bearing*"):
            if bf.is_dir():
                res = analizar_bearing(bf, "FEMTO", "FEMTO")
                if res: resultados.append(res)
        # fallback si no usa patron Bearing
        if not resultados:
            for bf in FEMTO_PATH.iterdir():
                if bf.is_dir():
                    res = analizar_bearing(bf, "FEMTO", "FEMTO")
                    if res: resultados.append(res)

    # XJTU-SY - RECURSIVO
    print("\n--- XJTU-SY ---")
    if XJTU_PATH.exists():
        bearings = list(XJTU_PATH.rglob("Bearing*")) + list(XJTU_PATH.rglob("bearing*"))
        bearings = list(set(bearings))
        print(f"Bearings encontrados: {len(bearings)}")
        for bf in bearings:
            if not bf.is_dir(): continue
            condicion = bf.parent.name  # 40Hz10kN, etc
            dataset_label = f"XJTU-SY / {condicion}"
            res = analizar_bearing(bf, dataset_label, "XJTU")
            if res: resultados.append(res)

    if not resultados:
        print("No se encontraron datos.")
        return

    df = pd.DataFrame(resultados)
    df = df.sort_values(by=["Dataset", "Nombre de Bearing"])
    df_export = df[["Dataset", "Nombre de Bearing", "Cantidad de archivos en bearing", "Tiempo HH:MM:SS", "Tiempo HH:MM", "Tiempo"]].copy()
    
    df_export.to_csv(CSV_SALIDA, index=False, encoding="utf-8-sig")
    print(f"\nCSV guardado: {CSV_SALIDA}")

    df_png = df_export[["Dataset", "Nombre de Bearing", "Cantidad de archivos en bearing", "Tiempo HH:MM"]]
    fig_h = max(6, len(df_png)*0.45 + 2)
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.axis('off')
    tabla = ax.table(cellText=df_png.values, colLabels=df_png.columns, loc='center', cellLoc='center')
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9)
    tabla.scale(1, 1.6)
    for j in range(len(df_png.columns)):
        tabla[0, j].set_facecolor("#2c3e50")
        tabla[0, j].set_text_props(color="white", weight="bold")
    
    plt.title(f"Resumen Bearings XJTU-SY + FEMTO - {len(df_png)} bearings - Tiempo HH:MM", fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(PNG_SALIDA, dpi=250, bbox_inches='tight')
    print(f"PNG guardado: {PNG_SALIDA}")
    print(df_export.to_string(index=False))

if __name__ == "__main__":
    main()
