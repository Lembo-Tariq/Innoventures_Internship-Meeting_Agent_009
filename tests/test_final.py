# tests/test_final.py
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.transcribe_gemini import transcribe_audio
from pipeline.extract_deepseek import extract_meeting_data
from pipeline.template import populate_mom_template


async def main():

    input_file = "tests/sample_audio.m4a"

    print("=" * 50)
    print("MEETING INTELLIGENCE AGENT — Final Pipeline")
    print("Gemini (transcription) → DeepSeek (extraction)")
    print("=" * 50)
    start = time.time()

    # Step 1: Gemini transcribes audio
    print(f"\n[1/3] Transcribing with Gemini: {input_file}")
    transcript = await transcribe_audio(input_file)
    t1 = time.time() - start
    print(f"  ✓ Transcript ready ({len(transcript)} chars) [{t1:.1f}s]")
    print(f"\n--- Transcript preview ---")
    print(transcript[:500])
    print("--- end preview ---\n")

    # Step 2: DeepSeek extracts structured data
    print("[2/3] Extracting with DeepSeek...")
    meeting_data = await extract_meeting_data(transcript)
    t2 = time.time() - start
    print(f"  ✓ Extracted [{t2:.1f}s]")

    # Step 3: Fill Word template
    print("\n[3/3] Generating MoM document...")
    doc_path = populate_mom_template(meeting_data)

    elapsed = time.time() - start

    # Summary
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"  Title:      {meeting_data.title}")
    print(f"  Date:       {meeting_data.date}")
    print(f"  Attendees:  {', '.join(meeting_data.attendees)}")
    print(f"  Agenda:     {len(meeting_data.agenda)} items")
    print(f"  Decisions:  {len(meeting_data.decisions)}")
    print(f"  Actions:    {len(meeting_data.action_items)}")
    for ai in meeting_data.action_items:
        print(f"    [{ai.priority}] {ai.task} → {ai.assignee} (deadline: {ai.deadline})")
    print(f"  Follow-ups: {len(meeting_data.follow_ups)}")
    print(f"  Output:     {doc_path}")
    print(f"  Total time: {elapsed:.1f}s")
    print("=" * 50)


asyncio.run(main())