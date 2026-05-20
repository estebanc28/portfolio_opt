"""Pruebas de frecuencias y anualización (Fase 3)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.finance.configuracion import anual_a_periodo
from src.finance.metricas import (
    calcular_rendimiento_esperado_anualizado,
    calcular_rendimientos,
    calcular_volatilidad_anualizada,
)
from src.finance.periodicidad import (
    FRECUENCIA_DIARIA,
    FRECUENCIA_MENSUAL,
    FRECUENCIA_SEMANAL,
    validar_rango_fechas,
)


def test_anual_a_periodo_mensual_equivale_a_mensual():
    tasa = 0.04
    assert np.isclose(
        anual_a_periodo(tasa, 12),
        (1 + tasa) ** (1 / 12) - 1,
    )


def test_volatilidad_escala_con_periodos_por_anio():
    fechas = pd.date_range("2020-01-01", periods=100, freq="D")
    precios = pd.DataFrame({"A": 100 * (1.001 ** np.arange(100))}, index=fechas)
    rend = calcular_rendimientos(precios)
    vol_252 = float(calcular_volatilidad_anualizada(rend["A"], periodos_por_anio=252))
    vol_12 = float(calcular_volatilidad_anualizada(rend["A"], periodos_por_anio=12))
    assert vol_252 > vol_12


def test_validar_rango_diario_rechaza_periodo_largo():
    inicio = date(2020, 1, 1)
    fin = inicio + timedelta(days=800)
    with pytest.raises(ValueError, match="rango máximo"):
        validar_rango_fechas(inicio, fin, FRECUENCIA_DIARIA)


def test_frecuencias_tienen_intervalos_yfinance():
    assert FRECUENCIA_MENSUAL.intervalo_yfinance == "1mo"
    assert FRECUENCIA_SEMANAL.intervalo_yfinance == "1wk"
    assert FRECUENCIA_DIARIA.intervalo_yfinance == "1d"
    assert FRECUENCIA_DIARIA.periodos_por_anio == 252
