from reports.test_de_eje.generator import (
    LessonStats,
    UnitProgress,
    _build_unit_activity_rows,
    _estimate_total_hours,
    _is_unit_fully_mastered,
    _should_mark_completed,
)


def test_lecture_threshold_marks_completed_at_or_above_70_percent():
    assert _should_mark_completed(70.0, 70.0) is True
    assert _should_mark_completed(89.9, 70.0) is True
    assert _should_mark_completed(69.9, 70.0) is False


def test_unit_mastery_requires_100_percent():
    assert _is_unit_fully_mastered(100.0, 100.0) is True
    assert _is_unit_fully_mastered(99.9, 100.0) is False


def test_unit_activity_rows_include_lectures_and_unit_tasks_with_symbols():
    unit = UnitProgress(name="Unidad A")
    unit.total = 4
    unit.correct = 3
    unit.lessons["Leccion 1"] = LessonStats(total=2, correct=2)  # 100% -> tick
    unit.lessons["Leccion 2"] = LessonStats(total=2, correct=1)  # 50% -> square

    rows = _build_unit_activity_rows(unit)

    assert rows[0]["activity"] == "Leccion 1"
    assert rows[0]["action"]
    assert rows[1]["activity"] == "Leccion 2"
    assert rows[1]["action"]
    assert rows[2]["activity"] == "Test de unidad"
    assert rows[2]["action"] == "□"
    assert rows[3]["activity"] == "Guia tematica"
    assert rows[3]["action"] == "□"
    assert len(rows) == 4


def test_full_mastery_marks_unit_test_and_guide_as_not_required():
    unit = UnitProgress(name="Unidad Completa")
    unit.total = 2
    unit.correct = 2
    unit.lessons["L1"] = LessonStats(total=1, correct=1)
    unit.lessons["L2"] = LessonStats(total=1, correct=1)

    rows = _build_unit_activity_rows(unit)
    assert rows[2]["activity"] == "Test de unidad"
    assert rows[2]["action"] == "No requerido"
    assert rows[3]["activity"] == "Guia tematica"
    assert rows[3]["action"] == "No requerido"


def test_unit_activity_rows_preserve_xlsx_insertion_order():
    unit = UnitProgress(name="Unidad Orden")
    unit.total = 3
    unit.correct = 3
    unit.lessons["Zeta"] = LessonStats(total=1, correct=1)
    unit.lessons["Alfa"] = LessonStats(total=1, correct=1)
    unit.lessons["Beta"] = LessonStats(total=1, correct=1)

    rows = _build_unit_activity_rows(unit)
    lesson_labels = [row["activity"] for row in rows[:3]]
    assert lesson_labels == ["Zeta", "Alfa", "Beta"]


def test_estimated_hours_adds_pending_lectures_unit_tasks_and_exam():
    unit_a = UnitProgress(name="Unidad A")
    unit_a.total = 4
    unit_a.correct = 3  # not 100% => includes test + guide
    unit_a.lessons["L1"] = LessonStats(total=2, correct=2)  # done
    unit_a.lessons["L2"] = LessonStats(total=2, correct=1)  # pending

    unit_b = UnitProgress(name="Unidad B")
    unit_b.total = 4
    unit_b.correct = 4  # full mastery => no test/guide
    unit_b.lessons["L1"] = LessonStats(total=2, correct=2)  # done
    unit_b.lessons["L2"] = LessonStats(total=2, correct=1)  # pending

    # Pending:
    # - lectures: 2 * 1h
    # - unit tests: 1 * 0.5h
    # - guides: 1 * 2h
    # - exam: 2h
    # Total: 6.5h
    assert _estimate_total_hours([unit_a, unit_b]) == 6.5
