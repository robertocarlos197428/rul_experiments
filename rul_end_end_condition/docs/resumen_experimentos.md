# Resumen de experimentos: CNN sobre señal cruda + condición de operación + Mamba

*Documento generado automáticamente por `end_end_condition.py`. Última actualización: 2026-10-24 18:13.*

## 1. Objetivo

Repetir el experimento `rul_end_end` (una CNN aprende las features desde la señal cruda H y V de FEMTO y se las entrega a Mamba, entrenadas juntas) agregando la **condición de operación** (1, 2 o 3) como entrada de Mamba, para ver si ayuda con los rodamientos que peor salieron, en particular los de la condición 2.

## 2. Datos y protocolo

- **Datos:** FEMTO/PRONOSTIA, los 17 rodamientos (3 condiciones), leídos desde `rul_ina/data/raw_femto/BearingX_Y` (o desde el caché de `rul_end_end`). Cada archivo tiene 2.560 puntos (0,1 s a 25,6 kHz); H es la columna 4 y V la columna 5.
- **Etiqueta:** RUL lineal descendente de 1 a 0 en la vida completa de cada rodamiento.
- **Entrada del modelo:** ventanas de 50 archivos consecutivos (2 canales × 2.560 puntos cada uno). Se predice el RUL del último archivo; si no hay historia suficiente, se repite el primer archivo hacia atrás (solo usa el pasado).
- **Condición de operación:** sale del nombre (`Bearing1_x` = condición 1, etc.) y se codifica en one-hot (3 números). Se le pega al vector de la CNN de cada archivo antes de entrar a Mamba.
- **Normalización:** media y desviación por canal (H y V), calculadas solo con los rodamientos de entrenamiento de cada fold.
- **Validación LOBO (leave-one-bearing-out):** un entrenamiento por rodamiento de test; se deja ese rodamiento afuera y se entrena con los otros 16. No hay búsqueda de hiperparámetros dentro del fold.
- **Rodamientos probados como test:** 7 de 17 (`LIMITE_RODAMIENTOS = 7`); siempre se entrena con los otros 16.
- **Entrenamiento:** 20 épocas, Adam con lr cosine, pérdida SmoothL1 (beta 0.1), gradiente recortado a 1.0. Cada época usa 1 de cada 10 ventanas (cambiando el punto de partida entre épocas), porque las ventanas consecutivas son casi iguales.

## 3. Configuración

### 3.1 Hiperparámetros fijos

| Hiperparámetro | Valor | Qué hace |
|---|---|---|
| Condición de operación | one-hot de 3 valores, como entrada de Mamba | Le dice al modelo en qué condición (velocidad y carga) trabaja el rodamiento |
| Filtros de la CNN | [32, 64] | Patrones distintos que busca cada capa convolucional |
| Stride / pooling de la CNN | 4 / 4 | Reducen la señal de 2.560 puntos a unos 160 antes de la segunda capa |
| n_capas | 6 | Bloques Mamba apilados |
| hidden | 32 | Ancho del modelo Mamba |
| d_state | 8 | Memoria interna de Mamba |
| expand | 2 | Ensanchamiento interno de cada bloque Mamba |
| d_conv | 4 | Ancho de la mini convolución dentro del bloque Mamba |
| lr | 0.00081685 | Tamaño de los pasos de corrección |
| dropout | 0.1785176 | Fracción de neuronas apagadas al azar al entrenar |
| batch | 8 | Ventanas por actualización |

### 3.2 Combinaciones (cada una es un LOBO)

| Carpeta en `resultados/` | Kernel de la CNN | Tamaño del vector |
|---|---|---|
| `k8_v16_L50_e20_cond` | 8 | 16 |

- **Kernel:** cuántos puntos seguidos de la señal mira cada filtro de la CNN.
- **Tamaño del vector:** cuántos números resumen cada archivo y se le pasan a Mamba.

## 4. Cómo está armado el script

