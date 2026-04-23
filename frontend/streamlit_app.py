from __future__ import annotations

import html
import os
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

            .summary-box.summary-box-waiting {{
                background: rgba(255,255,255,0.45);
                border: 1px dashed rgba(102,126,162,0.28);
                box-shadow: none;
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

            .summary-box.summary-box-waiting .summary-title,
            .summary-box.summary-box-waiting .summary-text {{
                color: {MUTED};
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
        "is_transcribing": False,
        "transcription_cancel_requested": False,
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
    st.session_state.is_transcribing = False
    st.session_state.transcription_cancel_requested = False
    st.session_state.job_started_at = None
    st.session_state.summary_started_at = None


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


def render_summary(
    summary: str | None,
    summary_status: str,
    summary_progress_percent: int = 0,
    summary_progress_message: str | None = None,
) -> None:
    if summary_status == "running":
        summary_text = (summary_progress_message or "Generating summary...").strip()
        summary_box_class = "summary-box"
    elif summary_status == "not_started":
        summary_text = (summary or "Waiting for transcription to be ready to summarize.").strip()
        summary_box_class = "summary-box summary-box-waiting"
    else:
        summary_text = (summary or "Summary unavailable").strip()
        summary_box_class = "summary-box"
    st.markdown(
        f"""
        <div class="{summary_box_class}">
            <div class="summary-title">Summary</div>
            <div class="summary-text">{html.escape(summary_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if summary_status == "running":
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
    st.session_state.transcription_cancel_requested = False
    st.session_state.job_started_at = time.time()
    st.session_state.summary_started_at = None


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
    st.session_state.transcription_cancel_requested = False
    st.session_state.job_started_at = time.time()
    st.session_state.summary_started_at = None


def build_updates_html(progress_items: list[dict]) -> str:
    recent_items = progress_items[-8:] if progress_items else []

    if not recent_items:
        return """
<div class="updates-box">
    <div class="updates-title">Live updates</div>
    <div class="update-item">
        <div class="update-bullet"></div>
        <div class="update-text">Waiting for the first backend update.</div>
    </div>
</div>
"""

    rows = []
    for item in reversed(recent_items):
        msg = html.escape(str(item.get("message", "Processing...")))
        rows.append(
            f"""
<div class="update-item">
    <div class="update-bullet"></div>
    <div class="update-text">{msg}</div>
</div>
"""
        )

    return f"""
<div class="updates-box">
    <div class="updates-title">Live updates</div>
    {''.join(rows)}
</div>
"""


def format_eta(seconds_remaining: float | None) -> str:
    if seconds_remaining is None:
        return "Calculating..."
    if seconds_remaining <= 0:
        return "Almost done"

    total_seconds = int(round(seconds_remaining))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m remaining"
    if minutes:
        return f"{minutes}m {seconds}s remaining"
    return f"{seconds}s remaining"


def eta_heading(percent: int, started_at: float | None) -> str:
    if started_at is None or percent < 15:
        return "Estimating Time Remaining"
    elapsed = time.time() - started_at
    if elapsed < 15:
        return "Estimating Time Remaining"
    return "Estimated Time Remaining"


def estimate_remaining_seconds(percent: int, started_at: float | None) -> float | None:
    if started_at is None or percent <= 0 or percent >= 100:
        return None

    elapsed = time.time() - started_at
    if elapsed <= 0:
        return None

    total_estimated = elapsed / (percent / 100.0)
    return max(0.0, total_estimated - elapsed)


def transcription_status_banner(job_result: dict | None, cancel_requested: bool) -> tuple[str, str] | None:
    status = (job_result or {}).get("status")
    if cancel_requested and status in {"queued", "running"}:
        return ("warning", "Stopping transcription after the current chunk finishes.")
    if status in {"queued", "running"}:
        return ("info", "Working... transcription is running now.")
    if status == "completed":
        return ("success", "Transcription ended successfully.")
    if status == "cancelled":
        return ("warning", "Transcription ended.")
    if status == "failed":
        return ("error", (job_result or {}).get("error") or "Transcription ended with an error.")
    return None


def render_transcription_restart_button(key_suffix: str) -> None:
    if st.button("Transcribe a new file", use_container_width=True, key=f"restart_transcription_{key_suffix}"):
        reset_transcription_state()
        st.rerun()


def request_transcription_cancel(job_id: str, key_suffix: str) -> None:
    if st.session_state.get("transcription_cancel_requested"):
        st.warning("Stopping transcription after the current chunk finishes.")
        return

    if st.button("Stop transcription", use_container_width=True, key=f"stop_transcription_{key_suffix}"):
        try:
            st.session_state.transcription_cancel_requested = True
            cancel_transcription(job_id)
        except requests.RequestException as exc:
            st.error(f"Could not stop transcription: {exc}")
        else:
            st.rerun()


def explain_transcription_step(step_name: str) -> str:
    explanations = {
        "queued": "The job is waiting to start locally.",
        "model_check": "Checking whether the selected Whisper model is already available on this device.",
        "model_download": "Downloading the selected Whisper model locally for first-time use.",
        "model_loaded": "The selected Whisper model is loaded and ready.",
        "audio_normalization": "Converting the audio into a clean local WAV format for Whisper.",
        "audio_normalized": "Audio preparation is complete.",
        "language_selected": "Choosing whether to keep automatic language detection or use a stable language hint.",
        "chunking": "Splitting the audio into processing chunks for transcription.",
        "chunking_done": "Chunk preparation is finished.",
        "parallel_transcription": "Multiple CPU workers are transcribing chunks in parallel.",
        "serial_cpu_transcription": "Stable serial CPU transcription is active to avoid worker crashes.",
        "gpu_acceleration": "A CUDA-capable GPU is active for local transcription.",
        "transcribing": "Whisper is transcribing the current chunk locally.",
        "retrying_chunk": "Retrying one chunk after a local processing issue.",
        "chunk_completed": "One chunk finished and the app is moving to the next one.",
        "merging": "Combining transcript pieces into a single transcript.",
        "outputs": "Generating transcript download files.",
        "completed": "Transcription finished successfully.",
        "cancelling": "Stopping safely after the current step completes.",
        "cancelled": "Transcription was stopped.",
        "failed": "The transcription job hit an error.",
        "summarization_requested": "The transcript is being prepared for local summarization.",
        "summarization": "Generating the local summary.",
        "summary_cancelling": "Stopping the summary safely after the current request finishes.",
        "summarization_done": "The summary finished and outputs were refreshed.",
        "summarization_cancelled": "The summary was stopped.",
        "summarization_failed": "The summary hit an error.",
    }
    return explanations.get(step_name, "The app is processing your file locally.")


def explain_summary_step(summary_status: str, summary_progress_percent: int) -> str:
    if summary_status == "running":
        if summary_progress_percent < 10:
            return "Preparing the transcript and local summary workflow."
        if summary_progress_percent < 80:
            return "The local model is drafting the summary."
        if summary_progress_percent < 96:
            return "Combining partial summary results."
        return "Final cleanup and save."
    if summary_status == "completed":
        return "Summary finished successfully."
    if summary_status == "cancelled":
        return "Summary was stopped."
    if summary_status == "failed":
        return "Summary could not be completed."
    return "Summary has not started yet."


def render_progress_panel(result: dict) -> None:
    progress_items = result.get("progress", [])
    last_progress = progress_items[-1] if progress_items else {"message": "Waiting...", "percent": 0}
    percent = max(0, min(int(float(last_progress.get("percent", 0))), 100))
    progress_step = str(last_progress.get("step", "queued"))

    status_value = html.escape(str(result.get("status", "queued")).replace("_", " ").title())
    current_message = html.escape(str(last_progress.get("message", "Waiting for progress...")))
    started_at = st.session_state.get("job_started_at")
    if progress_step in {"parallel_transcription", "serial_cpu_transcription"} and percent <= 50:
        eta_label = "Waiting for first chunk to finish"
        eta_title = "Estimating Time Remaining"
    else:
        eta_label = format_eta(estimate_remaining_seconds(percent, started_at))
        eta_title = eta_heading(percent, started_at)
    step_explanation = html.escape(explain_transcription_step(progress_step))

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
            <div class="status-tile">
                <div class="status-kicker">{html.escape(eta_title)}</div>
                <div class="status-value">{html.escape(eta_label)}</div>
            </div>
            <div class="status-tile">
                <div class="status-kicker">Current Step</div>
                <div class="status-value">{html.escape(progress_step.replace("_", " ").title())}</div>
            </div>
        </div>

        <div class="progress-meta">
            <div class="progress-message">{current_message}</div>
            <div class="progress-percent">{percent}%</div>
        </div>
        <div class="progress-shell">
            <div class="progress-fill" style="width: {percent}%;"></div>
        </div>
        <div class="hint" style="margin-top:0.75rem;">{step_explanation}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(build_updates_html(progress_items), unsafe_allow_html=True)


def poll_until_finished(job_id: str, poll_seconds: int = 2) -> dict | None:
    progress_placeholder = st.empty()
    controls_placeholder = st.empty()
    summary_placeholder = st.empty()

    final_result = None
    loop_iteration = 0
    while True:
        loop_iteration += 1
        try:
            result = fetch_job(job_id)
        except requests.RequestException as exc:
            progress_placeholder.error(f"Failed to retrieve job status: {exc}")
            return None

        st.session_state.job_result = result

        with progress_placeholder.container():
            render_progress_panel(result)

        with controls_placeholder.container():
            if result.get("status") in {"queued", "running"}:
                st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
                if st.session_state.get("transcription_cancel_requested"):
                    st.warning("Stopping transcription after the current chunk finishes.")
                else:
                    st.caption("Use the stop button above to cancel this transcription safely.")
            else:
                controls_placeholder.empty()

        with summary_placeholder.container():
            st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="result-column-title">Summary</div>', unsafe_allow_html=True)
            if result.get("status") in {"queued", "running"} and result.get("summary_status", "not_started") == "not_started":
                render_summary(
                    "Waiting for transcription to be ready to summarize.",
                    "not_started",
                    0,
                    None,
                )
            else:
                render_summary(
                    result.get("summary"),
                    result.get("summary_status", "not_started"),
                    int(result.get("summary_progress_percent", 0) or 0),
                    result.get("summary_progress_message"),
                )

        if result["status"] in {"completed", "failed", "cancelled"}:
            final_result = result
            break

        time.sleep(poll_seconds)

    return final_result


def poll_until_summary_ready(job_id: str, poll_seconds: int = 2) -> dict | None:
    status_placeholder = st.empty()

    loop_iteration = 0
    while True:
        loop_iteration += 1
        try:
            result = fetch_job(job_id)
        except requests.RequestException as exc:
            status_placeholder.error(f"Failed to retrieve summary status: {exc}")
            return None

        st.session_state.job_result = result
        summary_status = result.get("summary_status", "not_started")
        summary_progress_percent = int(result.get("summary_progress_percent", 0) or 0)
        summary_progress_message = result.get("summary_progress_message")
        summary_started_at = st.session_state.get("summary_started_at")
        summary_eta = format_eta(
            estimate_remaining_seconds(summary_progress_percent, summary_started_at)
        )
        summary_eta_title = eta_heading(summary_progress_percent, summary_started_at)
        summary_step_explanation = explain_summary_step(summary_status, summary_progress_percent)

        with status_placeholder.container():
            if summary_status == "running":
                st.info(summary_progress_message or "Working... summary is running now and will appear here when it is ready.")
                st.progress(max(0, min(summary_progress_percent, 100)) / 100.0, text=f"Summary progress: {max(0, min(summary_progress_percent, 100))}%")
                info_col, eta_col = st.columns(2)
                with info_col:
                    st.caption(f"Step: {summary_step_explanation}")
                with eta_col:
                    st.caption(f"{summary_eta_title}: {summary_eta}")
                if st.button(
                    "Stop summary",
                    use_container_width=True,
                    key=f"stop_summary_progress_{job_id}_{loop_iteration}",
                ):
                    try:
                        cancel_summary(job_id)
                    except requests.RequestException as exc:
                        st.error(f"Could not stop summary: {exc}")
                    else:
                        st.session_state.summary_requested = False
                        st.rerun()
            elif summary_status == "cancelled":
                st.warning(result.get("summary_error") or "Summary stopped.")
            elif summary_status == "failed":
                st.warning(result.get("summary_error") or "Summary unavailable.")

        if summary_status != "running":
            status_placeholder.empty()
            return result

        time.sleep(poll_seconds)


inject_css()
init_state()
if (st.session_state.get("job_result") or {}).get("status") in {"completed", "failed", "cancelled"}:
    st.session_state.is_transcribing = False
    st.session_state.transcription_cancel_requested = False
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
model_options = ["Select a Whisper model"] + list(model_lookup.keys())

# Step 1
st.markdown('<div class="section-card">', unsafe_allow_html=True)
render_section_intro(
    "1",
    "Choose a model",
    "Select the Whisper model you want to use for this transcription.",
)
model_name = st.selectbox(
    "Model",
    model_options,
    index=0,
    label_visibility="collapsed",
)
selected_model = model_lookup.get(model_name)
display_model_name = model_name
model_badge = (
    "Ready locally"
    if selected_model and selected_model.get("available_locally")
    else "Choose a model to continue"
)
st.markdown(
    f"""
    <div class="hint">
        Selected model: <strong>{html.escape(model_name)}</strong> - {html.escape(model_badge)}
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
transcription_banner = transcription_status_banner(
    st.session_state.get("job_result"),
    bool(st.session_state.get("transcription_cancel_requested")),
)
job_status = (st.session_state.get("job_result") or {}).get("status")
active_transcribing = bool(st.session_state.get("is_transcribing")) or job_status in {"queued", "running"}
if active_transcribing and not transcription_banner:
    transcription_banner = ("info", "Working... transcription is running now.")

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

    transcribe_label = "Transcribing..." if active_transcribing else "Transcribe audio"
    if st.button(
        transcribe_label,
        type="primary",
        use_container_width=True,
        disabled=active_transcribing or model_name == "Select a Whisper model",
    ):
        begin_transcription_from_upload(uploaded, model_name)
        if st.session_state.get("job_id"):
            st.rerun()
    if active_transcribing:
        st.markdown(
            """
            <div class="hint" style="margin-top:0.55rem; margin-bottom:0.2rem;">
                Transcribing locally now. The transcript and live progress will appear below as soon as the backend posts the first update.
            </div>
            """,
            unsafe_allow_html=True,
        )
    if transcription_banner:
        level, message = transcription_banner
        if level == "info":
            st.info(message)
        elif level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.error(message)
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

    record_button_label = "Transcribing..." if active_transcribing else "Transcribe recording"
    if st.button(
        record_button_label,
        type="primary",
        use_container_width=True,
        disabled=(not has_recording) or active_transcribing or model_name == "Select a Whisper model",
    ):
        begin_transcription_from_recording(model_name)
        if st.session_state.get("job_id"):
            st.rerun()
    if active_transcribing:
        st.markdown(
            """
            <div class="hint" style="margin-top:0.55rem; margin-bottom:0.2rem;">
                Transcribing locally now. The transcript and live progress will appear below as soon as the backend posts the first update.
            </div>
            """,
            unsafe_allow_html=True,
        )
    if transcription_banner:
        level, message = transcription_banner
        if level == "info":
            st.info(message)
        elif level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.error(message)

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
summary_text: str | None = None
summary_status = "not_started"
summary_progress_percent = 0
summary_progress_message: str | None = None
summary_error: str | None = None

if job_id and ((result or {}).get("status") in {"queued", "running"} or st.session_state.get("is_transcribing")):
    request_transcription_cancel(job_id, "primary")
    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)

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
else:
    latest_result = poll_until_finished(job_id)

    summary_text = (latest_result or {}).get("summary")
    summary_status = (latest_result or {}).get("summary_status", "not_started")
    summary_progress_percent = int((latest_result or {}).get("summary_progress_percent", 0) or 0)
    summary_progress_message = (latest_result or {}).get("summary_progress_message")
    summary_error = (latest_result or {}).get("summary_error")

    if latest_result is not None and latest_result.get("status") == "completed":
        st.session_state.is_transcribing = False
        transcript = render_segments(latest_result.get("segments", []))

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
        summary_download = (summary_text or "Summary unavailable").strip().encode("utf-8")

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

        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        summarize_disabled = summary_status in {"running", "completed"}
        summarize_label = "Summarizing..." if summary_status == "running" else "Summarize"
        if st.button(summarize_label, use_container_width=True, disabled=summarize_disabled, key="summarize_completed"):
            try:
                start_summary(job_id)
            except requests.RequestException as exc:
                st.error(f"Could not start summarization: {exc}")
            else:
                st.session_state.summary_requested = True
                st.session_state.summary_started_at = time.time()
                st.rerun()

        if st.session_state.summary_requested and summary_status == "running":
            refreshed_result = poll_until_summary_ready(job_id)
            if refreshed_result is not None:
                latest_result = refreshed_result
                summary_text = latest_result.get("summary")
                summary_status = latest_result.get("summary_status", "not_started")
                summary_progress_percent = int(latest_result.get("summary_progress_percent", 0) or 0)
                summary_progress_message = latest_result.get("summary_progress_message")
                summary_error = latest_result.get("summary_error")
                if summary_status != "running":
                    st.session_state.summary_requested = False

        if summary_status == "completed":
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
        render_transcription_restart_button("cancelled")

    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
    render_transcription_restart_button("footer")

st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
st.markdown('<div class="result-column-title">Summary</div>', unsafe_allow_html=True)
render_summary(summary_text, summary_status, summary_progress_percent, summary_progress_message)
if summary_status == "cancelled":
    st.warning(summary_error or "Summary stopped.")
elif summary_status == "failed":
    st.warning(summary_error or "Summary unavailable.")

st.markdown("</div>", unsafe_allow_html=True)
