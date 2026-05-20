"""
Caché de resultados finales (tabla de pesos y evolución histórica).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.finance.resultados import VALOR_INICIAL_DEFECTO, calcular_resultados_finales
from src.visualization.evolucion import crear_grafico_evolucion_historica


@st.cache_data(show_spinner=False)
def obtener_resultados_finales(
    precios: pd.DataFrame,
    activos_validos: tuple[str, ...],
    activos_seleccionados: tuple[str, ...],
    pesos_forzados: tuple[tuple[str, float], ...],
    tasa_libre_riesgo_anual: float,
    ticker_benchmark: str,
    periodos_por_anio: int,
    _version: int = 9,
) -> tuple[
    pd.DataFrame,
    object,
    list[str],
    dict[str, float],
    dict[str, float],
    float,
    float,
    float | None,
    list[str],
]:
    """
    Calcula y cachea tabla de pesos, gráfico y valores finales de cada escenario.

    Retorna también ``sin_peso_final``: activos seleccionados con peso optimizado 0 %
    (no entran en la tabla de pesos).
    """
    forzados = dict(pesos_forzados)
    datos = calcular_resultados_finales(
        precios=precios,
        activos_validos=list(activos_validos),
        activos_seleccionados=list(activos_seleccionados),
        tasa_libre_riesgo_anual=tasa_libre_riesgo_anual,
        pesos_forzados=forzados,
        ticker_benchmark=ticker_benchmark,
        valor_inicial=VALOR_INICIAL_DEFECTO,
        periodos_por_anio=periodos_por_anio,
    )
    figura = crear_grafico_evolucion_historica(datos)

    final_igual = float(datos.evolucion_igual.iloc[-1])
    final_opt = float(datos.evolucion_optimizado.iloc[-1])
    final_bench = (
        float(datos.evolucion_benchmark.iloc[-1])
        if datos.evolucion_benchmark is not None
        else None
    )

    pesos_igual = {
        t: float(datos.pesos_iguales[t])
        for t in datos.activos_seleccionados
        if float(datos.pesos_iguales[t]) > 0
    }
    pesos_opt = {
        t: float(datos.pesos_optimizados[t])
        for t in datos.activos_seleccionados
        if float(datos.pesos_optimizados[t]) > 0
    }

    sin_peso_final = sorted(
        t
        for t in datos.activos_seleccionados
        if float(datos.pesos_optimizados[t]) < 1e-10
    )

    return (
        datos.tabla_pesos,
        figura,
        datos.activos_no_utilizados,
        pesos_igual,
        pesos_opt,
        final_igual,
        final_opt,
        final_bench,
        sin_peso_final,
    )


def invalidar_cache_resultados() -> None:
    obtener_resultados_finales.clear()
