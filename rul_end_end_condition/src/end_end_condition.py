"""
end_end_condition.py  -  Igual que end_end.py (CNN sobre la senal cruda H y V de FEMTO +
Mamba, entrenadas juntas, validacion LOBO), pero agregando la CONDICION DE OPERACION
(1, 2 o 3, sale del nombre BearingX_Y) como entrada extra de Mamba.

Carpeta del proyecto (este archivo va en rul_end_end_condition/src/):
    rul_end_end_condition/
        src/end_end_condition.py
        processed/   etiquetas RUL (y cache de senales si no se puede reutilizar el de rul_end_end)
        resultados/  una carpeta por combinacion, ej. k8_v16_L50_e20_cond
        docs/        resumen_experimentos.md (se actualiza solo)

Que cambia respecto de end_end.py:
 - El vector que la CNN entrega por archivo (ej. 16 numeros) se concatena con la condicion
   en one-hot (3 numeros) antes de entrar a Mamba. USAR_CONDICION = False lo desactiva.
 - Reutiliza el cache de senales de ../rul_end_end/processed/senales si existe (no vuelve
   a leer los 24 mil CSV).
 - Compara cada rodamiento contra los resultados de rul_end_end (REFERENCIAS): en la consola,
   en la tabla del .md y al final de la combinacion.

Que hace:
 1. Lee los CSV crudos de FEMTO (H = columna 4, V = columna 5), o reutiliza el cache.
 2. Para cada combinacion (kernel de la CNN, tamano del vector), corre un LOBO: un
    entrenamiento por rodamiento de test, cada uno con los otros 16. Sin busqueda de
    hiperparametros dentro: todo lo demas es fijo (ver configuracion).
 3. En cada carpeta de resultados guarda: resumen_mae.csv (4 decimales),
    errores_completo.csv (todos los decimales), predicciones, perdidas y el grafico
    de los 17 rodamientos, que se actualiza al terminar cada uno.
 4. Actualiza docs/resumen_experimentos.md con configuracion, descripcion del script y
    resultados.

Si se corta a medias, al volver a correr se saltan los folds ya terminados.

Requisitos:  pip install torch pandas numpy matplotlib pyarrow
"""

from pathlib import Path
import datetime
import json
import math
import re
import sys
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    plt.style.use("seaborn-v0_8-whitegrid")
except Exception:
    pass


# ============================================================
# 1. CONFIGURACION  (todo lo que se puede cambiar esta aqui)
# ============================================================

# ---- Condicion de operacion como entrada -------------------
USAR_CONDICION = True        # True = la condicion (1, 2 o 3) entra a Mamba junto al vector de la CNN
N_CONDICIONES = 3            # FEMTO tiene 3 condiciones: se codifican en one-hot (3 numeros)

# ---- Datos crudos FEMTO ------------------------------------
COL_H = 4                    # indice de la columna de aceleracion horizontal
COL_V = 5                    # indice de la columna de aceleracion vertical
N_MUESTRAS = 2560            # filas esperadas por archivo (0,1 s a 25,6 kHz)
INTERVALO_S = 10.0           # segundos entre archivos consecutivos
RECALCULAR_CACHE = False     # True = vuelve a leer los CSV crudos

# ---- Ventanas y etiqueta -----------------------------------
LONG_SECUENCIA = 50          # archivos consecutivos por ventana (L)
# RUL: lineal descendente de 1 a 0 en la vida completa de cada rodamiento.

# ---- Combinaciones a correr (cada una es un LOBO) ----------
KERNELS = [8]                # kernel de la CNN sobre la senal cruda
VECTORES = [16]              # tamano del vector que la CNN le entrega a Mamba
# Orden: de la mas barata a la mas cara (kernel primero). Se puede escribir a mano:
# COMBINACIONES = [(8, 16), (8, 32)]
COMBINACIONES = [(k, v) for k in sorted(KERNELS) for v in sorted(VECTORES)]

# ---- Red CNN (parte fija) ----------------------------------
CNN_FILTROS = (32, 64)       # filtros de las 2 capas convolucionales
CNN_STRIDE = 4               # salto de la primera capa (reduce 2560 -> ~640 puntos)
CNN_POOL = 4                 # max-pooling despues de la primera capa (640 -> ~160)

# ---- Hiperparametros fijos (Mamba y comunes) ---------------
HP = {
    "n_capas": 6,            # bloques Mamba apilados
    "hidden": 32,            # ancho del modelo Mamba
    "d_state": 8,            # memoria interna de Mamba
    "expand": 2,             # ensanchamiento interno del bloque Mamba
    "d_conv": 4,             # ancho de la mini convolucion interna de Mamba
    "lr": 0.00081685,        # tamano de los pasos de correccion
    "dropout": 0.1785176,    # fraccion de neuronas apagadas al entrenar
    "batch": 8,              # ventanas por actualizacion
}

# ---- Entrenamiento -----------------------------------------
EPOCAS = 20
PASO_ENTRENAMIENTO = 10      # cada epoca usa 1 de cada N ventanas (cambiando el punto de
                             # partida entre epocas), porque ventanas consecutivas son casi
                             # iguales. 1 = usar todas
GRAD_CLIP = 1.0
BETA_SMOOTHL1 = 0.1
SEMILLA = 42
N_HILOS = None               # None = los que use PyTorch por defecto
DISPOSITIVO = "auto"         # "auto" (usa GPU si hay), "cpu" o "cuda"
CHUNK_EVAL = 256             # archivos/ventanas por bloque al predecir
ACTUALIZAR_BARRA_CADA = 5    # pasos de entrenamiento entre refrescos de la barra

# ---- Que folds correr --------------------------------------
LIMITE_RODAMIENTOS = 7       # None = los 17 como test. Un numero N = solo los primeros N
                             # como test (siempre se entrena con los otros 16)

# ---- Salidas -----------------------------------------------
CSV_SEP = ","                # cambia a ";" si Excel abre resumen_mae.csv en una sola columna
DPI = 150
COLUMNAS_GRAFICO = 4


# ============================================================
# 2. CARPETAS DE ENTRADA Y SALIDA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent          # carpeta rul_end_end_condition
PROCESSED_DIR = BASE_DIR / "processed"
RESULTS_DIR = BASE_DIR / "resultados"
DOCS_DIR = BASE_DIR / "docs"

