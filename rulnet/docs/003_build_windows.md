# SCRIPT: 003_build_windows.py v2 liviano

## QUE HACE
Genera índices de ventanas para modelo TCN+Transformer sin duplicar datos crudos en disco. Cumple punto 7 v4.0 (espacio en disco vs RAM).

- Ventana: WINDOW_SIZE=30 muestras
- Paso: STRIDE=1
- Tipo: Índices livianos [start, end) sobre array global de 001

## ENTRADAS
- `data/processed/001_build_input.npz` -> X global (N,2560), boundaries, bearing_names
- `data/processed/002_build_labels.npz` -> y global RUL [0,1]

## SALIDAS / ARCHIVOS QUE CREA
- `data/processed/003_build_windows.npz` (142.1 KB, 24396 ventanas)
    - windows_idx: (24396,2) int32 -> [s,e)
    - bearing_id: (24396,) int16 -> id bearing origen
    - y_windows: (24396,) float32 -> RUL del fin de ventana
    - window_size, stride, bearing_names, boundaries
- `logs/003_build_windows.log`
- `docs/003_build_windows.md` (este archivo)
- `results/003_build_windows/reporte.txt` (si aplica)
- `results/003_build_windows/verificacion_ventanas.png` (si aplica)

## REGLA v4.0 CUMPLIDA
Antes: materializaba X_windows (24396,30,2560) = 3.66 GB en disco -> VIOLA punto 7
Ahora: solo guarda índices (24396,2) = 142.1 KB -> 99.996% ahorro, carga al vuelo en Dataset.__getitem__ con X_global[s:e]

## VERIFICACION
- Total ventanas: 24396
- Bearings: 17 (7 condición 1, 7 condición 2, 3 condición 3)
- Rango y_windows: [0.0, 1.0]
- Sin leakage: ventanas de un mismo bearing no se parten dentro, se agrupan por bearing_id para split posterior en 004