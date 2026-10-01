import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

vehicle_file = Path(
    "data/processed/vehicle_gtfs_integrated.csv"
)

schedule_file = Path(
    "data/processed/schedule_reference.csv"
)

output_folder = Path(
    "data/processed"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

output_file = (
    output_folder
    / "schedule_performance.csv"
)


# ---------------------------------------------------------
# 2. Load integrated vehicle data
# ---------------------------------------------------------

print("Loading integrated vehicle data...")

vehicles = pd.read_csv(
    vehicle_file,
    dtype={
        "vehicle_id": "string",
        "route_id": "string",
        "trip_id": "string",
        "stop_id": "string"
    },
    low_memory=False
)

print(
    f"Live vehicle records: {len(vehicles):,}"
)


# ---------------------------------------------------------
# 3. Keep records with valid trip + stop matches
# ---------------------------------------------------------

vehicles = vehicles[
    (vehicles["trip_match_status"] == "MATCHED")
    & (vehicles["stop_match_status"] == "MATCHED")
].copy()

print(
    f"Records with matched trip + stop: {len(vehicles):,}"
)


# ---------------------------------------------------------
# 4. Load schedule reference
# ---------------------------------------------------------

print("\nLoading schedule reference...")

schedule = pd.read_csv(
    schedule_file,
    dtype={
        "trip_id": "string",
        "route_id": "string",
        "stop_id": "string"
    },
    low_memory=False
)

print(
    f"Schedule records: {len(schedule):,}"
)


# ---------------------------------------------------------
# 5. Join live vehicles to scheduled stop times
# ---------------------------------------------------------

performance = vehicles.merge(
    schedule[
        [
            "trip_id",
            "route_id",
            "stop_id",
            "stop_sequence",
            "arrival_time",
            "departure_time",
            "arrival_seconds",
            "departure_seconds"
        ]
    ],
    on=[
        "trip_id",
        "route_id",
        "stop_id"
    ],
    how="inner"
)

print(
    f"Schedule-matched records: {len(performance):,}"
)


# ---------------------------------------------------------
# 6. Convert live timestamp to UTC
# ---------------------------------------------------------

performance["updated_at"] = pd.to_datetime(
    performance["updated_at"],
    errors="coerce",
    utc=True
)

performance["snapshot_timestamp"] = pd.to_datetime(
    performance["snapshot_timestamp"],
    errors="coerce",
    utc=True
)


# ---------------------------------------------------------
# 7. Determine the local date of the live observation
# ---------------------------------------------------------

# MBTA operates in America/New_York.
performance["local_observation_time"] = (
    performance["updated_at"]
    .dt.tz_convert("America/New_York")
)

performance["observation_date"] = (
    performance["local_observation_time"]
    .dt.date
)


# ---------------------------------------------------------
# 8. Convert GTFS seconds to scheduled datetime
# ---------------------------------------------------------

# GTFS times can exceed 24 hours.
# We therefore calculate the scheduled datetime
# from the observation date plus GTFS seconds.

performance["scheduled_arrival_datetime"] = (
    pd.to_datetime(
        performance["observation_date"].astype(str)
    )
    + pd.to_timedelta(
        performance["arrival_seconds"],
        unit="s"
    )
)

performance["scheduled_departure_datetime"] = (
    pd.to_datetime(
        performance["observation_date"].astype(str)
    )
    + pd.to_timedelta(
        performance["departure_seconds"],
        unit="s"
    )
)


# ---------------------------------------------------------
# 9. Localize scheduled timestamps
# ---------------------------------------------------------

performance["scheduled_arrival_datetime"] = (
    performance["scheduled_arrival_datetime"]
    .dt.tz_localize(
        "America/New_York",
        ambiguous="NaT",
        nonexistent="shift_forward"
    )
)

performance["scheduled_departure_datetime"] = (
    performance["scheduled_departure_datetime"]
    .dt.tz_localize(
        "America/New_York",
        ambiguous="NaT",
        nonexistent="shift_forward"
    )
)


# ---------------------------------------------------------
# 10. Calculate schedule deviation
# ---------------------------------------------------------

performance["arrival_deviation_minutes"] = (
    (
        performance["local_observation_time"]
        - performance["scheduled_arrival_datetime"]
    )
    .dt.total_seconds()
    / 60
)


performance["departure_deviation_minutes"] = (
    (
        performance["local_observation_time"]
        - performance["scheduled_departure_datetime"]
    )
    .dt.total_seconds()
    / 60
)


# ---------------------------------------------------------
# 11. Classify schedule performance
# ---------------------------------------------------------

# Thresholds:
# <= -5 minutes  = EARLY
# -5 to +5       = ON_TIME
# > +5 minutes   = DELAYED

performance["schedule_status"] = "ON_TIME"

performance.loc[
    performance["arrival_deviation_minutes"] < -5,
    "schedule_status"
] = "EARLY"

performance.loc[
    performance["arrival_deviation_minutes"] > 5,
    "schedule_status"
] = "DELAYED"


# ---------------------------------------------------------
# 12. Data quality validation
# ---------------------------------------------------------

print("\nSchedule performance quality checks:")

print(
    "Missing live timestamps:",
    performance["local_observation_time"].isna().sum()
)

print(
    "Missing scheduled arrival:",
    performance["scheduled_arrival_datetime"].isna().sum()
)

print(
    "Missing scheduled departure:",
    performance["scheduled_departure_datetime"].isna().sum()
)

print(
    "Missing arrival deviation:",
    performance["arrival_deviation_minutes"].isna().sum()
)


# ---------------------------------------------------------
# 13. Save output
# ---------------------------------------------------------

performance.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 14. Summary
# ---------------------------------------------------------

print("\n========================================")
print("SCHEDULE PERFORMANCE SUMMARY")
print("========================================")

print(
    f"Schedule-matched records: {len(performance):,}"
)

print(
    "\nSchedule status:"
)

print(
    performance["schedule_status"]
    .value_counts()
)


print(
    "\nArrival deviation statistics (minutes):"
)

print(
    performance["arrival_deviation_minutes"]
    .describe()
)


print(
    "\nAverage arrival deviation:",
    round(
        performance[
            "arrival_deviation_minutes"
        ].mean(),
        2
    ),
    "minutes"
)


print(
    "\nMaximum arrival deviation:",
    round(
        performance[
            "arrival_deviation_minutes"
        ].max(),
        2
    ),
    "minutes"
)


print(
    "\nMinimum arrival deviation:",
    round(
        performance[
            "arrival_deviation_minutes"
        ].min(),
        2
    ),
    "minutes"
)


print(
    f"\nOutput file: {output_file}"
)

print(
    "\nSchedule performance calculation completed."
)