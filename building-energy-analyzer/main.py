"""
Building Energy Analyzer - main menu
====================================
Connects Module 1 (energy_calculator.py) and Module 2 (analysis.py).

Run with:   python main.py
"""

import os

import pandas as pd

import analysis
from energy_calculator import Room, RoomManager

DATA_DIR = "data"
ROOMS_CSV = os.path.join(DATA_DIR, "rooms.csv")
READINGS_CSV = os.path.join(DATA_DIR, "readings.csv")
REPORTS_DIR = "reports"
CHARTS_DIR = "charts"

MENU = """
==================== BUILDING ENERGY ANALYZER ====================
 MODULE 1 - Energy calculator (estimated)
   1. Add a room
   2. List rooms
   3. Search rooms
   4. Update a room
   5. Energy report (per room, total, per m2)
   6. Save rooms to CSV
 MODULE 2 - Consumption and cost analysis (actual readings)
   7. Run analysis (clean readings, merge, cost per room/building/month)
   8. Reduce AC power: before vs after (NumPy)
   9. Create the 4 charts (PNG)
  10. Export reports (CSV)
  11. Show one room: estimated vs actual
   0. Exit
==================================================================
"""


# ---------------------------------------------------------------------------
# Input helpers (keep asking until the value is valid)
# ---------------------------------------------------------------------------
def ask_room_field(field, prompt, current=None):
    """Ask for one Room field and validate it by trying to build a test Room."""
    template = {
        "room_id": "X", "room_name": "X", "building": "X", "area_m2": 1,
        "lighting_kw": 0, "ac_kw": 0, "equipment_kw": 0, "hours_per_day": 0,
    }
    while True:
        text = input(prompt).strip()
        if current is not None and text == "":
            return current  # keep the old value when updating
        try:
            Room.from_dict({**template, field: text})  # runs the Room validation
            return text
        except ValueError as error:
            print(f"  Invalid input: {error}")


def ask_number(prompt, low=None, high=None):
    """Ask for a number within an optional range."""
    while True:
        try:
            value = float(input(prompt))
        except ValueError:
            print("  Please enter a number.")
            continue
        if low is not None and value < low:
            print(f"  Value must be at least {low}.")
        elif high is not None and value > high:
            print(f"  Value must be at most {high}.")
        else:
            return value


# ---------------------------------------------------------------------------
# Module 1 actions
# ---------------------------------------------------------------------------
def add_room(manager):
    print("\n-- Add a room --")
    while True:
        room_id = ask_room_field("room_id", "Room ID (e.g. R09): ")
        if room_id.upper() in manager.rooms:
            print("  That room ID already exists.")
        else:
            break
    values = {"room_id": room_id}
    prompts = {
        "room_name": "Room name: ",
        "building": "Building: ",
        "area_m2": "Area (m2, > 0): ",
        "lighting_kw": "Lighting power (kW, >= 0): ",
        "ac_kw": "Air-conditioning power (kW, >= 0): ",
        "equipment_kw": "Equipment power (kW, >= 0): ",
        "hours_per_day": "Operating hours per day (0-24): ",
    }
    for field, prompt in prompts.items():
        values[field] = ask_room_field(field, prompt)
    manager.add_room(Room.from_dict(values))
    print(f"Room {values['room_id'].upper()} added.")


def print_rooms(rooms):
    if not rooms:
        print("No rooms found.")
        return
    print(f"{'ID':<4} {'Name':<15} {'Building':<15} {'Area':>10}  {'Power':>8}  {'Hours':>6}")
    for room in rooms:
        print(room)


def search_rooms(manager):
    text = input("Search text (ID, name or building): ")
    print_rooms(manager.search(text))


def update_room(manager):
    room_id = input("Room ID to update: ")
    try:
        room = manager.get_room(room_id)
    except KeyError as error:
        print(error)
        return
    print("Press Enter to keep the current value.")
    prompts = {
        "room_name": "Room name",
        "building": "Building",
        "area_m2": "Area (m2)",
        "lighting_kw": "Lighting (kW)",
        "ac_kw": "AC (kW)",
        "equipment_kw": "Equipment (kW)",
        "hours_per_day": "Hours per day",
    }
    changes = {}
    for field, label in prompts.items():
        old = getattr(room, field)
        changes[field] = ask_room_field(field, f"{label} [{old}]: ", current=old)
    manager.update_room(room_id, **changes)
    print("Room updated.")


def energy_report(manager):
    table = manager.energy_table()  # list of tuples
    if not table:
        print("No rooms.")
        return
    print(f"{'ID':<4} {'Room':<15} {'Building':<15} {'kWh/day':>9} {'kWh/m2/day':>11}")
    for room_id, name, building, kwh, per_m2 in table:
        print(f"{room_id:<4} {name:<15} {building:<15} {kwh:>9.2f} {per_m2:>11.3f}")
    print(f"\nTotal estimated consumption: {manager.total_daily_energy():.2f} kWh/day")
    for building, kwh in sorted(manager.energy_by_building().items()):
        print(f"  {building}: {kwh:.2f} kWh/day")
    top3 = sorted(table, key=lambda row: row[3], reverse=True)[:3]  # slicing
    print("Top 3 rooms by daily energy: " + ", ".join(f"{row[1]} ({row[3]:.1f})" for row in top3))


