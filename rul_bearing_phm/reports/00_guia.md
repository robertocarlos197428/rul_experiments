# GUÍA RÁPIDA - PIPELINE RUL RODAMIENTOS (rul_bearing_phm)

> Referencia de orientación. Úsala cuando te pierdas de en qué fase/flujo estás.

---

## Ruta oficial (12 fases)

```
FEMTO → tabla común → indicadores → HI/FPT opcional → etiquetas comparadas
→ baseline clásico → BiLSTM/TCN → ResNet-BiLSTM → IMS → XJTU-SY → transferencia → análisis
```

| # | Fase | Decisión clave |
|---|------|-----------------|
| 0 | Pregunta y protocolo | objetivo, datasets, splits, métricas |
| 1 | Auditoría FEMTO | truncamiento o no |
| 2 | Formato común | validación de unidades |
| 3 | Features básicas | features candidatas |
| 4 | **HI/FPT exploratorio** ← estás cerca de acá | FPT o no FPT |
| 5 | Etiquetas | lineal / truncada / piecewise |
| 6 | Baselines (RF/XGB) | relación básica |
| 7 | BiLSTM/TCN | secuencia adecuada |
| 8 | ResNet/CNN | comparar con manual |
| 9 | IMS | robustez |
| 10 | XJTU-SY | generalización |
| 11 | Análisis final | conclusiones |

**Estado actual:** Exp007 completo (fase 3 → tabla maestra, 22 cols: 6 ID + 16 feats H/V). Siguiente paso: fase 4, cargar la tabla y graficar features/HI candidato por rodamiento.

---

## Los 3 flujos (sin B)

| Flujo | Qué hace | Fase(s) | Modelo |
|-------|----------|---------|--------|
| **A** | FPT directo sobre RMS crudo, **sin HI** | 5-6 | ML (RF/XGB) |
| **C** ⭐ | HI (features combinadas) → FPT detectado sobre el HI | 4, 5, 7 | DL (BiLSTM/TCN) |
| **D** | Sin HI/FPT explícito — features automáticas (CNN/ResNet) entrenadas **contra etiqueta RUL** (sigue siendo supervisado) | 8 | DL (ResNet/BiLSTM) |

**C es el recomendado para la tesis.** A es el baseline simple de comparación. D llega recién en fase 8, no ahora.

*(B — HI sin FPT — no se usa como flujo final: su etiqueta sin fase de plateau cae en el riesgo #4. El paso de construir el HI se hace una sola vez y se hereda directo a C.)*

---

## Los 10 riesgos que te hacen reprobar

1. Fuga de info por normalizar con todo el dataset
2. Selección de umbral con datos de prueba
3. Mezcla de ventanas del mismo rodamiento en train/test
4. **RUL artificialmente preciso durante etapa sana** (label decae desde snapshot 1 sin plateau)
5. FPT definido por un pico aislado
6. Sobreajuste por pocas trayectorias (FEMTO = 17 bearings)
7. Comparar escalas sin normalizar
8. Ignorar cambios de velocidad/carga
9. Usar MAPE cerca de RUL=0
10. Comparar modelos con distintos splits

---

## Decisión inicial recomendada

- **Datos:** FEMTO solo
- **Features:** RMS, peak, kurtosis, crest factor — canales H/V separados
- **Etiqueta:** lineal primero (punto de partida, no la final de tesis)
- **Modelos:** baseline clásico (RF/XGB) + BiLSTM pequeño
- **Split:** por rodamiento, nunca mezclar ventanas del mismo bearing
- **Métricas:** MAE, RMSE, error por etapa + gráficos reales vs. estimados
- **Después:** RUL truncado, piecewise-FPT, ResNet/CNN, tiempo-frecuencia

