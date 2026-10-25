# EXP001 — Auditoría inicial del dataset FEMTO

## 1. Objetivo

Documentar manualmente la estructura, el formato y las características conocidas del dataset FEMTO antes de escribir el primer script de auditoría.

Esta inspección servirá para definir el formato de la tabla maestra y los requisitos de `01_audit_dataset.py`.

## 2. Ubicación del dataset

Ruta local:

```text
escribe aqui tu ruta
```

## 3. Estructura principal

El dataset contiene las siguientes carpetas:

```text
FEMTO/
├── Full_Test_Set/
├── Test_Set/
└── Learning_Set/
```

Interpretación provisional:

- `Learning_Set/`: conjunto de trayectorias utilizado para aprendizaje o desarrollo.
- `Test_Set/`: conjunto destinado a evaluación/prueba según la organización original del dataset.
- `Full_Test_Set/`: conjunto de pruebas completas o trayectorias run-to-failure completas.

La interpretación exacta de cada carpeta deberá confirmarse mediante la documentación del dataset y la auditoría automática.

## 4. Identificación de los rodamientos

La cantidad de archivos por rodamiento es variable.

La cantidad exacta de rodamientos y snapshots por trayectoria todavía debe determinarse automáticamente mediante el script de auditoría.

El primer script deberá identificar:

- nombre de la carpeta del rodamiento;
- conjunto al que pertenece;
- cantidad de snapshots;
- primer y último snapshot;
- archivos faltantes;
- archivos duplicados;
- archivos corruptos o ilegibles.

## 5. Formato de archivos

Los archivos tienen extensión:

```text
.csv
```

Ejemplo de archivo de vibración:

```text
acc_01124.csv
```

Los archivos de vibración no tienen encabezado.

También existen registros de temperatura con nombres similares a:

```text
temp_00001.csv
```

La nomenclatura exacta de los archivos de temperatura debe verificarse durante la auditoría.

## 6. Estructura de los archivos de vibración

Cada archivo de aceleración contiene seis columnas, sin encabezado:

| Posición | Significado |
|---:|---|
| 1 | Hora |
| 2 | Minutos |
| 3 | Segundos |
| 4 | Microsegundos |
| 5 | Aceleración horizontal, en g |
| 6 | Aceleración vertical, en g |

Nombre lógico de las columnas:

```text
hour
minute
second
microsecond
acc_horizontal_g
acc_vertical_g
```

## 7. Ejemplo de registro

Ejemplo observado:

```text
8,53,11,6.191e+05,0.259,-0.917
```

Interpretación provisional:

```text
hour = 8
minute = 53
second = 11
microsecond = 6.191e+05
acc_horizontal_g = 0.259
acc_vertical_g = -0.917
```

La interpretación de la cuarta columna debe confirmarse durante la auditoría, porque aparece expresada en notación científica.

## 8. Canales disponibles

Los archivos de vibración contienen dos canales de aceleración:

- canal horizontal;
- canal vertical.

Los nombres normalizados que se utilizarán inicialmente serán:

```text
acc_horizontal_g
acc_vertical_g
```

También existen archivos de temperatura, pero la temperatura no se incorporará todavía al primer análisis. Se conservará como una posible variable futura.

## 9. Frecuencia de muestreo

La frecuencia de muestreo documentada para los canales de vibración es:

```text
25.6 kHz = 25.600 muestras por segundo
```

Este valor deberá comprobarse indirectamente durante la auditoría mediante la cantidad de muestras de cada archivo y la duración temporal registrada.

## 10. Tamaño de los archivos

El tamaño aproximado de un archivo de vibración es:

```text
85 KB
```

Este valor es solamente orientativo. El script de auditoría deberá registrar el tamaño real de cada archivo y detectar archivos anormalmente pequeños o grandes.

## 11. Estado del preprocesamiento

El dataset se encuentra actualmente en su estado inicial dentro del proyecto.

No se ha aplicado todavía:

- eliminación de snapshots iniciales;
- corrección de archivos corruptos;
- imputación de datos;
- eliminación de valores faltantes;
- suavización;
- filtrado;
- normalización;
- extracción de características;
- cálculo de RMS;
- cálculo de kurtosis;
- construcción de HI;
- detección de FPT;
- generación de etiquetas RUL.

Cualquier corrección futura deberá realizarse mediante un proceso reproducible y quedar documentada.

## 12. Posibles archivos corruptos

Se sabe que existen o pueden existir archivos corruptos que deberán identificarse.

El script de auditoría deberá revisar:

- archivos vacíos;
- archivos ilegibles;
- archivos con menos o más de seis columnas;
- archivos con encabezados inesperados;
- valores no numéricos;
- valores faltantes;
- valores infinitos;
- cantidad anormal de muestras;
- timestamps inválidos;
- archivos duplicados;
- discontinuidades en los nombres de snapshot.

Los archivos problemáticos no deben eliminarse automáticamente durante la auditoría. Primero deben registrarse en un informe de calidad.

## 13. Decisiones pendientes

Antes de construir la tabla maestra se deben confirmar automáticamente:

- cantidad total de rodamientos;
- cantidad de snapshots por rodamiento;
- cantidad de muestras por archivo;
- duración temporal de cada snapshot;
- intervalo entre snapshots;
- existencia y estructura de los archivos de temperatura;
- correspondencia entre archivos de aceleración y temperatura;
- archivos corruptos;
- archivos faltantes;
- rodamientos incompletos;
- interpretación exacta de las tres carpetas principales.

## 14. Próximo paso

El próximo paso del proyecto es implementar y ejecutar:

```text
scripts/01_audit_dataset.py
```

El script leerá:

```text
data/raw/FEMTO
```

y generará:

```text
data/interim/FEMTO/metadata/
├── dataset_inventory_femto_v001.csv
├── bearing_summary_femto_v001.csv
└── data_quality_femto_v001.csv
```

También generará resultados del experimento:

```text
results/exp001_femto_audit/
├── figures/
├── tables/
└── logs/
```

## 15. Estado de la auditoría

Estado actual:

```text
INSPECCIÓN MANUAL COMPLETADA
AUDITORÍA AUTOMÁTICA PENDIENTE
```

No se deben fijar todavía:

- la zona sana;
- el método de suavización;
- los umbrales;
- el FPT;
- las etiquetas RUL;
- la división definitiva entre entrenamiento y prueba.

Estas decisiones se tomarán después de confirmar la estructura real del dataset mediante la auditoría automática.

Todas las carpetas que no existan deben ser creadas