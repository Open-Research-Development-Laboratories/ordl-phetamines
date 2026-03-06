from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CodeDigestChunk, CodeDigestFile, CodeDigestRun


SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


@dataclass
class DigestionSummary:
    run_id: str
    total_files: int
    total_lines: int
    reviewed_lines: int


def _text_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    if b"\x00" in raw:
        return []
    text = raw.decode("utf-8", errors="ignore")
    return text.splitlines()


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def run_code_digestion(
    db: Session,
    *,
    project_id: str,
    repo_root: str,
    chunk_size: int = 200,
) -> DigestionSummary:
    root = Path(repo_root).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("repo_root must be an existing directory")
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    run = CodeDigestRun(project_id=project_id, repo_root=str(root), status="running")
    db.add(run)
    db.flush()

    total_files = 0
    total_lines = 0
    reviewed_lines = 0

    for file_path in _iter_files(root):
        lines = _text_lines(file_path)
        if not lines:
            continue

        rel_path = file_path.relative_to(root).as_posix()
        file_hash = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
        digest_file = CodeDigestFile(
            run_id=run.id,
            project_id=project_id,
            file_path=rel_path,
            file_hash=file_hash,
            total_lines=len(lines),
            reviewed_lines=len(lines),
        )
        db.add(digest_file)
        db.flush()

        prev_hash = ""
        chunk_index = 0
        chunks: list[CodeDigestChunk] = []
        for start in range(0, len(lines), chunk_size):
            end = min(start + chunk_size, len(lines))
            body = "\n".join(lines[start:end])
            seed = f"{prev_hash}|{rel_path}|{start + 1}|{end}|{body}"
            chunk_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
            chunks.append(
                CodeDigestChunk(
                    file_id=digest_file.id,
                    chunk_index=chunk_index,
                    start_line=start + 1,
                    end_line=end,
                    chunk_hash=chunk_hash,
                )
            )
            prev_hash = chunk_hash
            chunk_index += 1
        if chunks:
            db.add_all(chunks)
        digest_file.last_chunk_hash = prev_hash

        total_files += 1
        total_lines += len(lines)
        reviewed_lines += len(lines)

    run.total_files = total_files
    run.total_lines = total_lines
    run.reviewed_lines = reviewed_lines
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.flush()

    return DigestionSummary(
        run_id=run.id,
        total_files=total_files,
        total_lines=total_lines,
        reviewed_lines=reviewed_lines,
    )


def get_project_digestion_status(db: Session, *, project_id: str) -> dict:
    latest = db.scalar(
        select(CodeDigestRun)
        .where(CodeDigestRun.project_id == project_id)
        .order_by(CodeDigestRun.started_at.desc())
        .limit(1)
    )
    if latest is None:
        return {"project_id": project_id, "status": "not_started", "coverage_percent": 0.0}

    reviewed_sum = db.scalar(
        select(func.coalesce(func.sum(CodeDigestFile.reviewed_lines), 0)).where(CodeDigestFile.run_id == latest.id)
    ) or 0
    total_sum = db.scalar(
        select(func.coalesce(func.sum(CodeDigestFile.total_lines), 0)).where(CodeDigestFile.run_id == latest.id)
    ) or 0
    coverage = 0.0 if total_sum == 0 else round((reviewed_sum / total_sum) * 100, 2)

    return {
        "project_id": project_id,
        "run_id": latest.id,
        "status": latest.status,
        "total_files": latest.total_files,
        "total_lines": total_sum,
        "reviewed_lines": reviewed_sum,
        "coverage_percent": coverage,
        "full_coverage": reviewed_sum >= total_sum and total_sum > 0,
    }
