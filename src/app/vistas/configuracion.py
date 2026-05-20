"""
Configuración unificada del portafolio (Fases 2 y 3).

Descarga Yahoo Finance (mensual/semanal/diaria), benchmark, selección de activos,
pesos forzados (Modo A), tasa libre de riesgo: descarga arriba y confirmación al final.
"""

from __future__ import annotations

import hashlib
from datetime import date

import streamlit as st

from src.config import (
    BENCHMARK_DEFECTO,
    MAX_TICKERS_PORTAFOLIO,
    OPCIONES_BENCHMARK,
    TASA_LIBRE_RIESGO_DEFAULT_ANUAL,
)
from src.finance.periodicidad import FRECUENCIA_DEFECTO, OPCIONES_FRECUENCIA
from src.data.loader import ResultadoCargaDatos
from src.data.yfinance_loader import ORIGEN_DATOS, descargar_desde_texto, parsear_tickers
from src.finance.configuracion import (
    anual_a_periodo,
    construir_configuracion,
    validar_configuracion,
)
from src.finance.periodicidad import fechas_por_defecto, obtener_frecuencia
from src.visualization.correlacion_cache import invalidar_cache_correlacion

# Claves de session_state (exportadas para el resto de la app)
CLAVE_CONFIG_CONFIRMADA = "config_confirmada"
CLAVE_ACTIVOS_SELECCIONADOS = "activos_seleccionados"
CLAVE_PESOS_FORZADOS = "pesos_forzados"
CLAVE_TASA_ANUAL = "tasa_libre_riesgo_anual"
CLAVE_TASA_MENSUAL = "tasa_libre_riesgo_mensual"
CLAVE_TEXTO_TICKERS = "texto_tickers_portafolio"
CLAVE_ETIQUETA_BENCHMARK = "etiqueta_benchmark"
CLAVE_FECHA_INICIO = "fecha_inicio_datos"
CLAVE_FECHA_FIN = "fecha_fin_datos"
CLAVE_FIRMA_DESCARGA = "firma_ultima_descarga"
CLAVE_ETIQUETA_FRECUENCIA = "etiqueta_frecuencia"
CLAVE_PERIODOS_POR_ANIO = "periodos_por_anio"
# Sufijo estable en las claves de ``number_input`` de pesos tras cada descarga (evita choques al cambiar universo)
CLAVE_SUFIJO_WIDGETS_PESO = "cfg_sufijo_widgets_peso"
# Clave del ``st.multiselect`` (hay que actualizarla en sesión tras cada descarga o Streamlit conserva la selección vieja)
CLAVE_WIDGET_MULTISELECT_ACTIVOS = "cfg_multiselect_activos"


def _firma_parametros_descarga(
    texto_tickers: str,
    etiqueta_benchmark: str,
    etiqueta_frecuencia: str,
    fecha_inicio: date,
    fecha_fin: date,
) -> str:
    return (
        f"{texto_tickers.strip()}|{etiqueta_benchmark}|{etiqueta_frecuencia}"
        f"|{fecha_inicio}|{fecha_fin}"
    )


def _inicializar_controles() -> None:
    if CLAVE_TEXTO_TICKERS not in st.session_state:
        st.session_state[CLAVE_TEXTO_TICKERS] = ""
    if CLAVE_ETIQUETA_BENCHMARK not in st.session_state:
        st.session_state[CLAVE_ETIQUETA_BENCHMARK] = BENCHMARK_DEFECTO
    if CLAVE_ETIQUETA_FRECUENCIA not in st.session_state:
        st.session_state[CLAVE_ETIQUETA_FRECUENCIA] = FRECUENCIA_DEFECTO
    frecuencia_def = obtener_frecuencia(st.session_state[CLAVE_ETIQUETA_FRECUENCIA])
    inicio_def, fin_def = fechas_por_defecto(frecuencia_def)
    if CLAVE_FECHA_INICIO not in st.session_state:
        st.session_state[CLAVE_FECHA_INICIO] = inicio_def
    if CLAVE_FECHA_FIN not in st.session_state:
        st.session_state[CLAVE_FECHA_FIN] = fin_def
    if CLAVE_TASA_ANUAL not in st.session_state:
        st.session_state[CLAVE_TASA_ANUAL] = TASA_LIBRE_RIESGO_DEFAULT_ANUAL


