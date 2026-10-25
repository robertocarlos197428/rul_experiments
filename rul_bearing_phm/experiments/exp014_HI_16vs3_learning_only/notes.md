# exp014_HI_16vs3_learning_only

## Objetivo
Version recortada de exp013. Mismo metodo pero SOLO sobre Learning_set (6 bearings).
El Learning_set es el unico conjunto valido para toma de decisiones de features.
Full_Test_set se excluye deliberadamente para no contaminar la evaluacion.

## Que se compara
- HI16 = promedio de 16 features normalizadas (8 x H/V) - version bruta exp012
- HI3  = promedio de 6 columnas (RMS, Std, Peak x H/V) - receta final exp011

Normalizacion: Xmin = media ventana sana primer 10%, Xmax = percentil 99, por bearing, clip [0,1], sin cummax.

## Salida
1 imagen: hi_comparison_learning_01.png con grid 3x4 (3 filas x 2 bearings, cada bearing 2 cols HI16/HI3)

## Decision esperada
Si HI3 se ve mas limpio y consistente que HI16 en los 6 Learning bearings, se confirma
que la seleccion de exp011 es correcta y se puede avanzar a aplicar cummax sobre HI3.
