# tests/test_compare.py
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.transcribe_whisper import transcribe_audio
from pipeline.extract_deepseek import extract_meeting_data
from pipeline.extract_gemini import extract_from_audio
from pipeline.template import populate_mom_template


async def run_option_a(audio_file):
    """Option A: Whisper transcription → DeepSeek extraction"""
    print("\n" + "=" * 50)
    print("OPTION A: Whisper + DeepSeek (two-step)")
    print("=" * 50)
    start = time.time()

    print("\n  [1/3] Transcribing with Whisper...")
    transcript = await transcribe_audio(audio_file)
    print(f"  ✓ Transcript: {len(transcript)} chars")
    print(f"  Preview: {transcript[:200]}...")

    print("\n  [2/3] Extracting with DeepSeek...")
    meeting_data = await extract_meeting_data(transcript)

    print("\n  [3/3] Generating MoM...")
    doc_path = populate_mom_template(meeting_data)

    elapsed = time.time() - start
    return meeting_data, doc_path, elapsed


async def run_option_b(audio_file):
    """Option B: Gemini does both in one shot"""
    print("\n" + "=" * 50)
    print("OPTION B: Gemini (one-shot audio → extraction)")
    print("=" * 50)
    start = time.time()

    print("\n  [1/2] Sending audio to Gemini...")
    meeting_data = await extract_from_audio(audio_file)

    print("\n  [2/2] Generating MoM...")
    # Avoid filename collision
    doc_path = populate_mom_template(meeting_data)

    elapsed = time.time() - start
    return meeting_data, doc_path, elapsed


async def main():
    audio_file = "tests/sample_audio.m4a"

    if not os.path.exists(audio_file):
        print(f"ERROR: Audio file not found: {audio_file}")
        print("Update the audio_file path in this script.")
        return

    # Run both options
    data_a, path_a, time_a = await run_option_a(audio_file)
    data_b, path_b, time_b = await run_option_b(audio_file)

    # Compare
    print("\n" + "=" * 50)
    print("COMPARISON")
    print("=" * 50)

    print(f"\n{'':30} {'Option A':20} {'Option B':20}")
    print(f"{'':30} {'Whisper+DeepSeek':20} {'Gemini':20}")
    print("-" * 70)
    print(f"{'Title':30} {data_a.title[:20]:20} {data_b.title[:20]:20}")
    print(f"{'Date':30} {str(data_a.date):20} {str(data_b.date):20}")
    print(f"{'Attendees':30} {len(data_a.attendees):20} {len(data_b.attendees):20}")
    print(f"{'Agenda items':30} {len(data_a.agenda):20} {len(data_b.agenda):20}")
    print(f"{'Decisions':30} {len(data_a.decisions):20} {len(data_b.decisions):20}")
    print(f"{'Action items':30} {len(data_a.action_items):20} {len(data_b.action_items):20}")
    print(f"{'Follow-ups':30} {len(data_a.follow_ups):20} {len(data_b.follow_ups):20}")
    print(f"{'Time':30} {f'{time_a:.1f}s':20} {f'{time_b:.1f}s':20}")

    print(f"\nOption A attendees: {', '.join(data_a.attendees)}")
    print(f"Option B attendees: {', '.join(data_b.attendees)}")
    print(f"Original attendees: Enan Sabah, Anas, Sarah from Marketing, Omar (IT)")

    print(f"\nOption A output: {path_a}")
    print(f"Option B output: {path_b}")


asyncio.run(main())