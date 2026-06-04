# tests/test_speed.py
import asyncio
import os
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.meeting import MeetingData
from pipeline.extract_deepseek import SYSTEM_PROMPT

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# Models to test — fast, capable, available on your key
MODELS = [
    "deepseek/deepseek-chat",
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4.6",
    "qwen/qwen3-30b-a3b",
    "deepseek/deepseek-v4-flash",
]


async def test_model(model_name: str, transcript: str):
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

        return {
            "model": model_name,
            "time": elapsed,
            "attendees": len(data.attendees),
            "actions": len(data.action_items),
            "decisions": len(data.decisions),
            "followups": len(data.follow_ups),
            "has_dates": all(ai.deadline for ai in data.action_items),
            "status": "✓",
        }
    except Exception as e:
        return {
            "model": model_name,
            "time": 0,
            "status": f"✗ {str(e)[:60]}",
        }


async def main():
    with open("tests/sample_transcript.txt", "r") as f:
        transcript = f.read()

    print("=" * 75)
    print("  MODEL SPEED & QUALITY BENCHMARK")
    print("  Input: sample_transcript.txt")
    print("=" * 75)
    print()

    results = []
    for model in MODELS:
        print(f"  Testing {model}...", end=" ", flush=True)
        result = await test_model(model, transcript)
        results.append(result)

        if result["status"] == "✓":
            print(f"{result['time']:.1f}s | "
                  f"{result['actions']} actions | "
                  f"{result['decisions']} decisions | "
                  f"dates: {'✓' if result.get('has_dates') else '✗'}")
        else:
            print(result["status"])

    # Summary table
    print()
    print(f"  {'Model':<35} {'Time':>6} {'Acts':>5} {'Decs':>5} {'F/U':>5} {'Dates':>6}")
    print("  " + "-" * 68)

    for r in sorted(results, key=lambda x: x.get("time", 999)):
        if r["status"] == "✓":
            print(f"  {r['model']:<35} {r['time']:>5.1f}s {r['actions']:>5} "
                  f"{r['decisions']:>5} {r['followups']:>5} {'  ✓' if r.get('has_dates') else '  ✗':>6}")

    print()


asyncio.run(main())