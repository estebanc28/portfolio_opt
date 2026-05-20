# ESPECIFICACIÓN DE REQUERIMIENTOS Y FUNCIONALIDADES: PORTAFOLIO DINÁMICO MPT

## 1. Contexto del Proyecto

El proyecto calcula un portafolio eficiente basado en la **Teoría Moderna de Portafolios (MPT)** de Markowitz. Los precios se obtienen desde **Yahoo Finance** (`yfinance`). El sistema compara el portafolio optimizado contra uno de **pesos iguales** y contra un **benchmark** seleccionable.

- Punto de entrada: `streamlit run portfolio_opt.py`

---

## 2. Estado de implementación

| Fase | Estado | Contenido |
|------|--------|-----------|
| **Fase 1** | Implementada | Descarga `yfinance`, tickers por `;`, benchmark, limpieza de huecos |
| **Fase 2** | Implementada | Panel único **Configuración del Portafolio** |
| **Fase 3** | Implementada | Frecuencias diaria / semanal / mensual y anualización parametrizada |
| Fase 4+ | Pendiente | Caché persistente, exportar CSV, etc. |

---

## 3. Configuración del Portafolio

### 3.1 Datos de mercado

| Control | Descripción |
|---------|-------------|
| **Tickers** | Texto separado por `;` (máx. **20** en portafolio). Se normalizan a **MAYÚSCULAS** al escribir. |
| **Temporalidad** | `selectbox`: **Mensual**, **Semanal** o **Diaria**. |
| **Fechas** | Inicio y fin del histórico. |
| **Límites de rango** | Diaria: máx. **730 días** (~2 años). Semanal: máx. **12 años**. Mensual: sin tope estricto en UI. |

| Temporalidad | Intervalo Yahoo | Periodos/año (anualización) | Mín. observaciones |
|--------------|-----------------|----------------------------|-------------------|
| Mensual | `1mo` | 12 | 12 |
| Semanal | `1wk` | 52 | 52 |
| Diaria | `1d` | 252 | 252 |

### 3.2 Benchmark y descarga

| Control | Descripción |
|---------|-------------|
| **Benchmark** | SPY, QQQ, IWM, DIA (no cuenta en el límite de 20). Entra en la firma de descarga. |
| **Descargar datos de mercado** | Botón **arriba** (tras tickers, temporalidad, fechas y benchmark). Solo descarga y actualiza precios en sesión; si cambian parámetros de descarga respecto a la memoria, hay que volver a pulsarlo antes de confirmar abajo. |

### 3.3 Universo y pesos — Modo A

- Multiselect de activos válidos tras la descarga; tras cada **Descargar datos de mercado** se seleccionan por defecto **todos** los activos del nuevo universo (se reinicia la selección del widget).
- **Un campo de % por cada activo descargado** (sin botón intermedio). Los pesos que cuentan para la suma y la validación son solo los de los activos **incluidos** en el multiselect.
- Pesos forzados opcionales (suma ≤ 100 % sobre los incluidos); Markowitz completa el resto.

### 3.4 Tasa libre de riesgo y confirmación final

| Control | Descripción |
|---------|-------------|
| **Tasa libre de riesgo** | Anual, default **4 %**; se muestra equivalente **por periodo** según la frecuencia elegida en 3.1. |
| **Confirmar configuración del portafolio** | Botón al **final** de la pantalla: fija multiselect, pesos y tasa para optimización y resultados. No descarga Yahoo; exige que los datos en sesión coincidan con la firma actual (tickers, fechas, benchmark, temporalidad). |
| **Multiselect** | Debe haber **al menos un activo** incluido para habilitar la confirmación. |

- Tras cambiar tickers, fechas, benchmark o temporalidad, use primero **Descargar datos de mercado** y luego confirme abajo.

---

## 4. Limpieza de datos

1. Alineación por frecuencia (`ME` / `W-FRI` / `D`).
2. Relleno de huecos cortos (límite según frecuencia).
3. Reintento por ticker con descarga individual.
4. Recorte al período común de cotización.

---

## 5. Backend — anualización (Fase 3)

| Módulo | Rol |
|--------|-----|
| `src/finance/periodicidad.py` | Metadatos de frecuencia y validación de rangos |
| `src/finance/metricas.py` | `periodos_por_anio` en retorno y volatilidad |
| `src/finance/markowitz.py` | μ y Σ escalados con `periodos_por_anio` |
| `src/finance/configuracion.py` | `anual_a_periodo(tasa, P)` |
| `src/data/yfinance_loader.py` | Descarga según `interval` |

**Fórmulas (P = periodos por año):**

- Rendimiento anual: `[ Π (1 + r_t) ]^(P/n) − 1`
- Volatilidad anual: `σ_periodo × √P`
- Tasa libre de riesgo por periodo: `(1 + r_anual)^(1/P) − 1`

`session_state['periodos_por_anio']` alimenta optimización y resultados.

---

## 6. Flujo de navegación

```
Inicio → Configuración del Portafolio → Optimización → Resultados finales
```

### Resultados finales — tabla de pesos

- La fila **Peso (%)** muestra **solo** activos con peso final **> 0 %** en el portafolio optimizado (más **Total**).
- En **No seleccionados para el análisis** se muestra la **métrica de descartes**: cantidad de tickers que usted sí incluyó en el multiselect pero que quedaron con **peso 0 %** en el óptimo, seguida de la lista de tickers.
- Otras listas: **Sin peso en el portafolio óptimo (< 0,1 %)** (detalle por umbral), **Descartados al descargar datos** (fallos de Yahoo).
- **Evolución histórica comparativa:** el eje X usa la **fecha completa** del índice de precios (no solo año-mes), para que las curvas con datos **semanales o diarios** no se vean escalonadas por colisión de etiquetas.

---

## 7. Fases futuras

- Caché de descargas (`@st.cache_data`) entre sesiones.
- Exportar CSV de series descargadas.
- Mejoras de UX al cambiar temporalidad (ajuste automático de fechas).
