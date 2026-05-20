"""
Frecuencias de datos y factores de anualización (Fase 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class FrecuenciaDatos:
    """Metadatos de una frecuencia soportada por yfinance y los cálculos MPT."""

    etiqueta: str
    intervalo_yfinance: str
    periodos_por_anio: int
    regla_resample: str
    min_observaciones: int
    max_relleno_ffill: int
    nombre_unidad: str
    max_dias_rango: int | None = None


FRECUENCIA_MENSUAL = FrecuenciaDatos(
    etiqueta="Mensual",
    intervalo_yfinance="1mo",
    periodos_por_anio=12,
    regla_resample="ME",
    min_observaciones=12,
    max_relleno_ffill=2,
    nombre_unidad="mes",
)

FRECUENCIA_SEMANAL = FrecuenciaDatos(
    etiqueta="Semanal",
    intervalo_yfinance="1wk",
    periodos_por_anio=52,
    regla_resample="W-FRI",
    min_observaciones=52,
    max_relleno_ffill=3,
    nombre_unidad="semana",
    max_dias_rango=365 * 12,
)

FRECUENCIA_DIARIA = FrecuenciaDatos(
    etiqueta="Diaria",
    intervalo_yfinance="1d",
    periodos_por_anio=252,
    regla_resample="D",
    min_observaciones=252,
    max_relleno_ffill=5,
    nombre_unidad="día",
    max_dias_rango=730,
)

OPCIONES_FRECUENCIA: dict[str, FrecuenciaDatos] = {
    FRECUENCIA_MENSUAL.etiqueta: FRECUENCIA_MENSUAL,
    FRECUENCIA_SEMANAL.etiqueta: FRECUENCIA_SEMANAL,
    FRECUENCIA_DIARIA.etiqueta: FRECUENCIA_DIARIA,
}

FRECUENCIA_DEFECTO = FRECUENCIA_MENSUAL.etiqueta


def obtener_frecuencia(etiqueta: str) -> FrecuenciaDatos:
    if etiqueta not in OPCIONES_FRECUENCIA:
        raise ValueError(f"Frecuencia no reconocida: {etiqueta}")
    return OPCIONES_FRECUENCIA[etiqueta]


def validar_rango_fechas(
    fecha_inicio: date,
    fecha_fin: date,
    frecuencia: FrecuenciaDatos,
) -> None:
    if fecha_inicio >= fecha_fin:
        raise ValueError("La fecha de inicio debe ser anterior a la fecha de fin.")

    dias = (fecha_fin - fecha_inicio).days
    if frecuencia.max_dias_rango is not None and dias > frecuencia.max_dias_rango:
        raise ValueError(
            f"Para frecuencia {frecuencia.etiqueta.lower()}, el rango máximo es "
            f"{frecuencia.max_dias_rango} días (~{frecuencia.max_dias_rango // 365} años). "
            f"Acorte las fechas o elija otra temporalidad."
        )


def fechas_por_defecto(frecuencia: FrecuenciaDatos) -> tuple[date, date]:
    """Rango inicial sugerido según límites prácticos de Yahoo Finance."""
    hoy = date.today()
    if frecuencia.intervalo_yfinance == "1d":
        inicio = hoy - timedelta(days=365 * 2)
    elif frecuencia.intervalo_yfinance == "1wk":
        inicio = hoy - timedelta(days=365 * 5)
    else:
        inicio = hoy - timedelta(days=365 * 5)
    return inicio, hoy
