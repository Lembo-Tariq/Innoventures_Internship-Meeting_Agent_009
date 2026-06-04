# tests/test_pipeline.py
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.transcribe_whisper import transcribe_audio
from pipeline.extract_deepseek import extract_meeting_data
from pipeline.template import populate_mom_template


async def main():
    # Change this to your audio file to test transcription
    input_file = "tests/sample_audio.m4a"

    # Uncomment the line below and use your audio filename:
    # input_file = "tests/your_recording.m4a"

    print("=" * 50)
    print("MEETING INTELLIGENCE AGENT — Full Pipeline")
    print("=" * 50)
    start = time.time()

    # Step 1: Transcribe (or read text)
    print(f"\n[1/3] Processing input: {input_file}")
    transcript = await transcribe_audio(input_file)
    print(f"  ✓ Transcript ready ({len(transcript)} characters)")

    # Step 2: LLM extracts structured data
    print("\n[2/3] Extracting meeting data via LLM...")
    meeting_data = await extract_meeting_data(transcript)
    print(f"  ✓ Extracted: {len(meeting_data.attendees)} attendees, "
          f"{len(meeting_data.action_items)} action items, "
          f"{len(meeting_data.decisions)} decisions")

    # Step 3: Fill the Word template
    print("\n[3/3] Generating MoM document...")
    doc_path = populate_mom_template(meeting_data)
    print(f"  ✓ Document saved: {doc_path}")

    elapsed = time.time() - start

    # Summary
    print("\n" + "=" * 50)
    print(f"  Title:      {meeting_data.title}")
    print(f"  Date:       {meeting_data.date}")
    print(f"  Attendees:  {', '.join(meeting_data.attendees)}")
    print(f"  Actions:    {len(meeting_data.action_items)}")
    print(f"  Output:     {doc_path}")
    print(f"  Size:       {os.path.getsize(doc_path) / 1024:.1f} KB")
    print(f"  Time:       {elapsed:.1f}s")
    print("=" * 50)


asyncio.run(main())