def _invalidar_caches_analisis() -> None:
    invalidar_cache_correlacion()
    try:
        from src.visualization.frontera_cache import invalidar_cache_frontera
        from src.visualization.resultados_cache import invalidar_cache_resultados
        from src.visualization.tabla_comparativa_cache import invalidar_cache_tabla_comparativa

        invalidar_cache_frontera()
        invalidar_cache_tabla_comparativa()
        invalidar_cache_resultados()
    except ImportError:
        pass


def _guardar_datos_en_sesion(resultado: ResultadoCargaDatos) -> None:
    st.session_state["datos_cargados"] = True
    st.session_state["precios"] = resultado.precios
    st.session_state["activos_validos"] = resultado.activos_validos
    st.session_state["benchmark"] = resultado.benchmark
    st.session_state["activos_excluidos"] = resultado.activos_excluidos
    st.session_state["mensajes_carga"] = resultado.mensajes
    st.session_state["nombre_archivo_datos"] = resultado.nombre_archivo


def _guardar_configuracion_en_sesion(
    activos_seleccionados: list[str],
    pesos_forzados: dict[str, float],
    tasa_anual: float,
    periodos_por_anio: int,
) -> None:
    config = construir_configuracion(
        activos_seleccionados,
        pesos_forzados,
        tasa_anual,
        periodos_por_anio=periodos_por_anio,
    )
    st.session_state[CLAVE_CONFIG_CONFIRMADA] = True
    st.session_state[CLAVE_ACTIVOS_SELECCIONADOS] = config.activos_seleccionados
    st.session_state[CLAVE_PESOS_FORZADOS] = config.pesos_forzados
    st.session_state[CLAVE_TASA_ANUAL] = config.tasa_libre_riesgo_anual
    st.session_state[CLAVE_TASA_MENSUAL] = config.tasa_libre_riesgo_periodo
    st.session_state[CLAVE_PERIODOS_POR_ANIO] = config.periodos_por_anio
    _invalidar_caches_analisis()


def _resultado_desde_sesion() -> ResultadoCargaDatos | None:
    if not st.session_state.get("datos_cargados"):
        return None
    precios = st.session_state.get("precios")
    if precios is None:
        return None
    return ResultadoCargaDatos(
        precios=precios,
        activos_validos=st.session_state.get("activos_validos", []),
        benchmark=st.session_state.get("benchmark", ""),
        activos_excluidos=st.session_state.get("activos_excluidos", []),
        mensajes=st.session_state.get("mensajes_carga", []),
        ruta_csv=ORIGEN_DATOS,
        nombre_archivo=st.session_state.get("nombre_archivo_datos", "Yahoo Finance"),
    )


def _mostrar_resumen_datos(resultado: ResultadoCargaDatos) -> None:
    if resultado.mensajes:
        for mensaje in resultado.mensajes:
            if mensaje.startswith("Advertencia"):
                st.warning(mensaje)
            else:
                st.warning(mensaje)

    col_resumen, col_detalle = st.columns([1, 2])
    with col_resumen:
        st.metric("Activos válidos", len(resultado.activos_validos))
        st.metric("Activos excluidos", len(resultado.activos_excluidos))
        etiqueta_freq = st.session_state.get(CLAVE_ETIQUETA_FRECUENCIA, "Mensual")
        st.metric(f"Observaciones ({etiqueta_freq.lower()})", len(resultado.precios))
        if resultado.benchmark:
            st.caption(f"Benchmark: `{resultado.benchmark}`")
    with col_detalle:
        st.markdown("**Activos disponibles:** " + ", ".join(resultado.activos_validos))
        if resultado.activos_excluidos:
            st.markdown(
                "**Excluidos:** " + ", ".join(resultado.activos_excluidos)
            )
        fecha_min = resultado.precios.index.min().strftime("%Y-%m-%d")
        fecha_max = resultado.precios.index.max().strftime("%Y-%m-%d")
        st.caption(f"Período en datos: {fecha_min} → {fecha_max}")


