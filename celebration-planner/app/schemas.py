"""Validated inputs and the public planning response."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Priority = Literal["food", "decor", "entertainment", "photography", "venue", "accessibility"]


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: Literal["wedding", "birthday", "community"]
    event_date: date
    budget: Annotated[Decimal, Field(ge=100, le=100_000_000, decimal_places=2, allow_inf_nan=False)]
    currency: Literal["INR", "USD", "EUR", "GBP"] = "INR"
    guest_count: Annotated[int, Field(strict=True, ge=1, le=10_000)]
    location: str = Field(default="", max_length=100)
    style: str = Field(default="A thoughtful celebration", max_length=80)
    priorities: list[Priority] = Field(default_factory=list, max_length=3)
    preferences: str = Field(default="", max_length=500)

    @field_validator("event_date")
    @classmethod
    def planning_window(cls, value: date) -> date:
        today = date.today()
        if not today <= value <= today + timedelta(days=730):
            raise ValueError("Choose a date from today through the next two years.")
        return value

    @field_validator("priorities")
    @classmethod
    def unique_priorities(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Choose each priority only once.")
        return values

    @field_validator("location", "style", "preferences")
    @classmethod
    def plain_text(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("Use readable text without control characters.")
        return " ".join(value.split())


class BudgetItem(BaseModel):
    category: str
    amount: float
    percent: int
    note: str


class TimelineItem(BaseModel):
    id: str
    title: str
    date: date
    phase: str
    note: str


class VendorItem(BaseModel):
    id: str
    category: str
    title: str
    note: str
    essential: bool


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=70)
    description: str = Field(min_length=1, max_length=300)


class AIEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ideas: list[Idea] = Field(min_length=3, max_length=4)
    tips: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(min_length=3, max_length=5)


class PlanResponse(BaseModel):
    event_type: str
    event_date: date
    budget: float
    currency: str
    guest_count: int
    summary: str
    budget_items: list[BudgetItem]
    timeline: list[TimelineItem]
    vendors: list[VendorItem]
    ideas: list[Idea]
    tips: list[str]
    source: Literal["local", "gemini"]
    source_note: str
    per_guest: float
    days_until: int
