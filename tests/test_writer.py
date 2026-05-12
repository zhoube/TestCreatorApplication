from pathlib import Path

import pytest

from state import GeneratedFile
from nodes.writer.writer import safe_output_path, write_generated_files


def test_safe_output_path_blocks_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, "../bad.py")


def test_write_generated_files(tmp_path: Path) -> None:
    written = write_generated_files([GeneratedFile(path="test_sample.py", content="def test_ok():\n    assert True\n")], tmp_path)

    assert len(written) == 1
    assert Path(written[0]).read_text(encoding="utf-8").startswith("def test_ok")
