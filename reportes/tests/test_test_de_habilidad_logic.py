"""Logic unit tests for the test_de_habilidad plugin.

Tests the estado assignment threshold and TareaStats percent property.
"""

import pytest

from reports.test_de_habilidad.generator import (
    ESTADO_DOMINADA,
    ESTADO_EN_DESARROLLO,
    TASK_MASTERY_PERCENT,
    TareaStats,
    _assign_estado,
)


# ---------------------------------------------------------------------------
# _assign_estado threshold
# ---------------------------------------------------------------------------


def test_assign_estado_dominada_at_exactly_80_percent():
    assert _assign_estado(80.0) == ESTADO_DOMINADA


def test_assign_estado_dominada_above_80_percent():
    assert _assign_estado(100.0) == ESTADO_DOMINADA
    assert _assign_estado(80.1) == ESTADO_DOMINADA


def test_assign_estado_en_desarrollo_below_80_percent():
    assert _assign_estado(79.9) == ESTADO_EN_DESARROLLO
    assert _assign_estado(0.0) == ESTADO_EN_DESARROLLO
    assert _assign_estado(50.0) == ESTADO_EN_DESARROLLO


def test_mastery_threshold_constant_is_80():
    assert TASK_MASTERY_PERCENT == 80.0


# ---------------------------------------------------------------------------
# TareaStats
# ---------------------------------------------------------------------------


def test_tarea_stats_percent_zero_when_no_questions():
    tarea = TareaStats(name="T1")
    assert tarea.percent == 0.0


def test_tarea_stats_percent_100_when_all_correct():
    tarea = TareaStats(name="T1", total=5, correct=5)
    assert tarea.percent == 100.0


def test_tarea_stats_percent_0_when_none_correct():
    tarea = TareaStats(name="T1", total=4, correct=0)
    assert tarea.percent == 0.0


def test_tarea_stats_percent_partial():
    tarea = TareaStats(name="T1", total=4, correct=3)
    assert tarea.percent == pytest.approx(75.0)


def test_tarea_stats_percent_boundary_just_below_mastery():
    # 3/4 = 75% -> En desarrollo
    tarea = TareaStats(name="T1", total=4, correct=3)
    assert _assign_estado(tarea.percent) == ESTADO_EN_DESARROLLO


def test_tarea_stats_percent_boundary_at_mastery():
    # 4/5 = 80% -> Dominada
    tarea = TareaStats(name="T1", total=5, correct=4)
    assert _assign_estado(tarea.percent) == ESTADO_DOMINADA
