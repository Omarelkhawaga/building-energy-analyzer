"""
Module 2 - Consumption and Cost Analysis
========================================
Reads the daily readings CSV (room_id, date, actual_kwh), cleans it with
pandas, merges it with the room data produced by Module 1, and calculates
consumption and cost per room, building and month.  NumPy is used for the
air-conditioning reduction scenario, and Matplotlib for the four charts.
"""

import os

import matplotlib
matplotlib.use("Agg")  # draw charts to files (works without a display window)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DAYS_PER_MONTH = 30  # used only to turn the daily AC saving into a monthly figure


# ---------------------------------------------------------------------------
# 1. Reading and cleaning
# ---------------------------------------------------------------------------
def load_readings(path):
    """Read the readings CSV into a DataFrame."""
    return pd.read_csv(path)


def clean_readings(readings, valid_room_ids):
    """Clean the raw readings and return (clean_dataframe, report_dictionary).

    Steps:
      1. convert dates; drop rows whose date is invalid
      2. drop rows whose room_id is not in the room list (set lookup)
      3. remove duplicate (room_id, date) rows
      4. treat negative kWh as invalid (set to missing)
      5. fill missing kWh with the average of the same room on the same type
         of day (weekday / weekend); fall back to the room average
    """
    df = readings.copy()
    report = {"rows_in": len(df)}

    df["room_id"] = df["room_id"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["actual_kwh"] = pd.to_numeric(df["actual_kwh"], errors="coerce")

    report["invalid_dates_dropped"] = int(df["date"].isna().sum())
    df = df.dropna(subset=["date"])

    known = set(valid_room_ids)  # a set gives fast membership tests
    unknown_mask = ~df["room_id"].isin(known)
    report["unknown_rooms_dropped"] = int(unknown_mask.sum())
    df = df[~unknown_mask]

    report["duplicates_removed"] = int(df.duplicated(subset=["room_id", "date"]).sum())
    df = df.drop_duplicates(subset=["room_id", "date"], keep="first")

    negative = df["actual_kwh"] < 0
    report["negative_values_set_missing"] = int(negative.sum())
    df.loc[negative, "actual_kwh"] = np.nan

    report["missing_values_found"] = int(df["actual_kwh"].isna().sum())
    df["day_type"] = np.where(df["date"].dt.dayofweek >= 5, "weekend", "weekday")
    same_day_type_mean = df.groupby(["room_id", "day_type"])["actual_kwh"].transform("mean")
    room_mean = df.groupby("room_id")["actual_kwh"].transform("mean")
    df["actual_kwh"] = df["actual_kwh"].fillna(same_day_type_mean).fillna(room_mean)
    report["missing_values_left"] = int(df["actual_kwh"].isna().sum())

    df = df.sort_values(["room_id", "date"]).reset_index(drop=True)
    report["rows_out"] = len(df)
    return df, report


# ---------------------------------------------------------------------------
# 2. Merging and cost
# ---------------------------------------------------------------------------
def load_rooms(path):
    """Read the rooms CSV (saved by Module 1) and add the estimated daily kWh."""
    rooms = pd.read_csv(path)
    rooms["room_id"] = rooms["room_id"].astype(str).str.strip().str.upper()
    total_kw = rooms["lighting_kw"] + rooms["ac_kw"] + rooms["equipment_kw"]
    rooms["estimated_daily_kwh"] = total_kw * rooms["hours_per_day"]
    return rooms


def merge_data(clean, rooms):
    """Merge readings with room data (one row per room per day)."""
    merged = clean.merge(rooms, on="room_id", how="left", validate="many_to_one")
    merged["month"] = merged["date"].dt.to_period("M").astype(str)
    return merged


def add_cost(merged, price_per_kwh):
    """Add a cost column = actual kWh x price per kWh."""
    if price_per_kwh < 0:
        raise ValueError("price per kWh must be non-negative")
    out = merged.copy()
    out["cost"] = out["actual_kwh"] * price_per_kwh
    return out


def summarize(merged, by):
    """Total kWh, average daily kWh and total cost grouped by one or more columns."""
    summary = (
        merged.groupby(by)
        .agg(
            days=("date", "nunique"),
            total_kwh=("actual_kwh", "sum"),
            avg_daily_kwh=("actual_kwh", "mean"),
            total_cost=("cost", "sum"),
        )
        .round(2)
        .reset_index()
    )
    return summary


def room_comparison(merged, rooms):
    """Per-room table: actual vs estimated consumption and consumption per m2."""
    summary = summarize(merged, ["room_id", "room_name", "building"])
    info = rooms[["room_id", "area_m2", "estimated_daily_kwh"]]
    table = summary.merge(info, on="room_id")
    table["estimated_total_kwh"] = (table["estimated_daily_kwh"] * table["days"]).round(2)
    table["actual_vs_estimated_pct"] = (
        table["total_kwh"] / table["estimated_total_kwh"] * 100
    ).round(1)
    table["actual_kwh_per_m2_day"] = (table["avg_daily_kwh"] / table["area_m2"]).round(3)
    return table


# ---------------------------------------------------------------------------
# 3. NumPy: air-conditioning reduction scenario
# ---------------------------------------------------------------------------
def ac_reduction_scenario(rooms, reduction_pct, price_per_kwh=0.0):
    """Estimated daily kWh before and after reducing AC power by reduction_pct %.

    Operating hours and lighting / equipment power stay unchanged.
    """
    if not 0 <= reduction_pct <= 100:
        raise ValueError("reduction percentage must be between 0 and 100")

    lighting = rooms["lighting_kw"].to_numpy(dtype=float)
    ac = rooms["ac_kw"].to_numpy(dtype=float)
    equipment = rooms["equipment_kw"].to_numpy(dtype=float)
    hours = rooms["hours_per_day"].to_numpy(dtype=float)

    ac_after = ac * (1 - reduction_pct / 100)           # vectorised: whole array at once
    before = (lighting + ac + equipment) * hours
    after = (lighting + ac_after + equipment) * hours
    saving = before - after
    saving_pct = np.divide(saving, before, out=np.zeros_like(saving), where=before > 0) * 100

    result = rooms[["room_id", "room_name", "building"]].copy()
    result["ac_kw_before"] = ac
    result["ac_kw_after"] = ac_after.round(3)
    result["daily_kwh_before"] = before.round(2)
    result["daily_kwh_after"] = after.round(2)
    result["daily_saving_kwh"] = saving.round(2)
    result["saving_pct"] = saving_pct.round(1)
    result["monthly_saving_cost"] = (saving * DAYS_PER_MONTH * price_per_kwh).round(2)

    totals = {
        "before_kwh": float(before.sum()),
        "after_kwh": float(after.sum()),
        "saving_kwh": float(saving.sum()),
        "saving_pct": float(saving.sum() / before.sum() * 100) if before.sum() else 0.0,
        "reduction_pct": reduction_pct,
    }
    return result, totals


# ---------------------------------------------------------------------------
# 4. Charts (line, bar, scatter, histogram)
# ---------------------------------------------------------------------------
def _save(fig, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def chart_line(merged, path=None):
    """Line chart: total daily actual consumption of each building."""
    daily = merged.groupby(["date", "building"])["actual_kwh"].sum().unstack()
    fig, ax = plt.subplots(figsize=(10, 5))
    for building in daily.columns:
        ax.plot(daily.index, daily[building], label=building)
    ax.set_title("Daily Actual Energy Consumption per Building")
    ax.set_xlabel("Date")
    ax.set_ylabel("Energy consumption (kWh/day)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    return _save(fig, path) if path else fig


def chart_bar(comparison, path=None):
    """Bar chart: actual vs estimated total consumption of each room."""
    x = np.arange(len(comparison))
    width = 0.4
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, comparison["total_kwh"], width, label="Actual (readings)")
    ax.bar(x + width / 2, comparison["estimated_total_kwh"], width, label="Estimated (formula)")
    ax.set_xticks(x)
    ax.set_xticklabels(comparison["room_name"], rotation=30, ha="right")
    ax.set_title("Actual vs Estimated Total Consumption per Room (Aug-Sep 2026)")
    ax.set_xlabel("Room")
    ax.set_ylabel("Total energy (kWh)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, path) if path else fig


def chart_scatter(comparison, path=None):
    """Scatter: estimated daily kWh vs average actual daily kWh (one point per room)."""
    fig, ax = plt.subplots(figsize=(7, 6))
    for building, group in comparison.groupby("building"):
        ax.scatter(group["estimated_daily_kwh"], group["avg_daily_kwh"], s=80, label=building)
    # staggered label offsets (in points) so labels of nearby rooms do not overlap
    offsets = [(8, 6), (8, -14), (-30, 6), (8, 6), (-32, -14), (-32, 6)]
    for i, (_, row) in enumerate(comparison.iterrows()):
        ax.annotate(row["room_id"], (row["estimated_daily_kwh"], row["avg_daily_kwh"]),
                    textcoords="offset points", xytext=offsets[i % len(offsets)])
    top = max(comparison["estimated_daily_kwh"].max(), comparison["avg_daily_kwh"].max()) * 1.05
    ax.plot([0, top], [0, top], "k--", alpha=0.5, label="Actual = Estimated")
    ax.set_title("Estimated vs Actual Average Daily Consumption")
    ax.set_xlabel("Estimated daily energy (kWh/day)")
    ax.set_ylabel("Average actual daily energy (kWh/day)")
    ax.legend()
    ax.grid(alpha=0.3)
    return _save(fig, path) if path else fig


def chart_histogram(merged, path=None):
    """Histogram: distribution of all daily actual readings."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(merged["actual_kwh"], bins=20, edgecolor="black")
    ax.set_title("Distribution of Daily Actual Energy Readings (all rooms)")
    ax.set_xlabel("Daily energy consumption (kWh/day)")
    ax.set_ylabel("Number of daily readings")
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, path) if path else fig


def make_all_charts(merged, comparison, folder="charts"):
    """Create the four charts and return the list of PNG paths."""
    paths = [
        os.path.join(folder, "1_line_daily_consumption.png"),
        os.path.join(folder, "2_bar_actual_vs_estimated.png"),
        os.path.join(folder, "3_scatter_estimated_vs_actual.png"),
        os.path.join(folder, "4_histogram_daily_readings.png"),
    ]
    chart_line(merged, paths[0])
    chart_bar(comparison, paths[1])
    chart_scatter(comparison, paths[2])
    chart_histogram(merged, paths[3])
    plt.close("all")
    return paths


# ---------------------------------------------------------------------------
# 5. Report export
# ---------------------------------------------------------------------------
def export_reports(merged, comparison, ac_result, folder="reports"):
    """Write the report CSV files and return the list of file paths."""
    os.makedirs(folder, exist_ok=True)
    reports = {
        "cleaned_merged_readings.csv": merged,
        "report_by_room.csv": comparison,
        "report_by_building.csv": summarize(merged, ["building"]),
        "report_by_month.csv": summarize(merged, ["month"]),
        "report_by_building_month.csv": summarize(merged, ["building", "month"]),
        "report_ac_reduction.csv": ac_result,
    }
    paths = []
    for name, frame in reports.items():
        path = os.path.join(folder, name)
        frame.to_csv(path, index=False)
        paths.append(path)
    return paths
