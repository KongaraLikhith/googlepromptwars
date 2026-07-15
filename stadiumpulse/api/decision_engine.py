"""Deterministic, explainable matchday recommendations.

Generative AI explains a recommendation; it does not decide safety-critical routing.
This module keeps the operational rule set inspectable and independently testable.
"""
from dataclasses import asdict, dataclass


ALLOWED_MOBILITY = {"standard", "step-free"}
ALLOWED_TRANSIT_STATUS = {"on_schedule", "minor_delay", "major_delay"}


@dataclass(frozen=True)
class VenueSignals:
    north_plaza_queue_percent: int
    north_plaza_projected_percent: int
    gate_c_walk_minutes: int
    elevator_wait_minutes: int
    transit_status: str
    waste_diversion_percent: int

    @classmethod
    def from_payload(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("Venue signals are required")
        required = {
            "northPlazaQueuePercent": (0, 100),
            "northPlazaProjectedPercent": (0, 100),
            "gateCWalkMinutes": (1, 90),
            "elevatorWaitMinutes": (0, 60),
            "wasteDiversionPercent": (0, 100),
        }
        values = {}
        for name, (lower, upper) in required.items():
            value = payload.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
                raise ValueError(f"Invalid venue signal: {name}")
            values[name] = value
        transit = payload.get("transitStatus")
        if transit not in ALLOWED_TRANSIT_STATUS:
            raise ValueError("Invalid venue signal: transitStatus")
        return cls(
            north_plaza_queue_percent=values["northPlazaQueuePercent"],
            north_plaza_projected_percent=values["northPlazaProjectedPercent"],
            gate_c_walk_minutes=values["gateCWalkMinutes"],
            elevator_wait_minutes=values["elevatorWaitMinutes"],
            transit_status=transit,
            waste_diversion_percent=values["wasteDiversionPercent"],
        )


@dataclass(frozen=True)
class RouteDecision:
    recommended_gate: str
    route: str
    arrival_buffer_minutes: int
    operational_action: str
    confidence: str
    reasons: tuple[str, ...]

    def as_dict(self):
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result


def recommend_route(signals, mobility):
    """Return a deterministic recommendation from bounded venue signals."""
    if mobility not in ALLOWED_MOBILITY:
        mobility = "standard"
    congestion_risk = max(signals.north_plaza_queue_percent, signals.north_plaza_projected_percent)
    use_gate_c = congestion_risk >= 70
    gate = "C" if use_gate_c else "A"
    route = "the step-free north concourse" if mobility == "step-free" else "the east concourse"
    arrival_buffer = 45 if congestion_risk >= 85 else 35
    reasons = [
        f"North Plaza is projected at {signals.north_plaza_projected_percent}% capacity"
        if use_gate_c else "North Plaza is below the reroute threshold"
    ]
    if mobility == "step-free":
        reasons.append(f"Step-free route selected; elevator wait is {signals.elevator_wait_minutes} minutes")
    if signals.transit_status != "on_schedule":
        reasons.append("Transit delay detected; arrival buffer increased")
        arrival_buffer += 10
    if signals.waste_diversion_percent < 80:
        reasons.append("Waste diversion is below the venue target; service team should check station capacity")
    action = ("Assign two volunteers to North Plaza wayfinding and update fan guidance."
              if congestion_risk >= 70 else "Continue monitoring arrivals; no volunteer reassignment is required.")
    confidence = "high" if congestion_risk >= 70 or signals.transit_status != "on_schedule" else "moderate"
    return RouteDecision(gate, route, arrival_buffer, action, confidence, tuple(reasons))
