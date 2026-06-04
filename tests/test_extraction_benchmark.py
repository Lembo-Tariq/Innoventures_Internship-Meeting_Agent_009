# tests/test_extraction_benchmark.py
"""
Extraction Model Benchmark
Tests multiple LLMs on the same transcript (Gemini 2.5 Pro output).
Compares: accuracy, completeness, speed, and cost.
"""
import asyncio
import os
import sys
import time
import json
from dotenv import load_dotenv
from openai import OpenAI
from datetime import date

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.meeting import MeetingData

API_KEY = os.environ["OPENROUTER_API_KEY"]
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "extraction_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

today = date.today().isoformat()

SYSTEM_PROMPT = f"""You are a meeting intelligence agent. You extract structured data from meeting transcripts.

Given a raw transcript, extract:
- title: the meeting name or main topic
- date: the meeting date. If not explicitly mentioned, default to today's date which is {today}
- attendees: list ALL people mentioned as present (use real names, not "Speaker 1")
- agenda: list of topics discussed
- discussion_points: key points from the discussion (brief summaries)
- decisions: decisions that were made
- action_items: each with task, assignee, deadline (as actual YYYY-MM-DD date, calculate from context), priority
- follow_ups: anything that needs follow-up but isn't a concrete task

Respond ONLY with valid JSON matching this exact structure:
{{"title": "string", "date": "YYYY-MM-DD", "attendees": ["string"], "agenda": ["string"], "discussion_points": ["string"], "decisions": ["string"], "action_items": [{{"task": "string", "assignee": "string", "deadline": "string or null", "priority": "low|medium|high"}}], "follow_ups": ["string"]}}

Be thorough. Capture every action item and decision. If a deadline is implied but not explicit, calculate the actual date. If priority isn't stated, infer from context."""

# Original ground truth for comparison
GROUND_TRUTH = {
    "attendees": {"Enan Sabah", "Sarah", "Anas", "Omar"},
    "agenda_count": 3,
    "action_items": [
        {"task_keyword": "wireframe", "assignee": "Sarah", "has_deadline": True},
        {"task_keyword": "backend", "assignee": "Anas", "has_deadline": True},
        {"task_keyword": "proof of concept", "assignee": "Omar", "has_deadline": True},
        {"task_keyword": "Azure resources", "assignee": "Enan", "has_deadline": True},
        {"task_keyword": "SharePoint", "assignee": "Anas", "has_deadline": True},
        {"task_keyword": "budget", "assignee": "All", "has_deadline": True},
    ],
    "min_decisions": 4,
    "min_followups": 1,
}

MODELS = [
    {"name": "google/gemini-2.5-flash", "cost": "$0.15/M input, $0.60/M output", "notes": "Fast and cheap"},
    {"name": "google/gemini-2.5-pro", "cost": "$1.25/M input, $10/M output", "notes": "Higher quality"},
    {"name": "deepseek/deepseek-chat", "cost": "$0.14/M input, $0.28/M output", "notes": "Previous default"},
    {"name": "deepseek/deepseek-v4-flash", "cost": "$0.20/M input, $0.60/M output", "notes": "Newer DeepSeek"},
    {"name": "openai/gpt-4o", "cost": "$2.50/M input, $10/M output", "notes": "Strong reasoning"},
    {"name": "openai/gpt-4o-mini", "cost": "$0.15/M input, $0.60/M output", "notes": "Cheap and fast"},
    {"name": "anthropic/claude-sonnet-4.6", "cost": "$3/M input, $15/M output", "notes": "Most thorough"},
    {"name": "qwen/qwen3-30b-a3b", "cost": "$0.20/M input, $0.60/M output", "notes": "Open source"},
]


def score_extraction(data):
    """Score extraction quality against ground truth."""
    scores = {}

    # Attendee accuracy
    extracted_names = set()
    for a in data.attendees:
        name = a.lower().strip()
        if "enan" in name:
            extracted_names.add("Enan Sabah")
        elif "sarah" in name:
            extracted_names.add("Sarah")
        elif "anas" in name:
            extracted_names.add("Anas")
        elif "omar" in name:
            extracted_names.add("Omar")

    scores["attendees_found"] = len(extracted_names)
    scores["attendees_correct"] = extracted_names

    # Action items
    scores["action_count"] = len(data.action_items)
    scores["decisions_count"] = len(data.decisions)
    scores["followups_count"] = len(data.follow_ups)
    scores["agenda_count"] = len(data.agenda)
    scores["discussion_count"] = len(data.discussion_points)

    # Deadline quality
    dates_as_yyyy = sum(
        1 for ai in data.action_items
        if ai.deadline and len(ai.deadline) == 10 and ai.deadline[4] == "-"
    )
    scores["deadlines_as_dates"] = dates_as_yyyy
    scores["deadlines_total"] = sum(1 for ai in data.action_items if ai.deadline)

    # Has Speaker 1/2 issues?
    scores["has_speaker_labels"] = any(
        "speaker" in a.lower() for a in data.attendees
    )

    return scores


