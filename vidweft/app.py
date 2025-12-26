import streamlit as st
import tempfile
import asyncio
import numpy as np

from moviepy import (
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
    AudioClip,
)
from moviepy.audio.AudioClip import CompositeAudioClip

import edge_tts

# ---------------- Page Setup ----------------
st.set_page_config(page_title="VidWeft", layout="wide")
st.title("🎬 VidWeft – Image to Video Generator")

# ---------------- Session State ----------------
if "images" not in st.session_state:
    st.session_state.images = []

# ---------------- UI ----------------
uploaded_images = st.file_uploader(
    "Upload Images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_images:
    st.session_state.images = uploaded_images

st.markdown("### 🎙️ Voiceover")

voice_text = st.text_area(
    "Enter voiceover text",
    height=160,
    placeholder="Paste your narration script here..."
)

voice_choice = st.radio(
    "Choose voice",
    ["Female", "Male"],
    horizontal=True
)

st.markdown("### 🎵 Background Music")
music_file = st.file_uploader(
    "Upload background music",
    type=["mp3", "wav"]
)

# ---------------- Constants ----------------
VOICE_MAP = {
    "Female": "en-US-JennyNeural",
    "Male": "en-US-GuyNeural",
}

IMAGE_DURATION = 3
MAX_AUDIO_SPEEDUP = 1.25
SAFETY_EPS = 0.05  # seconds

# ---------------- Helpers ----------------
async def generate_voice(text, voice):
    audio_path = tempfile.mktemp(suffix=".mp3")
    communicator = edge_tts.Communicate(text, voice)

    with open(audio_path, "wb") as f:
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])

    return audio_path


def silence_clip(duration, fps=44100):
    return AudioClip(
        lambda t: np.zeros((2,)),
        duration=duration,
        fps=fps,
    )


def align_audio_to_video(audio_clip, video_duration):
    audio_duration = audio_clip.duration
    target = max(video_duration - SAFETY_EPS, 0)

    # Audio shorter → pad silence
    if audio_duration < target:
        silence = silence_clip(target - audio_duration)
        return CompositeAudioClip([audio_clip, silence])

    # Audio longer → gentle speed-up
    speed_factor = min(audio_duration / target, MAX_AUDIO_SPEEDUP)
    sped = audio_clip.with_speed_scaled(speed_factor)

    return sped.with_start(0).with_duration(target)


# ---------------- Video Generation ----------------
if st.button("🎥 Generate Video"):

    if not st.session_state.images:
        st.error("Please upload at least one image.")
        st.stop()

    # ---- Build video ----
    image_clips = []
    for img in st.session_state.images:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(img.read())
            img_path = f.name

        image_clips.append(
            ImageClip(img_path).with_duration(IMAGE_DURATION)
        )

    video = concatenate_videoclips(image_clips, method="compose")
    VIDEO_DURATION = video.duration

    # ---- Voiceover ----
    if voice_text.strip():
        audio_path = asyncio.run(
            generate_voice(
                voice_text,
                VOICE_MAP[voice_choice]
            )
        )

        raw_audio = AudioFileClip(audio_path)
        aligned_audio = align_audio_to_video(raw_audio, VIDEO_DURATION)
        video = video.with_audio(aligned_audio)

    # ---- Background Music ----
    if music_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(music_file.read())
            music_path = f.name

        music = AudioFileClip(music_path).with_volume_scaled(0.2)
        music = music.with_start(0).with_duration(VIDEO_DURATION)

        if video.audio:
            video = video.with_audio(
                CompositeAudioClip([video.audio, music])
            )
        else:
            video = video.with_audio(music)

    # ---- Final Render ----
    output_path = "vidweft_output.mp4"

    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    st.success("✅ Video created successfully!")

    with open(output_path, "rb") as f:
        st.download_button(
            "⬇️ Download Video",
            f,
            file_name="vidweft.mp4"
        )
