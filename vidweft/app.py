import streamlit as st
import tempfile
import asyncio
import os
import numpy as np

from moviepy import (
    ImageClip,
    TextClip,
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

add_subtitles = st.checkbox("Add subtitles", value=False)

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

FONT = "DejaVu-Sans-Bold"
IMAGE_DURATION = 3
MAX_AUDIO_SPEEDUP = 1.25
SAFETY_EPS = 0.05  # seconds

# ---------------- Helpers ----------------
async def generate_voice_and_subtitles(text, voice):
    audio_path = tempfile.mktemp(suffix=".mp3")
    word_timings = []

    communicator = edge_tts.Communicate(text, voice)

    with open(audio_path, "wb") as f:
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 1e7,
                    "duration": chunk["duration"] / 1e7,
                })

    return audio_path, word_timings


def silence_clip(duration, fps=44100):
    return AudioClip(
        lambda t: np.zeros((2,)),  # stereo silence
        duration=duration,
        fps=fps,
    )


def align_audio_to_video(audio_clip, video_duration):
    audio_duration = audio_clip.duration
    target = max(video_duration - SAFETY_EPS, 0)

    # Case 1: audio is shorter → pad with silence
    if audio_duration < target:
        silence = silence_clip(target - audio_duration)
        return CompositeAudioClip([audio_clip, silence]), 1.0

    # Case 2: audio is longer → speed up gently
    speed_factor = min(audio_duration / target, MAX_AUDIO_SPEEDUP)
    sped = audio_clip.with_speed_scaled(speed_factor)

    # HARD RULE (MoviePy v2):
    # No subclip(). Ever.
    trimmed = sped.with_start(0).with_duration(target)

    return trimmed, speed_factor


def scale_subtitles(subs, speed_factor, video_duration):
    scaled = []
    limit = video_duration - SAFETY_EPS

    for item in subs:
        start = item["start"] / speed_factor
        duration = item["duration"] / speed_factor

        if start >= limit:
            break

        scaled.append({
            "word": item["word"],
            "start": start,
            "duration": min(duration, limit - start),
        })

    return scaled


def build_subtitle_clips(subs, video):
    clips = []
    buffer = []
    start_time = None

    MAX_WORDS = 6
    BOX_WIDTH = int(video.w * 0.9)
    BOX_HEIGHT = int(video.h * 0.25)

    for item in subs:
        if start_time is None:
            start_time = item["start"]

        buffer.append(item["word"])

        if len(buffer) >= MAX_WORDS:
            text = " ".join(buffer)
            end_time = item["start"] + item["duration"]

            if start_time >= video.duration:
                break

            duration = min(end_time, video.duration - SAFETY_EPS) - start_time
            if duration <= 0:
                buffer = []
                start_time = None
                continue

            clip = (
                TextClip(
                    text,
                    font=FONT,
                    fontsize=48,
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    size=(BOX_WIDTH, BOX_HEIGHT),
                    method="caption",
                    align="center",
                )
                .with_start(start_time)
                .with_duration(duration)
                .with_position(("center", int(video.h * 0.72)))
            )

            clips.append(clip)
            buffer = []
            start_time = None

    return clips

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

    subtitle_clips = []

    # ---- Voiceover ----
    if voice_text.strip():
        audio_path, word_timings = asyncio.run(
            generate_voice_and_subtitles(
                voice_text,
                VOICE_MAP[voice_choice]
            )
        )

        raw_audio = AudioFileClip(audio_path)

        aligned_audio, speed_factor = align_audio_to_video(
            raw_audio,
            VIDEO_DURATION
        )

        video = video.with_audio(aligned_audio)

        if add_subtitles:
            scaled = scale_subtitles(
                word_timings,
                speed_factor,
                VIDEO_DURATION
            )
            subtitle_clips = build_subtitle_clips(scaled, video)

    # ---- Background Music ----
    if music_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(music_file.read())
            music_path = f.name

        music = AudioFileClip(music_path).with_volume_scaled(0.2)

        if video.audio:
            video = video.with_audio(
                CompositeAudioClip([
                    video.audio,
                    music.subclip(0, VIDEO_DURATION)
                ])
            )
        else:
            video = video.with_audio(
                music.subclip(0, VIDEO_DURATION)
            )

    # ---- Composite ----
    if subtitle_clips:
        video = CompositeVideoClip([video, *subtitle_clips])

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
