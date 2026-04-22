# On-Prem Speech-to-Text

Production-style local speech-to-text application built with FastAPI and Streamlit for Windows. The system runs entirely on the user's machine, uses official `openai-whisper` locally, supports upload and microphone recording, detects GPU automatically when available, falls back to CPU automatically, and saves all models, recordings, logs, and outputs locally inside the project.

## Features

- Fully local transcription with official Whisper.
- Built for Windows.
- Automatic hardware detection with GPU acceleration when available and CPU fallback when not.
- Upload flow for MP3, WAV, M4A, OGG, FLAC, MP4, AAC, WebM, MPEG, and MPGA audio.
- Browser microphone recording flow that stores audio locally before transcription.
- Automatic local model download and reuse for `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, and `large-v3`.
- Local audio normalization to mono 16 kHz WAV with `ffmpeg`.
- Automatic chunking for long audio.
- Retries failed chunks up to three times.
- Manual local transcript summarization using a modular on-prem summarization service with Ollama and Qwen.
- Arabic-script-only final transcript output with phonetic transliteration of English words into Arabic letters.
- Timestamped transcript output with graceful fallback to sentence-level timestamps when diarization is unavailable.
- Download results as `.txt` and `.docx`.
- Local logs and JSON metadata for each job.

## Summary Feature

After transcription finishes, the user can press `Summarize` to generate a local summary of the transcript.

The summarizer is designed for noisy speech-to-text transcripts and treats Arabic and English as first-class languages. It:

- detects Arabic-dominant, English-dominant, and mixed transcripts
- builds dedicated Arabic and English prompts
- summarizes long transcripts in chunks and then runs a combine pass
- preserves important facts, examples, numbers, decisions, and next steps
- avoids strict lexical-overlap rejection, so Arabic summaries are not penalized unfairly
- can optionally fall back to another local Ollama model in code if you ever decide to extend it

This summary is generated on the same machine through a local backend, so the transcript is not sent to an external API.

The summary appears above the transcript in the app. Transcript downloads remain transcript-only.

## Summarization Architecture

The summarization service is modular and lives under `app/services/summarization/`.

Main pieces:

- `backends.py`: Ollama backend adapter
- `language.py`: Arabic/English/mixed detection
- `cleaning.py`: transcript cleanup for timestamps and noisy markers
- `chunking.py`: transcript chunking for long inputs
- `prompts.py`: Arabic and English prompt builders plus a combine-pass prompt
- `postprocess.py`: cleanup of raw model output
- `validation.py`: readability and malformed-output checks
- `service.py`: orchestration, chunk summarization, and combine pass

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
`-- start_all.bat
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

fixer.py uses pydub to read and normalize the original audio files before converting them into 16kHz mono PCM WAV. Because of that FFmpeg must be available in the runtime environment, especially when the source files are not already WAV.

Follow these steps:
## Install FFmpeg on Windows

1. Open the FFmpeg Windows builds page:  
   `https://github.com/BtbN/FFmpeg-Builds/releases`

2. Download this file:  
   `ffmpeg-master-latest-win64-gpl-shared.zip`

3. Extract the downloaded `.zip` file to a folder on your computer, for example:  
   `C:\ffmpeg`

4. Open the extracted folder.

5. Find and open the `bin` folder inside it.  
   This is the folder that contains:
   - `ffmpeg.exe`
   - `ffprobe.exe`

6. Copy the full path of that `bin` folder.  
   Example:
   `C:\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin`

7. Press the **Windows key** on your keyboard.

8. Search for:  
   `Environment Variables`

9. Click:  
   `Edit the system environment variables`

10. In the window that opens, click:  
    `Environment Variables`

11. Under **User variables**, click:  
    `Path`

12. Click:  
    `Edit`

13. Check whether this exact folder path is already listed:  
    `C:\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin`

14. If it is not there:
    - Click `New`
    - Paste the `bin` folder path
    - Click `OK`

15. Click `OK` on all windows to save.

16. VERY IMPORTANT: Close **VS Code**, **PowerShell**, and any open terminal windows.

