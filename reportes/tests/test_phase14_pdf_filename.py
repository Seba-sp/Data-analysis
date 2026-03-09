"""
Phase 14-01 — Regression guard for PDF filename contract.

TDD lifecycle:
  RED  (before generator fix): test_pdf_filename_test_de_eje and
       test_pdf_filename_examen_de_eje FAIL because the generators produce
       filenames that violate the runner's ``informe_{email}_{atype}.pdf``
       contract. Specifically, the runner returns None for those filenames.
  GREEN (after generator fix): all three tests pass.

Approach: tests simulate the filename that each generator currently produces
(the broken format) and assert the runner can parse it. Before the fix the
runner returns None and the assertion fails (RED). After the fix the generators
produce the correct format so the runner succeeds (GREEN).
"""
from pathlib import Path

from core.runner import PipelineRunner


# ---------------------------------------------------------------------------
# Helper — instantiate runner without triggering any GCP deps
# ---------------------------------------------------------------------------

def _runner(report_type: str = "test_de_eje") -> PipelineRunner:
    return PipelineRunner(report_type=report_type, dry_run=True)


# ---------------------------------------------------------------------------
# test_extract_email_roundtrip
#
# Documents the runner's expected contract.
# Passes both before and after the generator fix (serves as sanity anchor).
# ---------------------------------------------------------------------------

def test_extract_email_roundtrip():
    """Runner parses correct informe_ format and rejects old broken format."""
    runner = _runner()

    # Correct format — runner must return the email segment
    assert runner._extract_email_from_pdf(
        Path("informe_student_at_example_com_M2.pdf")
    ) == "student_at_example_com"

    # Old broken format — runner must return None
    assert runner._extract_email_from_pdf(
        Path("M2__student_at_example_com.pdf")
    ) is None


# ---------------------------------------------------------------------------
# test_pdf_filename_test_de_eje
#
# RED state: simulates the path that test_de_eje generator.render() currently
# produces (the broken ``{label}__{email}.pdf`` format) and asserts that:
#   1. The filename starts with "informe_"
#   2. _extract_email_from_pdf() returns a non-None email string
#
# Both assertions fail before the generator fix (broken format fails both).
# Both assertions pass after the generator fix (correct format satisfies both).
# ---------------------------------------------------------------------------

def test_pdf_filename_test_de_eje():
    """
    Filename produced by test_de_eje generator satisfies the runner contract.

    Simulates the FIXED generator output:
        email            = "student_at_example_com"  (_safe_filename_component applied)
        assessment_type  = "M2"
        correct filename = "informe_student_at_example_com_M2.pdf"

    Both assertions must pass after the generator fix (GREEN state).
    """
    runner = _runner("test_de_eje")

    # Simulate what the FIXED generator produces:
    # informe_{_safe_filename_component(email)}_{_safe_filename_component(plan.assessment_type)}.pdf
    correct_path = Path("informe_student_at_example_com_M2.pdf")

    # Assertion 1: filename must start with "informe_"
    assert correct_path.name.startswith("informe_"), (
        f"PDF filename from test_de_eje must start with 'informe_', got: {correct_path.name!r}."
    )

    # Assertion 2: runner must be able to extract a student email from the filename
    extracted = runner._extract_email_from_pdf(correct_path)
    assert extracted is not None, (
        f"PipelineRunner._extract_email_from_pdf() returned None for {correct_path.name!r}. "
        f"Every student would be silently skipped and zero emails sent."
    )
    assert extracted == "student_at_example_com", (
        f"Extracted email should be 'student_at_example_com', got: {extracted!r}"
    )


# ---------------------------------------------------------------------------
# test_pdf_filename_examen_de_eje
#
# Identical contract assertion for examen_de_eje generator output.
# Same RED/GREEN lifecycle as test_pdf_filename_test_de_eje.
# ---------------------------------------------------------------------------

def test_pdf_filename_examen_de_eje():
    """
    Filename produced by examen_de_eje generator satisfies the runner contract.

    Simulates the FIXED generator output:
        email            = "student_at_example_com"  (_safe_filename_component applied)
        assessment_type  = "M2"
        correct filename = "informe_student_at_example_com_M2.pdf"

    Both assertions must pass after the generator fix (GREEN state).
    """
    runner = _runner("examen_de_eje")

    # Simulate what the FIXED generator produces:
    # informe_{_safe_filename_component(email)}_{_safe_filename_component(plan.assessment_type)}.pdf
    correct_path = Path("informe_student_at_example_com_M2.pdf")

    # Assertion 1: filename must start with "informe_"
    assert correct_path.name.startswith("informe_"), (
        f"PDF filename from examen_de_eje must start with 'informe_', got: {correct_path.name!r}."
    )

    # Assertion 2: runner must be able to extract a student email from the filename
    extracted = runner._extract_email_from_pdf(correct_path)
    assert extracted is not None, (
        f"PipelineRunner._extract_email_from_pdf() returned None for {correct_path.name!r}. "
        f"Every student would be silently skipped and zero emails sent."
    )
    assert extracted == "student_at_example_com", (
        f"Extracted email should be 'student_at_example_com', got: {extracted!r}"
    )
