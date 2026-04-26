from __future__ import annotations

import html
import os
import re
import time

import requests
import streamlit as st
from streamlit_mic_recorder import mic_recorder

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

PRIMARY = "#0F172A"
TEXT = "#0B1220"
MUTED = "#667085"
BORDER = "rgba(15, 23, 42, 0.08)"
CARD_BG = "rgba(255, 255, 255, 0.82)"
SOFT_BG = "rgba(248, 250, 252, 0.9)"
ACCENT_1 = "#1D4ED8"
ACCENT_2 = "#7C3AED"
ACCENT_3 = "#06B6D4"

STEP_DETAILS = {
    "queued": ("Queued", "Your job has been created and is waiting to begin."),
    "model_check": ("Preparing model", "Checking that the selected transcription model is available and ready to use."),
    "model_download": ("Downloading model", "The selected model is being downloaded locally for first-time use on this machine."),
    "model_loaded": ("Model ready", "The transcription model is loaded locally and ready to process your audio."),
    "audio_normalization": ("Preparing audio", "Your audio is being cleaned up and converted into a format that works best for transcription."),
    "audio_normalized": ("Audio prepared", "The audio has been successfully prepared for the next stage."),
    "language_selected": ("Checking language", "The app is deciding whether Arabic, English, or automatic detection is the best fit for this recording."),
    "chunking": ("Splitting audio", "Long audio is being divided into smaller parts so processing stays reliable and steady."),
    "chunking_done": ("Audio sections ready", "All audio sections are prepared and ready for transcription."),
    "gpu_acceleration": ("Using GPU", "A compatible graphics processor was found, so the app is using it to speed things up."),
    "parallel_transcription": ("Transcribing in parallel", "Multiple audio sections are being processed at the same time to reduce waiting."),
    "transcribing": ("Transcribing audio", "The app is listening through the next part of the recording and turning speech into text."),
    "retrying_chunk": ("Retrying section", "One section needs another pass to improve reliability, so the app is trying it again."),
    "chunk_completed": ("Section finished", "One more section has finished processing and the transcript is coming together."),
    "merging": ("Combining transcript", "The app is stitching the transcribed sections into one continuous transcript."),
    "outputs": ("Preparing files", "Downloadable transcript files are being generated for you."),
    "completed": ("Finished", "Your transcription is complete and ready to review."),
    "cancelling": ("Stopping", "The app received your stop request and is wrapping up the current step safely."),
    "cancelled": ("Stopped", "The transcription was stopped before completion."),
    "failed": ("Needs attention", "The job could not finish. You can review the message below and try again."),
    "summarization_requested": ("Summary queued", "The app is getting the transcript summary workflow ready."),
    "summarization": ("Building summary", "The app is reading the transcript and preparing a clear local summary."),
    "summarization_done": ("Summary ready", "The local summary has been completed and added to the result."),
    "summary_cancelling": ("Stopping summary", "The app received your stop request and is safely finishing the current summary step."),
    "summarization_cancelled": ("Summary stopped", "The summary process was stopped before completion."),
    "summarization_failed": ("Summary unavailable", "The summary could not be completed this time."),
}

