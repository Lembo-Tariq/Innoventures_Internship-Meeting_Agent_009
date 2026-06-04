# models/meeting.py
from pydantic import BaseModel
from typing import Optional
from datetime import date

class ActionItem(BaseModel):
    task: str
    assignee: str
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"  # low, medium, high

class MeetingData(BaseModel):
    title: str
    date: date
    attendees: list[str]
    agenda: list[str]
    discussion_points: list[str]
    decisions: list[str]
    action_items: list[ActionItem]
    follow_ups: list[str] = []