import re
import glob
from pathlib import Path

import streamlit as st
import yt_dlp
from google import genai

st.set_page_config(
    page_title="YouTube Transcript Tool",
    page_icon="📝",
    layout="centered"
)

st.title("📝 YouTube Transcript Tool")
st.write(
    "Retrieve YouTube captions, download transcripts, "
    "and generate AI summaries with practical takeaways."
)

url = st.text_input(
    "YouTube video URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

language = st.selectbox(
    "Preferred caption language",
    ["en", "ar", "fr", "es", "de"]
)


def clean_captions(file_path):
    raw = Path(file_path).read_text(
        encoding="utf-8",
        errors="replace"
    )
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
        line = re.sub(r"&amp;", "&", line)
        line = re.sub(r"&lt;", "<", line)
        line = re.sub(r"&gt;", ">", line)

        if line and (not lines or lines[-1] != line):
            lines.append(line)

    return "\n".join(lines).strip()


if st.button("Get transcript", type="primary"):
    if not url.strip():
        st.warning("Please paste a YouTube video link.")
    elif not re.match(
        r"^https?://(www\.)?(youtube\.com|youtu\.be)/",
        url.strip()
    ):
        st.error("Please enter a valid YouTube URL.")
    else:
        try:
            with st.spinner("Checking video captions..."):
                options = {
                    "skip_download": True,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                }

                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(
                        url.strip(),
                        download=False
                    )

                video_id = info.get("id", "video")
                title = info.get("title", "YouTube video")

                manual = info.get("subtitles", {})
                automatic = info.get("automatic_captions", {})

                selected = next(
                    (
                        key for key in manual
                        if key == language
                        or key.startswith(language + "-")
                    ),
                    None
                )
                use_automatic = False

                if not selected:
                    selected = next(
                        (
                            key for key in automatic
                            if key == language
                            or key.startswith(language + "-")
                        ),
                        None
                    )
                    use_automatic = bool(selected)

                if not selected:
                    st.error(
                        f"No captions found in {language}. "
                        "Try another language."
                    )
                else:
                    download_options = {
                        "skip_download": True,
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "writesubtitles": not use_automatic,
                        "writeautomaticsub": use_automatic,
                        "subtitleslangs": [selected],
                        "subtitlesformat": "vtt/best",
                        "outtmpl": f"/tmp/{video_id}.%(ext)s",
                        "overwrites": True,
                    }

                    with yt_dlp.YoutubeDL(download_options) as ydl:
                        ydl.download([url.strip()])

                    files = (
                        glob.glob(f"/tmp/{video_id}*.vtt")
                        + glob.glob(f"/tmp/{video_id}*.srt")
                    )

                    if not files:
                        st.error(
                            "Captions were found, but could not be "
                            "downloaded. YouTube may be restricting access."
                        )
                    else:
                        transcript = clean_captions(files[0])

                        if transcript:
                            st.session_state["transcript"] = transcript
                            st.session_state["video_title"] = title
                            st.session_state["video_id"] = video_id
                            st.success(f"Transcript retrieved: {title}")
                        else:
                            st.error("The caption file was empty.")

        except Exception as exc:
            st.error(
                "Could not retrieve captions. The video may not have "
                "captions, or YouTube may be restricting cloud access."
            )
            st.caption(f"Technical detail: {str(exc)[:300]}")


if st.session_state.get("transcript"):
    transcript = st.session_state["transcript"]
    title = st.session_state.get("video_title", "YouTube video")
    video_id = st.session_state.get("video_id", "video")

    st.subheader("Transcript")
    st.text_area("Retrieved captions", transcript, height=300)

    st.download_button(
        "Download transcript (.txt)",
        data=transcript,
        file_name=f"{video_id}-transcript.txt",
        mime="text/plain"
    )

    st.divider()
 st.subheader("✨ AI Video Insights")

summary_style = st.selectbox(
    "Choose your summary style",
    ["Short summary", "Detailed summary", "Business insights"]
)

if st.button("Generate summary and action points", type="primary"):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            client = genai.Client(api_key=api_key)

            prompt = f"""
You are a clear, practical research assistant.

Analyze the following YouTube transcript.

Video title: {title}

Create these sections:
1. SUMMARY: Explain the main message clearly.
2. KEY TAKEAWAYS: List the most important ideas.
3. ACTION POINTS: Give practical steps the viewer can apply.
4. IMPORTANT DETAILS: Include useful examples, names, or figures
   mentioned in the transcript.

Use concise, readable language. Do not invent facts.
If the transcript is incomplete or unclear, say so.

TRANSCRIPT:
{transcript[:100000]}
"""

            with st.spinner("Gemini is analyzing the transcript..."):
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )

            result = response.text or "The AI returned an empty response."

            st.session_state["ai_result"] = result

        except Exception as exc:
            st.error(
                "Could not generate the AI insights. Check that your "
                "Gemini API key is valid and that API access is available."
            )
            st.caption(f"Technical detail: {str(exc)[:300]}")

    if st.session_state.get("ai_result"):
        st.markdown(st.session_state["ai_result"])
        st.download_button(
            "Download AI insights (.txt)",
            data=st.session_state["ai_result"],
            file_name=f"{video_id}-ai-insights.txt",
            mime="text/plain"
        )
