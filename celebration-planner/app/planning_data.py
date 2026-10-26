"""Immutable planning assumptions and event templates, allocated once per worker."""

from datetime import timedelta
from types import MappingProxyType
from typing import NamedTuple


class BudgetCategory(NamedTuple):
    key: str
    title: str
    note: str


class PreparationTask(NamedTuple):
    key: str
    lead_time: timedelta
    title: str
    phase: str
    note: str


class VendorTemplate(NamedTuple):
    key: str
    category: str
    title: str
    note: str
    essential: bool


class IdeaTemplate(NamedTuple):
    title: str
    description: str


CATEGORIES = (
    BudgetCategory(
        "venue", "Venue & rentals", "Compare itemized venue, furniture, and weather-backup quotes."
    ),
    BudgetCategory(
        "food",
        "Food & drinks",
        "Confirm dietary needs, water stations, staffing, and final headcount.",
    ),
    BudgetCategory(
        "decor", "Décor & styling", "Favor reusable, rented, or locally sourced decorations."
    ),
    BudgetCategory(
        "entertainment", "Entertainment", "Confirm timings, sound levels, and venue permissions."
    ),
    BudgetCategory(
        "photography", "Photography", "Agree deliverables, consent, and turnaround time in writing."
    ),
    BudgetCategory(
        "accessibility",
        "Accessibility & comfort",
        "Reserve step-free access, clear signage, and a quiet seating area.",
    ),
)

EVENT_WEIGHTS = MappingProxyType(
    {
        "wedding": (22, 30, 14, 8, 10, 6),
        "birthday": (18, 30, 18, 14, 4, 6),
        "community": (24, 24, 10, 10, 4, 18),
    }
)

EVENT_LABELS = MappingProxyType(
    {"wedding": "wedding", "birthday": "birthday celebration", "community": "community gathering"}
)

PREPARATION_TASKS = (
    PreparationTask(
        "vision",
        timedelta(days=120),
        "Set the vision & guest list",
        "Foundations",
        "Agree the guest count, priorities, and budget ceiling before paying deposits.",
    ),
    PreparationTask(
        "venue",
        timedelta(days=90),
        "Confirm venue & key vendors",
        "Book the essentials",
        "Check capacity, accessible entry, cancellation terms, and an indoor fallback.",
    ),
    PreparationTask(
        "invites",
        timedelta(days=60),
        "Send invitations",
        "Bring people together",
        "Share travel details and a way to request dietary or access accommodations privately.",
    ),
    PreparationTask(
        "details",
        timedelta(days=30),
        "Confirm food, activities & styling",
        "Make it yours",
        "Review quotes against the budget and choose reusable decorations.",
    ),
    PreparationTask(
        "headcount",
        timedelta(days=14),
        "Close RSVPs & confirm headcount",
        "Final details",
        "Send final dietary counts to the caterer and share the run of show with vendors.",
    ),
    PreparationTask(
        "brief",
        timedelta(days=7),
        "Brief your helpers",
        "Final details",
        "Assign a contact for each vendor, a setup lead, and a first-aid contact.",
    ),
    PreparationTask(
        "check",
        timedelta(days=1),
        "Pack & confirm the final checklist",
        "Almost there",
        "Reconfirm arrivals, signage, weather plans, water, and essential supplies.",
    ),
    PreparationTask(
        "celebrate",
        timedelta(days=0),
        "Celebrate & welcome everyone",
        "Event day",
        "Check access routes before guests arrive and let your helpers handle the schedule.",
    ),
)

COMMON_VENDORS = (
    VendorTemplate(
        "venue",
        "Venue",
        "Find the right space",
        "Confirm capacity, toilets, power, step-free entry, and a weather fallback.",
        True,
    ),
    VendorTemplate(
        "caterer",
        "Food & drinks",
        "Choose a caterer or food team",
        "Request an itemized quote for {guests} guests, including water and dietary options.",
        True,
    ),
    VendorTemplate(
        "styling",
        "Décor",
        "Plan décor & equipment rentals",
        "Share your {style} brief; check setup and collection charges.",
        False,
    ),
    VendorTemplate(
        "entertainment",
        "Entertainment",
        "Book activities or entertainment",
        "Agree duration, volume limits, age suitability, and any licensing requirements.",
        False,
    ),
    VendorTemplate(
        "photographer",
        "Photography",
        "Arrange photo coverage",
        "Define the shot list and guest consent; a volunteer photo team is also an option.",
        False,
    ),
    VendorTemplate(
        "access",
        "Accessibility",
        "Confirm access & guest comfort",
        "Check step-free routes, accessible toilets, seating, clear signs, and a quiet area.",
        True,
    ),
)

EVENT_VENDOR = MappingProxyType(
    {
        "wedding": VendorTemplate(
            "ceremony",
            "Ceremony",
            "Coordinate the ceremony",
            "Confirm officiant availability, ceremony order, and any required local paperwork.",
            True,
        ),
        "birthday": VendorTemplate(
            "cake",
            "Cake & treats",
            "Order a cake or celebration treats",
            "Check serving count, allergens, delivery timing, and refrigeration.",
            False,
        ),
        "community": VendorTemplate(
            "permits",
            "Community logistics",
            "Confirm permissions & volunteer cover",
            "Ask the venue or local authority about permits, insurance, waste collection, and first-aid arrangements.",
            True,
        ),
    }
)

EVENT_IDEAS = MappingProxyType(
    {
        "wedding": (
            IdeaTemplate(
                "A shared-story welcome",
                "Create a {style} welcome corner with a few favorite memories and a guest message book; skip expensive single-use favors.",
            ),
            IdeaTemplate(
                "A meaningful menu",
                "Choose two dishes with a story for the couple, with clearly labelled plant-based and allergen-aware alternatives.",
            ),
            IdeaTemplate(
                "A calm celebration space",
                "Place comfortable seats away from speakers, keep the ceremony route step-free, and offer guests a quieter way to take part.",
            ),
        ),
        "birthday": (
            IdeaTemplate(
                "A make-it-your-own moment",
                "Try a {style} craft or photo station with reusable supplies and choices suitable for the guest ages.",
            ),
            IdeaTemplate(
                "A favorite-things playlist",
                "Ask guests for one favorite song in advance and build a short playlist with a quieter break between activities.",
            ),
            IdeaTemplate(
                "A celebration without the waste",
                "Use a refillable drinks station, borrowed serving pieces, and a shared dessert table with clearly labelled allergens.",
            ),
        ),
        "community": (
            IdeaTemplate(
                "Let neighbors shape the day",
                "Invite a few volunteers to host short {style} activities, with a seated or low-sensory alternative at each station.",
            ),
            IdeaTemplate(
                "A local swap & share corner",
                "Create a clearly signed space for books, seedlings, or skills, with simple participation rules and a volunteer host.",
            ),
            IdeaTemplate(
                "A welcoming community table",
                "Use shared seating, multilingual welcome signs where useful, free drinking water, and clearly labelled food choices.",
            ),
        ),
    }
)

BASE_TIPS = (
    "These are planning allocations, not local market quotes. Compare written quotes and include taxes before booking.",
    "Keep the 10% contingency available; increase the total budget only after an explicit decision.",
    "Ask guests about access and dietary needs privately, and share only what vendors need to accommodate them.",
)
