# tests/test_template.py
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.meeting import MeetingData, ActionItem
from pipeline.template import populate_mom_template

# Create sample data (same as what the LLM would return)
sample_data = MeetingData(
    title="Q3 Planning Sync",
    date=date(2026, 5, 18),
    attendees=["Enan Sabah", "Anas", "Sarah from Marketing", "Omar (IT)"],
    agenda=[
        "New onboarding flow",
        "Meeting notes problem",
        "Q3 budget review",
    ],
    discussion_points=[
        "Wireframes for onboarding flow need another revision round for mobile layout",
        "Backend API work can start in parallel with design revisions",
        "Omar proposed building a meeting intelligence agent for automated MoM generation",
        "Azure Speech API and SharePoint template access needed for the proof of concept",
    ],
    decisions=[
        "Sarah will revise wireframes and deliver to dev by Thursday",
        "Omar will develop meeting agent PoC in two weeks",
        "IT will provision Azure resources by tomorrow",
        "All departments must submit Q3 budget estimates by Friday",
    ],
    action_items=[
        ActionItem(task="Revise wireframes for onboarding flow", assignee="Sarah", deadline="2026-05-21", priority="high"),
        ActionItem(task="Start backend API endpoints", assignee="Anas", deadline="2026-05-25", priority="medium"),
        ActionItem(task="Build meeting agent PoC", assignee="Omar", deadline="2026-06-01", priority="high"),
        ActionItem(task="Provision Azure resources", assignee="IT", deadline="2026-05-19", priority="high"),
        ActionItem(task="Grant SharePoint template access to Omar", assignee="Anas", deadline="2026-05-18", priority="high"),
        ActionItem(task="Submit Q3 budget estimates", assignee="All attendees", deadline="2026-05-22", priority="high"),
    ],
    follow_ups=[
        "Review revised wireframes before dev handoff",
        "Monitor meeting agent PoC progress",
    ],
)

output_path = populate_mom_template(sample_data)
print(f"MoM generated: {output_path}")