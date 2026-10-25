# Bitácora de Experimento: exp009_fpt_baseline

## Objetivo
Detectar el Failure Point Transition (FPT) para cada bearing del learning set utilizando una baseline estadística sobre los canales de RMS horizontal (`h_rms`) y vertical (`v_rms`).

## Criterios Técnicos
- **Ventana Sana**: Primer 10% de los snapshots ordenados cronológicamente por bearing.
- **Umbral**: $\text{media} + 3 \times \text{std}$ calculada en la ventana sana.
- **Cruce Sostenido**: El primer punto donde RMS supera el umbral y se mantiene durante 10 ventanas consecutivas.
- **Métricas**: Índice de FPT, tiempo total de vida, FPT en horas y formato HH:MM, además del porcentaje de vida sana.
