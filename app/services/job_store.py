from __future__ import annotations

import threading
from pathlib import Path

from app.models.job import JobRecord


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._file_index: dict[str, Path] = {}
        self._lock = threading.RLock()

    def save_file_reference(self, file_id: str, path: Path) -> None:
        with self._lock:
            self._file_index[file_id] = path

    def get_file_reference(self, file_id: str) -> Path | None:
        with self._lock:
            return self._file_index.get(file_id)

    def add_job(self, job: JobRecord) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job: JobRecord) -> None:
        with self._lock:
            self._jobs[job.job_id] = job


job_store = JobStore()