def save_rooms(manager):
    manager.save_csv(ROOMS_CSV)
    print(f"Saved {len(manager)} rooms to {ROOMS_CSV}")


# ---------------------------------------------------------------------------
# Module 2 actions
# ---------------------------------------------------------------------------
class Session:
    """Keeps the results of the analysis so later menu items can reuse them."""

    def __init__(self):
        self.merged = None
        self.comparison = None
        self.rooms_df = None
        self.price = None
        self.ac_result = None


def run_analysis(manager, session):
    print("\n-- Run analysis --")
    if len(manager) == 0:
        print("Add or load rooms first.")
        return
    manager.save_csv(ROOMS_CSV)  # Module 1 output feeds Module 2
    price = ask_number("Price per kWh (e.g. 2.0): ", low=0)
    try:
        readings = analysis.load_readings(READINGS_CSV)
    except FileNotFoundError:
        print(f"Readings file not found: {READINGS_CSV}")
        return

    rooms_df = analysis.load_rooms(ROOMS_CSV)
    clean, report = analysis.clean_readings(readings, set(rooms_df["room_id"]))
    merged = analysis.add_cost(analysis.merge_data(clean, rooms_df), price)

    session.rooms_df = rooms_df
    session.merged = merged
    session.price = price
    session.comparison = analysis.room_comparison(merged, rooms_df)

    print("\nCleaning report:")
    for key, value in report.items():
        print(f"  {key.replace('_', ' '):<30} {value}")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("\nPer room:")
    print(session.comparison[["room_id", "room_name", "building", "total_kwh",
                              "total_cost", "estimated_total_kwh",
                              "actual_vs_estimated_pct"]].to_string(index=False))
    print("\nPer building:")
    print(analysis.summarize(merged, ["building"]).to_string(index=False))
    print("\nPer month:")
    print(analysis.summarize(merged, ["month"]).to_string(index=False))


def need_analysis(session):
    if session.merged is None:
        print("Run the analysis first (option 7).")
        return False
    return True


def ac_scenario(session):
    if not need_analysis(session):
        return
    pct = ask_number("Reduce AC power by what percentage (0-100)? ", low=0, high=100)
    result, totals = analysis.ac_reduction_scenario(session.rooms_df, pct, session.price)
    session.ac_result = result
    print(result[["room_id", "room_name", "ac_kw_before", "ac_kw_after",
                  "daily_kwh_before", "daily_kwh_after", "daily_saving_kwh"]].to_string(index=False))
    print(f"\nTotal before: {totals['before_kwh']:.2f} kWh/day")
    print(f"Total after : {totals['after_kwh']:.2f} kWh/day")
    print(f"Saving      : {totals['saving_kwh']:.2f} kWh/day ({totals['saving_pct']:.1f} %)")


def make_charts(session):
    if not need_analysis(session):
        return
    paths = analysis.make_all_charts(session.merged, session.comparison, CHARTS_DIR)
    print("Charts saved:")
    for path in paths:
        print("  " + path)


def export_reports(session):
    if not need_analysis(session):
        return
    if session.ac_result is None:  # default scenario so the report file always exists
        session.ac_result, _ = analysis.ac_reduction_scenario(session.rooms_df, 20, session.price)
        print("(AC report uses a 20 % reduction; run option 8 to choose another value.)")
    paths = analysis.export_reports(session.merged, session.comparison, session.ac_result, REPORTS_DIR)
    print("Reports saved:")
    for path in paths:
        print("  " + path)


def show_room(manager, session):
    if not need_analysis(session):
        return
    room_id = input("Room ID: ").strip().upper()
    row = session.comparison[session.comparison["room_id"] == room_id]  # pandas filtering
    if row.empty:
        print("Room not found in the analysis.")
        return
    row = row.iloc[0]  # indexing
    room = manager.get_room(room_id)
    print(f"\n{room.room_id} - {room.room_name} ({room.building}), {room.area_m2:.0f} m2")
    print(f"  Estimated: {room.daily_energy_kwh():.2f} kWh/day "
          f"({room.energy_per_m2():.3f} kWh/m2/day)")
    print(f"  Actual   : {row['avg_daily_kwh']:.2f} kWh/day average "
          f"({row['actual_kwh_per_m2_day']:.3f} kWh/m2/day)")
    print(f"  Actual total {row['total_kwh']:.1f} kWh -> cost {row['total_cost']:.2f} "
          f"({row['actual_vs_estimated_pct']:.1f} % of estimate)")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    manager = RoomManager()
    session = Session()
    if os.path.exists(ROOMS_CSV):
        skipped = manager.load_csv(ROOMS_CSV)
        print(f"Loaded {len(manager)} rooms from {ROOMS_CSV}")
        for line_no, message in skipped:
            print(f"  Skipped line {line_no}: {message}")

    actions = {
        "1": lambda: add_room(manager),
        "2": lambda: print_rooms(manager.list_rooms()),
        "3": lambda: search_rooms(manager),
        "4": lambda: update_room(manager),
        "5": lambda: energy_report(manager),
        "6": lambda: save_rooms(manager),
        "7": lambda: run_analysis(manager, session),
        "8": lambda: ac_scenario(session),
        "9": lambda: make_charts(session),
        "10": lambda: export_reports(session),
        "11": lambda: show_room(manager, session),
    }
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye.")
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid option, try again.")
            continue
        try:
            action()
        except (ValueError, KeyError) as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    main()