`src/end_end_condition.py` es `end_end.py` más la condición de operación, dividido en secciones con encabezado:

1. **Configuración:** todos los parámetros (condición, combinaciones, hiperparámetros, épocas, folds a correr).
2. **Carpetas de entrada y salida:** rutas de datos crudos, `processed`, `resultados`, `docs`, y las referencias de `rul_end_end`.
3. **Utilidades de consola:** barra de avance con tiempo estimado.
4. **Lectura de datos crudos, caché y condición:** reutiliza el caché `.npy` de `rul_end_end` si existe (si no, lee los CSV una vez); calcula la condición de cada rodamiento a partir de su nombre; carga los resultados de referencia.
5. **Normalización y ventanas:** estadísticas por canal con los rodamientos de entrenamiento; las ventanas se arman por índice, sin copiarlas todas en memoria.
6. **Red CNN:** conv1 (con stride) → ReLU → dropout → max-pool → conv2 → ReLU → dropout → promedio y máximo en el tiempo → capa lineal al tamaño del vector.
7. **Red Mamba:** capa lineal de entrada, bloques Mamba con RMSNorm y conexión residual, y una cabeza que entrega el RUL del último paso. El scan selectivo está escrito en PyTorch puro (sin kernels CUDA).
8. **Modelo completo:** la CNN procesa cada archivo de la ventana, se le pega la condición (one-hot) a cada vector y Mamba procesa la secuencia.
9. **Entrenamiento y predicción:** al predecir, la CNN se calcula una sola vez por archivo y las ventanas se arman sobre los vectores (mismo resultado, mucho más rápido).
10. **Gráficos:** los 17 rodamientos (RUL real y predicción), actualizado al terminar cada fold.
11. **CSV resumen y este documento.**
12. **Programa principal:** recorre las combinaciones y, dentro de cada una, los folds; si se corta, retoma saltando los folds terminados.

Archivos que deja cada carpeta de `resultados/`:

- `resumen_mae.csv`: MAE de cada rodamiento con 4 decimales y el promedio.
- `errores_completo.csv`: MAE y RMSE con todos los decimales, pérdida final y minutos por fold.
- `predicciones.csv`, `perdida_por_epoca.csv`, `configuracion.json`.
- `lobo_17_rodamientos.png`: gráfico de los 17 rodamientos.
- `folds/`: archivos por fold (permiten retomar si se corta).

## 5. Resultados

MAE por rodamiento de test (4 decimales). `-` = fold aún sin correr. (ref.) = resultado de `rul_end_end` ya terminado, para comparar.

| Rodamiento | `k8_v16_L50_e20_cond` | k8_v16 sin condicion (ref.) |
|---|---|---|
| Bearing1_1 | 0.0604 | 0.0527 |
| Bearing1_2 | 0.1285 | 0.1644 |
| Bearing1_3 | 0.1150 | 0.0921 |
| Bearing1_4 | 0.1279 | 0.0667 |
| Bearing1_5 | - | 0.0628 |
| Bearing1_6 | - | 0.2404 |
| Bearing1_7 | - | 0.1230 |
| Bearing2_1 | - | 0.2064 |
| Bearing2_2 | - | 0.1335 |
| Bearing2_3 | - | 0.2357 |
| Bearing2_4 | - | 0.2942 |
| Bearing2_5 | - | 0.1478 |
| Bearing2_6 | - | 0.2223 |
| Bearing2_7 | - | 0.3442 |
| Bearing3_1 | - | 0.2026 |
| Bearing3_2 | - | 0.2800 |
| Bearing3_3 | - | 0.0763 |
| **Promedio propio** | **0.1080** | **0.1732** |
| **Promedio en comunes (n=4)** | **0.1080** | **0.0940** |
| Folds hechos | 4/7 | - |

> **Nota:** una sola corrida por configuración y sin repeticiones con otras semillas; las diferencias pequeñas entre columnas pueden ser azar. Para comparar de forma justa, usar el promedio en los rodamientos comunes.
