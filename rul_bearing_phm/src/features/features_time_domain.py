"""
Módulo: features_time_domain.py
Contiene 8 fórmulas base de dominio tiempo para señales de vibración.
Se aplican a eje H y V -> genera 16 features.

Dependencias: numpy, scipy
"""

import numpy as np
from scipy import stats

def calculate_mean(signal: np.ndarray) -> float:
    """mean = (1/N) * sum(x_i)"""
    return float(np.mean(signal))

def calculate_std(signal: np.ndarray, ddof: int = 1) -> float:
    """
    std = sqrt(1/(N-ddof) * sum((x_i - mean)^2))
    ddof: 1 = muestral (usado en papers PHM), 0 = poblacional
    """
    return float(np.std(signal, ddof=ddof))

def calculate_rms(signal: np.ndarray) -> float:
    """rms = sqrt((1/N) * sum(x_i^2)) - Directa"""
    return float(np.sqrt(np.mean(np.square(signal))))

def calculate_peak_to_peak(signal: np.ndarray) -> float:
    """p2p = max(x) - min(x) - Directa"""
    return float(np.max(signal) - np.min(signal))

def calculate_peak(signal: np.ndarray, definition: str = "max_abs") -> float:
    """
    peak: con variante
    - max_abs: max(abs(x)) -> estándar vibración, captura ambos lados
    - max_only: max(x) -> solo positivo
    """
    if definition == "max_abs":
        return float(np.max(np.abs(signal)))
    elif definition == "max_only":
        return float(np.max(signal))
    else:
        raise ValueError(f"definition no soportada: {definition}")

def calculate_crest_factor(peak: float, rms: float) -> float:
    """
    crest = peak / rms
    Directa, con protección div/0
    """
    if rms == 0:
        return 0.0
    return float(peak / rms)

def calculate_kurtosis(signal: np.ndarray, kurtosis_type: str = "fisher", bias: bool = False) -> float:
    """
    kurtosis con 2 variantes críticas:
    - fisher (exceso): Normal = 0 -> Pearson - 3 (scipy fisher=True) -> ESTÁNDAR PHM
    - pearson (bruta): Normal = 3 (scipy fisher=False)
    Fix: si std==0 devuelve 0.0 en vez de NaN
    """
    if np.std(signal) == 0 or len(signal) < 4:
        return 0.0
    if kurtosis_type == "fisher":
        val = stats.kurtosis(signal, fisher=True, bias=bias)
    elif kurtosis_type == "pearson":
        val = stats.kurtosis(signal, fisher=False, bias=bias)
    else:
        raise ValueError(f"kurtosis_type no soportado: {kurtosis_type}")
    return 0.0 if np.isnan(val) or np.isinf(val) else float(val)

def calculate_skewness(signal: np.ndarray, bias: bool = False) -> float:
    """
    skew = (1/N * sum((x_i - mean)^3)) / std^3
    bias: False = corregida por N pequeño (recomendado), True = bruta
    Fix: si std==0 devuelve 0.0 en vez de NaN
    """
    if np.std(signal) == 0 or len(signal) < 3:
        return 0.0
    val = stats.skew(signal, bias=bias)
    return 0.0 if np.isnan(val) or np.isinf(val) else float(val)

def extract_time_features(
    signal_h: np.ndarray,
    signal_v: np.ndarray,
    std_ddof: int = 1,
    peak_definition: str = "max_abs",
    kurtosis_type: str = "fisher",
    skewness_bias: bool = False,
    kurtosis_bias: bool = False
) -> dict:
    """
    Función orquestadora: aplica las 8 fórmulas a H y V.
    Devuelve dict con 16 features listo para tabla de 22 columnas.
    Hace cálculo eficiente reutilizando rms y peak para crest_factor.
    """
    # --- EJE H ---
    h_mean = calculate_mean(signal_h)
    h_std = calculate_std(signal_h, ddof=std_ddof)
    h_rms = calculate_rms(signal_h)
    h_p2p = calculate_peak_to_peak(signal_h)
    h_peak = calculate_peak(signal_h, definition=peak_definition)
    h_crest = calculate_crest_factor(h_peak, h_rms)
    h_kurt = calculate_kurtosis(signal_h, kurtosis_type=kurtosis_type, bias=kurtosis_bias)
    h_skew = calculate_skewness(signal_h, bias=skewness_bias)

    # --- EJE V ---
    v_mean = calculate_mean(signal_v)
    v_std = calculate_std(signal_v, ddof=std_ddof)
    v_rms = calculate_rms(signal_v)
    v_p2p = calculate_peak_to_peak(signal_v)
    v_peak = calculate_peak(signal_v, definition=peak_definition)
    v_crest = calculate_crest_factor(v_peak, v_rms)
    v_kurt = calculate_kurtosis(signal_v, kurtosis_type=kurtosis_type, bias=kurtosis_bias)
    v_skew = calculate_skewness(signal_v, bias=skewness_bias)

    return {
        "h_mean": h_mean,
        "h_std": h_std,
        "h_rms": h_rms,
        "h_peak_to_peak": h_p2p,
        "h_peak": h_peak,
        "h_crest_factor": h_crest,
        "h_kurtosis": h_kurt,
        "h_skewness": h_skew,
        "v_mean": v_mean,
        "v_std": v_std,
        "v_rms": v_rms,
        "v_peak_to_peak": v_p2p,
        "v_peak": v_peak,
        "v_crest_factor": v_crest,
        "v_kurtosis": v_kurt,
        "v_skewness": v_skew,
    }