st.set_page_config(
    page_title="On-Prem Speech to Text",
    layout="wide",
)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(29,78,216,0.10), transparent 28%),
                    radial-gradient(circle at top right, rgba(124,58,237,0.09), transparent 22%),
                    radial-gradient(circle at bottom left, rgba(6,182,212,0.08), transparent 24%),
                    linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
                color: {TEXT};
            }}

            .block-container {{
                max-width: 1050px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }}

            .hero {{
                padding: 2rem 2rem 1.8rem 2rem;
                border-radius: 26px;
                background:
                    linear-gradient(135deg, rgba(15,23,42,0.97) 0%, rgba(30,41,59,0.96) 35%, rgba(29,78,216,0.92) 100%);
                color: white;
                box-shadow: 0 20px 60px rgba(15,23,42,0.16);
                border: 1px solid rgba(255,255,255,0.10);
                margin-bottom: 1.15rem;
            }}

            .hero h1 {{
                margin: 0;
                font-size: 2.15rem;
                font-weight: 700;
                letter-spacing: -0.03em;
            }}

            .hero p {{
                margin: 0.85rem 0 0 0;
                font-size: 1rem;
                line-height: 1.65;
                color: rgba(255,255,255,0.84);
                max-width: 760px;
            }}

            .section-card {{
                background: {CARD_BG};
                border: 1px solid {BORDER};
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border-radius: 24px;
                padding: 1.35rem 1.35rem 1.25rem 1.35rem;
                box-shadow: 0 16px 40px rgba(15,23,42,0.06);
                margin-bottom: 1rem;
            }}

            .step-label {{
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                font-size: 0.82rem;
                font-weight: 700;
                color: {ACCENT_1};
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.55rem;
            }}

            .section-title {{
                font-size: 1.25rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.35rem;
                letter-spacing: -0.02em;
            }}

            .section-subtitle {{
                font-size: 0.96rem;
                color: {MUTED};
                line-height: 1.6;
                margin-bottom: 0.9rem;
            }}

            .status-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 0.25rem;
                margin-bottom: 1rem;
            }}

            .status-tile {{
                background: {SOFT_BG};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 0.85rem 0.95rem;
            }}

            .status-kicker {{
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: {MUTED};
                margin-bottom: 0.3rem;
                font-weight: 700;
            }}

            .status-value {{
                font-size: 1rem;
                font-weight: 700;
                color: {PRIMARY};
                line-height: 1.3;
            }}

            .progress-shell {{
                background: rgba(15,23,42,0.06);
                border-radius: 999px;
                height: 11px;
                overflow: hidden;
                margin: 0.45rem 0 0.85rem 0;
            }}

            .progress-fill {{
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, {ACCENT_1} 0%, {ACCENT_2} 55%, {ACCENT_3} 100%);
                transition: width 0.25s ease;
            }}

            .progress-meta {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin-top: 0.2rem;
                margin-bottom: 0.4rem;
            }}

            .progress-percent {{
                font-size: 1.1rem;
                font-weight: 700;
                color: {PRIMARY};
            }}

            .progress-message {{
                font-size: 0.95rem;
                color: {MUTED};
                line-height: 1.5;
            }}

            .updates-box {{
                background: rgba(255,255,255,0.72);
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 0.95rem 1rem;
                margin-top: 0.9rem;
            }}

            .stage-card {{
                background: linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(248,250,252,0.96) 100%);
                border: 1px solid rgba(29,78,216,0.12);
                border-radius: 18px;
                padding: 1rem 1.05rem;
                margin-top: 0.85rem;
                box-shadow: 0 10px 28px rgba(15,23,42,0.04);
            }}

            .stage-kicker {{
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: {ACCENT_1};
                font-weight: 700;
                margin-bottom: 0.35rem;
            }}

            .stage-title {{
                font-size: 1.08rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.3rem;
            }}

            .stage-description {{
                color: {MUTED};
                font-size: 0.95rem;
                line-height: 1.6;
            }}

            .timeline {{
                display: grid;
                gap: 0.7rem;
                margin-top: 0.95rem;
            }}

            .timeline-item {{
                display: grid;
                grid-template-columns: 0.7rem 1fr;
                gap: 0.8rem;
                align-items: start;
            }}

            .timeline-dot {{
                width: 0.7rem;
                height: 0.7rem;
                border-radius: 999px;
                margin-top: 0.35rem;
                background: linear-gradient(180deg, {ACCENT_1} 0%, {ACCENT_3} 100%);
                box-shadow: 0 0 0 4px rgba(29,78,216,0.10);
            }}

            .timeline-content {{
                background: rgba(255,255,255,0.72);
                border: 1px solid rgba(15,23,42,0.06);
                border-radius: 16px;
                padding: 0.75rem 0.85rem;
            }}

            .timeline-title {{
                color: {PRIMARY};
                font-size: 0.92rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }}

            .timeline-text {{
                color: {MUTED};
                font-size: 0.9rem;
                line-height: 1.55;
            }}

            .updates-title {{
                font-size: 0.9rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.75rem;
            }}

            .update-item {{
                display: flex;
                gap: 0.8rem;
                align-items: flex-start;
                padding: 0.62rem 0;
                border-bottom: 1px solid rgba(15,23,42,0.06);
            }}

            .update-item:last-child {{
                border-bottom: none;
                padding-bottom: 0;
            }}

            .update-bullet {{
                width: 0.5rem;
                height: 0.5rem;
                margin-top: 0.38rem;
                border-radius: 999px;
                background: linear-gradient(180deg, {ACCENT_1} 0%, {ACCENT_3} 100%);
                flex-shrink: 0;
            }}

            .update-text {{
                color: {PRIMARY};
                font-size: 0.95rem;
                line-height: 1.55;
            }}

            .result-box {{
                background: rgba(255,255,255,0.75);
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 0.95rem 1rem;
            }}

            .summary-box {{
                background: rgba(255,255,255,0.78);
                border: 1px solid rgba(29,78,216,0.16);
                border-radius: 18px;
                padding: 1rem 1.05rem;
                box-shadow: 0 10px 28px rgba(15,23,42,0.04);
                min-height: 160px;
            }}

            .summary-shell {{
                position: relative;
            }}

            .summary-shell.locked .summary-box {{
                filter: blur(5px);
                opacity: 0.72;
                user-select: none;
                pointer-events: none;
            }}

            .summary-lock {{
                position: absolute;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                padding: 1.25rem;
                border-radius: 18px;
                background: rgba(248, 250, 252, 0.28);
            }}

            .summary-lock-card {{
                max-width: 460px;
                background: rgba(255,255,255,0.92);
                border: 1px solid rgba(15,23,42,0.08);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 30px rgba(15,23,42,0.08);
            }}

            .summary-lock-title {{
                font-size: 0.95rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.35rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }}

            .summary-lock-text {{
                color: {MUTED};
                font-size: 0.94rem;
                line-height: 1.6;
            }}

            .summary-title {{
                font-size: 0.95rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.45rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }}

            .summary-text {{
                color: {PRIMARY};
                font-size: 0.98rem;
                line-height: 1.7;
                white-space: pre-wrap;
            }}

            .result-column-title {{
                font-size: 0.95rem;
                font-weight: 700;
                color: {PRIMARY};
                margin-bottom: 0.55rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }}

            .hint {{
                color: {MUTED};
                font-size: 0.93rem;
                line-height: 1.55;
            }}

            div[data-testid="stTextArea"] textarea {{
                font-size: 0.95rem !important;
                line-height: 1.6 !important;
                border-radius: 16px !important;
            }}

            div[data-testid="stFileUploader"] > section {{
                border-radius: 18px !important;
                border: 1px dashed rgba(29,78,216,0.35) !important;
                background: rgba(255,255,255,0.58) !important;
            }}

            div.stButton > button,
            div[data-testid="stDownloadButton"] > button {{
                border-radius: 14px !important;
                height: 2.9rem !important;
                font-weight: 600 !important;
                border: 1px solid rgba(15,23,42,0.08) !important;
                box-shadow: 0 8px 18px rgba(15,23,42,0.05) !important;
            }}

            div.stButton > button[kind="primary"] {{
                background: linear-gradient(90deg, {ACCENT_1} 0%, {ACCENT_2} 100%) !important;
                color: white !important;
                border: none !important;
            }}

            @media (max-width: 900px) {{
                .status-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "job_id": None,
        "job_result": None,
        "recording_blob": None,
        "active_source_label": None,
        "last_uploaded_name": None,
        "upload_widget_version": 0,
        "summary_requested": False,
        "summary_stop_requested": False,
        "is_transcribing": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_transcription_state() -> None:
    st.session_state.job_id = None
    st.session_state.job_result = None
    st.session_state.recording_blob = None
    st.session_state.active_source_label = None
    st.session_state.last_uploaded_name = None
    st.session_state.upload_widget_version += 1
    st.session_state.summary_requested = False
    st.session_state.summary_stop_requested = False
    st.session_state.is_transcribing = False


def api_get(path: str) -> requests.Response:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=60)
    response.raise_for_status()
    return response


def api_post(path: str, **kwargs) -> requests.Response:
    response = requests.post(f"{API_BASE_URL}{path}", timeout=300, **kwargs)
    response.raise_for_status()
    return response


def api_download(path: str) -> bytes:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=120)
    response.raise_for_status()
    return response.content


