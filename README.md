# On-Prem Speech-to-Text

Production-style local speech-to-text application built with FastAPI and Streamlit for Windows. The system runs entirely on the user's machine, uses official `openai-whisper` locally, supports upload and microphone recording, detects GPU automatically when available, falls back to CPU automatically, and saves all models, recordings, logs, and outputs locally inside the project.

## Features

- Fully local transcription with official Whisper.
- Built for Windows.
- CPU-first reliability with automatic CUDA acceleration when available.
- Upload flow for MP3, WAV, M4A, OGG, FLAC, MP4, AAC, WebM, MPEG, and MPGA audio.
- Browser microphone recording flow that stores audio locally before transcription.
- Automatic local model download and reuse for `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, and `large-v3`.
- Local audio normalization to mono 16 kHz WAV with `ffmpeg`.
- Automatic chunking for long audio.
- Retries failed chunks up to three times.
- Arabic-script-only final transcript output with phonetic transliteration of English words into Arabic letters.
- Timestamped transcript output with graceful fallback to sentence-level timestamps when diarization is unavailable.
- Download results as `.txt` and `.docx`.
- Local logs and JSON metadata for each job.

## Project Structure

```text
on-prem STT/
|-- app/
|   |-- api/
|   |-- core/
|   |-- models/
|   |-- schemas/
|   |-- services/
|   |-- utils/
|   `-- main.py
|-- frontend/
|   `-- streamlit_app.py
|-- logs/
|-- models/
|-- outputs/
|-- recordings/
|-- temp/
|-- requirements.txt
|-- README.md
|-- bootstrap_windows.bat
|-- start_all.bat
|-- run_backend.bat
`-- run_frontend.bat
```

## Quick Start For A New User

If you are opening this project for the first time, follow these steps in order.

### Step 1: Install Python 3.10

1. Download Python 3.10 from the official Python website.
2. Run the installer.
3. Make sure `Add Python to PATH` is checked before you click install.
4. Finish the installation.

### Step 2: Install `ffmpeg` and `ffprobe`

This app will not transcribe audio unless `ffmpeg` and `ffprobe` are installed.

They are not included in `requirements.txt`, because they are external Windows tools, not Python packages.

Follow these steps:s

fixer.py uses pydub to read and normalize the original audio files before converting them into 16kHz mono PCM WAV. Because of that FFmpeg must be available in the runtime environment, especially when the source files are not already WAV.
This means replication depends not only on GCP setup, but also on having:
the Python dependencies from requirements.txt
FFmpeg is installed and available in the system path
Download a Windows FFmpeg build such as ffmpeg-master-latest-win64-gpl-shared from the BtbN FFmpeg Builds release page, extract it, and add the FFmpeg bin folder to the system PATH.
Download: ffmpeg-master-latest-win64-gpl-shared from this repo: https://github.com/BtbN/FFmpeg-Builds/releases 


### Step 3: Check That `ffmpeg` Was Installed Correctly

In PowerShell, run:

```powershell
ffmpeg -version
ffprobe -version
```

If both commands show version information, then setup is correct.

If you get a message saying the command was not found, then `ffmpeg` was not added to `PATH` correctly yet.

### Step 4: Start The App

Open PowerShell in the project folder and run:

```powershell
.\start_all.bat
```

This one command will:

- create the Python virtual environment if needed
- install the Python packages
- start the backend
- start the frontend

After startup:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:8501`

### Step 5: Open The App

Open this in your browser:

```text
http://127.0.0.1:8501
```

## One-Command Setup And Launch

For normal use on Windows, run:

```powershell
.\start_all.bat
```

This is the main command most users should use.

## Install Python Dependencies

If you ever need to install Python dependencies manually instead of using `start_all.bat`, run:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip "setuptools<81.0.0" wheel
python -m pip install --no-build-isolation -r requirements.txt
```

### Build Tooling

- `setuptools` and `wheel` are required build tools for packages that are installed from source during dependency installation.
- The setup step upgrades these tools before installing the project requirements.
- `setuptools` is intentionally kept below version `81` because `openai-whisper` still expects `pkg_resources` during installation.
- The install command uses `--no-build-isolation` so `openai-whisper` installs against the local virtual environment build toolchain.

