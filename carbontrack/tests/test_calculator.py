from app.calculator import calculate_footprint, UserInputs


def test_calculate_footprint_zero_transport():
    inputs = UserInputs(
        transport_miles_per_week=0,
        mpg=20,
        electricity_kwh_per_month=0,
        diet_type="vegan",
    )
    res = calculate_footprint(inputs)
    assert res.transport_co2_lbs == 0.0
    assert res.energy_co2_lbs == 0.0
    assert res.diet_co2_lbs == 200.0
    assert res.total_co2_lbs == 200.0


def test_calculate_footprint_normal():
    inputs = UserInputs(
        transport_miles_per_week=100,
        mpg=25,
        electricity_kwh_per_month=500,
        diet_type="omnivore",
    )
    res = calculate_footprint(inputs)

    # 100 miles / 25 mpg = 4 gallons/wk -> * 19.6 lbs = 78.4 lbs/wk -> * 52/12 = 339.73 lbs/mo
    assert res.transport_co2_lbs > 0.0

    # 500 kWh * 0.85 = 425.0
    assert res.energy_co2_lbs == 425.0

    # Omnivore = 450.0
    assert res.diet_co2_lbs == 450.0


def test_calculate_footprint_invalid_diet():
    inputs = UserInputs(
        transport_miles_per_week=0,
        mpg=20,
        electricity_kwh_per_month=0,
        diet_type="unknown",
    )
    res = calculate_footprint(inputs)
    # Fallbacks to omnivore
    assert res.diet_co2_lbs == 450.0
