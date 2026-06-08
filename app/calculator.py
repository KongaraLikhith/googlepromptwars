from pydantic import BaseModel


class UserInputs(BaseModel):
    """
    Pydantic model representing the input data provided by the user.
    """

    transport_miles_per_week: float
    mpg: float
    electricity_kwh_per_month: float
    diet_type: str  # 'vegan', 'vegetarian', 'omnivore', 'heavy_meat'


class FootprintResult(BaseModel):
    """
    Pydantic model representing the calculated footprint metrics.
    """

    transport_co2_lbs: float
    energy_co2_lbs: float
    diet_co2_lbs: float
    total_co2_lbs: float


def calculate_footprint(inputs: UserInputs) -> FootprintResult:
    """
    Calculates the monthly carbon footprint based on user inputs.

    Args:
        inputs (UserInputs): The structured user data from the frontend.

    Returns:
        FootprintResult: The calculated CO2 metrics in pounds.
    """
    # Assumptions based on average EPA metrics:
    # 1 gallon of gasoline = ~19.6 lbs CO2
    if inputs.mpg > 0:
        gallons_per_week = inputs.transport_miles_per_week / inputs.mpg
        transport_lbs = gallons_per_week * 19.6 * 52 / 12  # monthly average
    else:
        transport_lbs = 0.0

    # Electricity: ~0.85 lbs CO2 per kWh
    energy_lbs = inputs.electricity_kwh_per_month * 0.85

    # Diet (monthly estimates)
    diet_multipliers = {
        "vegan": 200.0,
        "vegetarian": 250.0,
        "omnivore": 450.0,
        "heavy_meat": 600.0,
    }
    diet_lbs = diet_multipliers.get(inputs.diet_type.lower(), 450.0)

    total_lbs = transport_lbs + energy_lbs + diet_lbs

    return FootprintResult(
        transport_co2_lbs=round(transport_lbs, 2),
        energy_co2_lbs=round(energy_lbs, 2),
        diet_co2_lbs=round(diet_lbs, 2),
        total_co2_lbs=round(total_lbs, 2),
    )