## Install `ffmpeg` Later If Needed

If the app says `ffmpeg` or `ffprobe` was not found, go back to the setup section above and complete the `ffmpeg` installation steps.

## Running the Backend

```powershell
.\run_backend.bat
```

Manual command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Running the Frontend

```powershell
.\run_frontend.bat
```

Manual command:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/streamlit_app.py
```

## How Local Model Download and Reuse Works

- The model dropdown is populated from the backend.
- When a user starts a transcription job, the backend checks whether the selected model is already present in the local `models/` directory.
- If the model is missing, Whisper downloads it once to `models/`.
- Future jobs reuse the existing local model file and do not download it again.
- No cloud transcription service is used. Model download is the only network-dependent setup action, and it happens only for Whisper weights acquisition.

## How Outputs Are Saved

- Uploaded files are stored under `temp/uploads/`.
- Recorded microphone files are stored under `recordings/`.
- Temporary normalized and chunked audio is stored under `temp/<job_id>/`.
- Final transcript files are stored under `outputs/<job_id>/`.
- Logs are stored under `logs/app.log`.

## Upload Flow

1. Start the FastAPI backend.
2. Start the Streamlit frontend.
3. Open the Streamlit page in the browser.
4. Choose a Whisper model.
5. Select `Upload audio file`.
6. Upload an audio file and store it locally.
7. Click `Start Transcription`.
8. Watch the progress updates while the backend normalizes audio, chunks it, transcribes it, merges results, and generates output files.
9. Review the transcript and download the `.txt` and `.docx` outputs.

## Recording Flow

1. Choose a Whisper model.
2. Select `Record audio`.
3. Click `Start Recording`.
4. Click `Stop Recording` when finished.
5. Store the recording locally.
6. Start transcription.
7. Review the Arabic-script transcript and download the output files.

## Notes on Arabic Script Output

- The final transcript is rendered into Arabic script only.
- Arabic speech remains Arabic.
- English speech is phonetically transliterated into Arabic letters rather than translated into Arabic meaning.
- This is an approximate phonetic rendering. Exact pronunciation can vary by accent, recording quality, and Whisper output quality.

## Notes on Diarization

- This project is designed to stay reliable on fully local machines without requiring additional large diarization models.
- The current implementation falls back to timestamped sentence segments when diarization is unavailable.
- The API still reports diarization status so the frontend can display that the system is using timestamps-only mode.

## Troubleshooting

### `ffmpeg` not found

Install `ffmpeg` and `ffprobe`, then restart the terminal.

### Microphone recording does not work

- Confirm the browser has permission to access the microphone.
- Confirm the machine has a working microphone input device.
- Try Chrome or Edge if browser microphone support is limited.

### Model download fails

- Check internet connectivity for the initial Whisper model download.
- Retry the job after connectivity is restored.
- Confirm the local `models/` directory is writable.

### `ModuleNotFoundError: No module named 'pkg_resources'` during install

This error indicates that the package build environment could not locate a usable `setuptools` installation providing `pkg_resources`.

Recommended recovery steps:

```powershell
deactivate
Remove-Item -Recurse -Force .venv
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip "setuptools<81.0.0" wheel
python -m pip install --no-build-isolation -r requirements.txt
```

Alternative one-step installation:

```powershell
.\bootstrap_windows.bat
```

### GPU is not being used

- The application always works on CPU.
- CUDA is used only when `torch.cuda.is_available()` returns `True`.
- Ensure a CUDA-compatible local PyTorch build is installed if GPU acceleration is desired.

## API Endpoints

- `POST /api/upload-audio`
- `POST /api/record-audio`
- `GET /api/models`
- `POST /api/models/{model_name}/ensure`
- `POST /api/transcriptions/start`
- `GET /api/transcriptions/{job_id}`
- `GET /api/downloads/{job_id}/txt`
- `GET /api/downloads/{job_id}/docx`
- `GET /api/health`