def _sufijo_widgets_peso(firma: str) -> str:
    """Fragmento corto y seguro para claves de widgets según la firma de descarga."""
    return hashlib.sha256(firma.encode("utf-8")).hexdigest()[:16]


def _mostrar_pesos_forzados(
    activos_para_pesos: list[str],
    pesos_previos: dict[str, float],
    sufijo_clave: str,
) -> dict[str, float]:
    """Campos de peso (%) para cada ticker en ``activos_para_pesos``."""
    pesos_forzados: dict[str, float] = {}
    if not activos_para_pesos:
        return pesos_forzados

    cols = st.columns(2)
    for i, ticker in enumerate(sorted(activos_para_pesos)):
        peso_pct_previo = pesos_previos.get(ticker, 0.0) * 100.0
        with cols[i % 2]:
            peso_pct = st.number_input(
                f"{ticker} (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(peso_pct_previo),
                step=0.5,
                format="%.2f",
                key=f"peso_forzado_{ticker}_{sufijo_clave}",
                help="0 % = sin peso forzado; Markowitz asignará el resto (Modo A).",
            )
        if peso_pct > 0:
            pesos_forzados[ticker] = peso_pct / 100.0

    return pesos_forzados


def _puede_descargar_datos(n_tickers: int) -> bool:
    """Tickers en texto válidos para ejecutar la descarga."""
    return 0 < n_tickers <= MAX_TICKERS_PORTAFOLIO


def _puede_confirmar_analisis(
    activos_seleccionados: list[str],
    pesos_solo_seleccion: dict[str, float],
    *,
    datos_cargados: bool,
    hay_activos_en_datos: bool,
    datos_coinciden_con_formulario: bool,
) -> bool:
    """Habilita el botón final (multiselect, pesos de activos incluidos y datos alineados)."""
    if not datos_cargados or not hay_activos_en_datos:
        return False
    if not datos_coinciden_con_formulario:
        return False
    if not activos_seleccionados:
        return False
    if sum(pesos_solo_seleccion.values()) > 1.0 + 1e-9:
        return False
    return True