def fetch_models() -> list[dict]:
    return api_get("/api/models").json()


def upload_file(endpoint: str, file_name: str, file_bytes: bytes, mime_type: str) -> dict:
    files = {"file": (file_name, file_bytes, mime_type)}
    return api_post(endpoint, files=files).json()


def start_job(file_id: str, source_type: str, model_name: str) -> str:
    payload = {
        "file_id": file_id,
        "source_type": source_type,
        "model_name": model_name,
        "language": "auto",
    }
    return api_post("/api/transcriptions/start", json=payload).json()["job_id"]


def fetch_job(job_id: str) -> dict:
    return api_get(f"/api/transcriptions/{job_id}").json()


def start_summary(job_id: str) -> dict:
    return api_post(f"/api/transcriptions/{job_id}/summarize").json()


def cancel_transcription(job_id: str) -> dict:
    return api_post(f"/api/transcriptions/{job_id}/cancel").json()


def cancel_summary(job_id: str) -> dict:
    return api_post(f"/api/transcriptions/{job_id}/cancel-summary").json()


def seconds_to_label(seconds: float) -> str:
    total = max(0.0, float(seconds))
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = int(total % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render_segments(segments: list[dict]) -> str:
    lines = []
    for item in segments:
        speaker = item.get("speaker") or "Timestamp"
        lines.append(
            f"[{seconds_to_label(item['start'])} - {seconds_to_label(item['end'])}] {speaker}: {item['text']}"
        )
    return "\n".join(lines)


def contains_arabic(text: str | None) -> bool:
    return bool(text and re.search(r"[\u0600-\u06FF]", text))


def normalize_summary_spacing(text: str | None) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return "Summary unavailable"
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?m)\n{2,}(?=(?:[-*•]\s))", "\n", cleaned)
    cleaned = re.sub(r"(?m)(\*\*[^*\n]+\*\*|[^:\n]{1,80}:)\n{2,}(?=(?:[-*•]\s))", r"\1\n", cleaned)
    return cleaned.strip()


