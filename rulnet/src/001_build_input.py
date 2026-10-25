# SCRIPT: 001_build_input.py
"""
Lee FEMTO plano (17 BearingX_Y) y crea:
- 001_build_input.npz [N][1][2560] crudo
- 001_build_input.log
- 001_build_input.md detallado
"""

from pathlib import Path
import logging
import numpy as np
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw" / "FEMTO"
PROC_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"

LOG_FILE = LOG_DIR / "001_build_input.log"
NPZ_FILE = PROC_DIR / "001_build_input.npz"
MD_FILE = DOCS_DIR / "001_build_input.md"

PROC_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)

# Header obligatorio log
with open(LOG_FILE, 'a', encoding='utf-8') as f:
    f.write("# SCRIPT: 001_build_input.py\n")
    f.write("# QUE HACE: Lee 17 Bearings FEMTO (6 cols, col5=H), apila [N][1][2560] crudo sin normalizar, guarda limites de indice por bearing para trazabilidad liviana, y genera md detallado.\n")
    f.write(f"# ENTRADAS:\n# - {RAW_DIR}\n")
    f.write(f"# SALIDAS / ARCHIVOS QUE CREA:\n# - {NPZ_FILE}\n# - {LOG_FILE}\n# - {MD_FILE}\n")
    f.write("---\n")

logging.info("INICIO 001_build_input.py")

if not RAW_DIR.exists():
    logging.error(f"No existe {RAW_DIR}")
    raise SystemExit(1)

bearing_dirs = sorted([d for d in RAW_DIR.iterdir() if d.is_dir() and d.name.startswith("Bearing")])
logging.info(f"Bearings encontrados: {len(bearing_dirs)}")

all_signals = []
index_map = {}
bearing_counts = {}
current_idx = 0

for bdir in bearing_dirs:
    acc_files = sorted(bdir.glob("acc_*.csv"))
    bearing_counts[bdir.name] = len(acc_files)
    start = current_idx
    logging.info(f"Procesando {bdir.name}: {len(acc_files)} archivos")
    
    for acc in acc_files:
        df = pd.read_csv(acc, header=None)
        # FEMTO fijo 6 columnas: [hora, min, seg, micro, H, V] -> H = indice 4
        if df.shape[1] != 6:
            logging.warning(f"{acc} no tiene 6 cols: {df.shape[1]}")
            continue
        h_acc = df.iloc[:, 4].values  # col5 H
        # auditados: todos 2560
        if len(h_acc) != 2560:
            logging.warning(f"{acc} len {len(h_acc)} != 2560")
            continue
        all_signals.append(h_acc)
        current_idx += 1
    
    end = current_idx
    index_map[bdir.name] = [start, end]
    logging.info(f"  -> {bdir.name}: [{start}, {end}) = {end-start}")

# Stack [N][1][2560] CRUDO sin normalizar
X = np.array(all_signals, dtype=np.float32)  # [N,2560]
X_final = X[:, np.newaxis, :]  # [N,1,2560]

logging.info(f"Shape final: {X_final.shape} min {X_final.min():.6f} max {X_final.max():.6f}")

# Validaciones
if np.isnan(X_final).any():
    raise ValueError("NaN detectado")
if X_final.shape[1] != 1 or X_final.shape[2] != 2560:
    raise ValueError(f"Contrato violado {X_final.shape}")

# Guardar NPZ con trazabilidad liviana
bearing_names = np.array(list(index_map.keys()))
boundaries = np.array(list(index_map.values()))
np.savez_compressed(NPZ_FILE, X=X_final, bearing_names=bearing_names, boundaries=boundaries, counts=np.array(list(bearing_counts.values())))
logging.info(f"Guardado NPZ OK: {NPZ_FILE} N={X_final.shape[0]}")

# Generar MD detallado obligatorio
md_content = f"""# 001 - Build Input FEMTO

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Script:** `src/input_builder/001_build_input.py`

## Que hace
Lee los 17 Bearings planos de `data/raw/FEMTO/` (ya auditados, todos 2560 muestras) y crea un tensor congelado `[N][1][2560]` en crudo (g) sin normalizar.

## Por que no normaliza
- Si normaliza aqui, congela el factor de FEMTO y al cambiar de sensor (ULM u otro) hay que rehacer todo.
- La amplitud en g es indicador de falla. Normalizar global a -1/1 destruye severidad.
- La normalizacion se delega a `src/core/normalizer.py` con modo configurable (none, zscore global sana, etc) entrenado solo con train.

## Entradas
- `data/raw/FEMTO/BearingX_Y/acc_*.csv`
- Formato fijo: 6 columnas [hora, min, seg, microsec, H, V]
- Se usa solo columna 5 H (indice 4) -> contrato [N][1][2560]
- Todos los archivos ya auditados: 2560 muestras. Solo varia cantidad por bearing porque fallan en tiempos distintos.

## Salidas
- `{NPZ_FILE}` con:
  - `X`: float32 [N,1,2560] crudo
  - `bearing_names`: array ["Bearing1_1"...]
  - `boundaries`: array [[0,2802], [2803,3673]...] -> trazabilidad liviana
  - `counts`: cantidad por bearing
- `{LOG_FILE}`
- `{MD_FILE}` (este archivo)

## Trazabilidad sin lista de 40k
No se guarda lista de 40k strings `Bearing1_1/acc_00001.csv`. Eso pesa y no sirve.
Se guarda limites de indice:
```
Bearing1_1: [0, 2802) -> 2802 muestras
Bearing1_2: [2803, 3673) -> 870 muestras
...
```
Para debuggear muestra N, buscar en que intervalo cae. Es liviano (17x2 ints).

## Codigo en detalle
1. Busca 17 carpetas `Bearing*` en RAW_DIR
2. Por cada bearing, lista `acc_*.csv` ordenados temporalmente
3. Lee cada csv sin header, valida 6 cols, toma iloc[:,4] (H)
4. Valida 2560 muestras, apila en lista
5. Guarda start/end antes y despues de cada bearing para index_map
6. Stack a [N,1,2560], valida NaN y forma
7. Guarda NPZ comprimido
8. Genera este MD

## Contrato
- Entrada TCN: [N][1][2560]
- No normalizado
- Trazable por boundaries
"""

with open(MD_FILE, 'w', encoding='utf-8') as md:
    md.write(md_content)

# Agregar trazabilidad al MD
with open(MD_FILE, 'a', encoding='utf-8') as md:
    md.write("\n## Resultados de esta ejecucion\n")
    for name, (s,e) in index_map.items():
        md.write(f"- {name}: [{s}, {e}) -> {e-s}\n")
    md.write(f"\n- Total N={X_final.shape[0]}\n")
    md.write(f"- Rango crudo: min {X_final.min():.6f} max {X_final.max():.6f} mean {X_final.mean():.6f}\n")

logging.info(f"MD generado: {MD_FILE}")
logging.info("FIN OK - 001 crudo + trazabilidad liviana + md")