17. Open a new PowerShell window and run:

```powershell
ffmpeg -version
ffprobe -version
```

If both commands show version information, then setup is correct.

If you get a message saying either command was not found, then the FFmpeg `bin` folder was not added to `PATH` correctly yet.

### Step 3: Install Ollama For Local Summaries

The summary feature runs locally through Ollama.

1. Install Ollama for Windows from the official site:
   `https://ollama.com/download/windows`
2. Open a new PowerShell window and verify the install:

```powershell
ollama --version
```

3. Download and start a local summarization model once:

```powershell
ollama run qwen2.5:3b
```

4. Wait for the model to finish downloading locally.
5. After you see the Ollama prompt, you can close that terminal window if you want.

Notes:

- The first run can take a while because the model is downloaded locally.
- Ollama serves its local API on `http://localhost:11434` by default.
- The summarizer in this app uses that local Ollama service. No transcript data is sent to a cloud summarization API.
- The default local summarization model is `qwen2.5:3b`.
- The app is already configured to use `qwen2.5:3b` by default.

### Step 3.5: Optional GPU Note

You do not need to change the code to use a GPU.

This app automatically checks for a CUDA-capable NVIDIA GPU when transcription starts.

If a compatible CUDA setup is available, the app will use the GPU automatically.

If not, the app will continue on CPU automatically.

For GPU use, make sure:

- the machine has an NVIDIA GPU
- NVIDIA drivers are installed correctly
- the installed PyTorch build supports CUDA

If you are not sure whether the machine is ready for GPU use, that is okay. The app will still run on CPU.

## Install Python Dependencies

If you ever need to install Python dependencies manually instead of using `start_all.bat`, run:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip "setuptools<81.0.0" wheel
python -m pip install --no-build-isolation -r requirements.txt
```

## Summarizer Model

The default summarizer is:

1. `qwen2.5:3b`

Why this model:

- compact enough for local on-prem use
- better aligned with Arabic and English than a generic chat-only setup
- simpler to support and debug while we stabilize the summarizer

The intended default path is one clear runtime:

- Ollama
- `qwen2.5:3b`

## Prompt Design

Arabic prompt behavior:

- infer intended meaning despite STT errors and repetition
- produce natural, useful Modern Standard Arabic unless a colloquial phrase must be preserved
- use structured headers and bullets
- preserve important details, names, numbers, comparisons, and decisions
- avoid overly short summaries
- do not invent facts

English prompt behavior:

- infer intended meaning despite STT errors and repetition
- use structured headers and bullets
- preserve important details, names, numbers, comparisons, and decisions
- capture frameworks, methods, trade-offs, and next steps when present
- avoid generic summaries
- do not invent facts


### Step 4: Start The App

1. Open PowerShell. ( CTRL SHIFT `)
2. Go to the project folder.
3. Run this command:

```powershell
.\start_all.bat
```

This command will automatically:

- create the Python virtual environment if needed
- install the Python packages
- start the backend
- start the frontend

Wait until the windows finish loading.

After startup:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:8501`

### Step 5: Open The App

1. Open your web browser.
2. Paste this address into the address bar:

```text
http://127.0.0.1:8501
```



## How Local Model Download and Reuse Works

- The model dropdown is populated from the backend.
- When a user starts a transcription job, the backend checks whether the selected model is already present in the local `models/` directory.
- If the model is missing, Whisper downloads it once to `models/`.
- Future jobs reuse the existing local model file and do not download it again.
- On each run, the backend automatically checks for a CUDA-capable GPU. If one is available, Whisper uses the GPU automatically. If not, the app falls back to CPU automatically.
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
8. Watch the progress updates while the backend normalizes audio, chunks it, transcribes it, and writes the transcript files.
9. Press `Summarize` when you want a local summary.
10. Review the summary and transcript, then download the `.txt` and `.docx` outputs.

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

- The application checks automatically for a CUDA-capable GPU each time it starts a transcription job.
- If `torch.cuda.is_available()` returns `True`, the app will use the GPU automatically.
- If no compatible GPU is available, the app will continue on CPU automatically.
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
