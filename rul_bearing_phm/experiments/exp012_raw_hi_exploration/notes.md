# exp012_raw_hi_exploration

## IMPORTANTE: exploracion informal
Este experimento es exploratorio (Capa 1). NO se usa para decidir la receta
final del HI (esa decision se documenta en exp011_feature_zoom_for_HI y en
el reporte principal). Aqui solo se mira como se ve un HI "bruto" (todas las
8 features, sin filtrar outliers, sin cummax) en los 17 bearings, incluyendo
Full_Test_set.

## Que se calculo
- HI_H  = promedio de 8 features normalizadas (canal H), pesos iguales.
- HI_V  = promedio de 8 features normalizadas (canal V), pesos iguales.
- HI_HV = promedio de 16 features normalizadas (H+V), pesos iguales.

Normalizacion: Xmin = media ventana sana (primer 10%, SIN filtrar outliers),
Xmax = percentil 99, clip [0, 1]. Sin cummax (no se fuerza monotonicidad).

## Bearings incluidos
17 en total: 6 Learning_set + 11 Full_Test_set (orden: Learning primero).

## Pendiente / siguiente paso
- Comparar esta version bruta contra la version final del HI (solo RMS,
  Std, Peak; con cummax) para dimensionar el efecto de incluir features
  descartadas y de no forzar monotonicidad.
