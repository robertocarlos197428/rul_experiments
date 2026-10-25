# 002_build_labels

## Que hace
Genera las labels de RUL para cada muestra de `001_build_input.npz`. RUL = 1.0 al inicio de cada bearing y 0.0 al final (falla), lineal.

## Por que lo hace asi
RUL lineal es baseline estandar en FEMTO. No usa tiempo real sino porcentaje de vida por bearing. Deterministico y reproducible, cumple trazabilidad liviana.

## Entradas
- escribe aqui tu ruta
    - X.shape=(24889, 1, 2560)
    - bearing_names=[np.str_('Bearing1_1'), np.str_('Bearing1_2'), np.str_('Bearing1_3'), np.str_('Bearing1_4'), np.str_('Bearing1_5'), np.str_('Bearing1_6'), np.str_('Bearing1_7'), np.str_('Bearing2_1'), np.str_('Bearing2_2'), np.str_('Bearing2_3'), np.str_('Bearing2_4'), np.str_('Bearing2_5'), np.str_('Bearing2_6'), np.str_('Bearing2_7'), np.str_('Bearing3_1'), np.str_('Bearing3_2'), np.str_('Bearing3_3')]
    - boundaries=[[0, 2803], [2803, 3674], [3674, 6049], [6049, 7477], [7477, 9940], [9940, 12388], [12388, 14647], [14647, 15558], [15558, 16355], [16355, 18310], [18310, 19061], [19061, 21372], [21372, 22073], [22073, 22303], [22303, 22818], [22818, 24455], [24455, 24889]]

## Salidas
- escribe aqui tu ruta con y.shape=(24889,), bearing_names, boundaries
- escribe aqui tu ruta

## Explicacion del codigo en detalle paso a paso
1. Carga `001_build_input.npz` con boundaries.
2. Crea vector y de ceros de largo total=24889.
3. Por cada [start,end) en boundaries, genera `np.linspace(1,0,length)` y lo inserta en y[start:end].
4. Guarda npz comprimido en `processed/` (congelado, solo lectura).
5. Genera curva RUL en `results/002_build_labels/`.
6. Escribe log con header obligatorio y md.

## Resultados de esta ejecucion
- Total muestras: 24889
- Bearings: 17
- y min=0.0000 max=1.0000 mean=0.5000
- Ejemplo Bearing1_1: y[0]=1.0, y[2802]=0.0 (si Bearing1_1 len=2803)
- Archivo congelado: escribe aqui tu ruta - UNICO y de solo lectura, no se actualiza.
