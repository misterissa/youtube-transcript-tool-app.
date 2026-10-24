import re
import streamlit as st
import yt_dlp

st.set_page_config(
    page_title="YouTube Transcript Tool",
    page_icon="📝",
    layout="centered"
)

st.title("📝 YouTube Transcript Tool")
st.write("Paste a YouTube link to retrieve available captions and download them as a text file.")

url = st.text_input(
    "YouTube video URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

language = st.selectbox(
    "Preferred caption language",
    ["en", "ar", "fr", "es", "de"]
)

if st.button("Get transcript", type="primary"):
    if not url.strip():
        st.warning("Please paste a YouTube video link.")
    elif not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url.strip()):
        st.error("Please enter a valid YouTube URL.")
    else:
        with st.spinner("Checking for available captions..."):
            try:
                options = {
                    "skip_download": True,
                    "quiet": True,
                    "no_warnings": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": [language, f"{language}-.*"],
                    "subtitlesformat": "vtt/best",
                    "outtmpl": "/tmp/%(id)s.%(ext)s",
                    "noplaylist": True,
                }

                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url.strip(), download=False)
                    video_id = info.get("id", "video")
                    title = info.get("title", "YouTube video")

                    requested = [language, f"{language}-.*"]
                    available = info.get("subtitles", {})
                    automatic = info.get("automatic_captions", {})

                    selected = next(
                        (key for key in available if key == language or key.startswith(language + "-")),
                        None
                    )
                    source = available

                    if not selected:
                        selected = next(
                            (key for key in automatic if key == language or key.startswith(language + "-")),
                            None
                        )
                        source = automatic

                    if not selected:
                        st.error(
                            f"No captions were found for language '{language}'. "
                            "Try another language or a video with captions."
                        )
                    else:
                        options["subtitleslangs"] = [selected]
                        with yt_dlp.YoutubeDL(options) as ydl2:
                            ydl2.download([url.strip()])

                        import glob
                        from pathlib import Path

                        files = glob.glob(f"/tmp/{video_id}*.vtt")
                        if not files:
                            files = glob.glob(f"/tmp/{video_id}*.srt")

                        if not files:
                            st.error(
                                "Captions were detected, but the hosting service could not download them. "
                                "YouTube may be limiting access. Please try again later."
                            )
                        else:
                            raw = Path(files[0]).read_text(encoding="utf-8", errors="replace")
                            lines = []
                            for line in raw.splitlines():
                                line = line.strip()
                                if (
                                    not line
                                    or line == "WEBVTT"
                                    or "-->" in line
                                    or line.isdigit()
                                    or line.startswith(("NOTE", "Kind:", "Language:"))
                                ):
                                    continue
                                line = re.sub(r"<[^>]+>", "", line)
                                if not lines or lines[-1] != line:
                                    lines.append(line)

                            transcript = "\n".join(lines).strip()
                            if transcript:
                                st.success(f"Transcript retrieved: {title}")
                                st.text_area("Transcript", transcript, height=350)
                                st.download_button(
                                    "Download transcript (.txt)",
                                    data=transcript,
                                    file_name=f"{video_id}-transcript.txt",
                                    mime="text/plain"
                                )
                            else:
                                st.error("The caption file was empty.")
            except Exception as exc:
                st.error(
                    "Could not retrieve the transcript. The video may not have captions, "
                    "or YouTube may be restricting access from the cloud host."
                )
                st.caption(f"Technical detail: {str(exc)[:300]}")
