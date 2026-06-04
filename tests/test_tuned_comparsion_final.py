# tests/test_tuned_comparison.py
import asyncio
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.extract_flash_final import extract_meeting_data as extract_flash
from pipeline.extract_haiku_final import extract_meeting_data as extract_haiku
from pipeline.extract_sonnet_final import extract_meeting_data as extract_sonnet
from pipeline.template import populate_mom_template

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "tuned_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODELS = [
    ("Gemini Flash (tuned)", extract_flash),
    ("Claude Haiku 4.5 (tuned)", extract_haiku),
    ("Claude Sonnet 4.6 (tuned)", extract_sonnet),
]


async def main():
    transcript_path = os.path.join(
        os.path.dirname(__file__), "transcription_outputs",
        "transcript_google_gemini-2-5-pro.txt"
    )
    with open(transcript_path, "r") as f:
        transcript = f.read()

    print("=" * 75)
    print("  TUNED EXTRACTION COMPARISON — Best Prompt Per Model")
    print("=" * 75)

    results = []
    for name, extract_fn in MODELS:
        print(f"\n  Testing: {name}...", end=" ", flush=True)
        start = time.time()
        try:
            data = await extract_fn(transcript)
            elapsed = time.time() - start

            # Generate MoM for each
            safe = name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "")
            doc_path = populate_mom_template(data)

            # Also save JSON
            json_path = os.path.join(OUTPUT_DIR, f"{safe}.json")
            with open(json_path, "w") as f:
                json.dump(data.model_dump(), f, indent=2, default=str)

            results.append({"name": name, "data": data, "time": elapsed, "doc": doc_path})
            print(f"✓ {elapsed:.1f}s")
        except Exception as e:
            print(f"✗ {str(e)[:80]}")

    # Side by side comparison
    for r in results:
        d = r["data"]
        print(f"\n{'='*75}")
        print(f"  {r['name']} — {r['time']:.1f}s")
        print(f"{'='*75}")
        print(f"  Title:      {d.title}")
        print(f"  Attendees:  {', '.join(d.attendees)}")
        print(f"  Agenda:     {len(d.agenda)} items")
        print(f"  Discussion: {len(d.discussion_points)} points")
        print(f"  Decisions:  {len(d.decisions)}")
        print(f"\n  Action Items ({len(d.action_items)}):")
        for ai in d.action_items:
            print(f"    [{ai.priority}] {ai.task}")
            print(f"      → {ai.assignee} | Due: {ai.deadline}")
        print(f"\n  Follow-ups ({len(d.follow_ups)}):")
        for fu in d.follow_ups:
            print(f"    - {fu}")
        print(f"\n  MoM: {r['doc']}")

    # Quick summary
    print(f"\n{'='*75}")
    print(f"  SUMMARY")
    print(f"{'='*75}")
    print(f"  {'Model':<35} {'Time':>6} {'Acts':>5} {'Decs':>5} {'F/U':>5} {'Disc':>5}")
    print(f"  {'-'*62}")
    for r in results:
        d = r["data"]
        print(f"  {r['name']:<35} {r['time']:>5.1f}s {len(d.action_items):>5} "
              f"{len(d.decisions):>5} {len(d.follow_ups):>5} {len(d.discussion_points):>5}")


asyncio.run(main())