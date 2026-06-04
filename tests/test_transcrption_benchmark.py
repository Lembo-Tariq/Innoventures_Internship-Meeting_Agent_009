# tests/test_transcription_benchmark.py
"""
Transcription Model Benchmark
Tests multiple models on the same audio file and saves each output.
Compares: accuracy, time, and cost.
"""
import asyncio
import os
import sys
import time
import json
import base64
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

client = OpenAI(base_url=OPENROUTER_BASE, api_key=API_KEY)

# Output directory for transcripts
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "transcription_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def read_audio_b64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def transcribe_dedicated_endpoint(model_name, audio_b64, audio_format):
    """Use OpenRouter's /audio/transcriptions endpoint (Whisper, Chirp, etc.)"""
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post(
            f"{OPENROUTER_BASE}/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "input_audio": {"data": audio_b64, "format": audio_format},
                "language": "en",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"{response.status_code}: {response.text[:200]}")
        return response.json().get("text", "")


async def transcribe_multimodal(model_name, audio_b64, audio_format, prompt):
    """Use a multimodal model via /chat/completions with audio input"""
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": audio_format}},
                ],
            },
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content


# Define all models to test
MODELS = [
    # --- Dedicated transcription endpoint models ---
    {
        "name": "openai/whisper-1",
        "type": "dedicated",
        "cost": "$0.006/min",
        "notes": "Classic Whisper, most popular",
    },
    {
        "name": "openai/whisper-large-v3",
        "type": "dedicated",
        "cost": "$0.006/min",
        "notes": "Larger Whisper, better accuracy",
    },
    {
        "name": "openai/whisper-large-v3-turbo",
        "type": "dedicated",
        "cost": "$0.006/min",
        "notes": "Fastest Whisper variant",
    },
    {
        "name": "openai/gpt-4o-transcribe",
        "type": "dedicated",
        "cost": "$2.50/M input tokens",
        "notes": "GPT-4o based, high quality",
    },
    {
        "name": "openai/gpt-4o-mini-transcribe",
        "type": "dedicated",
        "cost": "$1.25/M input tokens",
        "notes": "Cheaper GPT-4o transcription",
    },
    {
        "name": "google/chirp-3",
        "type": "dedicated",
        "cost": "~$0.016/min",
        "notes": "Google's latest ASR model",
    },
    # --- Multimodal models (audio via chat completions) ---
    {
        "name": "google/gemini-2.5-flash",
        "type": "multimodal",
        "cost": "$0.15/M input tokens",
        "notes": "Can label speakers, very fast",
    },
    {
        "name": "google/gemini-2.5-pro",
        "type": "multimodal",
        "cost": "$1.25/M input tokens",
        "notes": "Higher quality, slower",
    },
    {
        "name": "openai/gpt-4o",
        "type": "multimodal",
        "cost": "$2.50/M input tokens",
        "notes": "Strong audio understanding",
    },
    {
        "name": "openai/gpt-4o-mini",
        "type": "multimodal",
        "cost": "$0.15/M input tokens",
        "notes": "Cheaper, decent quality",
    },
]

MULTIMODAL_PROMPT = """Transcribe this meeting recording accurately.

Rules:
- Label each speaker by name if mentioned, otherwise Speaker 1, Speaker 2, etc.
- Include every word spoken, do not summarize
- Format as "Name: what they said" on each line
- Pay close attention to names, especially Arabic or non-English names
- If you hear a date or number, transcribe it exactly"""


async def run_benchmark(audio_file):
    audio_b64 = read_audio_b64(audio_file)
    ext = os.path.splitext(audio_file)[1].lstrip(".")

    print("=" * 70)
    print("  TRANSCRIPTION MODEL BENCHMARK")
    print(f"  Audio: {audio_file}")
    print("=" * 70)

    results = []

    for model in MODELS:
        name = model["name"]
        print(f"\n  Testing: {name} ({model['type']})...", end=" ", flush=True)

        try:
            start = time.time()

            if model["type"] == "dedicated":
                text = await transcribe_dedicated_endpoint(name, audio_b64, ext)
            else:
                text = await transcribe_multimodal(name, audio_b64, ext, MULTIMODAL_PROMPT)

            elapsed = time.time() - start

            # Save output
            safe_name = name.replace("/", "_").replace(".", "-")
            output_path = os.path.join(OUTPUT_DIR, f"transcript_{safe_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)

            # Quick stats
            word_count = len(text.split())
            has_speaker_labels = any(
                label in text.lower()
                for label in ["speaker", "enan", "sarah", "anas", "omar", ":"]
            )

            results.append({
                "model": name,
                "type": model["type"],
                "time": elapsed,
                "words": word_count,
                "chars": len(text),
                "speakers": has_speaker_labels,
                "cost": model["cost"],
                "notes": model["notes"],
                "file": output_path,
                "status": "✓",
            })

            print(f"✓ {elapsed:.1f}s | {word_count} words | speakers: {'✓' if has_speaker_labels else '✗'}")

        except Exception as e:
            elapsed = time.time() - start
            error_msg = str(e)[:80]
            results.append({
                "model": name,
                "type": model["type"],
                "time": elapsed,
                "status": f"✗ {error_msg}",
                "cost": model["cost"],
            })
            print(f"✗ ({error_msg})")

    # Summary table
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"\n  {'Model':<35} {'Time':>6} {'Words':>7} {'Speakers':>9} {'Cost':<20}")
    print("  " + "-" * 78)

    for r in sorted(results, key=lambda x: x.get("time", 999)):
        if r["status"] == "✓":
            print(
                f"  {r['model']:<35} {r['time']:>5.1f}s {r['words']:>7} "
                f"{'  ✓' if r['speakers'] else '  ✗':>9} {r['cost']:<20}"
            )
        else:
            print(f"  {r['model']:<35} {r['status']}")

    # Save results as JSON for later analysis
    results_path = os.path.join(OUTPUT_DIR, "benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  All transcripts saved to: {OUTPUT_DIR}")
    print(f"  Results JSON: {results_path}")
    print(f"\n  Total models tested: {len([r for r in results if r['status'] == '✓'])}/{len(MODELS)}")
    print()


async def main():
    audio_file = "tests/sample_audio.m4a"

    if not os.path.exists(audio_file):
        print(f"  Error: {audio_file} not found")
        print("  Update the audio_file path in this script.")
        return

    await run_benchmark(audio_file)


asyncio.run(main())