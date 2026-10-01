import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

gtfs_folder = Path("data/processed/gtfs")
output_folder = Path("data/processed")

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

stop_times_file = gtfs_folder / "stop_times_clean.csv"
trips_file = gtfs_folder / "trips_clean.csv"

output_file = (
    output_folder
    / "schedule_reference.csv"
)


# ---------------------------------------------------------
# 2. Load GTFS trips
# ---------------------------------------------------------

print("Loading GTFS trips...")

trips = pd.read_csv(
    trips_file,
    dtype={
        "trip_id": "string",
        "route_id": "string",
        "service_id": "string",
        "trip_headsign": "string",
        "shape_id": "string",
        "route_pattern_id": "string"
    },
    low_memory=False
)

print(
    f"Trips loaded: {len(trips):,}"
)


# ---------------------------------------------------------
# 3. Load GTFS stop times
# ---------------------------------------------------------

print("\nLoading GTFS stop times...")

stop_times = pd.read_csv(
    stop_times_file,
    dtype={
        "trip_id": "string",
        "stop_id": "string",
        "stop_sequence": "Int64",
        "stop_headsign": "string",
        "pickup_type": "Int64",
        "drop_off_type": "Int64",
        "timepoint": "Int64"
    },
    low_memory=False
)

print(
    f"Stop time records: {len(stop_times):,}"
)


# ---------------------------------------------------------
# 4. Keep required schedule fields
# ---------------------------------------------------------

schedule = stop_times[
    [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence"
    ]
].copy()


# ---------------------------------------------------------
# 5. Add route information
# ---------------------------------------------------------

schedule = schedule.merge(
    trips[
        [
            "trip_id",
            "route_id",
            "service_id",
            "trip_headsign",
            "direction_id",
            "shape_id",
            "route_pattern_id"
        ]
    ],
    on="trip_id",
    how="left"
)


# ---------------------------------------------------------
# 6. Standardize schedule time fields
# ---------------------------------------------------------

# GTFS allows times beyond 24:00:00.
# Therefore we keep the original GTFS time and
# convert it into seconds after midnight.

def gtfs_time_to_seconds(value):
    if pd.isna(value):
        return pd.NA

    try:
        parts = str(value).split(":")

        if len(parts) != 3:
            return pd.NA

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])

        return (
            hours * 3600
            + minutes * 60
            + seconds
        )

    except (ValueError, TypeError):
        return pd.NA


schedule["arrival_seconds"] = (
    schedule["arrival_time"]
    .apply(gtfs_time_to_seconds)
    .astype("Int64")
)

schedule["departure_seconds"] = (
    schedule["departure_time"]
    .apply(gtfs_time_to_seconds)
    .astype("Int64")
)


# ---------------------------------------------------------
# 7. Data quality checks
# ---------------------------------------------------------

print("\nSchedule quality checks:")

print(
    "Missing arrival times:",
    schedule["arrival_seconds"].isna().sum()
)

print(
    "Missing departure times:",
    schedule["departure_seconds"].isna().sum()
)

print(
    "Missing route IDs:",
    schedule["route_id"].isna().sum()
)

print(
    "Missing stop IDs:",
    schedule["stop_id"].isna().sum()
)

print(
    "Missing trip IDs:",
    schedule["trip_id"].isna().sum()
)


# ---------------------------------------------------------
# 8. Save schedule reference
# ---------------------------------------------------------

schedule.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------

print("\n========================================")
print("SCHEDULE REFERENCE SUMMARY")
print("========================================")

print(
    f"Schedule records: {len(schedule):,}"
)

print(
    f"Unique trips: {schedule['trip_id'].nunique():,}"
)

print(
    f"Unique routes: {schedule['route_id'].nunique():,}"
)

print(
    f"Unique stops: {schedule['stop_id'].nunique():,}"
)

print(
    f"Output file: {output_file}"
)

print(
    "\nSchedule reference preparation completed."
)