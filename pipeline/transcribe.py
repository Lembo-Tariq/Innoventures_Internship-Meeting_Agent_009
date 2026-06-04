# transcribe.py
# Final: Gemini 2.5 Pro for transcription — best name accuracy and speaker labels
import os
import base64
from dotenv import load_dotenv
from openai import OpenAI
from config import OPENROUTER_API_KEY

load_dotenv()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".flac", ".aac"}

TRANSCRIPTION_PROMPT = """Transcribe this meeting recording accurately.

Context: This is a meeting involving InnoVentures, a digital transformation company. Known team members include:
- Hassan Odeh(Job Title:Head of AI Department)
- Enan Sabah(Job Title: Project Manager)
- Tariq Yaseen(Job Title: Intern)
- Shahul Hameed(Job Title: Service Delivery Manager)
- Alhasan Farajallah(Job Title: Director of Technology)
- Anas Al Ali(Job Title: Director of Business)

Rules:
- Label each speaker by name when identified. Use the names above if you recognize them.
- For unidentified speakers, use their role if inferable (e.g. "Meeting Lead", "Project Manager") or "Speaker 1", "Speaker 2" as last resort.
- Format as "Name: what they said" on each line
- Include every word spoken, do not summarize
- Pay close attention to names, especially Arabic names
- If a date or number is mentioned, transcribe it exactly
- For external participants, note their company if mentioned (e.g. "Alex (Google): ...")"""


def get_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio using Gemini 2.5 Pro, or read text files directly."""

    ext = os.path.splitext(file_path)[1].lower()

    # Text files: just read directly
    if ext in {".txt", ".md"}:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if ext not in AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    # Read and encode audio
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_format = ext.lstrip(".")

    client = get_client()

    response = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TRANSCRIPTION_PROMPT},
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": audio_format}},
                ],
            },
        ],
        temperature=0.1,
    )

    result = response.choices[0].message.content
    if not result:
        raise RuntimeError("Transcription returned empty — audio may be too large or in an unsupported format. Try converting to mp3.")
    return result