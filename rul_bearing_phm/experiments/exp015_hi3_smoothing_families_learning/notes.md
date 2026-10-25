# exp015_hi3_smoothing_families_learning - CORREGIDO

## Correccion critica
Mon original Mon=|N+-N-|/(K-1) daba 0.01 para cummax porque penalizaba diffs=0 (plateaus).
cummax sube en escalones: 30 subidas y 2770 planos -> 30/2800=0.01

Nueva formula: Mon(y)=1 - N-/(K-1), N-=count(dy<0)
- Mide "nunca baja" que es lo relevante para FPT
- A y C = 1.0 por construccion

## Familias sobre hi3
- raw: hi3 crudo
- A: cummax(hi3) - Mon=1.0 garantizado
- B: EWMA(hi3, alpha=0.1)
- C: cummax(EWMA) - Mon=1.0 garantizado

hi3 = promedio de 6 columnas: h_rms, v_rms, h_std, v_std, h_peak, v_peak

## Salidas
- hi_smoothing_comparison_learning_01.png
- tabla1_monotonicity_separabilidad.jpg con formula corregida arriba
- monotonicity_separabilidad.csv
