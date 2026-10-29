# extract.py
# Final: Claude Haiku 4.5 — best value, follows instructions perfectly
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from datetime import date
from pydantic import ValidationError
from models.meeting import MeetingData
from config import OPENROUTER_API_KEY

load_dotenv()


def get_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


def build_system_prompt(today: str) -> str:
    return f"""You are a senior meeting note-taker working for InnoVentures, a digital transformation company based in Abu Dhabi, UAE. You extract structured data from meeting transcripts and create MoM(Minutes of Meeting).

InnoVentures team members include (but are not limited to):
- Hassan Odeh(Job Title: Head of AI Department)
- Enan Sabah(Job Title: Project Manager)
- Tariq Yaseen(Job Title: Intern)
- Shahul Hameed(Job Title: Service Delivery Manager)
- Alhasan Farajallah(Job Title: Director of Technology)
- Anas Al Ali(Job Title: Director of Business)

Given a raw transcript, extract:
- title: a professional meeting title that captures the main topics
- date: meeting date in YYYY-MM-DD format. Default to {today} if not stated.
- attendees: list all participants as "First Name (Role) - Company". For INV employees, use their known title abbreviated if long (e.g. keep roles to 3 words max). For external participants, infer a short role from context. Use first names only for consistency unless full name is needed to avoid ambiguity. If someone's company is unknown, just use their name.
- agenda: the main topics discussed. Keep to 2-4 high-level topics. Do NOT list sub-topics as separate agenda items.
- discussion_points: summarize by TOPIC, not by speaker turn. Group related information together into thematic summaries. Do NOT write a chronological replay of who said what — instead, synthesize the key information discussed about each topic into 3-5 concise points. Each point should capture the conclusion or key takeaway, not the back-and-forth conversation that led to it. Each bullet point must be self-contained — always use the full company or person name, never start with "they" or "their" without first stating who.
- decisions: all decisions made, explicit and implicit
- action_items: IMPORTANT RULES FOR ACTION ITEMS:
  - Do NOT split a single task into multiple items. "Draft the proposal and send to client" is ONE task, not two.
  - When a task applies to everyone (e.g. "everyone submit their reports"), create ONE action item with assignee "All attendees" — do NOT create separate items per person.
  - task: specific description of what needs to be done
  - assignee: format as "First Name (Role) - Company", matching the attendees format. Keep role descriptions to 3 words max.
  - deadline: the due date in YYYY-MM-DD if stated or clearly implied (resolve relative dates like "by Thursday" against the meeting date), otherwise null.
  - priority: "high", "medium" or "low", based on urgency expressed in the meeting. Default to "medium".
  - Aim for 5-7 action items total. If you have more than 8, you are probably over-splitting.
- follow_ups: items needing monitoring. Be specific about WHEN and WHAT to check. Include timing (e.g. "by Thursday", "mid-week", "after two weeks").
- IMPORTANT: All output must be in English regardless of the transcript language. If the transcript contains Arabic or other languages, translate all content to English in your extraction.
Respond ONLY with valid JSON:
{{"title":"string","date":"YYYY-MM-DD","attendees":["string"],"agenda":["string"],"discussion_points":["string"],"decisions":["string"],"action_items":[{{"task":"string","assignee":"string","deadline":"YYYY-MM-DD or null","priority":"high|medium|low"}}],"follow_ups":["string"]}}"""


MAX_ATTEMPTS = 3


def _parse(raw: str) -> MeetingData:
    """Strip optional markdown fences and validate against the schema."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return MeetingData(**json.loads(raw))


async def extract_meeting_data(transcript: str) -> MeetingData:
    """Extract structured meeting data using Claude Haiku 4.5.

    If the model returns invalid JSON or data that fails schema validation,
    the error is sent back to the model so it can correct its own output
    (up to MAX_ATTEMPTS calls in total).
    """
    client = get_client()
    messages = [
        {"role": "system", "content": build_system_prompt(date.today().isoformat())},
        {"role": "user", "content": f"Extract structured meeting data:\n\n{transcript}"},
    ]

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        try:
            return _parse(raw)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            print(f"Extraction attempt {attempt}/{MAX_ATTEMPTS} failed validation: {str(e).splitlines()[0]}")
            if attempt == MAX_ATTEMPTS:
                break
            messages += [
                {"role": "assistant", "content": raw or ""},
                {"role": "user", "content": (
                    "Your JSON did not match the required schema. Fix these errors and "
                    f"respond again with ONLY the corrected JSON:\n{e}"
                )},
            ]

    raise RuntimeError(
        f"Could not extract valid meeting data after {MAX_ATTEMPTS} attempts. Last error: {last_error}"
    )
