# 🎧 Audium — Audio in. Insight out.

**Audium** is a sleek, self-hosted transcription dashboard powered by [WhisperX](https://github.com/m-bain/whisperx) with diarization, subtitles, job tracking, and full user management. Built by a documentary filmmaker, for anyone who works with voice — from storytellers to researchers, journalists, and creators.

## ✨ Features

- 🎤 Upload audio files and get accurate transcriptions powered by WhisperX
- 🗣️ Real speaker diarization (using pyannote-audio)
- 📜 Export transcripts as `.txt`, `.srt`, and `.vtt`
- 📂 Upload history and storage stats
- ⚙️ Admin panel with rename/delete controls
- 🔐 User login, account settings, and role-based access control (e.g., admin and standard user roles)
- 📊 Analytics and log dashboard (planned for version 1.2, estimated Q2 2024)
- 🕶️ Modern dark UI with responsive sidebar layout
- 📬 Optional daily summary email with transcription stats and usage reports (via `.env` config)

---

## 📦 Tech Stack

- **Flask** (Python 3.10+)
- **WhisperX** (v1.0.0) + **pyannote-audio** (v2.1.1)
- **HTML5 + CSS (custom dark mode)**
- **Docker** (v24.0.0) + **Docker Compose** (v2.17.0)
- **Postprocessing with utils & schedulers**
- **Email: SMTP via Gmail (dotenv-configurable)**

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose (ensure they are installed and properly configured on your system)
- Git
- Python 3.10+ (required if you plan to run the application directly on your local machine for testing purposes, without using Docker)

### Clone and Run

```bash
git clone https://github.com/TheMonolithOfPlex/Audium.git
cd audium
cp .env.example .env  # fill in your SMTP/email details (see `.env.example` for format or refer to the documentation)
docker compose up --build

# Note: Ensure Docker Compose is installed and accessible via the `docker compose` command. You can verify by running `docker compose version`.
