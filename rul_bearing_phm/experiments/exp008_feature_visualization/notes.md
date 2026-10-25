# notes.md - exp008_feature_visualization

## Objetivo

Generar visualizaciones exploratorias (series temporales) de las 16 features
estadisticas extraidas en exp007, para los 17 rodamientos con FPT valido
(6 de learning_set + 11 de full_test_set), con el fin de apoyar la decision
de que indicadores usar en las siguientes etapas del proyecto.

## Metodo

- Serie temporal de cada feature vs tiempo_horas, una subgrafica por rodamiento.
- Agrupacion en 3 imagenes por feature, siguiendo el split natural de los
  datasets de origen (6 learning_set / 6 full_test_set / 5 full_test_set),
  sin mezclar bearings de distinto dataset en la misma imagen.
- Escala Y global por feature (el maximo/minimo entre los 17 bearings manda),
  para permitir comparacion directa entre rodamientos.
- test_set queda fuera del analisis por ser version truncada (redundante)
  de full_test_set.

## Hallazgos

_Pendiente de completar tras revisar las 16 x 3 = 48 imagenes generadas._

## Anomalias detectadas

_Pendiente._

## Decisiones

_Pendiente._