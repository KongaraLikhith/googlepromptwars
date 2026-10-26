"""Pure, inspectable planning rules; no network calls or shared mutable plans."""

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TypedDict

from .planning_data import (
    BASE_TIPS,
    CATEGORIES,
    COMMON_VENDORS,
    EVENT_IDEAS,
    EVENT_LABELS,
    EVENT_VENDOR,
    EVENT_WEIGHTS,
    PREPARATION_TASKS,
)
from .schemas import PlanRequest, PlanResponse


# Typed records keep rule helpers independent of response-model construction.
# PlanResponse validates the complete nested result once at the boundary.
class BudgetAllocation(TypedDict):
    category: str
    amount: float
    percent: int
    note: str


class ScheduledTask(TypedDict):
    id: str
    title: str
    date: date
    phase: str
    note: str


class VendorTask(TypedDict):
    id: str
    category: str
    title: str
    note: str
    essential: bool


class LocalIdea(TypedDict):
    title: str
    description: str


CONTINGENCY_PERCENT = 10
PRIORITY_WEIGHT_BONUS = 6
CENT = Decimal("0.01")


def _apportion(total: int, weights: Sequence[int]) -> list[int]:
    """Largest-remainder allocation preserves every unit, including spare cents."""
    weight_sum = sum(weights)
    values = [total * weight // weight_sum for weight in weights]
    ranking = sorted(
        range(len(weights)), key=lambda index: total * weights[index] % weight_sum, reverse=True
    )
    for index in ranking[: total - sum(values)]:
        values[index] += 1
    return values


def _budget(request: PlanRequest) -> list[BudgetAllocation]:
    """Apply priorities to the spendable share while protecting the reserve."""
    weights = [
        weight + (PRIORITY_WEIGHT_BONUS if category.key in request.priorities else 0)
        for weight, category in zip(EVENT_WEIGHTS[request.event_type], CATEGORIES, strict=True)
    ]
    percentages = _apportion(100 - CONTINGENCY_PERCENT, weights) + [CONTINGENCY_PERCENT]
    cents = _apportion(int(request.budget * 100), percentages)
    items: list[BudgetAllocation] = [
        {
            "category": category.title,
            "amount": amount / 100,
            "percent": percent,
            "note": category.note,
        }
        for category, amount, percent in zip(CATEGORIES, cents[:-1], percentages[:-1], strict=True)
    ]
    items.append(
        {
            "category": "Contingency",
            "amount": cents[-1] / 100,
            "percent": CONTINGENCY_PERCENT,
            "note": "Keep this reserve uncommitted for taxes, delivery charges, and last-minute changes.",
        }
    )
    return items


def _timeline(event_date: date, today: date) -> list[ScheduledTask]:
    """Keep milestones ordered and explain catch-up work for short lead times."""
    items: list[ScheduledTask] = []
    for task in PREPARATION_TASKS:
        original = event_date - task.lead_time
        note = task.note
        if original < today:
            note = (
                "Start now: this milestone has been moved into your shorter planning window. "
                + note
            )
        items.append(
            {
                "id": task.key,
                "title": task.title,
                "date": max(today, original),
                "phase": task.phase,
                "note": note,
            }
        )
    return items


def _vendors(request: PlanRequest) -> list[VendorTask]:
    """Combine common access/logistics tasks with the relevant event task."""
    templates = (*COMMON_VENDORS, EVENT_VENDOR[request.event_type])
    guests = str(request.guest_count)
    style = request.style.lower()
    return [
        {
            "id": template.key,
            "category": template.category,
            "title": template.title,
            "note": template.note.replace("{guests}", guests).replace("{style}", style),
            "essential": template.essential,
        }
        for template in templates
    ]


def _ideas(event_type: str, style: str) -> list[LocalIdea]:
    """Return fresh suggestions without allowing edits to mutate templates."""
    return [
        {"title": template.title, "description": template.description.replace("{style}", style)}
        for template in EVENT_IDEAS[event_type]
    ]


def _tips(request: PlanRequest, days_until: int) -> list[str]:
    """Keep base guidance and add only the advice triggered by user context."""
    tips = list(BASE_TIPS)
    if request.guest_count > 200:
        tips.append(
            "For a large guest list, appoint zone leads and confirm venue capacity, emergency arrangements, and service staffing with qualified local providers."
        )
    if days_until < 30:
        tips.append(
            "Your date is close: prioritize the venue, guest confirmations, food, and access before optional extras."
        )
    if request.preferences:
        tips.append(
            "Share your additional preferences with vendors before requesting final quotes; confirm feasibility rather than assuming they can meet every request."
        )
    return tips


def build_plan(request: PlanRequest, today: date | None = None) -> PlanResponse:
    """Build an independent plan from validated context and an explicit calendar day."""
    today = today or date.today()
    days_until = (request.event_date - today).days
    style = (request.style or "thoughtful").lower()
    location = f" in {request.location}" if request.location else ""
    summary = f"A {style} {EVENT_LABELS[request.event_type]} for {request.guest_count} guests{location}, with a protected contingency and practical next steps."
    return PlanResponse(
        event_type=request.event_type,
        event_date=request.event_date,
        budget=float(request.budget),
        currency=request.currency,
        guest_count=request.guest_count,
        summary=summary,
        budget_items=_budget(request),
        timeline=_timeline(request.event_date, today),
        vendors=_vendors(request),
        ideas=_ideas(request.event_type, style),
        tips=_tips(request, days_until),
        source="local",
        source_note="Local planning mode: rule-based estimates and curated ideas. Add a Gemini API key for personalized AI ideas.",
        per_guest=float(
            (request.budget / request.guest_count).quantize(CENT, rounding=ROUND_HALF_UP)
        ),
        days_until=days_until,
    )
