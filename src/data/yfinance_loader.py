"""
Descarga y validación de precios desde Yahoo Finance (yfinance).
Soporta frecuencias mensual, semanal y diaria (Fase 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.config import MAX_TICKERS_PORTAFOLIO, OPCIONES_BENCHMARK
from src.data.loader import ResultadoCargaDatos
from src.finance.periodicidad import (
    FRECUENCIA_DEFECTO,
    FrecuenciaDatos,
    obtener_frecuencia,
    validar_rango_fechas,
)

ORIGEN_DATOS = Path("yfinance")


@dataclass(frozen=True)
class ParametrosDescarga:
    """Parámetros de una descarga vía yfinance."""

    tickers_portafolio: list[str]
    ticker_benchmark: str
    fecha_inicio: date
    fecha_fin: date
    frecuencia: FrecuenciaDatos


def parsear_tickers(texto: str) -> list[str]:
    """Convierte tickers separados por ';' en lista única en mayúsculas."""
    vistos: set[str] = set()
    resultado: list[str] = []
    for parte in texto.split(";"):
        ticker = parte.strip().upper()
        if not ticker or ticker in vistos:
            continue
        vistos.add(ticker)
        resultado.append(ticker)
    return resultado


def validar_parametros_descarga(
    tickers_portafolio: list[str],
    fecha_inicio: date,
    fecha_fin: date,
    frecuencia: FrecuenciaDatos,
    max_tickers: int = MAX_TICKERS_PORTAFOLIO,
) -> None:
    """Valida entradas antes de llamar a la API."""
    if not tickers_portafolio:
        raise ValueError("Ingrese al menos un ticker del portafolio (separados por ';').")
    if len(tickers_portafolio) > max_tickers:
        raise ValueError(
            f"Máximo {max_tickers} tickers en el portafolio; ingresó {len(tickers_portafolio)}."
        )
    validar_rango_fechas(fecha_inicio, fecha_fin, frecuencia)


def ticker_benchmark_desde_etiqueta(etiqueta: str) -> str:
    if etiqueta not in OPCIONES_BENCHMARK:
        raise ValueError(f"Benchmark no reconocido: {etiqueta}")
    return OPCIONES_BENCHMARK[etiqueta]


def _extraer_precios_cierre(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        raise ValueError("Yahoo Finance no devolvió datos para el rango y tickers indicados.")

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            precios = raw["Close"].copy()
        elif "Adj Close" in raw.columns.get_level_values(0):
            precios = raw["Adj Close"].copy()
        else:
            raise ValueError("No se encontró la columna de precios de cierre en la respuesta.")
    else:
        columna = "Close" if "Close" in raw.columns else "Adj Close"
        if columna not in raw.columns:
            raise ValueError("No se encontró la columna de precios de cierre en la respuesta.")
        precios = raw[[columna]].copy()
        precios.columns = [tickers[0]]

    if isinstance(precios, pd.Series):
        precios = precios.to_frame(name=tickers[0])

    precios.columns = [str(c).upper() for c in precios.columns]
    precios.index = pd.to_datetime(precios.index)
    precios = precios.sort_index()
    precios.index.name = "fecha"
    return precios


def _alinear_y_limpiar_precios(
    precios: pd.DataFrame,
    frecuencia: FrecuenciaDatos,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Alinea cada serie a la frecuencia elegida y rellena huecos cortos."""
    rellenos: dict[str, int] = {}
    series: dict[str, pd.Series] = {}
    limite_ffill = frecuencia.max_relleno_ffill

    for col in precios.columns:
        ticker = str(col).upper()
        s = precios[col].copy()
        s.index = pd.to_datetime(s.index)
        s = s[~s.index.duplicated(keep="last")].sort_index()

        if s.notna().sum() == 0:
            series[ticker] = s
            continue

        alineado = s.resample(frecuencia.regla_resample).last()
        faltantes_antes = int(alineado.isna().sum())
        limpio = alineado.ffill(limit=limite_ffill).bfill(limit=limite_ffill)
        rellenados = faltantes_antes - int(limpio.isna().sum())
        if rellenados > 0:
            rellenos[ticker] = rellenados
        series[ticker] = limpio

    if not series:
        return precios.iloc[0:0].copy(), rellenos

    resultado = pd.DataFrame(series).sort_index()
    resultado.index.name = "fecha"
    return resultado, rellenos


