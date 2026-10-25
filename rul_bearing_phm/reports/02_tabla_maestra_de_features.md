Tabla maestra (insumo del experimento): generada en exp007, contiene una fila por snapshot/archivo, con columnas de identificación (data_set, bearing_id, file_id, acc_filename, timestamp_sec, condition) más 16 time_features estadísticas calculadas sobre las señales cruda horizontal (h_) y vertical (v_):

crest_factor
kurtosis
mean
peak
peak_to_peak
rms
skewness
std

(8 indicadores × 2 ejes = 16 features). Existen 3 versiones de esta tabla: learning_set (6 rodamientos, run-to-failure completo), full_test_set (11 rodamientos, run-to-failure completo) y test_set (mismos 11 rodamientos de full_test_set, pero truncados según el formato challenge de FEMTO).

Objetivo: generar visualizaciones exploratorias de las 16 features estadísticas (exp007) para los 17 rodamientos con FPT válido, antes de decidir qué indicadores usar en las siguientes etapas.

Proceso:

Detectamos 3-4 valores "extremos" en la tabla resumen de estadísticos (v_mean=21.1, v_kurtosis~404, h_skewness=-14.4).
Primer intento con umbral automático (mediana + k×MAD) → falló: 40.000 filas marcadas como anómalas, porque kurtosis/skewness tienen colas naturalmente pesadas y el método asumía distribución simétrica.
Decidimos pivotar a inspección visual directa en vez de seguir ajustando umbrales.
Piloto con v_kurtosis: series temporales por rodamiento, agrupadas en 3 imágenes (6 learning_set + 6 + 5 full_test_set), escala Y global para comparar entre rodamientos.
Resultado clave: lo que parecía outlier estadístico era en realidad el patrón esperado de degradación — kurtosis plana durante vida sana, picos fuertes cerca de la falla. No hay error de cálculo ni dato corrupto.
Se formalizó como experimento completo (exp008_feature_visualization), con config.yaml, notes.md (plantilla, pendiente de completar con hallazgos), manifest.json, log dual, y se corrió para las 16 features → 48 imágenes generadas.

## Actualización post-Exp008: de FPT con RMS a Health Index multi-feature

**Exp009-010 — Validación de FPT con RMS (Flow A):**
Se calculó el FPT (First Predicting Time) usando RMS como única feature 
(enfoque baseline, Flow A). Los resultados mostraron que RMS aislado es 
insuficiente para una detección de FPT confiable — la feature no captura 
suficiente información temprana de degradación por sí sola. Esto motivó 
el cambio de estrategia hacia Flow C: construir primero un Health Index 
combinando múltiples features, y detectar el FPT sobre ese HI en vez de 
sobre una sola métrica.

**Exp011 — Construcción del Health Index (Flow C, en curso):**
Se definieron 3 métodos candidatos para el cálculo del HI. Se comenzó por 
el más simple: **promedio ponderado normalizado con pesos iguales**, como 
baseline interpretable antes de avanzar a ponderaciones más sofisticadas 
(ej. por monotonicidad/trendability).

*Selección de features de entrada:*
Antes de normalizar, se evaluaron las 8 features candidatas (RMS, Std, 
Peak, Peak-to-Peak, Mean, Skewness, Kurtosis, Crest Factor) contra 8 
criterios jerarquizados en dos grupos:
- **Eliminatorios:** dirección de tendencia y consistencia entre bearings.
- **Degradantes (no eliminatorios):** monotonicidad, estabilidad en 
  ventana sana, nivel de ruido, timing del onset, y outliers puntuales.

Para esta evaluación se generaron gráficos individuales por feature/canal 
(sub-experimento `exp011_feature_zoom_for_HI`), con escala fija en el eje 
Y por feature (para evitar que outliers puntuales distorsionen la lectura 
visual) y grid de los 6 bearings de Learning_set por imagen.

**Veredictos:**
- **RMS, Std, Peak** → ✅ quedan. Tendencia clara, consistente entre los 
  6 bearings, buena monotonicidad hacia el fin de vida.
- **Mean, Skewness** → ❌ descartadas. Sin tendencia distinguible, 
  oscilan en torno a 0 durante toda la vida útil.
- **Peak-to-Peak** → ❌ descartada. Redundante con Peak (mismo 
  comportamiento), se prioriza Peak.
- **Crest Factor** → ❌ descartada. Ruidosa, sin tendencia consistente.
- **Kurtosis** → ❌ descartada. Revalidando el hallazgo de Exp008: el 
  patrón "plana en sano, pico en falla" es real y no es artefacto de 
  cálculo, pero **no se repite de forma consistente entre bearings** 
  (Bearing1_2 en particular muestra ruido/picos dispersos durante toda 
  la vida útil, no solo cerca del fallo). Al fallar el criterio 
  eliminatorio de consistencia entre bearings, se descarta como 
  feature de entrada al HI ponderado, aunque el dato se mantiene 
  disponible para modelos de ML supervisado más adelante.

**Resultado:** el HI (pesos iguales) se construye con **3 features × 2 
canales (H/V) = 6 columnas**: RMS, Std y Peak.

**Siguiente paso:** verificar las siguientes técnicas: normalización de las 6 columnas usando healthy-window como Xmin y P99 como Xmax, clip superior en 1, cummax para forzar 
monotonicidad, y definición de si el HI se calcula combinando H/V o 
por canal separado.

**Exp012-013 — Validación empírica de la selección (raw_hi_exploration / 
HI_16vs3_features_comparison):**
Como exploración informal (no usada para decidir la receta, solo para 
dimensionar su efecto), se calculó un HI_HV bruto —sin cummax, sin 
filtrado de outliers— para los 17 bearings (6 Learning_set + 11 
Full_Test_set), comparando la versión con las 16 features completas 
(HI16) contra la versión con solo las 3 features seleccionadas (HI3). 
Sobre Learning_set (base válida para decisiones), HI3 mostró 
consistentemente menos ruido de fondo durante la ventana sana y una 
subida final más nítida que HI16, confirmando empíricamente la selección 
de Exp011. Se observó además, en 3 de los 6 bearings de Learning_set 
(Bearing2_1, Bearing2_2, Bearing3_2), un comportamiento claramente 
**no-monótono** (el HI sube, baja y vuelve a subir antes del fallo), lo 
que confirma la necesidad de aplicar alguna tecnica de suavizado o cummax. 

**Siguiente paso:** evaluar técnicas de suavizado/cummax sobre HI3 en 
Learning_set y revisar si se resuelve la no-monotonicidad observada.