def format_summary_for_download(text: str | None) -> bytes:
    normalized = normalize_summary_spacing(text)
    if contains_arabic(normalized):
        normalized = "\n".join(f"\u200f{line}" if line.strip() else "" for line in normalized.splitlines())
    return normalized.encode("utf-8")


def render_summary(
    summary: str | None,
    summary_status: str,
    summary_progress_percent: int = 0,
    summary_progress_message: str | None = None,
    locked: bool = False,
) -> None:
    if summary_status in {"running", "cancelling"}:
        summary_text = normalize_summary_spacing(summary_progress_message or "Generating summary...")
    elif locked:
        summary_text = "The summary will appear here once transcription is complete and ready for summarization."
    else:
        summary_text = normalize_summary_spacing(summary or "Summary unavailable")
    is_arabic = contains_arabic(summary_text)
    summary_dir = "rtl" if is_arabic else "ltr"
    summary_align = "right" if is_arabic else "left"
    shell_class = "summary-shell locked" if locked else "summary-shell"
    lock_overlay = """<div class="summary-lock">
<div class="summary-lock-card">
<div class="summary-lock-title">Summarization Locked</div>
<div class="summary-lock-text">
Finish transcription first, then this section will unlock so you can generate the local summary.
</div>
</div>
</div>""" if locked else ""
    st.markdown(
        f"""<div class="{shell_class}">
<div class="summary-box" dir="{summary_dir}" style="text-align:{summary_align};">
<div class="summary-title">Summarization</div>
<div class="summary-text">{html.escape(summary_text)}</div>
</div>
{lock_overlay}
</div>""",
        unsafe_allow_html=True,
    )
    if summary_status in {"running", "cancelling"} and not locked:
        st.progress(max(0, min(summary_progress_percent, 100)) / 100.0, text=f"Summary progress: {max(0, min(summary_progress_percent, 100))}%")


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>On-Prem Speech to Text</h1>
            <p>
                Upload audio or record directly in the browser, transcribe locally with Whisper,
                generate a local Ollama summary on the same machine, and export both results in one workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_intro(step_number: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="step-label">Step {step_number}</div>
        <div class="section-title">{html.escape(title)}</div>
        <div class="section-subtitle">{html.escape(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def begin_transcription_from_upload(uploaded_file, model_name: str) -> None:
    if uploaded_file is None:
        st.warning("Please upload an audio file first.")
        return

    try:
        stored = upload_file(
            "/api/upload-audio",
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "audio/mpeg",
        )
        job_id = start_job(stored["file_id"], stored["source_type"], model_name)
    except requests.RequestException as exc:
        st.error(f"Could not start transcription: {exc}")
        return

    st.session_state.job_id = job_id
    st.session_state.job_result = None
    st.session_state.active_source_label = uploaded_file.name
    st.session_state.last_uploaded_name = uploaded_file.name
    st.session_state.is_transcribing = True


def begin_transcription_from_recording(model_name: str) -> None:
    recording_blob = st.session_state.get("recording_blob")
    if not recording_blob:
        st.warning("Please record audio first.")
        return

    try:
        file_name = f"recording_{int(time.time())}.webm"
        stored = upload_file(
            "/api/record-audio",
            file_name,
            recording_blob["bytes"],
            "audio/webm",
        )
        job_id = start_job(stored["file_id"], stored["source_type"], model_name)
    except requests.RequestException as exc:
        st.error(f"Could not start transcription: {exc}")
        return

    st.session_state.job_id = job_id
    st.session_state.job_result = None
    st.session_state.active_source_label = "Browser recording"
    st.session_state.recording_blob = None
    st.session_state.is_transcribing = True


def get_step_detail(progress_item: dict | None) -> tuple[str, str]:
    if not progress_item:
        return (
            "Waiting to begin",
            "The app will show each major step here so you can follow what is happening while it works.",
        )

    step_name = str(progress_item.get("step", "") or "")
    fallback_message = str(progress_item.get("message", "Processing your request."))
    return STEP_DETAILS.get(
        step_name,
        ("In progress", fallback_message),
    )


def extract_chunk_detail(progress_items: list[dict]) -> str | None:
    for item in reversed(progress_items):
        message = str(item.get("message", "") or "")
        match = re.search(r"chunk\s+(\d+)\s+of\s+(\d+)", message, flags=re.IGNORECASE)
        if match:
            current = match.group(1)
            total = match.group(2)
            return f"Processing part {current} of {total}."
    return None


def render_stage_detail(progress_items: list[dict]) -> None:
    current = progress_items[-1] if progress_items else None
    title, description = get_step_detail(current)
    chunk_detail = extract_chunk_detail(progress_items)
    chunk_html = (
        f'<div class="stage-description" style="margin-top:0.45rem;"><strong>{html.escape(chunk_detail)}</strong></div>'
        if chunk_detail
        else ""
    )
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-kicker">Current stage</div>
            <div class="stage-title">{html.escape(title)}</div>
            <div class="stage-description">{html.escape(description)}</div>
            {chunk_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_timeline(progress_items: list[dict]) -> None:
    if not progress_items:
        return

    recent_items = progress_items[-6:]
    rows: list[str] = []
    rendered_steps: set[str] = set()
    for item in reversed(recent_items):
        step_name = str(item.get("step", "") or "")
        if step_name in rendered_steps:
            continue
        rendered_steps.add(step_name)
        title, description = get_step_detail(item)
        rows.append(
            f"""<div class="timeline-item">
<div class="timeline-dot"></div>
<div class="timeline-content">
<div class="timeline-title">{html.escape(title)}</div>
<div class="timeline-text">{html.escape(description)}</div>
</div>
</div>"""
        )

    st.markdown(
        f"""<div class="timeline">
{''.join(rows)}
</div>""",
        unsafe_allow_html=True,
    )


def render_progress_panel(result: dict) -> None:
    progress_items = result.get("progress", [])
    last_progress = progress_items[-1] if progress_items else {"message": "Waiting...", "percent": 0}
    percent = max(0, min(int(float(last_progress.get("percent", 0))), 100))

    status_value = html.escape(str(result.get("status", "queued")).replace("_", " ").title())
    diarization_value = html.escape(str(result.get("diarization_status", "not_available")).replace("_", " ").title())
    current_message = html.escape(str(last_progress.get("message", "Waiting for progress...")))

    st.markdown(
        f"""
        <div class="status-grid">
            <div class="status-tile">
                <div class="status-kicker">Status</div>
                <div class="status-value">{status_value}</div>
            </div>
            <div class="status-tile">
                <div class="status-kicker">Progress</div>
                <div class="status-value">{percent}%</div>
            </div>
        </div>

        <div class="progress-meta">
            <div class="progress-message">{current_message}</div>
            <div class="progress-percent">{percent}%</div>
        </div>
        <div class="progress-shell">
            <div class="progress-fill" style="width: {percent}%;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_stage_detail(progress_items)
    render_timeline(progress_items)

    st.markdown(
        f"""
        <div class="hint" style="margin-top:0.8rem;">
            Diarization: <strong>{diarization_value}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def poll_until_finished(job_id: str) -> dict | None:
    try:
        result = fetch_job(job_id)
    except requests.RequestException as exc:
        st.error(f"Failed to retrieve job status: {exc}")
        return None

    st.session_state.job_result = result
    render_progress_panel(result)
    return result


inject_css()
init_state()
render_hero()

models: list[dict] = []
try:
    models = fetch_models()
except requests.RequestException as exc:
    st.error(f"Backend connection failed: {exc}")
    st.stop()

if not models:
    st.error("No Whisper models are currently available from the backend.")
    st.stop()

model_lookup = {item["name"]: item for item in models}
default_index = 2 if len(models) > 2 else 0

# Step 1
st.markdown('<div class="section-card">', unsafe_allow_html=True)
render_section_intro(
    "1",
    "Choose a model",
    "Select the Whisper model you want to use for this transcription.",
)
model_name = st.selectbox(
    "Model",
    list(model_lookup.keys()),
    index=default_index,
    label_visibility="collapsed",
)
selected_model = model_lookup[model_name]
model_badge = "Ready locally" if selected_model.get("available_locally") else "Prepared on first run"
st.markdown(
    f"""
    <div class="hint">
        Selected model: <strong>{html.escape(model_name)}</strong> · {html.escape(model_badge)}
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# Step 2
st.markdown('<div class="section-card">', unsafe_allow_html=True)
render_section_intro(
    "2",
    "Add audio",
    "Upload a file or record directly in the browser, then start transcription from the same section.",
)

input_mode = st.radio(
    "Input method",
    ["Upload audio file", "Record audio"],
    horizontal=True,
    label_visibility="collapsed",
)

if input_mode == "Upload audio file":
    uploaded = st.file_uploader(
        "Upload audio",
        type=["mp3", "wav", "m4a", "ogg", "flac", "mp4", "aac", "webm", "mpeg", "mpga"],
        label_visibility="collapsed",
        key=f"upload_audio_{st.session_state.upload_widget_version}",
    )

    if uploaded is not None:
        st.markdown(
            f"""
            <div class="hint" style="margin-bottom:0.8rem;">
                Ready to transcribe: <strong>{html.escape(uploaded.name)}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    transcribe_label = "Transcribing..." if st.session_state.is_transcribing else "Transcribe audio"
    if st.button(transcribe_label, type="primary", use_container_width=True, disabled=st.session_state.is_transcribing):
        begin_transcription_from_upload(uploaded, model_name)
    if st.session_state.is_transcribing:
        st.info("Working... transcription is running now.")
else:
    st.markdown(
        """
        <div class="hint" style="margin-bottom:0.8rem;">
            Start recording, stop when finished, then transcribe immediately.
        </div>
        """,
        unsafe_allow_html=True,
    )

    recording = mic_recorder(
        start_prompt="Start recording",
        stop_prompt="Stop recording",
        just_once=False,
        use_container_width=True,
        format="webm",
    )

    if recording:
        st.session_state.recording_blob = recording

    has_recording = st.session_state.recording_blob is not None
    if has_recording:
        st.markdown(
            """
            <div class="hint" style="margin-bottom:0.8rem;">
                Recording captured and ready for transcription.
            </div>
            """,
            unsafe_allow_html=True,
        )

    record_button_label = "Transcribing..." if st.session_state.is_transcribing else "Transcribe recording"
    if st.button(
        record_button_label,
        type="primary",
        use_container_width=True,
        disabled=(not has_recording) or st.session_state.is_transcribing,
    ):
        begin_transcription_from_recording(model_name)
    if st.session_state.is_transcribing:
        st.info("Working... transcription is running now.")

st.markdown("</div>", unsafe_allow_html=True)

# Step 3
st.markdown('<div class="section-card">', unsafe_allow_html=True)
render_section_intro(
    "3",
    "Track progress and review results",
    "Follow live backend updates, then download the completed transcript.",
)

active_source = st.session_state.get("active_source_label")
if active_source:
    st.markdown(
        f"""
        <div class="hint" style="margin-bottom:0.8rem;">
            Current source: <strong>{html.escape(active_source)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

job_id = st.session_state.get("job_id")
result = st.session_state.get("job_result")

if not job_id:
    st.markdown(
        """
        <div class="result-box">
            <div class="hint">
                No transcription job is running yet. Once you start one, live progress and results will appear here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
    render_summary(
        None,
        "not_started",
        0,
        None,
        locked=True,
    )
else:
    latest_result = poll_until_finished(job_id)
    should_rerun = False

    transcription_complete = latest_result is not None and latest_result.get("status") == "completed"
    if not transcription_complete:
        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        if latest_result is not None and latest_result.get("status") in {"queued", "running"}:
            if st.button("Stop transcription", use_container_width=True, key="stop_transcription_progress"):
                try:
                    cancel_transcription(job_id)
                except requests.RequestException as exc:
                    st.error(f"Could not stop transcription: {exc}")
                else:
                    st.rerun()

        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        pending_summary = latest_result.get("summary") if latest_result is not None else None
        pending_summary_status = latest_result.get("summary_status", "not_started") if latest_result is not None else "not_started"
        pending_summary_percent = int(latest_result.get("summary_progress_percent", 0) or 0) if latest_result is not None else 0
        pending_summary_message = latest_result.get("summary_progress_message") if latest_result is not None else None
        render_summary(
            pending_summary,
            pending_summary_status,
            pending_summary_percent,
            pending_summary_message,
            locked=True,
        )
        if latest_result is not None and latest_result.get("status") in {"queued", "running"}:
            should_rerun = True

    if latest_result is not None and latest_result.get("status") == "completed":
        st.session_state.is_transcribing = False
        transcript = render_segments(latest_result.get("segments", []))
        summary_text = latest_result.get("summary")
        summary_status = latest_result.get("summary_status", "not_started")
        summary_progress_percent = int(latest_result.get("summary_progress_percent", 0) or 0)
        summary_progress_message = latest_result.get("summary_progress_message")

        st.markdown(
            '<div class="result-column-title">Transcript</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Transcript with timestamps",
            transcript,
            height=420,
        )

        txt_url = latest_result.get("text_download_url")
        docx_url = latest_result.get("docx_download_url")
        summary_download = format_summary_for_download(summary_text or "Summary unavailable")

        if txt_url and docx_url:
            try:
                txt_bytes = api_download(txt_url)
                docx_bytes = api_download(docx_url)
            except requests.RequestException as exc:
                st.error(f"Could not download output files: {exc}")
            else:
                transcript_download_col, transcript_docx_col = st.columns(2)
                with transcript_download_col:
                    st.download_button(
                        "Download Transcript TXT",
                        data=txt_bytes,
                        file_name=f"{job_id}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with transcript_docx_col:
                    st.download_button(
                        "Download Transcript DOCX",
                        data=docx_bytes,
                        file_name=f"{job_id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

        show_primary_summarize_button = summary_status not in {"failed", "cancelled"}
        summarize_disabled = summary_status in {"running", "cancelling", "completed"} or st.session_state.summary_stop_requested
        summarize_label = (
            "Summarizing..."
            if summary_status == "running"
            else "Stopping summary..."
            if summary_status == "cancelling" or st.session_state.summary_stop_requested
            else "Summarize"
        )
        if show_primary_summarize_button and st.button(
            summarize_label,
            use_container_width=True,
            disabled=summarize_disabled,
            key="summarize_completed",
        ):
            try:
                start_summary(job_id)
            except requests.RequestException as exc:
                st.error(f"Could not start summarization: {exc}")
            else:
                st.session_state.summary_requested = True
                st.session_state.summary_stop_requested = False
                st.rerun()

        if summary_status in {"completed", "failed", "cancelled", "not_started"}:
            st.session_state.summary_stop_requested = False

        effective_summary_status = (
            "cancelling"
            if st.session_state.summary_stop_requested and summary_status == "running"
            else summary_status
        )

        effective_summary_message = (
            "Stopping summary after the current request finishes."
            if effective_summary_status == "cancelling"
            else summary_progress_message
        )

        if effective_summary_status in {"running", "cancelling", "completed", "failed", "cancelled"}:
            st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
            render_summary(summary_text, effective_summary_status, summary_progress_percent, effective_summary_message)
            if effective_summary_status == "cancelled":
                st.warning(latest_result.get("summary_error") or "Summary stopped.")
            if effective_summary_status == "running":
                st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
                if st.button("Stop summarizing", use_container_width=True, key="stop_summarizing"):
                    try:
                        cancel_summary(job_id)
                    except requests.RequestException as exc:
                        st.error(f"Could not stop summary: {exc}")
                    else:
                        st.session_state.summary_requested = False
                        st.session_state.summary_stop_requested = True
                        st.rerun()
                should_rerun = True
            elif effective_summary_status == "cancelling":
                should_rerun = True
            elif effective_summary_status in {"failed", "cancelled"}:
                st.session_state.summary_requested = False
                st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
                if st.button("Summarize again", use_container_width=True, key="summarize_again_after_cancel"):
                    try:
                        start_summary(job_id)
                    except requests.RequestException as exc:
                        st.error(f"Could not restart summarization: {exc}")
                    else:
                        st.session_state.summary_requested = True
                        st.session_state.summary_stop_requested = False
                        st.rerun()

        if summary_status == "completed":
            st.session_state.summary_requested = False
            st.download_button(
                "Download Summary TXT",
                data=summary_download,
                file_name=f"{job_id}_summary.txt",
                mime="text/plain",
                use_container_width=True,
                key="download_summary_completed",
            )

    elif latest_result is not None and latest_result.get("status") == "failed":
        st.session_state.is_transcribing = False
        st.error(latest_result.get("error") or "The transcription job failed.")
    elif latest_result is not None and latest_result.get("status") == "cancelled":
        st.session_state.is_transcribing = False
        st.warning(latest_result.get("error") or "The transcription was stopped.")
    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
    if st.button("Transcribe a new file", use_container_width=True, key="new_file_failed"):
        reset_transcription_state()
        st.rerun()
    if should_rerun:
        time.sleep(2)
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
