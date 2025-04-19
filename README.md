# 🎧 Audium — Audio in. Insight out.

**Audium** is a sleek, self-hosted transcription dashboard powered by [WhisperX](https://github.com/m-bain/whisperx) with diarization, subtitles, job tracking, and full user management. Built by a documentary filmmaker, for anyone who works with voice — from storytellers to researchers, journalists, and creators.

## ✨ Features

- 🎤 Upload audio files and get accurate transcriptions powered by WhisperX
- 🗣️ Real speaker diarization (using pyannote-audio)
- 📜 Export transcripts as `.txt`, `.srt`, and `.vtt`
- 📂 Upload history and storage stats
- ⚙️ Admin panel with rename/delete controls
- 🔐 User login and account settings
- 📊 Analytics and log dashboard (coming soon)
- 🕶️ Modern dark UI with responsive sidebar layout
- 📬 Optional daily summary email (via `.env` config)

---

## 📦 Tech Stack

- **Flask** (Python)
- **WhisperX** + **pyannote-audio**
- **HTML5 + CSS (custom dark mode)**
- **Docker + Docker Compose**
- **Postprocessing with utils & schedulers**
- **Email: SMTP via Gmail (dotenv-configurable)**

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Git
- Python 3.10+ (for standalone testing)

### Clone and Run

```bash
git clone https://github.com/yourusername/audium.git
cd audium
cp .env.example .env  # fill in your SMTP/email details
docker compose up --build
