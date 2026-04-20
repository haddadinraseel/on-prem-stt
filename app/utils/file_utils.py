from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile


def make_file_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def sanitize_filename(filename: str) -> str:
    keep = []
    for char in filename:
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "audio"


def save_upload_file(upload_file: UploadFile, destination: Path, max_size_bytes: int | None = None) -> int:
    size = 0
    with destination.open("wb") as target:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if max_size_bytes is not None and size > max_size_bytes:
                target.close()
                destination.unlink(missing_ok=True)
                upload_file.file.close()
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds the maximum allowed size of {max_size_bytes // (1024 * 1024)} MB.",
                )
            target.write(chunk)
    upload_file.file.close()
    return size


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
