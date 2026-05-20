"""
Fase 2 — Backend de cálculos cuantitativos (métricas auxiliares).

Este módulo prepara las fórmulas de riesgo y rendimiento necesarias para el análisis
de portafolios. Corresponde a la Fase 2 del proyecto.

Importante: en esta fase NO se implementa optimización de Markowitz ni frontera eficiente.
Eso corresponde a una fase posterior (Fase 3).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Factores de anualización (Fase 3: 12 mensual, 52 semanal, 252 diario)
PERIODOS_POR_ANIO_DEFECTO = 12
MESES_POR_ANIO = PERIODOS_POR_ANIO_DEFECTO  # alias retrocompatible


def calcular_rendimientos(precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula rendimientos históricos por periodo a partir de precios.

    Usa rendimientos simples: r_t = P_t / P_{t-1} - 1

    Parámetros
    ----------
    precios : pd.DataFrame
        Precios históricos con índice temporal (fechas) y una columna por activo.

    Retorna
    -------
    pd.DataFrame
        Rendimientos por periodo (sin la primera fila NaN).
    """
    if precios.empty:
        raise ValueError("El DataFrame de precios está vacío.")

    rendimientos = precios.pct_change()
    return rendimientos.dropna(how="all")


def _anualizar_rendimiento_multiplicativo(
    rendimientos_periodo: pd.Series,
    periodos_por_anio: int = PERIODOS_POR_ANIO_DEFECTO,
) -> float:
    """
    Anualiza el rendimiento esperado con capitalización compuesta.

    Fórmula: r_anual = [ Π (1 + r_t) ]^(P / n) - 1, con P = periodos por año.
    """
    if rendimientos_periodo.empty:
        raise ValueError("La serie de rendimientos está vacía.")

    n = len(rendimientos_periodo)
    producto_uno_mas_r = float((1.0 + rendimientos_periodo).prod())
    return producto_uno_mas_r ** (periodos_por_anio / n) - 1.0


def calcular_rendimiento_esperado_anualizado(
    rendimientos: pd.DataFrame | pd.Series,
    periodos_por_anio: int = PERIODOS_POR_ANIO_DEFECTO,
    *,
    meses_por_anio: int | None = None,
) -> pd.Series | float:
    """
    Calcula el rendimiento esperado anualizado por activo (fórmula multiplicativa).

    Parámetros
    ----------
    rendimientos : pd.DataFrame | pd.Series
        Rendimientos mensuales históricos.
    periodos_por_anio : int
        Factor de anualización (12, 52 o 252 según la frecuencia).
    meses_por_anio : int | None
        Alias retrocompatible; si se indica, sustituye a periodos_por_anio.

    Retorna
    -------
    pd.Series | float
        Rendimiento anualizado por columna, o escalar si la entrada es una Serie.
    """
    p = meses_por_anio if meses_por_anio is not None else periodos_por_anio

    if isinstance(rendimientos, pd.Series):
        return _anualizar_rendimiento_multiplicativo(rendimientos, p)

    if rendimientos.empty:
        raise ValueError("El DataFrame de rendimientos está vacío.")

    return rendimientos.apply(
        _anualizar_rendimiento_multiplicativo,
        periodos_por_anio=p,
    )


def calcular_volatilidad_anualizada(
    rendimientos: pd.DataFrame | pd.Series,
    periodos_por_anio: int = PERIODOS_POR_ANIO_DEFECTO,
    grados_libertad: int = 1,
    *,
    meses_por_anio: int | None = None,
) -> pd.Series | float:
    """
    Calcula la volatilidad anualizada (fórmula multiplicativa estándar).

    La volatilidad NO se obtiene multiplicando por 12, sino escalando con la raíz
    del número de periodos al año (supuesto de independencia mensual):

        σ_anual = σ_mensual × √(12)

    Parámetros
    ----------
    rendimientos : pd.DataFrame | pd.Series
        Rendimientos mensuales históricos.
    periodos_por_anio : int
        Periodos por año (12, 52 o 252).
    meses_por_anio : int | None
        Alias retrocompatible.
    grados_libertad : int
        Grados de libertad para la desviación estándar muestral (default 1).

    Retorna
    -------
    pd.Series | float
        Volatilidad anualizada por activo, o escalar si la entrada es una Serie.
    """
    p = meses_por_anio if meses_por_anio is not None else periodos_por_anio
    factor = float(np.sqrt(p))
    vol_mensual = rendimientos.std(ddof=grados_libertad)
    return vol_mensual * factor


def calcular_matriz_covarianza(
    rendimientos: pd.DataFrame,
    grados_libertad: int = 1,
) -> pd.DataFrame:
    """
    Calcula la matriz de covarianzas entre activos (base mensual).

    Parámetros
    ----------
    rendimientos : pd.DataFrame
        Rendimientos mensuales históricos.
    grados_libertad : int
        Grados de libertad para la covarianza muestral.

    Retorna
    -------
    pd.DataFrame
        Matriz de covarianzas (activos × activos).
    """
    if rendimientos.empty:
        raise ValueError("El DataFrame de rendimientos está vacío.")

    return rendimientos.cov()


def calcular_matriz_correlacion(rendimientos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la matriz de correlaciones entre activos.

    Parámetros
    ----------
    rendimientos : pd.DataFrame
        Rendimientos mensuales históricos.

    Retorna
    -------
    pd.DataFrame
        Matriz de correlaciones (activos × activos), valores entre -1 y 1.
    """
    if rendimientos.empty:
        raise ValueError("El DataFrame de rendimientos está vacío.")

    return rendimientos.corr()


def calcular_metricas_activos(
    precios: pd.DataFrame,
    periodos_por_anio: int = PERIODOS_POR_ANIO_DEFECTO,
) -> pd.DataFrame:
    """
    Pipeline auxiliar de Fase 2: rendimientos y métricas anualizadas por activo.

    No incluye optimización. Útil para validar el backend antes de la Fase 3.

    Retorna un DataFrame con columnas:
        rendimiento_esperado_anual, volatilidad_anual
    """
    rendimientos = calcular_rendimientos(precios)
    retorno_anual = calcular_rendimiento_esperado_anualizado(
        rendimientos, periodos_por_anio
    )
    vol_anual = calcular_volatilidad_anualizada(rendimientos, periodos_por_anio)

    return pd.DataFrame(
        {
            "rendimiento_esperado_anual": retorno_anual,
            "volatilidad_anual": vol_anual,
        }
    )
