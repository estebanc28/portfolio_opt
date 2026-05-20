"""Compatibilidad: redirige a la vista unificada de configuración (Fase 2)."""

from src.app.vistas.configuracion import (
    CLAVE_ACTIVOS_SELECCIONADOS,
    CLAVE_CONFIG_CONFIRMADA,
    CLAVE_PESOS_FORZADOS,
    CLAVE_TASA_ANUAL,
    CLAVE_TASA_MENSUAL,
    mostrar,
)

__all__ = [
    "mostrar",
    "CLAVE_CONFIG_CONFIRMADA",
    "CLAVE_ACTIVOS_SELECCIONADOS",
    "CLAVE_PESOS_FORZADOS",
    "CLAVE_TASA_ANUAL",
    "CLAVE_TASA_MENSUAL",
]
