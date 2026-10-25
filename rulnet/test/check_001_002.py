from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
f1 = BASE / "data/processed/001_build_input.npz"
f2 = BASE / "data/processed/002_build_labels.npz"

print("=== CHECK 001_build_input ===")
d1 = np.load(f1, allow_pickle=True)
X = d1['X']
boundaries = d1['boundaries']
names = d1['bearing_names']
print(f"X shape {X.shape} dtype {X.dtype} - {X.nbytes/1024**2:.1f} MB")
print(f"NaN? {np.isnan(X).any()} Inf? {np.isinf(X).any()}")
print(f"Bearings {len(names)}: {list(names)[:3]}...")
print(f"Boundaries len {len(boundaries)} -> suma longitudes {sum(e-s for s,e in boundaries)} == {len(X)}? {sum(e-s for s,e in boundaries) == len(X)}")

# chequea continuidad de boundaries
for i,(s,e) in enumerate(boundaries):
    if e<=s:
        print(f"ERROR boundary {i} {s},{e}")

print("\n=== CHECK 002_build_labels ===")
d2 = np.load(f2, allow_pickle=True)
y = d2['y']
print(f"y shape {y.shape} dtype {y.dtype}")
print(f"y min {y.min():.4f} max {y.max():.4f} - debe ser [0,1]")
print(f"NaN? {np.isnan(y).any()} fuera de rango? {((y<0)|(y>1)).any()}")
print(f"len y {len(y)} == len X {len(X)}? {len(y)==len(X)}")

# Monotonia decreciente por bearing
print("\nMonotonia por bearing (debe decrecer):")
for idx,(s,e) in enumerate(boundaries[:5]): # revisa primeros 5
    y_b = y[s:e]
    decrece = np.all(np.diff(y_b) <= 0.001) # permite ruido chico
    print(f" {names[idx]} [{s}:{e}] len {len(y_b)} y[0]={y_b[0]:.3f} y[-1]={y_b[-1]:.3f} decrece? {decrece}")
    if not decrece:
        print(f" WARN no monotono estricto")

print("\nOK si todo True y sin WARN graves -> 001 y 002 congelados bien")