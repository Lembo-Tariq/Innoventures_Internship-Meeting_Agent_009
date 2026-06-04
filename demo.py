# demo.py
"""
Meeting Intelligence Agent — Local Demo
========================================
Transforms meeting recordings or notes into professional
Minutes of Meeting (MoM) documents.

Usage:
    python demo.py <audio_or_text_file>

Examples:
    python demo.py meeting_recording.mp3
    python demo.py meeting_recording.m4a
    python demo.py meeting_notes.txt

Supported formats:
    Audio: .mp3, .wav, .m4a, .ogg, .webm, .mp4, .flac, .aac
    Text:  .txt, .md
"""

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.transcribe import transcribe_audio
from pipeline.extract import extract_meeting_data
from pipeline.template import populate_mom_template

# Supported file types
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".flac", ".aac"}
TEXT_EXTS = {".txt", ".md"}
ALL_EXTS = AUDIO_EXTS | TEXT_EXTS


def print_header():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     Meeting Intelligence Agent  (AGT-009)    ║")
    print("  ║         Local Demo — Innoventures            ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


def print_step(num, total, msg):
    bar = "█" * num + "░" * (total - num)
    print(f"  [{bar}] Step {num}/{total}: {msg}")


def print_results(data, doc_path, elapsed, costs):
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │              Pipeline Complete               │")
    print("  └─────────────────────────────────────────────┘")
    print()
    print(f"  Title:       {data.title}")
    print(f"  Date:        {data.date}")
    print(f"  Attendees:   {', '.join(data.attendees)}")
    print()
    print(f"  Agenda:      {len(data.agenda)} items")
    print(f"  Decisions:   {len(data.decisions)}")
    print(f"  Actions:     {len(data.action_items)}")
    print(f"  Follow-ups:  {len(data.follow_ups)}")
    print()

    if data.action_items:
        print("  Action Items:")
        for item in data.action_items:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                (item.priority or "medium").lower(), "⚪"
            )
            deadline = item.deadline or "TBD"
            print(f"    {priority_icon} {item.task}")
            print(f"       → {item.assignee}  |  Due: {deadline}")
        print()

    size_kb = os.path.getsize(doc_path) / 1024
    print(f"  Output:      {doc_path}")
    print(f"  File size:   {size_kb:.1f} KB")
    print(f"  Total time:  {elapsed:.1f}s")
    print(f"  ─── Cost Breakdown ───")
    if costs["transcription_in"] > 0:
        t_cost = costs["transcription_in"] + costs["transcription_out"]
        print(f"  Transcription:  ${t_cost:.4f}")
    e_cost = costs["extraction_in"] + costs["extraction_out"]
    print(f"  Extraction:     ${e_cost:.4f}")
    print(f"  Template:       Free")
    print(f"  Total:          ${costs['total']:.4f}")
    print()

def estimate_cost(transcript_len: int, is_audio: bool, audio_duration_sec: int = 0):
    """Estimate pipeline cost based on token usage."""
    costs = {}

    if is_audio:
        # Gemini 2.5 Pro: audio input ~25 tokens/sec at $1.25/M input
        audio_tokens = audio_duration_sec * 25
        transcript_tokens = transcript_len // 4  # rough: 4 chars per token
        costs["transcription_in"] = (audio_tokens / 1_000_000) * 1.25
        costs["transcription_out"] = (transcript_tokens / 1_000_000) * 5.00
    else:
        costs["transcription_in"] = 0
        costs["transcription_out"] = 0

    # Claude Haiku 4.5: extraction
    input_tokens = (transcript_len // 4) + 500  # transcript + system prompt
    output_tokens = 1500  # typical JSON output
    costs["extraction_in"] = (input_tokens / 1_000_000) * 0.80
    costs["extraction_out"] = (output_tokens / 1_000_000) * 4.00

    costs["total"] = sum(costs.values())
    return costs


async def run(input_file: str):
    print_header()

    ext = os.path.splitext(input_file)[1].lower()
    is_audio = ext in AUDIO_EXTS

    total_steps = 3

    # Step 1: Transcribe
    if is_audio:
        print_step(1, total_steps, "Transcribing audio with Gemini...")
    else:
        print_step(1, total_steps, "Reading text input...")

    start = time.time()
    transcript = await transcribe_audio(input_file)
    t1 = time.time() - start
    print(f"           ✓ Done ({len(transcript)} chars, {t1:.1f}s)\n")

    # Step 2: Extract
    print_step(2, total_steps, "Extracting meeting data with Haiku...")
    meeting_data = await extract_meeting_data(transcript)
    t2 = time.time() - start
    print(f"           ✓ Done ({len(meeting_data.action_items)} actions found, {t2:.1f}s)\n")

    # Step 3: Generate document
    print_step(3, total_steps, "Generating MoM document...")
    doc_path = populate_mom_template(meeting_data)
    elapsed = time.time() - start
    print(f"           ✓ Done ({elapsed:.1f}s)\n")

    # Cost estimate
    is_audio = os.path.splitext(input_file)[1].lower() in AUDIO_EXTS
    file_size = os.path.getsize(input_file)
    # Rough estimate: 16KB/sec for mp3, so duration ≈ filesize / 16000
    audio_duration = int(file_size / 16000) if is_audio else 0
    costs = estimate_cost(len(transcript), is_audio, audio_duration)

    # Results
    print_results(meeting_data, doc_path, elapsed,costs)


def main():
    # Check arguments
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    input_file = os.path.normpath(input_file)

    # Validate file exists
    if not os.path.exists(input_file):
        print(f"\n  Error: File not found: {input_file}")
        sys.exit(1)

    # Validate file type
    ext = os.path.splitext(input_file)[1].lower()
    if ext not in ALL_EXTS:
        print(f"\n  Error: Unsupported file type: {ext}")
        print(f"  Supported: {', '.join(sorted(ALL_EXTS))}")
        sys.exit(1)

    # Run
    asyncio.run(run(input_file))


if __name__ == "__main__":
    main()