async def test_model(model_name, transcript):
    try:
        start = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract structured meeting data:\n\n{transcript}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        elapsed = time.time() - start

        raw = response.choices[0].message.content
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()

        parsed = json.loads(raw)
        data = MeetingData(**parsed)
        scores = score_extraction(data)

        # Save full output
        safe_name = model_name.replace("/", "_").replace(".", "-")
        output_path = os.path.join(OUTPUT_DIR, f"extraction_{safe_name}.json")
        with open(output_path, "w") as f:
            json.dump(parsed, f, indent=2)

        return {
            "model": model_name,
            "time": elapsed,
            "scores": scores,
            "data": data,
            "status": "ok",
        }

    except Exception as e:
        return {
            "model": model_name,
            "time": time.time() - start,
            "status": f"FAIL: {str(e)[:80]}",
        }


async def main():
    # Use Gemini Pro transcript as input
    transcript_path = os.path.join(
        os.path.dirname(__file__),
        "transcription_outputs",
        "transcript_google_gemini-2-5-pro.txt"
    )

    if not os.path.exists(transcript_path):
        print(f"  Error: {transcript_path} not found")
        print("  Run the transcription benchmark first.")
        return

    with open(transcript_path, "r") as f:
        transcript = f.read()

    print("=" * 75)
    print("  EXTRACTION MODEL BENCHMARK")
    print(f"  Input: Gemini 2.5 Pro transcript ({len(transcript)} chars)")
    print(f"  Ground truth: 4 attendees, 6 action items, 3 agenda items")
    print("=" * 75)

    results = []
    for model in MODELS:
        name = model["name"]
        print(f"\n  Testing: {name}...", end=" ", flush=True)
        result = await test_model(name, transcript)
        result["cost"] = model["cost"]
        result["notes"] = model["notes"]
        results.append(result)

        if result["status"] == "ok":
            s = result["scores"]
            print(
                f"✓ {result['time']:.1f}s | "
                f"attendees: {s['attendees_found']}/4 | "
                f"actions: {s['action_count']} | "
                f"decisions: {s['decisions_count']} | "
                f"dates: {s['deadlines_as_dates']}/{s['deadlines_total']} | "
                f"follow-ups: {s['followups_count']}"
            )
        else:
            print(result["status"])

    # Summary table
    print("\n" + "=" * 75)
    print("  RESULTS SUMMARY")
    print("=" * 75)

    header = f"  {'Model':<28} {'Time':>6} {'Att':>4} {'Acts':>5} {'Decs':>5} {'F/U':>4} {'Dates':>6} {'Spkr?':>6}"
    print(f"\n{header}")
    print("  " + "-" * 72)

    for r in sorted(results, key=lambda x: x.get("time", 999)):
        if r["status"] == "ok":
            s = r["scores"]
            spkr = "✗ yes" if s["has_speaker_labels"] else "✓ no"
            print(
                f"  {r['model']:<28} {r['time']:>5.1f}s "
                f"{s['attendees_found']:>4}/4 "
                f"{s['action_count']:>5} "
                f"{s['decisions_count']:>5} "
                f"{s['followups_count']:>4} "
                f"{s['deadlines_as_dates']}/{s['deadlines_total']:>4} "
                f"{spkr:>6}"
            )

    # Detailed attendee breakdown
    print(f"\n  Attendee details:")
    print(f"  {'Model':<28} {'Names found'}")
    print("  " + "-" * 60)
    for r in results:
        if r["status"] == "ok":
            names = ", ".join(sorted(r["scores"]["attendees_correct"]))
            raw = ", ".join(r["data"].attendees)
            print(f"  {r['model']:<28} {names}")
            print(f"  {'':28} Raw: {raw}")

    # Action items detail
    print(f"\n  Action items detail (per model):")
    for r in results:
        if r["status"] == "ok":
            print(f"\n  {r['model']}:")
            for ai in r["data"].action_items:
                print(f"    [{ai.priority}] {ai.task} → {ai.assignee} (deadline: {ai.deadline})")

    # Save results
    results_path = os.path.join(OUTPUT_DIR, "extraction_benchmark_results.json")
    save_data = []
    for r in results:
        entry = {"model": r["model"], "time": r.get("time"), "cost": r.get("cost"), "status": r["status"]}
        if r["status"] == "ok":
            entry["scores"] = r["scores"]
            entry["scores"]["attendees_correct"] = list(r["scores"]["attendees_correct"])
            entry["attendees_raw"] = r["data"].attendees
            entry["action_items"] = [
                {"task": ai.task, "assignee": ai.assignee, "deadline": ai.deadline, "priority": ai.priority}
                for ai in r["data"].action_items
            ]
        save_data.append(entry)

    with open(results_path, "w") as f:
        json.dump(save_data, f, indent=2)

    print(f"\n  All outputs saved to: {OUTPUT_DIR}")
    print(f"  Results JSON: {results_path}")


asyncio.run(main())