def _descargar_serie_individual(
    download_fn,
    ticker: str,
    fecha_inicio: date,
    fecha_fin: date,
    frecuencia: FrecuenciaDatos,
) -> pd.Series:
    raw = download_fn(
        tickers=ticker,
        start=fecha_inicio.isoformat(),
        end=fecha_fin.isoformat(),
        interval=frecuencia.intervalo_yfinance,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    marco = _extraer_precios_cierre(raw, [ticker])
    if ticker not in marco.columns:
        return pd.Series(dtype=float, name=ticker)
    alineado, _ = _alinear_y_limpiar_precios(marco, frecuencia)
    return alineado[ticker]


def _completar_tickers_incompletos(
    precios: pd.DataFrame,
    tickers: list[str],
    download_fn,
    parametros: ParametrosDescarga,
) -> pd.DataFrame:
    resultado = precios.copy()
    frecuencia = parametros.frecuencia
    limite = frecuencia.max_relleno_ffill

    for ticker in tickers:
        if ticker not in resultado.columns:
            continue
        if not resultado[ticker].isna().any():
            continue
        serie = _descargar_serie_individual(
            download_fn,
            ticker,
            parametros.fecha_inicio,
            parametros.fecha_fin,
            frecuencia,
        )
        if serie.empty:
            continue
        resultado[ticker] = serie.reindex(resultado.index)
        if resultado[ticker].isna().any():
            resultado[ticker] = resultado[ticker].ffill(limit=limite).bfill(limit=limite)
    return resultado


def _recortar_inicio_comun(
    precios: pd.DataFrame,
    tickers: list[str],
) -> pd.DataFrame:
    inicio = precios.index.min()
    for ticker in tickers:
        if ticker not in precios.columns:
            continue
        primer_dato = precios[ticker].first_valid_index()
        if primer_dato is not None:
            inicio = max(inicio, primer_dato)
    return precios.loc[precios.index >= inicio].copy()


def _validar_dataframe_precios(
    precios: pd.DataFrame,
    parametros: ParametrosDescarga,
    rellenos: dict[str, int] | None = None,
) -> ResultadoCargaDatos:
    frecuencia = parametros.frecuencia
    tickers_portafolio = parametros.tickers_portafolio
    ticker_benchmark = parametros.ticker_benchmark
    min_obs = frecuencia.min_observaciones
    unidad = frecuencia.nombre_unidad

    mensajes: list[str] = []
    activos_excluidos: list[str] = []
    activos_validos: list[str] = []

    if rellenos:
        for ticker, cantidad in sorted(rellenos.items()):
            if cantidad > 0 and ticker in tickers_portafolio:
                mensajes.append(
                    f"Advertencia: se completaron {cantidad} {unidad}(es) faltantes en "
                    f"{ticker} con el último precio disponible."
                )

    for ticker in tickers_portafolio:
        if ticker not in precios.columns:
            activos_excluidos.append(ticker)
            mensajes.append(f"No se obtuvieron datos para el ticker {ticker}.")
            continue
        serie = precios[ticker]
        n_validos = int(serie.notna().sum())
        if n_validos < min_obs:
            activos_excluidos.append(ticker)
            mensajes.append(
                f"Se omitió {ticker}: solo hay {n_validos} {unidad}(es) con precio "
                f"(mínimo recomendado: {min_obs})."
            )
            continue
        if serie.isna().any():
            activos_excluidos.append(ticker)
            mensajes.append(
                f"Se omitió {ticker} por datos incompletos tras limpiar y reintentar la descarga."
            )
        else:
            activos_validos.append(ticker)

    if not activos_validos:
        raise ValueError(
            "No quedó ningún activo del portafolio con datos completos tras la validación."
        )

    columnas_finales = list(activos_validos)
    benchmark_ok = False

    if ticker_benchmark not in precios.columns:
        mensajes.append(f"No se obtuvieron datos para el benchmark {ticker_benchmark}.")
    elif precios[ticker_benchmark].isna().any():
        mensajes.append(
            f"Se omitió el benchmark {ticker_benchmark} por datos incompletos."
        )
    else:
        columnas_finales.append(ticker_benchmark)
        benchmark_ok = True

    columnas_trabajo = tickers_portafolio + (
        [ticker_benchmark] if ticker_benchmark not in tickers_portafolio else []
    )
    precios_recortados = _recortar_inicio_comun(precios, columnas_trabajo)

    if len(precios_recortados) < min_obs:
        mensajes.append(
            f"Advertencia: tras alinear el período común quedaron "
            f"{len(precios_recortados)} observaciones "
            f"(recomendado: al menos {min_obs} {unidad}(es))."
        )

    precios_final = precios_recortados[columnas_finales].copy()
    etiqueta_benchmark = ticker_benchmark if benchmark_ok else ""

    return ResultadoCargaDatos(
        precios=precios_final,
        activos_validos=activos_validos,
        benchmark=etiqueta_benchmark,
        activos_excluidos=activos_excluidos,
        mensajes=mensajes,
        ruta_csv=ORIGEN_DATOS,
        nombre_archivo=(
            f"Yahoo Finance ({frecuencia.etiqueta}, {frecuencia.intervalo_yfinance})"
        ),
    )


def descargar_y_validar_datos(
    parametros: ParametrosDescarga,
    *,
    download_fn=None,
) -> ResultadoCargaDatos:
    """Descarga precios con yfinance y devuelve un ResultadoCargaDatos."""
    validar_parametros_descarga(
        parametros.tickers_portafolio,
        parametros.fecha_inicio,
        parametros.fecha_fin,
        parametros.frecuencia,
    )

    if download_fn is None:
        import yfinance as yf

        download_fn = yf.download

    frecuencia = parametros.frecuencia
    tickers_unicos = list(parametros.tickers_portafolio)
    if parametros.ticker_benchmark not in tickers_unicos:
        tickers_descarga = tickers_unicos + [parametros.ticker_benchmark]
    else:
        tickers_descarga = tickers_unicos

    raw = download_fn(
        tickers=tickers_descarga,
        start=parametros.fecha_inicio.isoformat(),
        end=parametros.fecha_fin.isoformat(),
        interval=frecuencia.intervalo_yfinance,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )

    precios = _extraer_precios_cierre(raw, tickers_descarga)
    precios, rellenos = _alinear_y_limpiar_precios(precios, frecuencia)

    incompletos = [
        t
        for t in tickers_descarga
        if t in precios.columns and precios[t].isna().any()
    ]
    if incompletos:
        precios = _completar_tickers_incompletos(
            precios, incompletos, download_fn, parametros
        )

    return _validar_dataframe_precios(precios, parametros, rellenos=rellenos)


def descargar_desde_texto(
    texto_tickers: str,
    etiqueta_benchmark: str,
    fecha_inicio: date,
    fecha_fin: date,
    etiqueta_frecuencia: str = FRECUENCIA_DEFECTO,
    *,
    download_fn=None,
) -> ResultadoCargaDatos:
    """Atajo: parsea tickers, resuelve benchmark/frecuencia y descarga."""
    tickers = parsear_tickers(texto_tickers)
    benchmark = ticker_benchmark_desde_etiqueta(etiqueta_benchmark)
    frecuencia = obtener_frecuencia(etiqueta_frecuencia)
    parametros = ParametrosDescarga(
        tickers_portafolio=tickers,
        ticker_benchmark=benchmark,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        frecuencia=frecuencia,
    )
    return descargar_y_validar_datos(parametros, download_fn=download_fn)
