from pathlib import Path
import numpy as np
import logging
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
RESULTS_DIR = BASE_DIR / "results" / "003_build_windows"
for d in [LOG_DIR, DOCS_DIR, RESULTS_DIR]: d.mkdir(parents=True, exist_ok=True)

NPZ_FILE = PROC_DIR / "003_build_windows.npz"

d1 = np.load(PROC_DIR / "001_build_input.npz", allow_pickle=True)
d2 = np.load(PROC_DIR / "002_build_labels.npz", allow_pickle=True)
boundaries = d1['boundaries'].tolist()
bearing_names = list(d1['bearing_names'])
y_global = d2['y']

print(f"Generando indices para {len(boundaries)} bearings...")

windows_idx = []
bearing_id = []
y_windows = []

# UNA SOLA BARRITA
pbar = tqdm(total=len(boundaries), desc="Bearings")
for b_idx, (start, end) in enumerate(boundaries):
    length = end - start
    if length < 30:
        pbar.update(1)
        continue
    starts = np.arange(start, end - 30 + 1, 1)
    ends = starts + 30
    windows_idx.extend(np.stack([starts, ends], axis=1).tolist())
    bearing_id.extend([b_idx]*len(starts))
    y_windows.extend(y_global[ends-1].tolist())
    pbar.update(1)
pbar.close()

windows_idx = np.array(windows_idx, dtype=np.int32)
bearing_id = np.array(bearing_id, dtype=np.int16)
y_windows = np.array(y_windows, dtype=np.float32)

np.savez_compressed(NPZ_FILE, windows_idx=windows_idx, bearing_id=bearing_id, y_windows=y_windows,
                    window_size=np.array(30), stride=np.array(1),
                    bearing_names=np.array(bearing_names), boundaries=np.array(boundaries))

print(f"OK LIVIANO -> {NPZ_FILE} {NPZ_FILE.stat().st_size/1024:.1f} KB - {len(windows_idx)} ventanas")