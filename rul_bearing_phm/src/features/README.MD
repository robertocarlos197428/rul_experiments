# features_time_domain - Guía completa

## 1. Qué es
Librería pura de 8 fórmulas de dominio tiempo para vibración. No lee ni escribe archivos. Entra una señal de 2560 puntos, sale un número.
Ubicación del código: `src/features/features_time_domain.py`

## 2. Código fuente (copiar tal cual en features_time_domain.py)

```python
"""
Módulo: features_time_domain.py
Contiene 8 fórmulas base de dominio tiempo para señales de vibración.
Se aplican a eje H y V -> genera 16 features.
"""

import numpy as np
from scipy import stats

def calculate_mean(signal: np.ndarray) -> float:
    """mean = (1/N) * sum(x_i)"""
    return float(np.mean(signal))

def calculate_std(signal: np.ndarray, ddof: int = 1) -> float:
    """std con variante ddof=1 muestral (papers PHM), ddof=0 poblacional"""
    return float(np.std(signal, ddof=ddof))

def calculate_rms(signal: np.ndarray) -> float:
    """rms = sqrt((1/N) * sum(x_i^2))"""
    return float(np.sqrt(np.mean(np.square(signal))))

def calculate_peak_to_peak(signal: np.ndarray) -> float:
    """p2p = max(x) - min(x)"""
    return float(np.max(signal) - np.min(signal))

def calculate_peak(signal: np.ndarray, definition: str = "max_abs") -> float:
    """max_abs = max(abs(x)) estándar vibración, max_only = max(x)"""
    if definition == "max_abs":
        return float(np.max(np.abs(signal)))
    elif definition == "max_only":
        return float(np.max(signal))
    else:
        raise ValueError(f"definition no soportada: {definition}")

def calculate_crest_factor(peak: float, rms: float) -> float:
    """crest = peak / rms, con protección div/0"""
    if rms == 0:
        return 0.0
    return float(peak / rms)

def calculate_kurtosis(signal: np.ndarray, kurtosis_type: str = "fisher", bias: bool = False) -> float:
    """
    fisher (default): Normal = 0 -> Pearson - 3 -> ESTÁNDAR PHM
    pearson: Normal = 3 -> Bruta
    """
    if kurtosis_type == "fisher":
        return float(stats.kurtosis(signal, fisher=True, bias=bias))
    elif kurtosis_type == "pearson":
        return float(stats.kurtosis(signal, fisher=False, bias=bias))
    else:
        raise ValueError(f"kurtosis_type no soportado: {kurtosis_type}")

def calculate_skewness(signal: np.ndarray, bias: bool = False) -> float:
    """bias=False corregida (recomendado), bias=True bruta"""
    return float(stats.skew(signal, bias=bias))

def extract_time_features(signal_h, signal_v, std_ddof=1, peak_definition="max_abs", kurtosis_type="fisher", skewness_bias=False, kurtosis_bias=False) -> dict:
    h_mean = calculate_mean(signal_h)
    h_std = calculate_std(signal_h, ddof=std_ddof)
    h_rms = calculate_rms(signal_h)
    h_p2p = calculate_peak_to_peak(signal_h)
    h_peak = calculate_peak(signal_h, definition=peak_definition)
    h_crest = calculate_crest_factor(h_peak, h_rms)
    h_kurt = calculate_kurtosis(signal_h, kurtosis_type=kurtosis_type, bias=kurtosis_bias)
    h_skew = calculate_skewness(signal_h, bias=skewness_bias)
    v_mean = calculate_mean(signal_v)
    v_std = calculate_std(signal_v, ddof=std_ddof)
    v_rms = calculate_rms(signal_v)
    v_p2p = calculate_peak_to_peak(signal_v)
    v_peak = calculate_peak(signal_v, definition=peak_definition)
    v_crest = calculate_crest_factor(v_peak, v_rms)
    v_kurt = calculate_kurtosis(signal_v, kurtosis_type=kurtosis_type, bias=kurtosis_bias)
    v_skew = calculate_skewness(signal_v, bias=skewness_bias)
    return {
        "h_mean": h_mean, "h_std": h_std, "h_rms": h_rms, "h_peak_to_peak": h_p2p,
        "h_peak": h_peak, "h_crest_factor": h_crest, "h_kurtosis": h_kurt, "h_skewness": h_skew,
        "v_mean": v_mean, "v_std": v_std, "v_rms": v_rms, "v_peak_to_peak": v_p2p,
        "v_peak": v_peak, "v_crest_factor": v_crest, "v_kurtosis": v_kurt, "v_skewness": v_skew,
    }