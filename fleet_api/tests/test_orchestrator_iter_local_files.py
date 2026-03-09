from __future__ import annotations

from pathlib import Path

from fleet_api.fleet_api.orchestrator import _iter_local_files


def test_iter_local_files_skips_traversal_and_absolute_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    inside = root / "safe.txt"
    inside.write_text("ok", encoding="utf-8")

    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    results = list(_iter_local_files(root, ["safe.txt", "../secret.txt", str(outside)]))
    rel_paths = [rel for _, rel in results]

    assert rel_paths == ["safe.txt"]


def test_iter_local_files_keeps_symlinked_escape_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("secret", encoding="utf-8")

    link = root / "linked"
    link.symlink_to(outside_dir, target_is_directory=True)

    results = list(_iter_local_files(root, ["linked"]))
    assert results == []

