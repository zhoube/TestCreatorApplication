from __future__ import annotations

from pathlib import Path

from state import GeneratedFile


def safe_output_path(output_dir: str | Path, filename: str) -> Path:
    base = Path(output_dir).resolve()
    target = (base / filename).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"Unsafe output path: {filename}")
    return target


def write_generated_files(files: list[GeneratedFile], output_dir: str | Path) -> list[str]:
    base = Path(output_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for generated in files:
        target = safe_output_path(base, Path(generated.path).name)
        target.write_text(generated.content, encoding="utf-8")
        written.append(str(target))
    return written
