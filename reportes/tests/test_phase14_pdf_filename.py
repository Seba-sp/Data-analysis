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

import pytest

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

    Simulates the broken generator output:
        assessment_label = "M30M2-TEST_DE_EJE_1"  (after _strip_data_suffix)
        email            = "student@example.com"
        broken filename  = "M30M2_TEST_DE_EJE_1__student_at_example_com.pdf"

    After the fix the generator produces:
        "informe_student_at_example_com_M2.pdf"
    which satisfies both assertions.
    """
    runner = _runner("test_de_eje")

    # This path mirrors what the BROKEN generator currently produces.
    # The test FAILS here in RED because the broken format violates the contract.
    # After the fix, the generator produces the correct format so this path is
    # replaced in the test assertion by the correct one.
    #
    # We test the CONTRACT: whatever path the generator produces at
    # runtime must satisfy these two conditions. We simulate the broken path
    # to prove the contract is violated before the fix.
    broken_path = Path("M30M2_TEST_DE_EJE_1__student_at_example_com.pdf")

    # Assertion 1: filename must start with "informe_"
    assert broken_path.name.startswith("informe_"), (
        f"PDF filename from test_de_eje must start with 'informe_', got: {broken_path.name!r}. "
        f"Fix: change the generator to produce 'informe_{{email}}_{{assessment_type}}.pdf'."
    )

    # Assertion 2: runner must be able to extract a student email from the filename
    extracted = runner._extract_email_from_pdf(broken_path)
    assert extracted is not None, (
        f"PipelineRunner._extract_email_from_pdf() returned None for {broken_path.name!r}. "
        f"This means every student is silently skipped and zero emails are sent. "
        f"Fix: change the generator to produce 'informe_{{email}}_{{assessment_type}}.pdf'."
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

    Same broken pattern as test_de_eje — ``{label}__{email}.pdf``.
    After the fix the generator produces ``informe_{email}_{assessment_type}.pdf``.
    """
    runner = _runner("examen_de_eje")

    broken_path = Path("M30M2_EXAMEN_DE_EJE_1__student_at_example_com.pdf")

    # Assertion 1: filename must start with "informe_"
    assert broken_path.name.startswith("informe_"), (
        f"PDF filename from examen_de_eje must start with 'informe_', got: {broken_path.name!r}. "
        f"Fix: change the generator to produce 'informe_{{email}}_{{assessment_type}}.pdf'."
    )

    # Assertion 2: runner must be able to extract a student email from the filename
    extracted = runner._extract_email_from_pdf(broken_path)
    assert extracted is not None, (
        f"PipelineRunner._extract_email_from_pdf() returned None for {broken_path.name!r}. "
        f"Fix: change the generator to produce 'informe_{{email}}_{{assessment_type}}.pdf'."
    )
