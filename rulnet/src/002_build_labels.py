from pathlib import Path
import numpy as np
import logging

"""
SCRIPT: 002_build_labels.py
QUE HACE: Genera labels RUL lineal 1.0->0.0 por bearing a partir de boundaries de 001_build_input.npz
ENTRADAS:
- data/processed/001_build_input.npz
SALIDAS / ARCHIVOS QUE CREA:
- data/processed/002_build_labels.npz
- logs/002_build_labels.log
- docs/002_build_labels.md
- results/002_build_labels/rul_curve.png
REGLA v4.0: Solo lectura en processed/, trazabilidad liviana con boundaries, rutas con parents[1]
"""

# --- 1. RUTAS PORTABLES v4.0 ---
BASE_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
RESULTS_DIR = BASE_DIR / "results" / "002_build_labels"

STEM = Path(__file__).stem # 002_build_labels

LOG_FILE = LOG_DIR / f"{STEM}.log"
NPZ_FILE = PROC_DIR / f"{STEM}.npz"
MD_FILE = DOCS_DIR / f"{STEM}.md"
INPUT_NPZ = PROC_DIR / "001_build_input.npz"

PROC_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# --- 2. LOG CON HEADER OBLIGATORIO v4.0 PUNTO 5 ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

header = f"""# SCRIPT: {STEM}.py
# QUE HACE: genera labels RUL lineal 1.0->0.0 por bearing a partir de boundaries de 001
# ENTRADAS:
# - {INPUT_NPZ}
# SALIDAS / ARCHIVOS QUE CREA:
# - {NPZ_FILE}
# - {MD_FILE}
# - {RESULTS_DIR}/rul_curve.png
---
"""
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(header)

log.info(f"Iniciando {STEM}")
log.info(f"Entrada: {INPUT_NPZ}")

# --- 3. CORE ---
data = np.load(INPUT_NPZ, allow_pickle=True)
X_shape = data['X'].shape
bearing_names = list(data['bearing_names'])
boundaries = data['boundaries'].tolist()
total = X_shape[0]

log.info(f"Total muestras de 001: {total}, bearings: {bearing_names}")

y = np.zeros(total, dtype=np.float32)

for name, (start, end) in zip(bearing_names, boundaries):
    length = end - start
    # RUL lineal 1 -> 0
    rul = np.linspace(1.0, 0.0, length, dtype=np.float32)
    y[start:end] = rul
    log.info(f"{name}: [{start},{end}) len={length} rul {rul[0]:.4f}->{rul[-1]:.4f}")

# --- 4. GUARDAR EN PROCESSED (SOLO LECTURA, CONGELADO) v4.0 PUNTO 4 y 7 ---
np.savez_compressed(NPZ_FILE, y=y, bearing_names=np.array(bearing_names), boundaries=np.array(boundaries))
log.info(f"Guardado {NPZ_FILE} con y.shape={y.shape}")

# --- 5. GRAFICO EN results/002_build_labels/ ---
try:
    import matplotlib.pyplot as plt
    plt.figure()
    plt.plot(y)
    plt.title("RUL lineal concatenado - todos los bearings")
    plt.xlabel("muestra global")
    plt.ylabel("RUL")
    plt.savefig(RESULTS_DIR / "rul_curve.png")
    plt.close()
    log.info(f"Grafico guardado en {RESULTS_DIR / 'rul_curve.png'}")
except Exception as e:
    log.warning(f"No se pudo generar grafico: {e}")

# --- 6. MD AUTO-GENERADO v4.0 PUNTO 6 ---
md_content = f"""# {STEM}

## Que hace
Genera las labels de RUL para cada muestra de `001_build_input.npz`. RUL = 1.0 al inicio de cada bearing y 0.0 al final (falla), lineal.

## Por que lo hace asi
RUL lineal es baseline estandar en FEMTO. No usa tiempo real sino porcentaje de vida por bearing. Deterministico y reproducible, cumple trazabilidad liviana.

## Entradas
- {INPUT_NPZ}
    - X.shape={X_shape}
    - bearing_names={bearing_names}
    - boundaries={boundaries}

## Salidas
- {NPZ_FILE} con y.shape={y.shape}, bearing_names, boundaries
- {RESULTS_DIR}/rul_curve.png

## Explicacion del codigo en detalle paso a paso
1. Carga `001_build_input.npz` con boundaries.
2. Crea vector y de ceros de largo total={total}.
3. Por cada [start,end) en boundaries, genera `np.linspace(1,0,length)` y lo inserta en y[start:end].
4. Guarda npz comprimido en `processed/` (congelado, solo lectura).
5. Genera curva RUL en `results/002_build_labels/`.
6. Escribe log con header obligatorio y md.

## Resultados de esta ejecucion
- Total muestras: {total}
- Bearings: {len(bearing_names)}
- y min={y.min():.4f} max={y.max():.4f} mean={y.mean():.4f}
- Ejemplo Bearing1_1: y[0]=1.0, y[2802]=0.0 (si Bearing1_1 len=2803)
- Archivo congelado: {NPZ_FILE} - UNICO y de solo lectura, no se actualiza.
"""

MD_FILE.write_text(md_content, encoding='utf-8')
log.info(f"MD generado en {MD_FILE}")
log.info("FIN OK")
print(f"OK -> {NPZ_FILE}")