from pathlib import Path
import uuid

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """
    Sandbox-safe tmp_path replacement.

    The default pytest tmp_path factory relies on directories that are not
    accessible in this environment. Keep temp artifacts in-repo instead.
    """
    base = Path(".tmp_testdata_runtime")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"pytest-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path
