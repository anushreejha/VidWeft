# 🎬 VidWeft

VidWeft is a lightweight **image-to-video creation tool** built with **Streamlit** and **MoviePy (v2)**.  
It lets you combine images, voiceovers, and optional background music into a downloadable MP4 video.

---

## ✨ Features

- 🖼️ Upload multiple images and convert them into a video
- 🎙️ Add a voiceover audio track
- 🎵 Optional background music with volume control
- ⬇️ Download the generated video directly from the UI
- ⚡ Built on MoviePy v2 (modern, Python 3.13 compatible)

---

## 🧱 Tech Stack

- **Python** 3.12+
- **Streamlit** – UI
- **MoviePy v2** – Video & audio processing
- **Pillow** – Image handling
- **Edge TTS / Faster-Whisper** – (optional, future extensions)

---

## 📁 Project Structure

```
VidWeft/
├── vidweft/
│   └── app.py
├── requirements.txt
├── README.md
└── venv/
```

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```
git clone <your-repo-url>
cd VidWeft
```

### 2️⃣ Create & activate virtual environment

```
python -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

### 3️⃣ Install dependencies

```
pip install -r requirements.txt
```

## ▶️ Run the App

```
streamlit run vidweft/app.py
```

Then open the URL shown in the terminal (usually http://localhost:8501).

## 🛠️ How It Works

1. Upload images (PNG / JPG)
2. Upload a voiceover audio file (MP3 / WAV)
3. (Optional) Upload background music
4. Click Generate Video
5. Download the generated MP4

**Note:** Each image is currently displayed for 3 seconds (can be customized in code).
