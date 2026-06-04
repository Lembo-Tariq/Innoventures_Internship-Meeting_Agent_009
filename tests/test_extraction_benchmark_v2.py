# tests/test_extraction_v2.py
"""
Extraction Benchmark V2 — Final comparison with improved prompts
Tests: Gemini Flash (improved), Claude Sonnet 4.6, Claude Haiku 4.5, GPT-4o, GPT-4o Mini
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

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "extraction_v2_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

today = date.today().isoformat()

# Improved prompt — added follow-up requirement and Speaker resolution
SYSTEM_PROMPT = f"""You are a meeting intelligence agent. You extract structured data from meeting transcripts.

Given a raw transcript, extract:
- title: the meeting name or main topic
- date: the meeting date. If not explicitly mentioned, default to today's date which is {today}
- attendees: list ALL people mentioned as present. Use real names only. If you see "Speaker 1" or similar generic labels, try to infer their role (e.g. "Meeting Lead", "Team Manager") from context. Do NOT include "Speaker 1", "Speaker 2" etc as attendees — resolve them or omit them.
- agenda: list of topics discussed
- discussion_points: key points from the discussion (brief but informative summaries)
- decisions: every decision that was made, even implicit ones
- action_items: each with task (be specific about what needs to be done), assignee (real name), deadline (as actual YYYY-MM-DD date calculated from context), priority (infer from urgency)
- follow_ups: items that need monitoring or checking but aren't concrete tasks. ALWAYS generate at least 2-3 follow-ups — meetings always have things worth following up on.

Respond ONLY with valid JSON matching this exact structure:
{{"title": "string", "date": "YYYY-MM-DD", "attendees": ["string"], "agenda": ["string"], "discussion_points": ["string"], "decisions": ["string"], "action_items": [{{"task": "string", "assignee": "string", "deadline": "string or null", "priority": "low|medium|high"}}], "follow_ups": ["string"]}}

Be thorough. Capture every action item and decision. If a deadline is implied, calculate the actual date. If priority isn't stated, infer from context."""

MODELS = [
    {"name": "google/gemini-2.5-flash", "cost_in": 0.15, "cost_out": 0.60, "notes": "Improved prompt"},
    {"name": "anthropic/claude-sonnet-4.6", "cost_in": 3.00, "cost_out": 15.00, "notes": "Most thorough"},
    {"name": "anthropic/claude-haiku-4.5", "cost_in": 0.80, "cost_out": 4.00, "notes": "Cheaper Claude"},
    {"name": "openai/gpt-4o", "cost_in": 2.50, "cost_out": 10.00, "notes": "Fast, expensive"},
    {"name": "openai/gpt-4o-mini", "cost_in": 0.15, "cost_out": 0.60, "notes": "Fast, cheap"},
    {"name": "deepseek/deepseek-chat", "cost_in": 0.14, "cost_out": 0.28, "notes": "Cheapest, slow"},
]


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

        # Save
        safe_name = model_name.replace("/", "_").replace(".", "-")
        with open(os.path.join(OUTPUT_DIR, f"{safe_name}.json"), "w") as f:
            json.dump(parsed, f, indent=2)

        # Score
        has_speaker = any("speaker" in a.lower() for a in data.attendees)
        real_names = [a for a in data.attendees if "speaker" not in a.lower()]
        dates_ok = sum(1 for ai in data.action_items if ai.deadline and len(ai.deadline) == 10 and "-" in ai.deadline)

        return {
            "model": model_name,
            "time": elapsed,
            "attendees_raw": data.attendees,
            "attendees_clean": real_names,
            "has_speaker_labels": has_speaker,
            "action_count": len(data.action_items),
            "decisions": len(data.decisions),
            "followups": len(data.follow_ups),
            "dates_ok": dates_ok,
            "discussion": len(data.discussion_points),
            "actions": data.action_items,
            "followup_list": data.follow_ups,
            "title": data.title,
            "status": "ok",
        }
    except Exception as e:
        return {"model": model_name, "time": 0, "status": f"FAIL: {str(e)[:80]}"}


async def main():
    transcript_path = os.path.join(
        os.path.dirname(__file__), "transcription_outputs",
        "transcript_google_gemini-2-5-pro.txt"
    )

    if not os.path.exists(transcript_path):
        print(f"  Error: {transcript_path} not found")
        return

    with open(transcript_path, "r") as f:
        transcript = f.read()

    print("=" * 75)
    print("  EXTRACTION BENCHMARK V2 — Improved Prompts")
    print(f"  Input: Gemini 2.5 Pro transcript ({len(transcript)} chars)")
    print("=" * 75)

    results = []
    for model in MODELS:
        name = model["name"]
        print(f"\n  Testing: {name}...", end=" ", flush=True)
        result = await test_model(name, transcript)
        result["cost_in"] = model["cost_in"]
        result["cost_out"] = model["cost_out"]
        result["notes"] = model["notes"]
        results.append(result)

        if result["status"] == "ok":
            print(
                f"✓ {result['time']:.1f}s | "
                f"acts: {result['action_count']} | "
                f"decs: {result['decisions']} | "
                f"f/u: {result['followups']} | "
                f"dates: {result['dates_ok']}/{result['action_count']} | "
                f"clean: {'✓' if not result['has_speaker_labels'] else '✗'}"
            )
        else:
            print(result["status"])

    # Summary
    print("\n" + "=" * 75)
    print("  RESULTS")
    print("=" * 75)

    print(f"\n  {'Model':<30} {'Time':>6} {'Acts':>5} {'Decs':>5} {'F/U':>5} {'Dates':>6} {'Clean':>6} {'$/M in':>7} {'$/M out':>8}")
    print("  " + "-" * 80)

    for r in sorted(results, key=lambda x: x.get("time", 999)):
        if r["status"] == "ok":
            clean = "✓" if not r["has_speaker_labels"] else "✗"
            print(
                f"  {r['model']:<30} {r['time']:>5.1f}s "
                f"{r['action_count']:>5} {r['decisions']:>5} {r['followups']:>5} "
                f"{r['dates_ok']}/{r['action_count']:>4} "
                f"{clean:>6} "
                f"${r['cost_in']:>5.2f} ${r['cost_out']:>6.2f}"
            )

    # Detailed comparison
    print(f"\n  === ATTENDEES ===")
    for r in results:
        if r["status"] == "ok":
            print(f"  {r['model']:<30} {', '.join(r['attendees_raw'])}")

    print(f"\n  === FOLLOW-UPS ===")
    for r in results:
        if r["status"] == "ok":
            print(f"\n  {r['model']}:")
            if r["followup_list"]:
                for fu in r["followup_list"]:
                    print(f"    - {fu}")
            else:
                print(f"    (none)")

    print(f"\n  === ACTION ITEMS (side by side) ===")
    for r in results:
        if r["status"] == "ok":
            print(f"\n  {r['model']}:")
            for ai in r["actions"]:
                print(f"    [{ai.priority}] {ai.task}")
                print(f"      → {ai.assignee} | Due: {ai.deadline}")

    # Save
    with open(os.path.join(OUTPUT_DIR, "v2_results.json"), "w") as f:
        save = []
        for r in results:
            entry = {k: v for k, v in r.items() if k not in ("actions", "followup_list")}
            if r["status"] == "ok":
                entry["actions"] = [{"task": a.task, "assignee": a.assignee, "deadline": a.deadline, "priority": a.priority} for a in r["actions"]]
                entry["followups"] = r["followup_list"]
            save.append(entry)
        json.dump(save, f, indent=2)

    print(f"\n  Outputs saved to: {OUTPUT_DIR}")


asyncio.run(main())