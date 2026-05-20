from pathlib import Path

# Raíz del proyecto (carpeta que contiene src/, documentos/, portfolio_opt.py)
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# Archivo CSV legado (tests y referencia histórica del curso)
RUTA_CSV_DEFECTO = RAIZ_PROYECTO / "documentos" / "portafolio_21_activos.csv"
COLUMNA_FECHA = "Date"

# Descarga vía yfinance
MAX_TICKERS_PORTAFOLIO = 20

# Compatibilidad Fase 1 (mensual) — valores alineados con FRECUENCIA_MENSUAL
INTERVALO_YFINANCE_MENSUAL = "1mo"
MIN_OBSERVACIONES_MENSUALES = 12
MAX_MESES_RELLENO_FFILL = 2

# Benchmarks (etiqueta visible -> ticker Yahoo)
OPCIONES_BENCHMARK: dict[str, str] = {
    "S&P 500 (SPY)": "SPY",
    "Nasdaq 100 (QQQ)": "QQQ",
    "Russell 2000 (IWM)": "IWM",
    "Dow Jones (DIA)": "DIA",
}
BENCHMARK_DEFECTO = "S&P 500 (SPY)"
TICKER_BENCHMARK = OPCIONES_BENCHMARK[BENCHMARK_DEFECTO]

# Tasa libre de riesgo por defecto (Treasury 10 años ≈ 4% anual)
TASA_LIBRE_RIESGO_DEFAULT_ANUAL = 0.04
