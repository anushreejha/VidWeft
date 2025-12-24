from faster_whisper import WhisperModel
import streamlit as st
import hashlib
from moviepy import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
)
from moviepy.audio.AudioClip import CompositeAudioClip
from PIL import Image
import edge_tts
import asyncio
import os
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="VidWeft", layout="wide")

# ---------------- Session State ----------------
if "images" not in st.session_state:
    st.session_state.images = []
if "audio_files" not in st.session_state:
    st.session_state.audio_files = []
if "music_file" not in st.session_state:
    st.session_state.music_file = None

# ---------------- UI ----------------
st.title("🎬 VidWeft – Image → Video Generator")

uploaded_images = st.file_uploader(
    "Upload Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True
)

if uploaded_images:
    st.session_state.images = uploaded_images

uploaded_audio = st.file_uploader(
    "Upload Voiceover Audio", type=["mp3", "wav"]
)
if uploaded_audio:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(uploaded_audio.read())
        st.session_state.audio_files = [f.name]

music_file = st.file_uploader(
    "Optional Background Music", type=["mp3", "wav"]
)
if music_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(music_file.read())
        st.session_state.music_file = f.name

add_music = st.checkbox("Add Background Music", value=True)
add_subtitles = st.checkbox("Add Subtitles", value=False)

# ---------------- Video Creation ----------------
if st.button("🎥 Generate Video"):
    clips = []

    for img in st.session_state.images:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(img.read())
            img_path = f.name

        clip = ImageClip(img_path).with_duration(3)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # ---- Voiceover ----
    if st.session_state.audio_files:
        audio = AudioFileClip(st.session_state.audio_files[0])
        video = video.with_audio(audio)

    # ---- Background Music ----
    if add_music and st.session_state.music_file:
        music = AudioFileClip(st.session_state.music_file).with_volume_scaled(0.3)
        if video.audio:
            mixed = CompositeAudioClip([
                video.audio,
                music.with_duration(video.duration),
            ])
            video = video.with_audio(mixed)
        else:
            video = video.with_audio(music.with_duration(video.duration))

    # ---- Export ----
    output_path = "vidweft_output.mp4"
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
    )

    st.success("✅ Video created!")
    with open(output_path, "rb") as f:
        st.download_button("⬇️ Download Video", f, file_name="vidweft.mp4")

# ---------------- Sidebar ----------------
st.sidebar.markdown("### 🚀 VidWeft")
st.sidebar.metric("Images", len(st.session_state.images))
st.sidebar.metric("Audio", len(st.session_state.audio_files))
st.sidebar.metric("Music", "Yes" if st.session_state.music_file else "No")

if st.sidebar.button("🗑️ Clear All"):
    st.session_state.images = []
    st.session_state.audio_files = []
    st.session_state.music_file = None
    st.rerun()

st.caption("Built with ❤️ | MIT License")
