"""
Module 1 - Energy Consumption Calculator
========================================
Defines the Room class (with input validation), a RoomManager that stores
rooms and supports add / list / search / update, and the energy formulas:

    daily energy (kWh)      = (lighting + AC + equipment kW) x hours per day
    consumption per m2      = daily energy / room area
"""

import csv
import os

# ---- Validation limits (tuples are immutable, so they suit constants) ------
HOURS_RANGE = (0, 24)  # allowed operating hours per day, inclusive

# Column order used when saving / loading the rooms CSV file.
FIELDNAMES = [
    "room_id", "room_name", "building", "area_m2",
    "lighting_kw", "ac_kw", "equipment_kw", "hours_per_day",
]
POWER_FIELDS = ("lighting_kw", "ac_kw", "equipment_kw")  # must be >= 0


# ---- Small validation helpers ---------------------------------------------
def _to_number(value, field):
    """Convert a value to float or raise a clear ValueError."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number, got {value!r}")


def validate_text(value, field):
    """Text fields (id, name, building) must not be empty."""
    value = str(value).strip()
    if not value:
        raise ValueError(f"{field} cannot be empty")
    return value


def validate_area(value):
    """Room area must be strictly greater than zero."""
    area = _to_number(value, "area_m2")
    if area <= 0:
        raise ValueError(f"area_m2 must be greater than 0, got {area}")
    return area


def validate_power(value, field):
    """Power values (kW) must be zero or positive."""
    power = _to_number(value, field)
    if power < 0:
        raise ValueError(f"{field} must be non-negative, got {power}")
    return power


def validate_hours(value):
    """Operating hours must be between 0 and 24 (inclusive)."""
    low, high = HOURS_RANGE  # tuple unpacking
    hours = _to_number(value, "hours_per_day")
    if not low <= hours <= high:
        raise ValueError(f"hours_per_day must be between {low} and {high}, got {hours}")
    return hours


# ---- Room class -------------------------------------------------------------
class Room:
    """A room with its power loads (kW) and daily operating hours.

    Every attribute is validated when it is set, so a Room object can never
    hold invalid data (even after an update).
    """

    def __init__(self, room_id, room_name, building, area_m2,
                 lighting_kw, ac_kw, equipment_kw, hours_per_day):
        self.room_id = room_id
        self.room_name = room_name
        self.building = building
        self.area_m2 = area_m2
        self.lighting_kw = lighting_kw
        self.ac_kw = ac_kw
        self.equipment_kw = equipment_kw
        self.hours_per_day = hours_per_day

    # -- validated attributes (property setters run the checks) --
    @property
    def room_id(self):
        return self._room_id

    @room_id.setter
    def room_id(self, value):
        self._room_id = validate_text(value, "room_id").upper()

    @property
    def room_name(self):
        return self._room_name

    @room_name.setter
    def room_name(self, value):
        self._room_name = validate_text(value, "room_name")

    @property
    def building(self):
        return self._building

    @building.setter
    def building(self, value):
        self._building = validate_text(value, "building")

    @property
    def area_m2(self):
        return self._area_m2

    @area_m2.setter
    def area_m2(self, value):
        self._area_m2 = validate_area(value)

    @property
    def lighting_kw(self):
        return self._lighting_kw

    @lighting_kw.setter
    def lighting_kw(self, value):
        self._lighting_kw = validate_power(value, "lighting_kw")

    @property
    def ac_kw(self):
        return self._ac_kw

    @ac_kw.setter
    def ac_kw(self, value):
        self._ac_kw = validate_power(value, "ac_kw")

    @property
    def equipment_kw(self):
        return self._equipment_kw

    @equipment_kw.setter
    def equipment_kw(self, value):
        self._equipment_kw = validate_power(value, "equipment_kw")

    @property
    def hours_per_day(self):
        return self._hours_per_day

    @hours_per_day.setter
    def hours_per_day(self, value):
        self._hours_per_day = validate_hours(value)

    # -- calculations --
    def total_power_kw(self):
        """Sum of lighting, air-conditioning and equipment power (kW)."""
        return self.lighting_kw + self.ac_kw + self.equipment_kw

    def daily_energy_kwh(self):
        """Daily energy (kWh) = total power (kW) x operating hours."""
        return self.total_power_kw() * self.hours_per_day

    def energy_per_m2(self):
        """Daily energy per square metre (kWh/m2/day)."""
        return self.daily_energy_kwh() / self.area_m2

    # -- conversion helpers --
    def to_dict(self):
        """Return the room as a dictionary using the CSV column names."""
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "building": self.building,
            "area_m2": self.area_m2,
            "lighting_kw": self.lighting_kw,
            "ac_kw": self.ac_kw,
            "equipment_kw": self.equipment_kw,
            "hours_per_day": self.hours_per_day,
        }

    @classmethod
    def from_dict(cls, data):
        """Build a Room from a dictionary (e.g. one CSV row)."""
        return cls(**{key: data[key] for key in FIELDNAMES})

    def __str__(self):
        return (f"{self.room_id:<4} {self.room_name:<15} {self.building:<15} "
                f"{self.area_m2:>7.1f} m2  {self.total_power_kw():>5.1f} kW  "
                f"{self.hours_per_day:>4.1f} h")


# ---- Room manager -------------------------------------------------------------
class RoomManager:
    """Keeps all rooms in a dictionary {room_id: Room} and works on them."""

    def __init__(self):
        self.rooms = {}

    def __len__(self):
        return len(self.rooms)

    # -- add / list / search / update --
    def add_room(self, room):
        """Add a Room. Room IDs must be unique."""
        if room.room_id in self.rooms:
            raise ValueError(f"Room {room.room_id} already exists")
        self.rooms[room.room_id] = room

    def get_room(self, room_id):
        """Return the Room with this ID, or raise KeyError."""
        key = str(room_id).strip().upper()
        if key not in self.rooms:
            raise KeyError(f"Room {key} not found")
        return self.rooms[key]

    def list_rooms(self):
        """Return all rooms as a list, sorted by room ID."""
        return [self.rooms[key] for key in sorted(self.rooms)]

    def search(self, text):
        """Case-insensitive search in room ID, name and building."""
        text = str(text).strip().lower()
        results = []
        for room in self.list_rooms():
            if text in (room.room_id + " " + room.room_name + " " + room.building).lower():
                results.append(room)
        return results

    def update_room(self, room_id, **changes):
        """Update one or more fields of a room.

        The update is all-or-nothing: the changes are tried on a copy first,
        so an invalid value leaves the original room untouched.
        """
        room = self.get_room(room_id)
        allowed = set(FIELDNAMES) - {"room_id"}  # the ID cannot be changed
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Cannot update field(s): {', '.join(sorted(unknown))}")
        candidate = Room.from_dict({**room.to_dict(), **changes})  # validates
        self.rooms[room.room_id] = candidate
        return candidate

    # -- calculations --
    def energy_table(self):
        """List of tuples: (room_id, room_name, building, kWh/day, kWh/m2/day)."""
        return [
            (r.room_id, r.room_name, r.building, r.daily_energy_kwh(), r.energy_per_m2())
            for r in self.list_rooms()
        ]

    def total_daily_energy(self):
        """Total estimated daily energy of all rooms (kWh)."""
        return sum(r.daily_energy_kwh() for r in self.rooms.values())

    def buildings(self):
        """Set of distinct building names."""
        return {r.building for r in self.rooms.values()}

    def energy_by_building(self):
        """Dictionary {building: total daily kWh}."""
        totals = {}
        for room in self.rooms.values():
            totals[room.building] = totals.get(room.building, 0.0) + room.daily_energy_kwh()
        return totals

    # -- CSV storage --
    def save_csv(self, path):
        """Write all rooms to a CSV file."""
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            for room in self.list_rooms():
                writer.writerow(room.to_dict())

    def load_csv(self, path):
        """Load rooms from a CSV file, replacing the current rooms.

        Rows that fail validation are skipped; they are returned as a list of
        (line_number, error_message) tuples so the caller can report them.
        """
        loaded = {}
        skipped = []
        with open(path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            missing = set(FIELDNAMES) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV is missing column(s): {', '.join(sorted(missing))}")
            for line_no, row in enumerate(reader, start=2):  # line 1 is the header
                try:
                    room = Room.from_dict(row)
                    if room.room_id in loaded:
                        raise ValueError(f"duplicate room_id {room.room_id}")
                    loaded[room.room_id] = room
                except ValueError as error:
                    skipped.append((line_no, str(error)))
        self.rooms = loaded
        return skipped
