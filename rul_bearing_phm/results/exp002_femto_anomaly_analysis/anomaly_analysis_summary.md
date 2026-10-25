# Informe de Análisis de Anomalías - Dataset FEMTO (EXP002)

## 1. Qué se revisó
Se realizó una revisión exhaustiva cruzando el inventario de la auditoría inicial (`EXP001`) con la estructura interna de los archivos originales ubicados en `data/raw/FEMTO/`. Se evaluaron columnas, integridad de lectura, consistencia de timestamps y presencia de valores nulos o anómalos.

## 2. Cuántos archivos se analizaron
- **Total de archivos evaluados:** 43592

## 3. Qué anomalías se encontraron y dónde están
Se detectaron un total de **4284** registros de anomalías distribuidos en los diferentes rodamientos y conjuntos. El detalle completo por archivo se encuentra en `tables/anomalies_femto_v001.csv`.

## 4. Tipo de falla y severidad
Las fallas identificadas comprenden principalmente advertencias de auditoría previa, posibles duplicados y validaciones de estructura. Los contadores detallados están disponibles en `tables/anomaly_counts_femto_v001.csv`.

## 5. Estado de confirmación de anomalías
- **Detectadas / Requieren revisión:** La gran mayoría de los casos detectados se encuentran en estado `needs_review` para evaluar su impacto real antes de aplicar cualquier regla.
- **No confirmadas:** Ninguna anomalía ha sido marcada como descartada o falsa todavía.

## 6. Correcciones pendientes y qué NO debe modificarse
- **Correcciones pendientes:** Ninguna. Este análisis es estrictamente descriptivo.
- **Qué NO debe modificarse:** 
  - No se modifica ningún archivo en `data/raw/FEMTO/`.
  - No se eliminan archivos ni se decide qué regla de corrección aplicar.
  - No se definen zonas sanas, umbrales, FPT ni etiquetas RUL en esta etapa.
