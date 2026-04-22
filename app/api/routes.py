from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.constants import SUPPORTED_MODELS, is_supported_audio_file
from app.schemas.audio import JobStatusResponse, ModelStatusResponse, StartTranscriptionRequest, StoredFileResponse
from app.services.job_store import job_store
from app.services.model_service import model_service
from app.services.transcription_service import transcription_coordinator
from app.utils.file_utils import make_file_id, sanitize_filename, save_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["speech-to-text"])


def _save_incoming_file(upload: UploadFile, destination_root: Path, source_type: str) -> StoredFileResponse:
    sanitized = sanitize_filename(upload.filename or "audio")
    file_id = make_file_id(source_type)
    destination = destination_root / f"{file_id}_{sanitized}"
    size = save_upload_file(upload, destination, settings.max_upload_size_mb * 1024 * 1024)
    if size <= 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded audio file is empty.")
    if not is_supported_audio_file(destination):
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    job_store.save_file_reference(file_id, destination)
    return StoredFileResponse(
        file_id=file_id,
        filename=destination.name,
        path=str(destination),
        size_bytes=size,
        source_type=source_type,
    )


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/models", response_model=list[ModelStatusResponse])
def list_models() -> list[ModelStatusResponse]:
    return [ModelStatusResponse(**item) for item in model_service.list_models()]


@router.post("/models/{model_name}/ensure")
def ensure_model(model_name: str) -> dict[str, str | bool]:
    if model_name not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported model selected.")

    try:
        model_path_before = model_service.is_model_downloaded(model_name)
        _model, device, _cached = model_service.load_model(model_name)
        model_path = model_service.get_model_path(model_name)
        return {
            "name": model_name,
            "available_locally": bool(model_path and model_path.exists()),
            "downloaded_now": not model_path_before,
            "device": device,
            "path": str(model_path) if model_path and model_path.exists() else "",
        }
    except Exception as exc:
        logger.exception("Failed to ensure model %s", model_name)
        raise HTTPException(status_code=500, detail=f"Failed to prepare model '{model_name}': {exc}") from exc


@router.post("/upload-audio", response_model=StoredFileResponse)
def upload_audio(file: UploadFile = File(...)) -> StoredFileResponse:
    return _save_incoming_file(file, settings.uploads_dir, "upload")


@router.post("/record-audio", response_model=StoredFileResponse)
def record_audio(file: UploadFile = File(...)) -> StoredFileResponse:
    return _save_incoming_file(file, settings.recordings_dir, "recording")


@router.post("/transcriptions/start")
def start_transcription(request: StartTranscriptionRequest) -> dict[str, str]:
    if request.model_name not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported model selected.")

    source_path = job_store.get_file_reference(request.file_id)
    if source_path is None or not source_path.exists():
        raise HTTPException(status_code=404, detail="Stored audio file was not found.")

    job = transcription_coordinator.start_job(
        source_path=source_path,
        source_type=request.source_type,
        model_name=request.model_name,
        language=request.language,
    )
    return {"job_id": job.job_id, "status": job.status}


@router.post("/transcriptions/{job_id}/summarize")
def start_summarization(job_id: str) -> dict[str, str]:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Transcription must complete before summarization can start.")
    if not job.transcript_text:
        raise HTTPException(status_code=400, detail="Transcript is not available for summarization.")
    if job.summary_status == "running":
        return {"job_id": job.job_id, "summary_status": job.summary_status}
    if job.summary_status == "completed":
        return {"job_id": job.job_id, "summary_status": job.summary_status}

    transcription_coordinator.start_summary_job(job_id)
    return {"job_id": job.job_id, "summary_status": "running"}


@router.post("/transcriptions/{job_id}/cancel")
def cancel_transcription(job_id: str) -> dict[str, str]:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status not in {"queued", "running"}:
        raise HTTPException(status_code=400, detail="Transcription is not currently running.")

    transcription_coordinator.cancel_job(job_id)
    return {"job_id": job.job_id, "status": "cancelling"}


@router.post("/transcriptions/{job_id}/cancel-summary")
def cancel_summary(job_id: str) -> dict[str, str]:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.summary_status != "running":
        raise HTTPException(status_code=400, detail="Summary is not currently running.")

    transcription_coordinator.cancel_summary_job(job_id)
    return {"job_id": job.job_id, "summary_status": "cancelling"}


@router.get("/transcriptions/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    text_url = f"/api/downloads/{job.job_id}/txt" if job.text_file else None
    docx_url = f"/api/downloads/{job.job_id}/docx" if job.docx_file else None
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        error=job.error,
        progress=[vars(item) for item in job.progress],
        transcript_text=job.transcript_text,
        summary=job.summary,
        summary_status=job.summary_status,
        summary_error=job.summary_error,
        summary_progress_percent=job.summary_progress_percent,
        summary_progress_message=job.summary_progress_message,
        segments=[segment.to_dict() for segment in job.segments],
        text_download_url=text_url,
        docx_download_url=docx_url,
        diarization_status=job.diarization_status,
        device=job.device,
    )


@router.get("/downloads/{job_id}/{file_type}")
def download_result(job_id: str, file_type: str) -> FileResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    file_path: Path | None = None
    media_type = "text/plain"
    if file_type == "txt":
        file_path = job.text_file
    elif file_type == "docx":
        file_path = job.docx_file
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Unsupported download type.")

    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested file not found.")

    return FileResponse(path=file_path, filename=file_path.name, media_type=media_type)
