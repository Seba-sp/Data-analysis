"""Phase 11 – TDD RED: PDU% threshold logic and UnitStats/ExamenPlan data contracts.

All tests in this file must FAIL with ImportError until reports/examen_de_eje/generator.py
is implemented (Plan 02).
"""

from reports.examen_de_eje.generator import (
    ExamenPlan,
    UnitStats,
    _assign_estado_recomendacion,
)


# ---------------------------------------------------------------------------
# PDU% threshold tests
# ---------------------------------------------------------------------------


def test_pdu_threshold_riesgo_at_zero():
    assert _assign_estado_recomendacion(0.0) == ("Riesgo", "RR")


def test_pdu_threshold_riesgo_at_49_9():
    assert _assign_estado_recomendacion(49.9) == ("Riesgo", "RR")


def test_pdu_threshold_boundary_50():
    assert _assign_estado_recomendacion(50.0) == ("En desarrollo", "RD")


def test_pdu_threshold_en_desarrollo_at_79_9():
    assert _assign_estado_recomendacion(79.9) == ("En desarrollo", "RD")


def test_pdu_threshold_boundary_80():
    assert _assign_estado_recomendacion(80.0) == ("Solido", "RS")


def test_pdu_threshold_solido_at_100():
    assert _assign_estado_recomendacion(100.0) == ("Solido", "RS")


# ---------------------------------------------------------------------------
# UnitStats dataclass tests
# ---------------------------------------------------------------------------


def test_unit_stats_percent_with_zero_total():
    unit = UnitStats(name="X")
    assert unit.percent == 0.0  # must not raise ZeroDivisionError


def test_unit_stats_percent_calculation():
    unit = UnitStats(name="Matematica", total=5, correct=4)
    assert unit.percent == 80.0


# ---------------------------------------------------------------------------
# ExamenPlan unit_order preservation test
# ---------------------------------------------------------------------------


def test_analyze_preserves_bank_row_order():
    """analyze() must return units in bank row order, not alphabetical."""
    plan = ExamenPlan(
        assessment_type="M30M2",
        student_id="u-1",
        email="student@example.com",
        assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
    )
    plan.unit_order = ["Matematica financiera", "Logaritmos", "Numeros reales"]
    assert plan.unit_order == ["Matematica financiera", "Logaritmos", "Numeros reales"]
