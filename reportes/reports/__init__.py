from typing import Dict, Type
from reports.base import BaseReportGenerator
from reports.diagnosticos.generator import DiagnosticosGenerator
from reports.diagnosticos_uim.generator import DiagnosticosUIMGenerator
from reports.ensayos_generales.generator import EnsayosGeneralesGenerator
from reports.test_diagnostico.generator import TestDiagnosticoGenerator
from reports.test_de_eje.generator import TestDeEjeGenerator
from reports.examen_de_eje.generator import ExamenDeEjeGenerator
from reports.test_de_habilidad.generator import TestDeHabilidadGenerator
from reports.examen_de_habilidad.generator import ExamenDeHabilidadGenerator

# Plugin registry — maps report type name strings to generator classes.
# To add a new report type: import its generator class and add one entry here.
REGISTRY: Dict[str, Type[BaseReportGenerator]] = {
    "diagnosticos":        DiagnosticosGenerator,
    "diagnosticos_uim":    DiagnosticosUIMGenerator,
    "ensayos_generales":   EnsayosGeneralesGenerator,
    "test_diagnostico":    TestDiagnosticoGenerator,
    "test_de_eje":         TestDeEjeGenerator,
    "examen_de_eje":       ExamenDeEjeGenerator,
    "test_de_habilidad":   TestDeHabilidadGenerator,
    "examen_de_habilidad": ExamenDeHabilidadGenerator,
}


def get_generator(report_type: str) -> Type[BaseReportGenerator]:
    """
    Look up a generator class by report type string.

    Args:
        report_type: String key from REGISTRY (e.g., "diagnosticos")

    Returns:
        Generator class (not instance) for the requested report type

    Raises:
        KeyError: if report_type is not registered
    """
    if report_type not in REGISTRY:
        available = list(REGISTRY.keys())
        raise KeyError(
            f"Unknown report type '{report_type}'. "
            f"Available types: {available}"
        )
    return REGISTRY[report_type]