# Se usa la primera que exista (las carpetas BearingX_Y estan directamente dentro).
RAW_DIR_CANDIDATOS = [
    Path(r"escribe aqui tu ruta"),
    BASE_DIR.parent / "rul_ina" / "data" / "raw_femto",
]

# Proyecto sin condicion (rul_end_end): se reutiliza su cache de senales y se compara contra
# sus resultados. Si no existe, simplemente se omite.
CARPETA_SIN_CONDICION = BASE_DIR.parent / "rul_end_end"
CACHE_SENALES_ALTERNATIVAS = [CARPETA_SIN_CONDICION / "processed" / "senales"]
REFERENCIAS = {
    "k8_v16 sin condicion": CARPETA_SIN_CONDICION / "resultados" / "k8_v16_L50_e20",
}
REFS = {}                    # se llena al iniciar: nombre -> {rodamiento: (MAE, RMSE)}

BEARING_COL = "bearing_id"
TIME_COL = "time_seconds"
TARGET_COL = "rul_frac"


def encontrar_raw():
    for c in RAW_DIR_CANDIDATOS:
        if c.is_dir():
            return c
    print("No se encontro la carpeta de datos crudos. Rutas probadas:")
    for c in RAW_DIR_CANDIDATOS:
        print(f"   {c}")
    sys.exit(1)


def nombre_corrida(kernel, vector):
    s = f"k{kernel}_v{vector}_L{LONG_SECUENCIA}_e{EPOCAS}"
    return s + "_cond" if USAR_CONDICION else s


def carpeta_corrida(kernel, vector):
    return RESULTS_DIR / nombre_corrida(kernel, vector)


# ============================================================
# 3. UTILIDADES DE CONSOLA (barra de avance)
# ============================================================

ANCHO_LINEA = 105


def fmt_tiempo(seg):
    if seg < 60:
        return f"{seg:.0f}s"
    if seg < 3600:
        return f"{seg / 60:.0f}m"
    if seg < 86400:
        return f"{int(seg // 3600)}h {int((seg % 3600) // 60):02d}m"
    return f"{int(seg // 86400)}d {int((seg % 86400) // 3600)}h"


class Barra:
    """Barra de avance de una sola linea, con ETA. Permite imprimir mensajes encima."""

    def __init__(self, ancho=26):
        self.ancho = ancho
        self.t0 = None
        self.f0 = 0.0
        self.frac = 0.0
        self.extra = ""
        self.activa = False

    def iniciar(self, f0=0.0):
        self.t0 = time.time()
        self.f0 = f0
        self.frac = f0
        self.activa = True

    def _texto(self):
        frac = min(max(self.frac, 0.0), 1.0)
        n = int(round(frac * self.ancho))
        eta = ""
        hecho = frac - self.f0
        if self.t0 is not None and hecho > 0.0005 and frac < 1.0:
            eta = " ETA " + fmt_tiempo((time.time() - self.t0) * (1.0 - frac) / hecho)
        return f"[{'#' * n}{'-' * (self.ancho - n)}] {frac * 100:5.1f}%{eta}  {self.extra}"

    def _dibujar(self):
        sys.stdout.write("\r" + self._texto().ljust(ANCHO_LINEA)[:ANCHO_LINEA])
        sys.stdout.flush()

    def actualizar(self, frac, extra=""):
        self.frac, self.extra = frac, extra
        self._dibujar()

    def mensaje(self, texto):
        sys.stdout.write("\r" + " " * ANCHO_LINEA + "\r" + texto + "\n")
        if self.activa:
            self._dibujar()
        sys.stdout.flush()

    def cerrar(self):
        if self.activa:
            sys.stdout.write("\n")
            sys.stdout.flush()
        self.activa = False


# ============================================================
# 4. LECTURA DE DATOS CRUDOS, CACHE (processed/) Y CONDICION
# ============================================================

def leer_archivo(path):
    """Lee un CSV de FEMTO (separador ',' o ';' detectado) y devuelve [2, N] (H, V)."""
    with open(path, "r") as fh:
        primera = fh.readline()
    sep = ";" if primera.count(";") > primera.count(",") else ","
    df = pd.read_csv(path, header=None, sep=sep, usecols=[COL_H, COL_V], dtype=np.float32)
    arr = df[[COL_H, COL_V]].to_numpy(dtype=np.float32)
    if arr.shape[0] != N_MUESTRAS:
        raise ValueError(f"{path} tiene {arr.shape[0]} filas (se esperaban {N_MUESTRAS}).")
    if not np.isfinite(arr).all():
        raise ValueError(f"{path} contiene valores no numericos.")
    return arr.T


def listar_rodamientos(raw_dir):
    patron = re.compile(r"^bearing(\d+)_(\d+)$", re.IGNORECASE)
    encontrados = []
    for p in raw_dir.iterdir():
        m = patron.match(p.name)
        if p.is_dir() and m:
            encontrados.append(((int(m.group(1)), int(m.group(2))), p))
    encontrados.sort(key=lambda t: t[0])
    return [(p.name, p) for _, p in encontrados]


def archivos_de(carpeta):
    arch = sorted(carpeta.glob("acc_*.csv"))
    if not arch:
        arch = sorted(p for p in carpeta.glob("*.csv") if not p.name.lower().startswith("temp"))
    return arch


def condicion_de(nombre):
    """Condicion de operacion (0, 1 o 2) a partir del nombre BearingX_Y (X = 1, 2 o 3)."""
    m = re.match(r"^bearing(\d+)_", nombre, re.IGNORECASE)
    if not m or not (1 <= int(m.group(1)) <= N_CONDICIONES):
        raise ValueError(f"No se pudo sacar la condicion de '{nombre}' (se esperaba BearingX_Y "
                         f"con X entre 1 y {N_CONDICIONES}).")
    return int(m.group(1)) - 1


def one_hot_condicion(nombre):
    v = np.zeros(N_CONDICIONES, dtype=np.float32)
    v[condicion_de(nombre)] = 1.0
    return v


def n_cond_modelo():
    """Cuantos numeros de condicion recibe Mamba (0 si USAR_CONDICION = False)."""
    return N_CONDICIONES if USAR_CONDICION else 0


