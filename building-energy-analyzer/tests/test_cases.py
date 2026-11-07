"""
Test cases: 3 valid inputs and 3 invalid inputs.
Each test records what we EXPECT (worked out by hand) and what ACTUALLY
happens, then marks PASS or FAIL.
Run from the project folder:   python tests/test_cases.py
"""
import os
import sys

import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analysis
from energy_calculator import Room
# ---------------------------------------------------------------------------
# Valid cases: the program must ACCEPT the input and give the right answer
# ---------------------------------------------------------------------------
def valid_daily_energy():
    room = Room("R09", "Test Lab", "Admin Block", 50, 1, 5, 2, 8)
    expected = 64.0  # (1 + 5 + 2) kW x 8 h
    actual = room.daily_energy_kwh()
    return "Daily energy of a normal room", "lighting 1, AC 5, equipment 2 kW, 8 h, 50 m2", \
        f"{expected} kWh/day", f"{actual} kWh/day", actual == expected

def valid_boundary_values():
    room = Room("R10", "Boundary", "Admin Block", 20, 0.2, 5.0, 8.0, 24)  # 24 h is allowed
    zero = Room("R11", "Off", "Admin Block", 10, 0, 0, 0, 0)               # zero power and 0 h allowed
    expected = "316.8 kWh/day and 0.0 kWh/day"
    actual = f"{round(room.daily_energy_kwh(), 1)} kWh/day and {zero.daily_energy_kwh()} kWh/day"
    return "Boundary values (24 h, zero power / 0 h)", "hours = 24 with 13.2 kW; all power = 0 with hours = 0", \
        expected, actual, expected == actual

def valid_ac_reduction():
    rooms = analysis.load_rooms(os.path.join("data", "rooms.csv"))
    r01 = rooms[rooms["room_id"] == "R01"]
    result, _ = analysis.ac_reduction_scenario(r01, 20)
    expected = "143.0 -> 125.0 kWh/day"  # AC 9.0 -> 7.2 kW: (1.8 + 7.2 + 3.5) x 10 = 125
    actual = f"{result['daily_kwh_before'].iloc[0]} -> {result['daily_kwh_after'].iloc[0]} kWh/day"
    return "AC power reduced by 20 % (room R01)", "R01 from rooms.csv, reduction = 20 %", \
        expected, actual, expected == actual

# ---------------------------------------------------------------------------
# Invalid cases: the program must REJECT the input (raise ValueError)
# ---------------------------------------------------------------------------
def _expect_rejection(name, description, args):
    expected = "ValueError (input rejected)"
    try:
        Room(*args)
        actual = "accepted (no error)"
    except ValueError as error:
        actual = f"ValueError: {error}"
    return name, description, expected, actual, actual.startswith("ValueError")


def invalid_area_zero():
    return _expect_rejection("Area equal to zero", "area_m2 = 0",
                             ("R12", "Bad", "Admin Block", 0, 1, 5, 2, 8))


def invalid_negative_power():
    return _expect_rejection("Negative power", "ac_kw = -3",
                             ("R13", "Bad", "Admin Block", 50, 1, -3, 2, 8))


def invalid_hours_over_24():
    return _expect_rejection("Operating hours above 24", "hours_per_day = 25",
                             ("R14", "Bad", "Admin Block", 50, 1, 5, 2, 25))


ALL_TESTS = [
    ("Valid", valid_daily_energy), ("Valid", valid_boundary_values), ("Valid", valid_ac_reduction),
    ("Invalid", invalid_area_zero), ("Invalid", invalid_negative_power), ("Invalid", invalid_hours_over_24),
]


def run_tests():
    """Run every test and return the results as a DataFrame."""
    rows = []
    for number, (kind, test) in enumerate(ALL_TESTS, start=1):
        name, description, expected, actual, passed = test()
        rows.append({
            "test": number, "type": kind, "case": name, "input": description,
            "expected": expected, "actual": actual, "result": "PASS" if passed else "FAIL",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    results = run_tests()
    pd.set_option("display.width", 250, "display.max_colwidth", 70)
    print(results.to_string(index=False))
    os.makedirs("reports", exist_ok=True)
    results.to_csv(os.path.join("reports", "test_results.csv"), index=False)
    print(f"\n{(results['result'] == 'PASS').sum()} of {len(results)} tests passed.")
