"""Pruebas del cargador Yahoo Finance (sin llamadas reales a la API)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.data.yfinance_loader import (
    ParametrosDescarga,
    _alinear_y_limpiar_precios,
    descargar_y_validar_datos,
    parsear_tickers,
    validar_parametros_descarga,
)
from src.finance.periodicidad import FRECUENCIA_MENSUAL


def test_parsear_tickers_elimina_vacios_y_duplicados():
    assert parsear_tickers("aapl; MSFT ;aapl; GOOGL") == ["AAPL", "MSFT", "GOOGL"]


def test_validar_parametros_rechaza_lista_vacia():
    with pytest.raises(ValueError, match="al menos un ticker"):
        validar_parametros_descarga(
            [], date(2020, 1, 1), date(2024, 1, 1), FRECUENCIA_MENSUAL
        )


def test_validar_parametros_rechaza_mas_de_20():
    tickers = [f"T{i}" for i in range(21)]
    with pytest.raises(ValueError, match="Máximo 20"):
        validar_parametros_descarga(
            tickers, date(2020, 1, 1), date(2024, 1, 1), FRECUENCIA_MENSUAL
        )


def test_validar_parametros_rechaza_fechas_invertidas():
    with pytest.raises(ValueError, match="fecha de inicio"):
        validar_parametros_descarga(
            ["AAPL"], date(2024, 1, 1), date(2020, 1, 1), FRECUENCIA_MENSUAL
        )


def _mock_download(tickers, start, end, interval, **kwargs):
    fechas = pd.date_range("2020-01-01", periods=24, freq="MS")
    rng = np.random.default_rng(1)
    columnas = {}
    for t in tickers:
        columnas[("Close", t)] = 100 * np.cumprod(1 + rng.normal(0.01, 0.02, 24))
    return pd.DataFrame(columnas, index=fechas)


def test_descargar_y_validar_datos_mock():
    parametros = ParametrosDescarga(
        tickers_portafolio=["AAPL", "MSFT"],
        ticker_benchmark="SPY",
        fecha_inicio=date(2020, 1, 1),
        fecha_fin=date(2024, 1, 1),
        frecuencia=FRECUENCIA_MENSUAL,
    )
    resultado = descargar_y_validar_datos(parametros, download_fn=_mock_download)

    assert resultado.activos_validos == ["AAPL", "MSFT"]
    assert resultado.benchmark == "SPY"
    assert "SPY" in resultado.precios.columns
    assert len(resultado.precios) == 24


def test_alinear_rellena_hueco_puntual():
    fechas = pd.date_range("2020-01-31", periods=24, freq="ME")
    valores = np.linspace(100, 120, 24)
    valores[5] = np.nan
    precios = pd.DataFrame({"DE": valores}, index=fechas)
    limpio, rellenos = _alinear_y_limpiar_precios(precios, FRECUENCIA_MENSUAL)
    assert limpio["DE"].isna().sum() == 0
    assert rellenos.get("DE", 0) >= 1


def test_descargar_recupera_ticker_con_hueco_en_batch():
    fechas = pd.date_range("2020-01-01", periods=24, freq="MS")

    def mock_batch(tickers, start, end, interval, **kwargs):
        datos = {}
        for t in tickers:
            serie = np.linspace(100, 120, 24)
            if t == "DE":
                serie[3] = np.nan
            datos[("Close", t)] = serie
        return pd.DataFrame(datos, index=fechas)

    def mock_individual(ticker, start, end, interval, **kwargs):
        return mock_batch([ticker], start, end, interval)

    llamadas = {"n": 0}

    def download_router(tickers, start, end, interval, **kwargs):
        if isinstance(tickers, str):
            tickers = [tickers]
        llamadas["n"] += 1
        if len(tickers) == 1:
            return mock_individual(tickers[0], start, end, interval)
        return mock_batch(tickers, start, end, interval)

    parametros = ParametrosDescarga(
        tickers_portafolio=["AAPL", "DE"],
        ticker_benchmark="SPY",
        fecha_inicio=date(2020, 1, 1),
        fecha_fin=date(2024, 1, 1),
        frecuencia=FRECUENCIA_MENSUAL,
    )
    resultado = descargar_y_validar_datos(parametros, download_fn=download_router)
    assert "DE" in resultado.activos_validos
    assert "DE" not in resultado.activos_excluidos


def test_descargar_omite_activo_con_nan():
    def mock_con_nan(tickers, start, end, interval, **kwargs):
        fechas = pd.date_range("2020-01-01", periods=24, freq="MS")
        datos = {
            ("Close", "AAPL"): np.linspace(100, 120, 24),
            ("Close", "BAD"): [np.nan] * 24,
            ("Close", "SPY"): np.linspace(400, 420, 24),
        }
        return pd.DataFrame(datos, index=fechas)

    parametros = ParametrosDescarga(
        tickers_portafolio=["AAPL", "BAD"],
        ticker_benchmark="SPY",
        fecha_inicio=date(2020, 1, 1),
        fecha_fin=date(2024, 1, 1),
        frecuencia=FRECUENCIA_MENSUAL,
    )
    resultado = descargar_y_validar_datos(parametros, download_fn=mock_con_nan)

    assert resultado.activos_validos == ["AAPL"]
    assert "BAD" in resultado.activos_excluidos