def cargar_senales(raw_dir):
    """Devuelve (senal, y, tiempo): diccionarios por rodamiento.
    senal[b]: float32 [n_archivos, 2, 2560]  (canal 0 = H, canal 1 = V)
    y[b]:     RUL lineal descendente de 1 a 0 en la vida completa."""
    rodamientos = listar_rodamientos(raw_dir)
    if not rodamientos:
        raise FileNotFoundError(f"No se encontraron carpetas BearingX_Y en {raw_dir}")

    cache_dir = PROCESSED_DIR / "senales"
    cache_dir.mkdir(parents=True, exist_ok=True)

    senal, por_leer, desde_alt = {}, [], 0
    for nombre, carpeta in rodamientos:
        archivos = archivos_de(carpeta)
        if not archivos:
            raise FileNotFoundError(f"No hay archivos acc_*.csv en {carpeta}")
        cache = cache_dir / f"{nombre}.npy"
        candidatos = [cache] + [d / f"{nombre}.npy" for d in CACHE_SENALES_ALTERNATIVAS]
        cargado = False
        if not RECALCULAR_CACHE:
            for c in candidatos:
                if c.exists():
                    arr = np.load(c)
                    if arr.shape == (len(archivos), 2, N_MUESTRAS):
                        senal[nombre] = arr
                        desde_alt += int(c != cache)
                        cargado = True
                        break
                    print(f"   cache {c} no coincide con los CSV; se descarta")
        if not cargado:
            por_leer.append((nombre, archivos, cache))
    if desde_alt:
        print(f"{desde_alt} rodamientos cargados desde el cache de rul_end_end (sin releer CSV)")

    if por_leer:
        total = sum(len(a) for _, a, _ in por_leer)
        print(f"Leyendo {total:,} archivos CSV crudos desde {raw_dir} (solo la primera vez)")
        barra = Barra()
        barra.iniciar(0.0)
        hechos = 0
        for nombre, archivos, cache in por_leer:
            arr = np.empty((len(archivos), 2, N_MUESTRAS), dtype=np.float32)
            for i, a in enumerate(archivos):
                arr[i] = leer_archivo(a)
                hechos += 1
                if hechos % 100 == 0:
                    barra.actualizar(hechos / total, f"{nombre} {i + 1}/{len(archivos)}")
            np.save(cache, arr)
            senal[nombre] = arr
        barra.actualizar(1.0, "listo")
        barra.cerrar()

    senal = {nombre: senal[nombre] for nombre, _ in rodamientos}
    y = {b: np.linspace(1.0, 0.0, len(x)).astype(np.float32) for b, x in senal.items()}
    tiempo = {b: np.arange(len(x)) * INTERVALO_S for b, x in senal.items()}

    etiquetas = pd.concat([
        pd.DataFrame({BEARING_COL: b, "condicion": condicion_de(b) + 1,
                      "file_idx": np.arange(len(y[b])), TIME_COL: tiempo[b],
                      TARGET_COL: y[b]})
        for b in senal
    ], ignore_index=True)
    try:
        etiquetas.to_parquet(PROCESSED_DIR / "rul_etiquetas.parquet", index=False)
    except Exception:
        etiquetas.to_csv(PROCESSED_DIR / "rul_etiquetas.csv", index=False)
    return senal, y, tiempo


def cargar_referencias(bearings):
    """MAE y RMSE por rodamiento de las corridas de referencia (rul_end_end), si existen."""
    refs = {}
    for nombre, carpeta in REFERENCIAS.items():
        folds = carpeta / "folds"
        if not folds.is_dir():
            print(f"(sin referencia '{nombre}': no existe {folds})")
            continue
        d = {}
        for b in bearings:
            f = folds / f"{b}_pred.csv"
            if f.exists():
                d[b] = errores_de(pd.read_csv(f))
        if d:
            refs[nombre] = d
            print(f"Referencia '{nombre}': {len(d)} rodamientos")
    return refs


# ============================================================
# 5. NORMALIZACION Y VENTANAS
# ============================================================

def estadisticas(senal, ids):
    """Media y desviacion por canal (H, V), calculadas SOLO con los rodamientos ids."""
    s = np.zeros(2)
    ss = np.zeros(2)
    n = 0
    for b in ids:
        x = senal[b]
        s += x.sum(axis=(0, 2), dtype=np.float64)
        ss += (x * x).sum(axis=(0, 2), dtype=np.float64)
        n += x.shape[0] * x.shape[2]
    media = s / n
    desv = np.sqrt(np.maximum(ss / n - media ** 2, 0.0))
    desv[desv == 0] = 1.0
    return media.astype(np.float32), desv.astype(np.float32)


def armar_batch(listas, b_idx, t_idx, idxs, media, desv, dispositivo):
    """Ventanas por indice (no se copian todas): para cada muestra (rodamiento, t), las L
    filas hasta t. Sin historia suficiente se repite la primera fila (solo usa el pasado)."""
    L = LONG_SECUENCIA
    xb = np.empty((len(idxs), L, 2, N_MUESTRAS), dtype=np.float32)
    for j, g in enumerate(idxs):
        X = listas[b_idx[g]]
        filas = np.clip(np.arange(t_idx[g] - L + 1, t_idx[g] + 1), 0, len(X) - 1)
        xb[j] = X[filas]
    x = torch.from_numpy(xb).to(dispositivo)
    m = torch.from_numpy(media).view(1, 1, 2, 1).to(dispositivo)
    d = torch.from_numpy(desv).view(1, 1, 2, 1).to(dispositivo)
    return (x - m) / d


# ============================================================
# 6. RED CNN (aprende las features desde la senal cruda)
# ============================================================

