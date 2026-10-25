from pathlib import Path
import numpy as np
BASE = Path(__file__).resolve().parents[1]
f = BASE / "data/processed/003_build_windows.npz"
data = np.load(f)
Xw = data['X_windows']
print(f"Archivo: {f.stat().st_size / 1024**3:.2f} GB")
print(f"X_windows shape {Xw.shape} dtype {Xw.dtype}")
print(f"Memoria sin comprimir ~ {Xw.nbytes / 1024**3:.2f} GB")
print(f"y_windows {data['y_windows'].shape}")
print(f"bearing_id unique {np.unique(data['bearing_id'])}")

# Chequeo de duplicacion: ventana 0 y 1 se solapan 29
if Xw.shape[0] > 1:
    # si ndim 4 -> squeeze
    x0 = Xw[0].squeeze()
    x1 = Xw[1].squeeze()
    print(f"Solape check: x0[1:] == x1[:-1]? {np.allclose(x0[1:], x1[:-1])} -> Confirmado duplicado")