# Bitácora de Experimento: exp010_piecewise_labels

## Objetivo
Construir las etiquetas de Remaining Useful Life (RUL) bajo el enfoque **Piecewise** (tramos) y generar gráficos de validación integrando la señal física (RMS) de fondo junto al RUL resultante.

## Criterios Técnicos
- **Fase Sana (Pre-FPT)**: El RUL se mantiene constante (meseta horizontal) en el valor de vida útil restante desde el momento del FPT.
- **Fase de Degradación (Post-FPT)**: El RUL decrece de forma lineal y proporcional desde el FPT hasta llegar a 0 en el último snapshot del rodamiento.
