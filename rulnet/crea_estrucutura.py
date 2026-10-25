import os
from pathlib import Path

base = Path(r"escribe aqui tu ruta")

carpetas = [
    "data/raw/FEMTO",
    "data/processed",
    "src/input_builder",
    "src/core",
    "models",
    "logs"
]

for c in carpetas:
    (base / c).mkdir(parents=True, exist_ok=True)
    print(f"OK: {base / c}")

# archivos vacíos para que queden listos
(base / "src" / "__init__.py").touch()
(base / "src" / "input_builder" / "__init__.py").touch()
(base / "src" / "core" / "__init__.py").touch()
(base / "src" / "run.py").touch()

print("\nEstructura lista en:", base)