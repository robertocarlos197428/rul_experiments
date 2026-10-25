# exp013_HI_16vs3_features_comparison

## IMPORTANTE: exploracion informal
Este experimento es exploratorio (Capa 1). Compara visualmente el HI_HV
calculado con las 16 features (version bruta, exp012) contra el HI_HV
calculado solo con RMS+Std+Peak (receta final decidida en exp011).
No decide nada nuevo por si solo, sirve para dimensionar el efecto de
la seleccion de features hecha en exp011.

## Que se calculo
- HI16 = promedio de 16 features normalizadas (8 features x H/V), pesos iguales.
- HI3  = promedio de 6 columnas normalizadas (RMS, Std, Peak x H/V), pesos iguales.

Mismo metodo de normalizacion en ambos casos: Xmin = media ventana sana
(primer 10%, sin filtrar outliers), Xmax = percentil 99, clip [0, 1].
Sin cummax.

## Bearings incluidos
17 en total: 6 Learning_set + 11 Full_Test_set (orden: Learning primero).

## Pendiente / siguiente paso
- Revisar si HI3 reduce el ruido/falsos picos observados en HI16 para
  bearings problematicos (ej. Bearing2_3 en exp012).
- Si HI3 se ve limpio y consistente, avanzar a aplicar cummax sobre HI3
  como version candidata final.