class CNNSenal(nn.Module):
    """Resume cada archivo [2 canales, 2560 puntos] en un vector de `vector` numeros.
    conv1 (a saltos) -> ReLU -> dropout -> max-pool -> conv2 -> ReLU -> dropout
    -> promedio y maximo en el tiempo -> capa lineal."""

    def __init__(self, kernel, vector, dropout, filtros=CNN_FILTROS,
                 stride=CNN_STRIDE, pool=CNN_POOL, c_in=2):
        super().__init__()
        f1, f2 = filtros
        self.conv1 = nn.Conv1d(c_in, f1, kernel, stride=stride, padding=kernel // 2)
        self.pool = nn.MaxPool1d(pool)
        self.conv2 = nn.Conv1d(f1, f2, kernel, stride=1, padding=kernel // 2)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(2 * f2, vector)

    def forward(self, x):                       # x: [N, 2, 2560]
        h = self.drop(F.relu(self.conv1(x)))
        h = self.pool(h)
        h = self.drop(F.relu(self.conv2(h)))
        h = torch.cat([h.mean(dim=2), h.amax(dim=2)], dim=1)
        return self.fc(h)                       # [N, vector]


# ============================================================
# 7. RED MAMBA
# ============================================================

class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps) * self.weight


class MambaBlock(nn.Module):
    """Bloque Mamba (SSM selectivo) con scan secuencial en PyTorch puro."""

    def __init__(self, d_model, d_state, expand, d_conv):
        super().__init__()
        self.d_inner = expand * d_model
        self.d_state = d_state
        self.dt_rank = max(1, math.ceil(d_model / 16))

        self.in_proj = nn.Linear(d_model, 2 * self.d_inner, bias=False)
        self.conv1d = nn.Conv1d(
            self.d_inner, self.d_inner, d_conv,
            groups=self.d_inner, padding=d_conv - 1, bias=True,
        )
        self.x_proj = nn.Linear(self.d_inner, self.dt_rank + 2 * d_state, bias=False)
        self.dt_proj = nn.Linear(self.dt_rank, self.d_inner, bias=True)

        A = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        self.A_log = nn.Parameter(torch.log(A))
        self.D = nn.Parameter(torch.ones(self.d_inner))
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

        dt = torch.exp(
            torch.rand(self.d_inner) * (math.log(0.1) - math.log(0.001)) + math.log(0.001)
        ).clamp(min=1e-4)
        inv_dt = dt + torch.log(-torch.expm1(-dt))
        with torch.no_grad():
            self.dt_proj.bias.copy_(inv_dt)

    def forward(self, x):                       # x: [B, L, d_model]
        B, L, _ = x.shape
        x_in, z = self.in_proj(x).chunk(2, dim=-1)

        x_in = self.conv1d(x_in.transpose(1, 2))[:, :, :L].transpose(1, 2)
        x_in = F.silu(x_in)

        dt, Bm, Cm = torch.split(
            self.x_proj(x_in), [self.dt_rank, self.d_state, self.d_state], dim=-1
        )
        dt = F.softplus(self.dt_proj(dt))       # [B, L, d_inner]
        A = -torch.exp(self.A_log)              # [d_inner, d_state]

        dA = torch.exp(dt.unsqueeze(-1) * A)                                  # [B,L,Di,N]
        dBx = dt.unsqueeze(-1) * Bm.unsqueeze(2) * x_in.unsqueeze(-1)         # [B,L,Di,N]

        h = torch.zeros(B, self.d_inner, self.d_state, dtype=x.dtype, device=x.device)
        ys = []
        for t in range(L):
            h = dA[:, t] * h + dBx[:, t]
            ys.append((h * Cm[:, t].unsqueeze(1)).sum(-1))
        y = torch.stack(ys, dim=1) + x_in * self.D

        y = y * F.silu(z)
        return self.out_proj(y)


class MambaRUL(nn.Module):
    """Secuencia de vectores [B, L, n_in] -> RUL del ultimo paso."""

    def __init__(self, n_in, hp):
        super().__init__()
        H = hp["hidden"]
        self.embed = nn.Linear(n_in, H)
        self.norms = nn.ModuleList([RMSNorm(H) for _ in range(hp["n_capas"])])
        self.bloques = nn.ModuleList(
            [MambaBlock(H, hp["d_state"], hp["expand"], hp["d_conv"]) for _ in range(hp["n_capas"])]
        )
        self.norm_f = RMSNorm(H)
        self.head = nn.Linear(H, 1)

    def forward(self, e):
        h = self.embed(e)
        for norm, bloque in zip(self.norms, self.bloques):
            h = h + bloque(norm(h))
        return self.head(self.norm_f(h[:, -1])).squeeze(-1)


# ============================================================
# 8. MODELO COMPLETO (CNN + CONDICION + MAMBA, entrenados juntos)
# ============================================================

class ModeloEndEnd(nn.Module):
    """CNN por archivo -> vector; si n_cond > 0, se le pega la condicion (one-hot) a cada
    vector de la secuencia; Mamba procesa la secuencia y predice el RUL."""

    def __init__(self, kernel, vector, hp, n_cond=0):
        super().__init__()
        self.n_cond = n_cond
        self.cnn = CNNSenal(kernel, vector, hp["dropout"])
        self.drop = nn.Dropout(hp["dropout"])
        self.mamba = MambaRUL(vector + n_cond, hp)

    def secuencia(self, e, c=None):             # e: [B, L, vector]; c: [B, n_cond] o None
        e = self.drop(e)
        if self.n_cond > 0:
            e = torch.cat([e, c.unsqueeze(1).expand(-1, e.shape[1], -1)], dim=2)
        return self.mamba(e)

    def forward(self, x, c=None):               # x: [B, L, 2, 2560]
        B, L, C, T = x.shape
        e = self.cnn(x.reshape(B * L, C, T)).reshape(B, L, -1)
        return self.secuencia(e, c)


def contar_parametros(modelo):
    return sum(p.numel() for p in modelo.parameters())


# ============================================================
# 9. ENTRENAMIENTO Y PREDICCION
# ============================================================

def entrenar(senal, y, train_ids, kernel, vector, semilla, dispositivo, callback=None):
    """Entrena CNN + Mamba con los rodamientos train_ids. La normalizacion de la senal se
    calcula solo con ellos. callback(epoca, fraccion_de_la_epoca, perdida_anterior)."""
    media, desv = estadisticas(senal, train_ids)

    listas = [senal[b] for b in train_ids]
    ys = [y[b] for b in train_ids]
    b_idx = np.concatenate([np.full(len(x), i, dtype=np.int32) for i, x in enumerate(listas)])
    t_idx = np.concatenate([np.arange(len(x), dtype=np.int32) for x in listas])
    y_all = np.concatenate(ys)
    n_total = len(y_all)
    cond_arr = np.stack([one_hot_condicion(b) for b in train_ids]) if USAR_CONDICION else None

    torch.manual_seed(semilla)
    rng = np.random.default_rng(semilla)
    modelo = ModeloEndEnd(kernel, vector, HP, n_cond_modelo()).to(dispositivo)
    opt = torch.optim.Adam(modelo.parameters(), lr=HP["lr"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCAS)

    batch = int(HP["batch"])
    perdidas = []
    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        inicio = (epoca - 1) % PASO_ENTRENAMIENTO
        perm = rng.permutation(np.arange(inicio, n_total, PASO_ENTRENAMIENTO))
        n = len(perm)
        n_pasos = max(1, math.ceil(n / batch))
        total = 0.0
        for p, i in enumerate(range(0, n, batch)):
            idxs = perm[i:i + batch]
            xb = armar_batch(listas, b_idx, t_idx, idxs, media, desv, dispositivo)
            yb = torch.from_numpy(y_all[idxs]).to(dispositivo)
            cb = (torch.from_numpy(cond_arr[b_idx[idxs]]).to(dispositivo)
                  if USAR_CONDICION else None)
            pred = modelo(xb, cb)
            loss = F.smooth_l1_loss(pred, yb, beta=BETA_SMOOTHL1)
            opt.zero_grad()
            loss.backward()
            if GRAD_CLIP:
                torch.nn.utils.clip_grad_norm_(modelo.parameters(), GRAD_CLIP)
            opt.step()
            total += loss.item() * len(idxs)
            if callback is not None and p % ACTUALIZAR_BARRA_CADA == 0:
                callback(epoca, p / n_pasos, perdidas[-1] if perdidas else float("nan"))
        sched.step()
        perdida = total / n
        if not np.isfinite(perdida):
            raise RuntimeError("La perdida no es finita; revisa los datos o baja el lr.")
        perdidas.append(perdida)
        if callback is not None:
            callback(epoca, 1.0, perdida)
    return modelo, (media, desv), perdidas


def predecir(modelo, X, norma, cond_vec, dispositivo):
    """Predice el RUL de todos los archivos de un rodamiento. Como en evaluacion la CNN
    no depende de la ventana, se calcula una sola vez por archivo y luego se arman las
    ventanas sobre los vectores (mismo resultado, mucho mas rapido). cond_vec: one-hot de
    la condicion del rodamiento (o None si USAR_CONDICION = False)."""
    media, desv = norma
    n = len(X)
    L = LONG_SECUENCIA
    modelo.eval()
    m = torch.from_numpy(media).view(1, 2, 1).to(dispositivo)
    d = torch.from_numpy(desv).view(1, 2, 1).to(dispositivo)
    c_all = (torch.from_numpy(cond_vec).view(1, -1).to(dispositivo)
             if cond_vec is not None else None)
    with torch.no_grad():
        embs = []
        for i in range(0, n, CHUNK_EVAL):
            xb = torch.from_numpy(X[i:i + CHUNK_EVAL]).to(dispositivo)
            embs.append(modelo.cnn((xb - m) / d))
        E = torch.cat(embs)                                        # [n, vector]
        idx = np.clip(np.arange(n)[:, None] + np.arange(-(L - 1), 1)[None, :], 0, n - 1)
        idx = torch.from_numpy(idx).to(dispositivo)
        preds = []
        for i in range(0, n, CHUNK_EVAL):
            w = E[idx[i:i + CHUNK_EVAL]]
            c = c_all.expand(w.shape[0], -1) if c_all is not None else None
            preds.append(modelo.secuencia(w, c))
    return torch.cat(preds).cpu().numpy()


# ============================================================
# 10. GRAFICOS
# ============================================================

def graficar(bearings, preds, maes, destino, titulo):
    """Grafico de los 17 rodamientos (real vs prediccion). Los que aun no se han probado
    quedan en blanco con la etiqueta 'pendiente'."""
    n = len(bearings)
    n_cols = min(COLUMNAS_GRAFICO, n)
    n_rows = int(np.ceil(n / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 3.2 * n_rows),
                             sharey=True, squeeze=False)
    for ax, b in zip(axes.flat, bearings):
        if b in preds:
            part = preds[b]
            vida = np.linspace(0, 100, len(part))
            ax.plot(vida, part["rul_real"], color="black", linewidth=1.5, label="Real")
            ax.plot(vida, part["rul_pred"], color="tab:red", linewidth=0.9, alpha=0.9,
                    label="Prediccion")
            ax.set_title(f"{b}  |  MAE {maes[b]:.4f}", fontsize=10)
        else:
            ax.set_title(f"{b}  |  pendiente", fontsize=10, color="gray")
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.05, 1.05)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    for ax in axes[-1, :]:
        ax.set_xlabel("Vida util (%)", fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel("RUL (1 a 0)", fontsize=9)
    if preds:
        axes[0, 0].legend(fontsize=8)
    fig.suptitle(titulo, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(destino, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 11. CSV RESUMEN Y DOCUMENTO .md
# ============================================================

def fold_hecho(folds_dir, b):
    return all((folds_dir / f"{b}_{s}").exists() for s in ("pred.csv", "loss.csv", "info.json"))


def errores_de(pred_df):
    e = pred_df["rul_pred"] - pred_df["rul_real"]
    return float(np.mean(np.abs(e))), float(np.sqrt(np.mean(e ** 2)))


def leer_resultados(kernel, vector, bearings):
    """MAE y RMSE por rodamiento a partir de los folds terminados en disco."""
    folds_dir = carpeta_corrida(kernel, vector) / "folds"
    res = {}
    for b in bearings:
        if folds_dir.is_dir() and fold_hecho(folds_dir, b):
            res[b] = errores_de(pd.read_csv(folds_dir / f"{b}_pred.csv"))
    return res


def escribir_csvs(out_dir, bearings, a_probar):
    """resumen_mae.csv (4 decimales), errores_completo.csv, predicciones y perdidas."""
    folds_dir = out_dir / "folds"
    hechos = [b for b in a_probar if fold_hecho(folds_dir, b)]
    if not hechos:
        return {}, {}
    preds = {b: pd.read_csv(folds_dir / f"{b}_pred.csv") for b in hechos}
    maes = {b: errores_de(preds[b])[0] for b in hechos}
    rmses = {b: errores_de(preds[b])[1] for b in hechos}
    infos = {b: json.loads((folds_dir / f"{b}_info.json").read_text(encoding="utf-8"))
             for b in hechos}

    resumen = pd.DataFrame({BEARING_COL: hechos, "MAE": [maes[b] for b in hechos]})
    resumen.loc[len(resumen)] = ["PROMEDIO", float(np.mean([maes[b] for b in hechos]))]
    resumen.to_csv(out_dir / "resumen_mae.csv", index=False, sep=CSV_SEP, float_format="%.4f")

    completo = pd.DataFrame({
        BEARING_COL: hechos,
        "filas": [len(preds[b]) for b in hechos],
        "MAE": [maes[b] for b in hechos],
        "RMSE": [rmses[b] for b in hechos],
        "perdida_final": [infos[b]["perdida_final"] for b in hechos],
        "minutos": [infos[b]["segundos"] / 60.0 for b in hechos],
    })
    e_glob = pd.concat(preds.values())
    mae_g, rmse_g = errores_de(e_glob)
    completo.loc[len(completo)] = ["PROMEDIO_RODAMIENTOS", int(completo["filas"].sum()),
                                   completo["MAE"].mean(), completo["RMSE"].mean(),
                                   completo["perdida_final"].mean(), completo["minutos"].sum()]
    completo.loc[len(completo)] = ["GLOBAL_TODAS_LAS_FILAS", len(e_glob), mae_g, rmse_g,
                                   float("nan"), float("nan")]
    completo.to_csv(out_dir / "errores_completo.csv", index=False)

    pd.concat(preds.values(), ignore_index=True).to_csv(out_dir / "predicciones.csv", index=False)
    pd.concat([pd.read_csv(folds_dir / f"{b}_loss.csv") for b in hechos],
              ignore_index=True).to_csv(out_dir / "perdida_por_epoca.csv", index=False)
    return preds, maes


def escribir_docs(bearings, a_probar):
    """Genera docs/resumen_experimentos.md a partir de lo que hay en disco."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    res = {c: leer_resultados(c[0], c[1], bearings) for c in COMBINACIONES}
    nombres = {c: nombre_corrida(*c) for c in COMBINACIONES}
    n_prueba = len(a_probar)

    L = []
    L.append("# Resumen de experimentos: CNN sobre señal cruda + condición de operación + Mamba")
    L.append("")
    L.append(f"*Documento generado automáticamente por `end_end_condition.py`. Última actualización: {ahora}.*")
    L.append("")
    L.append("## 1. Objetivo")
    L.append("")
    L.append("Repetir el experimento `rul_end_end` (una CNN aprende las features desde la señal cruda "
             "H y V de FEMTO y se las entrega a Mamba, entrenadas juntas) agregando la **condición de "
             "operación** (1, 2 o 3) como entrada de Mamba, para ver si ayuda con los rodamientos que "
             "peor salieron, en particular los de la condición 2." if USAR_CONDICION else
             "Repetir el experimento `rul_end_end` con `USAR_CONDICION = False` (control sin condición).")
    L.append("")
    L.append("## 2. Datos y protocolo")
    L.append("")
    L.append("- **Datos:** FEMTO/PRONOSTIA, los 17 rodamientos (3 condiciones), leídos desde "
             "`rul_ina/data/raw_femto/BearingX_Y` (o desde el caché de `rul_end_end`). Cada archivo "
             "tiene 2.560 puntos (0,1 s a 25,6 kHz); H es la columna 4 y V la columna 5.")
    L.append("- **Etiqueta:** RUL lineal descendente de 1 a 0 en la vida completa de cada rodamiento.")
    L.append(f"- **Entrada del modelo:** ventanas de {LONG_SECUENCIA} archivos consecutivos "
             "(2 canales × 2.560 puntos cada uno). Se predice el RUL del último archivo; si no hay "
             "historia suficiente, se repite el primer archivo hacia atrás (solo usa el pasado).")
    if USAR_CONDICION:
        L.append(f"- **Condición de operación:** sale del nombre (`Bearing1_x` = condición 1, etc.) y se "
                 f"codifica en one-hot ({N_CONDICIONES} números). Se le pega al vector de la CNN de cada "
                 "archivo antes de entrar a Mamba.")
    L.append("- **Normalización:** media y desviación por canal (H y V), calculadas solo con los "
             "rodamientos de entrenamiento de cada fold.")
    L.append("- **Validación LOBO (leave-one-bearing-out):** un entrenamiento por rodamiento de test; "
             "se deja ese rodamiento afuera y se entrena con los otros 16. No hay búsqueda de "
             "hiperparámetros dentro del fold.")
    L.append(f"- **Rodamientos probados como test:** {n_prueba} de {len(bearings)} "
             f"(`LIMITE_RODAMIENTOS = {LIMITE_RODAMIENTOS}`); siempre se entrena con los otros 16.")
    L.append(f"- **Entrenamiento:** {EPOCAS} épocas, Adam con lr cosine, pérdida SmoothL1 "
             f"(beta {BETA_SMOOTHL1}), gradiente recortado a {GRAD_CLIP}. Cada época usa 1 de cada "
             f"{PASO_ENTRENAMIENTO} ventanas (cambiando el punto de partida entre épocas), porque "
             "las ventanas consecutivas son casi iguales.")
    L.append("")
    L.append("## 3. Configuración")
    L.append("")
    L.append("### 3.1 Hiperparámetros fijos")
    L.append("")
    L.append("| Hiperparámetro | Valor | Qué hace |")
    L.append("|---|---|---|")
    L.append(f"| Condición de operación | {'one-hot de ' + str(N_CONDICIONES) + ' valores, como entrada de Mamba' if USAR_CONDICION else 'no se usa'} | Le dice al modelo en qué condición (velocidad y carga) trabaja el rodamiento |")
    L.append(f"| Filtros de la CNN | {list(CNN_FILTROS)} | Patrones distintos que busca cada capa convolucional |")
    L.append(f"| Stride / pooling de la CNN | {CNN_STRIDE} / {CNN_POOL} | Reducen la señal de 2.560 puntos a unos 160 antes de la segunda capa |")
    L.append(f"| n_capas | {HP['n_capas']} | Bloques Mamba apilados |")
    L.append(f"| hidden | {HP['hidden']} | Ancho del modelo Mamba |")
    L.append(f"| d_state | {HP['d_state']} | Memoria interna de Mamba |")
    L.append(f"| expand | {HP['expand']} | Ensanchamiento interno de cada bloque Mamba |")
    L.append(f"| d_conv | {HP['d_conv']} | Ancho de la mini convolución dentro del bloque Mamba |")
    L.append(f"| lr | {HP['lr']} | Tamaño de los pasos de corrección |")
    L.append(f"| dropout | {HP['dropout']} | Fracción de neuronas apagadas al azar al entrenar |")
    L.append(f"| batch | {HP['batch']} | Ventanas por actualización |")
    L.append("")
    L.append("### 3.2 Combinaciones (cada una es un LOBO)")
    L.append("")
    L.append("| Carpeta en `resultados/` | Kernel de la CNN | Tamaño del vector |")
    L.append("|---|---|---|")
    for c in COMBINACIONES:
        L.append(f"| `{nombres[c]}` | {c[0]} | {c[1]} |")
    L.append("")
    L.append("- **Kernel:** cuántos puntos seguidos de la señal mira cada filtro de la CNN.")
    L.append("- **Tamaño del vector:** cuántos números resumen cada archivo y se le pasan a Mamba.")
    L.append("")
    L.append("## 4. Cómo está armado el script")
    L.append("")
    L.append("`src/end_end_condition.py` es `end_end.py` más la condición de operación, dividido en secciones con encabezado:")
    L.append("")
    L.append("1. **Configuración:** todos los parámetros (condición, combinaciones, hiperparámetros, épocas, folds a correr).")
    L.append("2. **Carpetas de entrada y salida:** rutas de datos crudos, `processed`, `resultados`, `docs`, y las referencias de `rul_end_end`.")
    L.append("3. **Utilidades de consola:** barra de avance con tiempo estimado.")
    L.append("4. **Lectura de datos crudos, caché y condición:** reutiliza el caché `.npy` de `rul_end_end` si existe (si no, lee los CSV una vez); calcula la condición de cada rodamiento a partir de su nombre; carga los resultados de referencia.")
    L.append("5. **Normalización y ventanas:** estadísticas por canal con los rodamientos de entrenamiento; las ventanas se arman por índice, sin copiarlas todas en memoria.")
    L.append("6. **Red CNN:** conv1 (con stride) → ReLU → dropout → max-pool → conv2 → ReLU → dropout → promedio y máximo en el tiempo → capa lineal al tamaño del vector.")
    L.append("7. **Red Mamba:** capa lineal de entrada, bloques Mamba con RMSNorm y conexión residual, y una cabeza que entrega el RUL del último paso. El scan selectivo está escrito en PyTorch puro (sin kernels CUDA).")
    L.append("8. **Modelo completo:** la CNN procesa cada archivo de la ventana, se le pega la condición (one-hot) a cada vector y Mamba procesa la secuencia.")
    L.append("9. **Entrenamiento y predicción:** al predecir, la CNN se calcula una sola vez por archivo y las ventanas se arman sobre los vectores (mismo resultado, mucho más rápido).")
    L.append("10. **Gráficos:** los 17 rodamientos (RUL real y predicción), actualizado al terminar cada fold.")
    L.append("11. **CSV resumen y este documento.**")
    L.append("12. **Programa principal:** recorre las combinaciones y, dentro de cada una, los folds; si se corta, retoma saltando los folds terminados.")
    L.append("")
    L.append("Archivos que deja cada carpeta de `resultados/`:")
    L.append("")
    L.append("- `resumen_mae.csv`: MAE de cada rodamiento con 4 decimales y el promedio.")
    L.append("- `errores_completo.csv`: MAE y RMSE con todos los decimales, pérdida final y minutos por fold.")
    L.append("- `predicciones.csv`, `perdida_por_epoca.csv`, `configuracion.json`.")
    L.append("- `lobo_17_rodamientos.png`: gráfico de los 17 rodamientos.")
    L.append("- `folds/`: archivos por fold (permiten retomar si se corta).")
    L.append("")
    L.append("## 5. Resultados")
    L.append("")
    columnas = [(f"`{nombres[c]}`", res[c]) for c in COMBINACIONES]
    columnas += [(f"{n} (ref.)", {b: v for b, v in d.items()}) for n, d in REFS.items()]
    L.append("MAE por rodamiento de test (4 decimales). `-` = fold aún sin correr. "
             "(ref.) = resultado de `rul_end_end` ya terminado, para comparar.")
    L.append("")
    L.append("| Rodamiento | " + " | ".join(t for t, _ in columnas) + " |")
    L.append("|---|" + "---|" * len(columnas))
    for b in bearings:
        fila = [f"{d[b][0]:.4f}" if b in d else "-" for _, d in columnas]
        if all(x == "-" for x in fila):
            continue
        L.append(f"| {b} | " + " | ".join(fila) + " |")
    prop = [f"{np.mean([v[0] for v in d.values()]):.4f}" if d else "-" for _, d in columnas]
    L.append("| **Promedio propio** | " + " | ".join(f"**{p}**" for p in prop) + " |")
    comunes = [b for b in bearings if all(b in d for _, d in columnas)]
    if comunes:
        pc = [f"{np.mean([d[b][0] for b in comunes]):.4f}" for _, d in columnas]
        L.append(f"| **Promedio en comunes (n={len(comunes)})** | " +
                 " | ".join(f"**{p}**" for p in pc) + " |")
    celdas = [f"{len(res[c])}/{n_prueba}" for c in COMBINACIONES] + ["-" for _ in REFS]
    L.append("| Folds hechos | " + " | ".join(celdas) + " |")
    L.append("")
    L.append("> **Nota:** una sola corrida por configuración y sin repeticiones con otras semillas; "
             "las diferencias pequeñas entre columnas pueden ser azar. Para comparar de forma justa, "
             "usar el promedio en los rodamientos comunes.")
    L.append("")
    (DOCS_DIR / "resumen_experimentos.md").write_text("\n".join(L), encoding="utf-8")


# ============================================================
# 12. PROGRAMA PRINCIPAL
# ============================================================

def correr_combinacion(ic, n_comb, kernel, vector, senal, y, tiempo, bearings, a_probar,
                       dispositivo):
    out_dir = carpeta_corrida(kernel, vector)
    folds_dir = out_dir / "folds"
    folds_dir.mkdir(parents=True, exist_ok=True)

    modelo_tmp = ModeloEndEnd(kernel, vector, HP, n_cond_modelo())
    n_par = contar_parametros(modelo_tmp)
    n_cnn = contar_parametros(modelo_tmp.cnn)
    del modelo_tmp
    print("=" * 100)
    print(f"Combinacion {ic + 1}/{n_comb}: kernel {kernel}, vector {vector}, "
          f"condicion {'SI' if USAR_CONDICION else 'NO'}  ->  {out_dir.name}")
    print(f"   Parametros: {n_par:,} (CNN {n_cnn:,} + Mamba {n_par - n_cnn:,})")

    (out_dir / "configuracion.json").write_text(json.dumps({
        "kernel": kernel, "vector": vector, "USAR_CONDICION": USAR_CONDICION,
        "N_CONDICIONES": N_CONDICIONES, "HP": HP, "CNN_FILTROS": CNN_FILTROS,
        "CNN_STRIDE": CNN_STRIDE, "CNN_POOL": CNN_POOL, "EPOCAS": EPOCAS,
        "PASO_ENTRENAMIENTO": PASO_ENTRENAMIENTO, "LONG_SECUENCIA": LONG_SECUENCIA,
        "SEMILLA": SEMILLA, "LIMITE_RODAMIENTOS": LIMITE_RODAMIENTOS,
        "canales": ["H", "V"], "rodamientos": bearings,
    }, indent=2, default=list), encoding="utf-8")

    preds, maes = escribir_csvs(out_dir, bearings, a_probar)
    titulo = (f"CNN + Mamba{' + condicion' if USAR_CONDICION else ''}, LOBO  |  "
              f"kernel {kernel}, vector {vector}")
    N = len(a_probar)
    barra = Barra()

    def txt_ref(b):
        return "".join(f"   [{n}: {d[b][0]:.4f}]" for n, d in REFS.items() if b in d)

    for k, b in enumerate(a_probar):
        if fold_hecho(folds_dir, b):
            barra.mensaje(f"  [{k + 1:2d}/{N}] {b:<11s} ya estaba hecho  MAE {maes[b]:.4f}"
                          f"{txt_ref(b)}")
            continue

        if not barra.activa:
            barra.iniciar(k / N)
        t0 = time.time()
        train_ids = [x for x in bearings if x != b]

        def cb(epoca, frac_ep, perdida_prev, k=k, b=b):
            frac = (k + ((epoca - 1) + frac_ep) / EPOCAS) / N
            barra.actualizar(frac, f"fold {k + 1}/{N} {b} ep {epoca}/{EPOCAS} "
                                   f"loss {perdida_prev:.4f}")

        modelo, norma, perdidas = entrenar(senal, y, train_ids, kernel, vector,
                                           SEMILLA + bearings.index(b), dispositivo, cb)
        pred = predecir(modelo, senal[b], norma,
                        one_hot_condicion(b) if USAR_CONDICION else None, dispositivo)
        del modelo

        df_pred = pd.DataFrame({BEARING_COL: b, TIME_COL: tiempo[b],
                                "rul_real": y[b], "rul_pred": pred})
        df_pred.to_csv(folds_dir / f"{b}_pred.csv", index=False)
        pd.DataFrame({BEARING_COL: b, "epoca": range(1, len(perdidas) + 1),
                      "perdida_entrenamiento": perdidas}).to_csv(
            folds_dir / f"{b}_loss.csv", index=False)
        mae, rmse = errores_de(df_pred)
        seg = time.time() - t0
        (folds_dir / f"{b}_info.json").write_text(json.dumps({
            "mae": mae, "rmse": rmse, "segundos": seg, "perdida_final": perdidas[-1],
        }), encoding="utf-8")

        preds, maes = escribir_csvs(out_dir, bearings, a_probar)
        graficar(bearings, preds, maes, out_dir / "lobo_17_rodamientos.png",
                 f"{titulo}  ({len(maes)}/{N} rodamientos)")
        escribir_docs(bearings, a_probar)
        barra.mensaje(f"  [{k + 1:2d}/{N}] {b:<11s} MAE {mae:.4f}   RMSE {rmse:.4f}   "
                      f"({fmt_tiempo(seg)})   promedio parcial {np.mean(list(maes.values())):.4f}"
                      f"{txt_ref(b)}")
    barra.cerrar()

    preds, maes = escribir_csvs(out_dir, bearings, a_probar)
    if maes:
        graficar(bearings, preds, maes, out_dir / "lobo_17_rodamientos.png",
                 f"{titulo}  ({len(maes)}/{N} rodamientos)")
        escribir_docs(bearings, a_probar)
        print(f"   Combinacion lista: MAE promedio {np.mean(list(maes.values())):.4f} "
              f"({len(maes)}/{N} rodamientos)  ->  {out_dir}")
        for nombre, d in REFS.items():
            comunes = [b for b in maes if b in d]
            if comunes:
                a = np.mean([maes[b] for b in comunes])
                r = np.mean([d[b][0] for b in comunes])
                print(f"   Frente a '{nombre}': {a:.4f} contra {r:.4f} en {len(comunes)} "
                      f"rodamientos (diferencia {a - r:+.4f}; negativa = mejor)")
    return maes


def main():
    if N_HILOS is not None:
        torch.set_num_threads(N_HILOS)
    if DISPOSITIVO == "auto":
        dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        dispositivo = DISPOSITIVO

    raw_dir = encontrar_raw()
    senal, y, tiempo = cargar_senales(raw_dir)
    bearings = list(senal.keys())
    a_probar = bearings if LIMITE_RODAMIENTOS is None else bearings[:LIMITE_RODAMIENTOS]
    REFS.update(cargar_referencias(bearings))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nRodamientos: {len(bearings)}  |  Folds de test por combinacion: {len(a_probar)}  |  "
          f"Archivos: {sum(len(x) for x in senal.values()):,}")
    print(f"Condicion de operacion como entrada: {'SI' if USAR_CONDICION else 'NO'}")
    print(f"Combinaciones: {len(COMBINACIONES)}  {COMBINACIONES}")
    print(f"Epocas: {EPOCAS}  |  Paso de entrenamiento: {PASO_ENTRENAMIENTO}  |  "
          f"L: {LONG_SECUENCIA}  |  Dispositivo: {dispositivo}  |  Hilos CPU: {torch.get_num_threads()}")
    print(f"Datos: {raw_dir}\nSalidas: {BASE_DIR}\n")
    escribir_docs(bearings, a_probar)

    t_total = time.time()
    promedios = {}
    for ic, (kernel, vector) in enumerate(COMBINACIONES):
        maes = correr_combinacion(ic, len(COMBINACIONES), kernel, vector, senal, y, tiempo,
                                  bearings, a_probar, dispositivo)
        if maes:
            promedios[(kernel, vector)] = (float(np.mean(list(maes.values()))), len(maes))

    print("\n" + "=" * 100)
    print(f"Tiempo total de esta ejecucion: {fmt_tiempo(time.time() - t_total)}")
    print("MAE promedio por combinacion:")
    for (k, v), (m, n) in promedios.items():
        print(f"   kernel {k:>2d}, vector {v:>2d}:  {m:.4f}   ({n}/{len(a_probar)} rodamientos)")
    print(f"\nResumen del experimento: {DOCS_DIR / 'resumen_experimentos.md'}")
    print("Listo.")


if __name__ == "__main__":
    main()
