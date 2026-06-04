# tests/test_extract.py
import asyncio
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.extract import extract_meeting_data

async def main():
    # Read sample transcript
    with open("tests/sample_transcript.txt", "r") as f:
        transcript = f.read()

    print("Sending transcript to LLM...\n")
    result = await extract_meeting_data(transcript)

    print(f"Title: {result.title}")
    print(f"Date: {result.date}")
    print(f"Attendees: {', '.join(result.attendees)}")
    print(f"\nAgenda ({len(result.agenda)} items):")
    for item in result.agenda:
        print(f"  - {item}")
    print(f"\nDecisions ({len(result.decisions)}):")
    for d in result.decisions:
        print(f"  - {d}")
    print(f"\nAction Items ({len(result.action_items)}):")
    for ai in result.action_items:
        print(f"  [{ai.priority}] {ai.task} -> {ai.assignee} (deadline: {ai.deadline})")
    print(f"\nFollow-ups ({len(result.follow_ups)}):")
    for f in result.follow_ups:
        print(f"  - {f}")

asyncio.run(main())