def mostrar() -> None:
    st.markdown("### Configuración del Portafolio")
    st.caption(
        "Descargue precios desde Yahoo Finance (arriba), ajuste universo y pesos, "
        "defina la tasa libre de riesgo y confirme al final para fijar el análisis."
    )

    _inicializar_controles()

    # Debe ejecutarse ANTES de ``st.text_input(..., key=CLAVE_TEXTO_TICKERS)``:
    # Streamlit no permite modificar ``session_state`` de esa clave después de
    # instanciar el widget en la misma corrida.
    _tickers_raw = str(st.session_state.get(CLAVE_TEXTO_TICKERS, ""))
    _tickers_mayus = _tickers_raw.upper()
    if _tickers_mayus != _tickers_raw:
        st.session_state[CLAVE_TEXTO_TICKERS] = _tickers_mayus
        st.rerun()

    # --- Bloque 1: origen de datos y parámetros globales ---
    st.subheader("1. Datos de mercado")
    st.text_input(
        "Tickers del portafolio (separados por `;`)",
        placeholder="AAPL;MSFT;GOOGL;DE;JNJ",
        help="Máximo 20 tickers. Se muestran en MAYÚSCULAS (símbolos Yahoo Finance).",
        key=CLAVE_TEXTO_TICKERS,
    )
    texto_tickers = str(st.session_state.get(CLAVE_TEXTO_TICKERS, ""))

    tickers_parseados = parsear_tickers(texto_tickers)
    n_tickers = len(tickers_parseados)
    st.caption(
        f"Hasta **{MAX_TICKERS_PORTAFOLIO}** tickers en el portafolio "
        f"(actualmente **{n_tickers}**). El benchmark no cuenta en ese límite."
    )
    if n_tickers > MAX_TICKERS_PORTAFOLIO:
        st.error(f"Máximo {MAX_TICKERS_PORTAFOLIO} tickers; reduzca la lista.")

    etiquetas_freq = list(OPCIONES_FRECUENCIA.keys())
    freq_prev = st.session_state.get(CLAVE_ETIQUETA_FRECUENCIA, FRECUENCIA_DEFECTO)
    indice_freq = (
        etiquetas_freq.index(freq_prev)
        if freq_prev in etiquetas_freq
        else etiquetas_freq.index(FRECUENCIA_DEFECTO)
    )
    etiqueta_frecuencia = st.selectbox(
        "Temporalidad de los datos",
        options=etiquetas_freq,
        index=indice_freq,
        help="Diaria (~2 años máx.), semanal (~12 años) o mensual.",
        key="cfg_select_frecuencia",
    )
    st.session_state[CLAVE_ETIQUETA_FRECUENCIA] = etiqueta_frecuencia
    frecuencia = obtener_frecuencia(etiqueta_frecuencia)

    col_inicio, col_fin = st.columns(2)
    with col_inicio:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            value=st.session_state[CLAVE_FECHA_INICIO],
            key="cfg_fecha_inicio",
        )
    with col_fin:
        fecha_fin = st.date_input(
            "Fecha de fin",
            value=st.session_state[CLAVE_FECHA_FIN],
            key="cfg_fecha_fin",
        )
    st.session_state[CLAVE_FECHA_INICIO] = fecha_inicio
    st.session_state[CLAVE_FECHA_FIN] = fecha_fin

    if frecuencia.max_dias_rango:
        st.caption(
            f"Intervalo Yahoo: `{frecuencia.intervalo_yfinance}` · "
            f"Anualización con **{frecuencia.periodos_por_anio}** periodos/año · "
            f"Rango máximo sugerido: **{frecuencia.max_dias_rango}** días."
        )
    else:
        st.caption(
            f"Intervalo Yahoo: `{frecuencia.intervalo_yfinance}` · "
            f"Anualización con **{frecuencia.periodos_por_anio}** periodos/año."
        )

    st.subheader("2. Benchmark y descarga de datos")
    st.caption(
        "El benchmark define la serie de referencia en la descarga. "
        "Si cambia tickers, fechas, temporalidad o benchmark, vuelva a descargar antes de confirmar abajo."
    )
    etiquetas_bench = list(OPCIONES_BENCHMARK.keys())
    indice_def = etiquetas_bench.index(
        st.session_state.get(CLAVE_ETIQUETA_BENCHMARK, BENCHMARK_DEFECTO)
        if st.session_state.get(CLAVE_ETIQUETA_BENCHMARK, BENCHMARK_DEFECTO)
        in etiquetas_bench
        else etiquetas_bench.index(BENCHMARK_DEFECTO)
    )
    etiqueta_benchmark = st.selectbox(
        "Benchmark",
        options=etiquetas_bench,
        index=indice_def,
        key="cfg_select_benchmark",
    )
    st.session_state[CLAVE_ETIQUETA_BENCHMARK] = etiqueta_benchmark

    firma_parametros = _firma_parametros_descarga(
        texto_tickers,
        etiqueta_benchmark,
        etiqueta_frecuencia,
        fecha_inicio,
        fecha_fin,
    )
    datos_coinciden = st.session_state.get(CLAVE_FIRMA_DESCARGA) == firma_parametros

    col_btn_desc, col_info_desc = st.columns([1, 2])
    with col_btn_desc:
        descargar_mercado = st.button(
            "Descargar datos de mercado",
            type="primary",
            use_container_width=True,
            disabled=not _puede_descargar_datos(n_tickers),
            key="cfg_btn_descargar_mercado",
        )
    with col_info_desc:
        st.caption(
            "Obtiene precios de Yahoo Finance. Use este botón al cambiar de universo o parámetros de descarga; "
            "la confirmación final del análisis permanece al pie de la página."
        )

    if descargar_mercado:
        try:
            resultado = descargar_desde_texto(
                texto_tickers=texto_tickers,
                etiqueta_benchmark=etiqueta_benchmark,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                etiqueta_frecuencia=etiqueta_frecuencia,
            )
            _guardar_datos_en_sesion(resultado)
            st.session_state[CLAVE_FIRMA_DESCARGA] = firma_parametros
            st.session_state[CLAVE_SUFIJO_WIDGETS_PESO] = _sufijo_widgets_peso(firma_parametros)
            st.session_state[CLAVE_CONFIG_CONFIRMADA] = False
            # El multiselect guarda la selección en ``session_state`` por ``key``; sin esto quedarían
            # tickers de un universo anterior aunque los pesos ya usen la nueva descarga.
            nuevos_validos = list(resultado.activos_validos)
            st.session_state[CLAVE_WIDGET_MULTISELECT_ACTIVOS] = nuevos_validos
            st.session_state[CLAVE_ACTIVOS_SELECCIONADOS] = nuevos_validos
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(
                "No se pudieron descargar los datos. Verifique tickers, fechas y conexión."
            )
            st.caption(str(error))

    activos_disponibles: list[str] = list(st.session_state.get("activos_validos", []))
    activos_seleccionados: list[str] = []
    pesos_todos: dict[str, float] = {}
    datos_ya_cargados = bool(st.session_state.get("datos_cargados"))

    if (
        activos_disponibles
        and datos_ya_cargados
        and st.session_state.get(CLAVE_FIRMA_DESCARGA)
        and CLAVE_SUFIJO_WIDGETS_PESO not in st.session_state
    ):
        # Sesiones antiguas sin sufijo: evita colisiones de claves al actualizar el código
        st.session_state[CLAVE_SUFIJO_WIDGETS_PESO] = _sufijo_widgets_peso(
            str(st.session_state[CLAVE_FIRMA_DESCARGA])
        )

    if activos_disponibles:
        st.subheader("3. Universo y pesos forzados (Modo A)")
        st.caption(
            f"{len(activos_disponibles)} activo(s) con datos válidos en la última descarga. "
            "Los porcentajes opcionales aplican solo a los activos que deje incluidos en el análisis."
        )

        activos_previos = [
            a
            for a in st.session_state.get(
                CLAVE_ACTIVOS_SELECCIONADOS, activos_disponibles
            )
            if a in activos_disponibles
        ]
        if not activos_previos:
            activos_previos = list(activos_disponibles)

        activos_seleccionados = st.multiselect(
            "Activos a incluir en el análisis",
            options=activos_disponibles,
            default=activos_previos,
            help="Retire activos que no desee optimizar.",
            key=CLAVE_WIDGET_MULTISELECT_ACTIVOS,
        )

        st.markdown(
            "**Pesos forzados (opcional)** — un campo por cada activo descargado; "
            "Markowitz completa el resto. La suma de los pesos de los **activos incluidos** no debe superar 100 %."
        )
        sufijo_pesos = str(st.session_state.get(CLAVE_SUFIJO_WIDGETS_PESO, "sin_datos"))
        pesos_previos = dict(st.session_state.get(CLAVE_PESOS_FORZADOS, {}))
        pesos_todos = _mostrar_pesos_forzados(
            sorted(activos_disponibles),
            pesos_previos,
            sufijo_pesos,
        )

        sel_set = set(activos_seleccionados)
        pesos_solo_seleccion = {k: v for k, v in pesos_todos.items() if k in sel_set}
        suma_sel = sum(pesos_solo_seleccion.values())
        if pesos_solo_seleccion:
            st.write(
                f"**Suma de pesos forzados (solo activos incluidos):** {suma_sel * 100:.2f} %"
            )
        if suma_sel > 1.0 + 1e-9:
            st.error(
                "La suma de pesos forzados de los activos incluidos supera el 100 %. "
                "Ajuste los valores o excluya activos del multiselect."
            )

        resultado = _resultado_desde_sesion()
        if resultado is not None:
            with st.expander("Resumen de datos descargados", expanded=False):
                _mostrar_resumen_datos(resultado)
    elif st.session_state.get("datos_cargados"):
        st.info("No quedaron activos válidos en la última descarga. Revise los tickers.")
    else:
        st.info(
            "Defina tickers, temporalidad y fechas, luego pulse **Descargar datos de mercado**. "
            "Después podrá elegir activos, opcionalmente forzar pesos y confirmar al final de la página."
        )

    st.subheader("4. Tasa libre de riesgo y confirmación final")
    tasa_anual_previa = float(
        st.session_state.get(CLAVE_TASA_ANUAL, TASA_LIBRE_RIESGO_DEFAULT_ANUAL)
    )
    tasa_pct = st.number_input(
        "Tasa libre de riesgo anual (%)",
        min_value=0.0,
        max_value=100.0,
        value=tasa_anual_previa * 100.0,
        step=0.1,
        format="%.2f",
        key="cfg_tasa_riesgo",
    )
    tasa_anual = tasa_pct / 100.0
    tasa_periodo = anual_a_periodo(tasa_anual, frecuencia.periodos_por_anio)
    st.caption(
        f"Equivalente por {frecuencia.nombre_unidad}: **{tasa_periodo * 100:.4f} %** "
        f"(desde tasa anual; default Treasury ~4 %)."
    )

    st.divider()
    confirmada = bool(st.session_state.get(CLAVE_CONFIG_CONFIRMADA))
    if confirmada and st.session_state.get("datos_cargados"):
        st.success(
            "Configuración confirmada. Puede continuar con **Optimización y Frontera Eficiente**."
        )

    hay_activos = bool(activos_disponibles)
    sel_set = set(activos_seleccionados)
    pesos_para_validar = {k: v for k, v in pesos_todos.items() if k in sel_set}

    confirmar_deshabilitado = not _puede_confirmar_analisis(
        activos_seleccionados,
        pesos_para_validar,
        datos_cargados=datos_ya_cargados,
        hay_activos_en_datos=hay_activos,
        datos_coinciden_con_formulario=datos_coinciden,
    )

    if datos_ya_cargados and hay_activos and not datos_coinciden:
        st.warning(
            "Los parámetros de descarga (tickers, fechas, temporalidad o benchmark) no coinciden "
            "con los datos en memoria. Pulse **Descargar datos de mercado** (sección 2) antes de confirmar."
        )

    col_btn_ok, col_info_ok = st.columns([1, 2])
    with col_btn_ok:
        confirmar_config = st.button(
            "Confirmar configuración del portafolio",
            type="primary",
            use_container_width=True,
            disabled=confirmar_deshabilitado,
            key="cfg_btn_confirmar_config",
        )
    with col_info_ok:
        st.caption(
            "Fija activos incluidos, pesos forzados y tasa para optimización y resultados. "
            "No descarga de nuevo Yahoo si los parámetros de la sección 2 coinciden con la última descarga."
        )

    if confirmar_config:
        try:
            resultado = _resultado_desde_sesion()
            if resultado is None:
                raise ValueError(
                    "No hay datos en sesión; descargue primero los datos de mercado."
                )

            disponibles = list(resultado.activos_validos)
            seleccion = [a for a in activos_seleccionados if a in disponibles]
            if not seleccion:
                st.error("Debe incluir al menos un activo en el análisis (multiselect).")
                st.session_state[CLAVE_CONFIG_CONFIRMADA] = False
                st.rerun()

            pesos_final = {k: v for k, v in pesos_todos.items() if k in set(seleccion)}

            es_valida, mensaje = validar_configuracion(
                activos_disponibles=disponibles,
                activos_seleccionados=seleccion,
                pesos_forzados=pesos_final,
                tasa_libre_riesgo_anual=tasa_anual,
            )
            if not es_valida:
                st.error(mensaje)
                st.session_state[CLAVE_CONFIG_CONFIRMADA] = False
            else:
                _guardar_configuracion_en_sesion(
                    seleccion,
                    pesos_final,
                    tasa_anual,
                    frecuencia.periodos_por_anio,
                )
                st.rerun()

        except ValueError as error:
            st.error(str(error))
            st.session_state[CLAVE_CONFIG_CONFIRMADA] = False
        except Exception as error:
            st.error("No se pudo confirmar la configuración.")
            st.caption(str(error))
            st.session_state[CLAVE_CONFIG_CONFIRMADA] = False
