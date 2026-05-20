"""
Gráfico comparativo de evolución histórica (Funcionalidad 4).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.app.texto_formato import capitalizar_palabras_largas
from src.finance.resultados import DatosResultadosFinales

_CAP = capitalizar_palabras_largas

COLOR_FONDO = "#000000"
COLOR_TEXTO = "#f0f0f0"
COLOR_IGUAL = "#ff6b9d"
COLOR_OPTIMIZADO = "#00e5ff"
COLOR_BENCHMARK = "#ffd54f"


def _fechas_eje_x(serie: pd.Series) -> pd.DatetimeIndex | list:
    """
    Fechas para el eje X del gráfico.

    Antes se usaba solo ``%Y-%m``, lo que agrupaba semanas y días bajo la misma
    etiqueta y producía curvas escalonadas; con fechas completas Plotly interpola bien.
    """
    idx = serie.index
    if isinstance(idx, pd.DatetimeIndex):
        return idx
    try:
        return pd.to_datetime(idx, errors="raise")
    except (ValueError, TypeError):
        return [str(i) for i in idx]


def crear_grafico_evolucion_historica(datos: DatosResultadosFinales) -> go.Figure:
    """Tres líneas: pesos iguales, optimizado y benchmark (ticker según configuración)."""
    fig = go.Figure()

    series = [
        (datos.evolucion_igual, _CAP("Portafolio pesos iguales"), COLOR_IGUAL, "solid"),
        (datos.evolucion_optimizado, _CAP("Portafolio optimizado"), COLOR_OPTIMIZADO, "solid"),
    ]
    if datos.evolucion_benchmark is not None:
        nombre_bench = _CAP(f"{datos.ticker_benchmark} (benchmark)")
        series.append(
            (datos.evolucion_benchmark, nombre_bench, COLOR_BENCHMARK, "dot"),
        )

    for serie, nombre, color, dash in series:
        fechas_x = _fechas_eje_x(serie)
        fig.add_trace(
            go.Scatter(
                x=fechas_x,
                y=serie.values,
                mode="lines",
                name=nombre,
                line=dict(color=color, width=2.5, dash=dash),
                hovertemplate=(
                    f"<b>{nombre}</b><br>"
                    "Tiempo: %{x}<br>"
                    "Valor: $%{y:,.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text=_CAP("Evolución histórica comparativa"),
            font=dict(size=16, color=COLOR_TEXTO),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            title=_CAP("Tiempo"),
            type="date",
            tickfont=dict(color=COLOR_TEXTO),
            gridcolor="#2a2a2a",
        ),
        yaxis=dict(
            title=_CAP("Valor acumulado"),
            tickfont=dict(color=COLOR_TEXTO),
            tickformat="$,.0f",
            gridcolor="#2a2a2a",
        ),
        plot_bgcolor=COLOR_FONDO,
        paper_bgcolor=COLOR_FONDO,
        font=dict(color=COLOR_TEXTO, family="Arial, sans-serif"),
        legend=dict(
            bgcolor="rgba(0,0,0,0.6)",
            bordercolor="#444444",
            borderwidth=1,
            font=dict(size=10, color=COLOR_TEXTO),
            y=0.98,
            yanchor="top",
        ),
        height=560,
        margin=dict(l=80, r=40, t=70, b=80),
        hovermode="x unified",
    )

    return fig
