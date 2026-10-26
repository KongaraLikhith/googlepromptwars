"""Explainable budgets, achievable dates, and event-specific checklists."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .schemas import PlanRequest, PlanResponse

_CATEGORIES = (
    ("venue", "Venue & rentals", "Compare itemized venue, furniture, and weather-backup quotes."),
    (
        "food",
        "Food & drinks",
        "Confirm dietary needs, water stations, staffing, and final headcount.",
    ),
    ("decor", "Décor & styling", "Favor reusable, rented, or locally sourced decorations."),
    ("entertainment", "Entertainment", "Confirm timings, sound levels, and venue permissions."),
    ("photography", "Photography", "Agree deliverables, consent, and turnaround time in writing."),
    (
        "accessibility",
        "Accessibility & comfort",
        "Reserve step-free access, clear signage, and a quiet seating area.",
    ),
)
_WEIGHTS = {
    "wedding": [22, 30, 14, 8, 10, 6],
    "birthday": [18, 30, 18, 14, 4, 6],
    "community": [24, 24, 10, 10, 4, 18],
}
_LABELS = {
    "wedding": "wedding",
    "birthday": "birthday celebration",
    "community": "community gathering",
}


def _apportion(total: int, weights: list[int]) -> list[int]:
    """Largest-remainder allocation preserves every unit, including spare cents."""
    weight_sum = sum(weights)
    values = [(total * weight) // weight_sum for weight in weights]
    ranking = sorted(
        range(len(weights)), key=lambda index: (total * weights[index]) % weight_sum, reverse=True
    )
    for index in ranking[: total - sum(values)]:
        values[index] += 1
    return values


def build_plan(request: PlanRequest, today: date | None = None) -> PlanResponse:
    today = today or date.today()
    days_until = (request.event_date - today).days
    weights = [
        weight + (6 if category[0] in request.priorities else 0)
        for weight, category in zip(_WEIGHTS[request.event_type], _CATEGORIES, strict=True)
    ]
    percentages = _apportion(90, weights) + [10]
    amounts = _apportion(int(request.budget * 100), percentages)
    budget_items = [
        {"category": category[1], "amount": cents / 100, "percent": percent, "note": category[2]}
        for category, cents, percent in zip(
            _CATEGORIES, amounts[:-1], percentages[:-1], strict=True
        )
    ]
    budget_items.append(
        {
            "category": "Contingency",
            "amount": amounts[-1] / 100,
            "percent": 10,
            "note": "Keep this reserve uncommitted for taxes, delivery charges, and last-minute changes.",
        }
    )

    schedule = [
        (
            "vision",
            120,
            "Set the vision & guest list",
            "Foundations",
            "Agree the guest count, priorities, and budget ceiling before paying deposits.",
        ),
        (
            "venue",
            90,
            "Confirm venue & key vendors",
            "Book the essentials",
            "Check capacity, accessible entry, cancellation terms, and an indoor fallback.",
        ),
        (
            "invites",
            60,
            "Send invitations",
            "Bring people together",
            "Share travel details and a way to request dietary or access accommodations privately.",
        ),
        (
            "details",
            30,
            "Confirm food, activities & styling",
            "Make it yours",
            "Review quotes against the budget and choose reusable decorations.",
        ),
        (
            "headcount",
            14,
            "Close RSVPs & confirm headcount",
            "Final details",
            "Send final dietary counts to the caterer and share the run of show with vendors.",
        ),
        (
            "brief",
            7,
            "Brief your helpers",
            "Final details",
            "Assign a contact for each vendor, a setup lead, and a first-aid contact.",
        ),
        (
            "check",
            1,
            "Pack & confirm the final checklist",
            "Almost there",
            "Reconfirm arrivals, signage, weather plans, water, and essential supplies.",
        ),
        (
            "celebrate",
            0,
            "Celebrate & welcome everyone",
            "Event day",
            "Check access routes before guests arrive and let your helpers handle the schedule.",
        ),
    ]
    timeline = []
    for item_id, offset, title, phase, note in schedule:
        original = request.event_date - timedelta(days=offset)
        if original < today:
            note = (
                "Start now: this milestone has been moved into your shorter planning window. "
                + note
            )
        timeline.append(
            {
                "id": item_id,
                "title": title,
                "date": max(today, original),
                "phase": phase,
                "note": note,
            }
        )

    vendor_specs = [
        (
            "venue",
            "Venue",
            "Find the right space",
            "Confirm capacity, toilets, power, step-free entry, and a weather fallback.",
            True,
        ),
        (
            "caterer",
            "Food & drinks",
            "Choose a caterer or food team",
            f"Request an itemized quote for {request.guest_count} guests, including water and dietary options.",
            True,
        ),
        (
            "styling",
            "Décor",
            "Plan décor & equipment rentals",
            f"Share your {request.style.lower()} brief; check setup and collection charges.",
            False,
        ),
        (
            "entertainment",
            "Entertainment",
            "Book activities or entertainment",
            "Agree duration, volume limits, age suitability, and any licensing requirements.",
            False,
        ),
        (
            "photographer",
            "Photography",
            "Arrange photo coverage",
            "Define the shot list and guest consent; a volunteer photo team is also an option.",
            False,
        ),
        (
            "access",
            "Accessibility",
            "Confirm access & guest comfort",
            "Check step-free routes, accessible toilets, seating, clear signs, and a quiet area.",
            True,
        ),
    ]
    if request.event_type == "wedding":
        vendor_specs.append(
            (
                "ceremony",
                "Ceremony",
                "Coordinate the ceremony",
                "Confirm officiant availability, ceremony order, and any required local paperwork.",
                True,
            )
        )
    elif request.event_type == "birthday":
        vendor_specs.append(
            (
                "cake",
                "Cake & treats",
                "Order a cake or celebration treats",
                "Check serving count, allergens, delivery timing, and refrigeration.",
                False,
            )
        )
    else:
        vendor_specs.append(
            (
                "permits",
                "Community logistics",
                "Confirm permissions & volunteer cover",
                "Ask the venue or local authority about permits, insurance, waste collection, and first-aid arrangements.",
                True,
            )
        )
    vendors = [
        {"id": item_id, "category": category, "title": title, "note": note, "essential": essential}
        for item_id, category, title, note, essential in vendor_specs
    ]

    style = request.style or "thoughtful"
    if request.event_type == "wedding":
        ideas = [
            {
                "title": "A shared-story welcome",
                "description": f"Create a {style.lower()} welcome corner with a few favorite memories and a guest message book; skip expensive single-use favors.",
            },
            {
                "title": "A meaningful menu",
                "description": "Choose two dishes with a story for the couple, with clearly labelled plant-based and allergen-aware alternatives.",
            },
            {
                "title": "A calm celebration space",
                "description": "Place comfortable seats away from speakers, keep the ceremony route step-free, and offer guests a quieter way to take part.",
            },
        ]
    elif request.event_type == "birthday":
        ideas = [
            {
                "title": "A make-it-your-own moment",
                "description": f"Try a {style.lower()} craft or photo station with reusable supplies and choices suitable for the guest ages.",
            },
            {
                "title": "A favorite-things playlist",
                "description": "Ask guests for one favorite song in advance and build a short playlist with a quieter break between activities.",
            },
            {
                "title": "A celebration without the waste",
                "description": "Use a refillable drinks station, borrowed serving pieces, and a shared dessert table with clearly labelled allergens.",
            },
        ]
    else:
        ideas = [
            {
                "title": "Let neighbors shape the day",
                "description": f"Invite a few volunteers to host short {style.lower()} activities, with a seated or low-sensory alternative at each station.",
            },
            {
                "title": "A local swap & share corner",
                "description": "Create a clearly signed space for books, seedlings, or skills, with simple participation rules and a volunteer host.",
            },
            {
                "title": "A welcoming community table",
                "description": "Use shared seating, multilingual welcome signs where useful, free drinking water, and clearly labelled food choices.",
            },
        ]
    tips = [
        "These are planning allocations, not local market quotes. Compare written quotes and include taxes before booking.",
        "Keep the 10% contingency available; increase the total budget only after an explicit decision.",
        "Ask guests about access and dietary needs privately, and share only what vendors need to accommodate them.",
    ]
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
    location = f" in {request.location}" if request.location else ""
    summary = f"A {style.lower()} {_LABELS[request.event_type]} for {request.guest_count} guests{location}, with a protected contingency and practical next steps."
    return PlanResponse(
        event_type=request.event_type,
        event_date=request.event_date,
        budget=float(request.budget),
        currency=request.currency,
        guest_count=request.guest_count,
        summary=summary,
        budget_items=budget_items,
        timeline=timeline,
        vendors=vendors,
        ideas=ideas,
        tips=tips,
        source="local",
        source_note="Local planning mode: rule-based estimates and curated ideas. Add a Gemini API key for personalized AI ideas.",
        per_guest=float(
            (request.budget / request.guest_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        days_until=days_until,
    )
