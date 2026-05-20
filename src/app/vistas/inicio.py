"""Vista de inicio con descripción general del proyecto."""

import streamlit as st


def mostrar() -> None:
    st.markdown(
        '<h1 class="titulo-principal">'
        "📊 Portafolio de Inversión con Optimización de Markowitz"
        "</h1>",
        unsafe_allow_html=True,
    )

    st.markdown("### 🎯 Descripción General")
    st.write(
        "Esta aplicación permite analizar y optimizar un portafolio de inversión "
        "con datos históricos descargados desde **Yahoo Finance**. Puede incorporar "
        "hasta **20 activos** (ingresados separados por `;`), elegir **temporalidad** "
        "(diaria, semanal o mensual), definir pesos forzados opcionales y "
        "comparar contra un benchmark (SPY, QQQ, IWM o DIA)."
    )

    st.markdown("### 📋 Funcionalidades Disponibles")
    funcionalidades = [
        ("🏠", "Inicio"),
        ("⚙️", "Configuración del Portafolio"),
        ("🎯", "Optimización y Frontera Eficiente"),
        ("📋", "Resultados Finales y Validación Histórica"),
    ]
    for icono, nombre in funcionalidades:
        st.markdown(f"{icono} {nombre}")

    st.markdown("### 🚀 Comenzar")
    st.info(
        "Selecciona **Configuración del Portafolio** en el menú lateral: allí descargas "
        "los precios, eliges activos, benchmark y tasa libre de riesgo en un solo paso. "
        "Luego avanza a optimización y resultados finales."
    )
