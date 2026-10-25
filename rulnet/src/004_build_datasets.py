"""
SCRIPT: 004_build_datasets.py
QUE HACE: Crea splits train/val/test por BEARING (no por ventana) para evitar leakage, usando los indices livianos de 003
ENTRADAS:
- data/processed/003_build_windows.npz
SALIDAS / ARCHIVOS QUE CREA:
- data/processed/004_build_datasets.npz (indices de splits)
- logs/004_build_datasets.log
- docs/004_build_datasets.md
- results/004_build_datasets/reporte.txt
- results/004_build_datasets/distribucion_splits.png
REGLA v4.0: Split por bearing_id, tqdm, parents[1]
"""
from pathlib import Path
import numpy as np
import logging
from tqdm import tqdm
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
RESULTS_DIR = BASE_DIR / "results" / "004_build_datasets"

for d in [LOG_DIR, DOCS_DIR, RESULTS_DIR, PROC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

STEM = Path(__file__).stem
LOG_FILE = LOG_DIR / f"{STEM}.log"
MD_FILE = DOCS_DIR / f"{STEM}.md"
NPZ_FILE = PROC_DIR / f"{STEM}.npz"
REPORTE_FILE = RESULTS_DIR / "reporte.txt"
PLOT_FILE = RESULTS_DIR / "distribucion_splits.png"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s')

d = np.load(PROC_DIR / "003_build_windows.npz", allow_pickle=True)
bearing_id = d['bearing_id']
bearing_names = list(d['bearing_names'])
windows_idx = d['windows_idx']
y_windows = d['y_windows']

print(f"Cargado {len(windows_idx)} ventanas de {len(bearing_names)} bearings")

# SPLIT POR BEARING para no mezclar ventanas del mismo rodamiento
unique_bearings = np.unique(bearing_id)
print(f"Bearings unicos: {unique_bearings}")

# 70% train, 15% val, 15% test a nivel bearing
train_b, temp_b = train_test_split(unique_bearings, test_size=0.3, random_state=42)
val_b, test_b = train_test_split(temp_b, test_size=0.5, random_state=42)

print(f"Train bearings: {train_b} | Val: {val_b} | Test: {test_b}")

train_idx = []
val_idx = []
test_idx = []

# BARRITA OBLIGATORIA v4.0
for i in tqdm(range(len(windows_idx)), desc="Asignando splits"):
    bid = bearing_id[i]
    if bid in train_b:
        train_idx.append(i)
    elif bid in val_b:
        val_idx.append(i)
    else:
        test_idx.append(i)

train_idx = np.array(train_idx, dtype=np.int32)
val_idx = np.array(val_idx, dtype=np.int32)
test_idx = np.array(test_idx, dtype=np.int32)

np.savez_compressed(NPZ_FILE, train_idx=train_idx, val_idx=val_idx, test_idx=test_idx,
                    train_bearings=train_b, val_bearings=val_b, test_bearings=test_b,
                    bearing_names=np.array(bearing_names))

size_kb = NPZ_FILE.stat().st_size
print(f"OK -> {NPZ_FILE} {size_kb/1024:.1f} KB | train {len(train_idx)} val {len(val_idx)} test {len(test_idx)}")
logging.info(f"Guardado {len(train_idx)} {len(val_idx)} {len(test_idx)}")

# REPORTE EN RESULTS/004_build_datasets/
with open(REPORTE_FILE, 'w', encoding='utf-8') as f:
    f.write(f"REPORTE 004 SPLITS\n")
    f.write(f"Total {len(windows_idx)} ventanas\n")
    f.write(f"Train {len(train_idx)} ({len(train_idx)/len(windows_idx)*100:.1f}%) bearings {train_b}\n")
    f.write(f"Val {len(val_idx)} ({len(val_idx)/len(windows_idx)*100:.1f}%) bearings {val_b}\n")
    f.write(f"Test {len(test_idx)} ({len(test_idx)/len(windows_idx)*100:.1f}%) bearings {test_b}\n")
    f.write(f"Sin leakage: ningun bearing se repite entre splits\n")

try:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1,2, figsize=(10,4))
    ax[0].bar(['train','val','test'], [len(train_idx), len(val_idx), len(test_idx)])
    ax[0].set_title("Ventanas por split")
    ax[1].hist([y_windows[train_idx], y_windows[val_idx], y_windows[test_idx]], label=['train','val','test'], bins=30)
    ax[1].legend()
    ax[1].set_title("Distribucion RUL por split")
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=150)
    plt.close()
except Exception as e:
    print(f"No plot {e}")

MD_FILE.write_text(f"""# {STEM}

## Que hace
Split por bearing para evitar leakage. No mezcla ventanas del mismo rodamiento.

## Entradas
- 003_build_windows.npz {len(windows_idx)} ventanas

## Salidas
- {NPZ_FILE}
- {REPORTE_FILE}
- {PLOT_FILE}

Train {len(train_idx)} Val {len(val_idx)} Test {len(test_idx)}
""", encoding='utf-8')