from datetime import date, timedelta
from decimal import Decimal
from itertools import combinations

import pytest

from app.planner import build_plan
from app.schemas import PlanRequest


def request(**changes):
    values = {
        "event_type": "wedding",
        "event_date": date.today() + timedelta(days=180),
        "budget": "250000.01",
        "currency": "INR",
        "guest_count": 150,
        "style": "Garden gathering",
        "location": "Pune",
        "priorities": [],
    }
    return PlanRequest(**(values | changes))


@pytest.mark.parametrize(
    "event_type,extra_vendor",
    [("wedding", "ceremony"), ("birthday", "cake"), ("community", "permits")],
)
def test_each_event_has_complete_budget_and_relevant_vendors(event_type, extra_vendor):
    plan = build_plan(request(event_type=event_type))
    assert sum(Decimal(str(item.amount)) for item in plan.budget_items) == Decimal("250000.01")
    assert sum(item.percent for item in plan.budget_items) == 100
    assert plan.budget_items[-1].category == "Contingency"
    assert plan.budget_items[-1].percent == 10
    assert all(item.amount > 0 for item in plan.budget_items)
    assert extra_vendor in {vendor.id for vendor in plan.vendors}
    assert any(vendor.category == "Accessibility" and vendor.essential for vendor in plan.vendors)
    assert plan.source == "local" and len(plan.ideas) == 3


@pytest.mark.parametrize("budget", ["100.00", "100.01", "999.99", "100000000.00"])
def test_cent_allocation_preserves_total_at_boundaries(budget):
    plan = build_plan(request(budget=budget))
    assert sum(Decimal(str(item.amount)) for item in plan.budget_items) == Decimal(budget)
    assert all(item.amount >= 0 for item in plan.budget_items)


def test_priority_increases_its_allocation_without_using_contingency():
    normal = build_plan(request())
    prioritized = build_plan(request(priorities=["photography"]))
    assert prioritized.budget_items[4].amount > normal.budget_items[4].amount
    assert prioritized.budget_items[-1].percent == 10
    assert sum(item.percent for item in prioritized.budget_items) == 100


def test_short_timeline_moves_overdue_tasks_to_today_in_order():
    today = date.today()
    plan = build_plan(request(event_date=today + timedelta(days=10)))
    dates = [item.date for item in plan.timeline]
    assert dates == sorted(dates)
    assert min(dates) == today and max(dates) == plan.event_date
    assert "Start now" in plan.timeline[0].note
    assert "Start now" not in plan.timeline[-1].note
    assert any("date is close" in tip for tip in plan.tips)


def test_today_event_has_no_past_tasks_and_per_guest_rounds_to_cents():
    plan = build_plan(request(event_date=date.today(), budget="100", guest_count=3))
    assert all(item.date == date.today() for item in plan.timeline)
    assert plan.days_until == 0 and plan.per_guest == 33.33


def test_local_plan_reflects_event_style_location_and_guest_count():
    plan = build_plan(
        request(event_type="birthday", style="Cozy book club", location="Delhi", guest_count=12)
    )
    assert "cozy book club" in plan.summary
    assert "Delhi" in plan.summary and "12 guests" in plan.summary
    assert "12 guests" in next(item.note for item in plan.vendors if item.id == "caterer")
    assert "cozy book club" in plan.ideas[0].description


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_every_supported_priority_combination_preserves_budget(event_type):
    priorities = ("food", "decor", "entertainment", "photography", "venue", "accessibility")
    for count in range(4):
        for chosen in combinations(priorities, count):
            plan = build_plan(request(event_type=event_type, budget="100.01", priorities=chosen))
            assert sum(Decimal(str(item.amount)) for item in plan.budget_items) == Decimal("100.01")
            assert sum(item.percent for item in plan.budget_items) == 100
            assert plan.budget_items[-1].percent == 10
            assert all(item.amount >= 0 for item in plan.budget_items)


def test_editing_a_plan_cannot_change_another_plan_or_shared_templates():
    brief = request()
    original = build_plan(brief).model_dump(mode="json")
    edited = build_plan(brief)
    edited.budget_items[0].amount = 0
    edited.timeline[0].note = "Changed"
    edited.vendors[0].title = "Changed"
    edited.ideas[0].description = "Changed"
    edited.tips.clear()
    assert build_plan(brief).model_dump(mode="json") == original


def test_user_style_with_template_markers_is_kept_as_literal_text():
    plan = build_plan(request(style="A {style} and {guests} gathering"))
    assert "a {style} and {guests} gathering" in plan.ideas[0].description
    assert "a {style} and {guests} gathering" in next(
        item.note for item in plan.vendors if item.id == "styling"
    )
