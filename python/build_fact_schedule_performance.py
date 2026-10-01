import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

processed_folder = Path("data/processed")
gold_folder = Path("data/processed/gold")

gold_folder.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# 2. Load schedule performance data
# ---------------------------------------------------------

print("Loading schedule performance data...")

performance = pd.read_csv(
    processed_folder / "schedule_performance.csv",
    dtype={
        "vehicle_id": "string",
        "route_id": "string",
        "trip_id": "string",
        "stop_id": "string",
        "schedule_status": "string"
    },
    low_memory=False
)

print(
    f"Schedule performance records loaded: {len(performance):,}"
)


# ---------------------------------------------------------
# 3. Select Gold fact columns
# ---------------------------------------------------------

fact_schedule_performance = performance[
    [
        "vehicle_id",
        "route_id",
        "trip_id",
        "stop_id",
        "snapshot_timestamp",
        "local_observation_time",
        "scheduled_arrival_datetime",
        "scheduled_departure_datetime",
        "arrival_deviation_minutes",
        "departure_deviation_minutes",
        "schedule_status"
    ]
].copy()


# ---------------------------------------------------------
# 4. Create performance key
# ---------------------------------------------------------

fact_schedule_performance.insert(
    0,
    "performance_key",
    range(
        1,
        len(fact_schedule_performance) + 1
    )
)


# ---------------------------------------------------------
# 5. Standardize timestamps
# ---------------------------------------------------------

timestamp_columns = [
    "snapshot_timestamp",
    "local_observation_time",
    "scheduled_arrival_datetime",
    "scheduled_departure_datetime"
]

for column in timestamp_columns:

    fact_schedule_performance[column] = pd.to_datetime(
        fact_schedule_performance[column],
        errors="coerce",
        utc=True
    )


# ---------------------------------------------------------
# 6. Data quality checks
# ---------------------------------------------------------

print("\nFact table quality checks:")

print(
    "Duplicate performance keys:",
    fact_schedule_performance[
        "performance_key"
    ].duplicated().sum()
)

print(
    "Missing vehicle IDs:",
    fact_schedule_performance[
        "vehicle_id"
    ].isna().sum()
)

print(
    "Missing route IDs:",
    fact_schedule_performance[
        "route_id"
    ].isna().sum()
)

print(
    "Missing trip IDs:",
    fact_schedule_performance[
        "trip_id"
    ].isna().sum()
)

print(
    "Missing stop IDs:",
    fact_schedule_performance[
        "stop_id"
    ].isna().sum()
)

print(
    "Missing observation timestamps:",
    fact_schedule_performance[
        "local_observation_time"
    ].isna().sum()
)

print(
    "Missing arrival deviations:",
    fact_schedule_performance[
        "arrival_deviation_minutes"
    ].isna().sum()
)


# ---------------------------------------------------------
# 7. Referential integrity checks
# ---------------------------------------------------------

dim_route = pd.read_csv(
    gold_folder / "dim_route.csv",
    dtype={"route_key": "string"},
    usecols=["route_key"]
)

dim_stop = pd.read_csv(
    gold_folder / "dim_stop.csv",
    dtype={"stop_key": "string"},
    usecols=["stop_key"]
)

dim_trip = pd.read_csv(
    gold_folder / "dim_trip.csv",
    dtype={"trip_key": "string"},
    usecols=["trip_key"]
)


route_keys = set(
    dim_route["route_key"].dropna()
)

stop_keys = set(
    dim_stop["stop_key"].dropna()
)

trip_keys = set(
    dim_trip["trip_key"].dropna()
)


route_missing = (
    fact_schedule_performance["route_id"].notna()
    & ~fact_schedule_performance["route_id"].isin(route_keys)
)

stop_missing = (
    fact_schedule_performance["stop_id"].notna()
    & ~fact_schedule_performance["stop_id"].isin(stop_keys)
)

trip_missing = (
    fact_schedule_performance["trip_id"].notna()
    & ~fact_schedule_performance["trip_id"].isin(trip_keys)
)


print(
    "Records with invalid route:",
    route_missing.sum()
)

print(
    "Records with invalid stop:",
    stop_missing.sum()
)

print(
    "Records with invalid trip:",
    trip_missing.sum()
)


# ---------------------------------------------------------
# 8. Schedule status summary
# ---------------------------------------------------------

print("\nSchedule status:")

print(
    fact_schedule_performance[
        "schedule_status"
    ].value_counts(dropna=False)
)


# ---------------------------------------------------------
# 9. Deviation summary
# ---------------------------------------------------------

print("\nArrival deviation summary:")

print(
    fact_schedule_performance[
        "arrival_deviation_minutes"
    ].describe()
)


# ---------------------------------------------------------
# 10. Save Gold fact
# ---------------------------------------------------------

output_file = (
    gold_folder /
    "fact_schedule_performance.csv"
)

fact_schedule_performance.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 11. Final summary
# ---------------------------------------------------------

print("\n========================================")
print("FACT SCHEDULE PERFORMANCE SUMMARY")
print("========================================")

print(
    f"Rows: {len(fact_schedule_performance):,}"
)

print(
    f"Columns: {len(fact_schedule_performance.columns)}"
)

print(
    f"Unique vehicles: "
    f"{fact_schedule_performance['vehicle_id'].nunique():,}"
)

print(
    f"Unique routes: "
    f"{fact_schedule_performance['route_id'].nunique():,}"
)

print(
    f"Unique trips: "
    f"{fact_schedule_performance['trip_id'].nunique():,}"
)

print(
    f"Unique stops: "
    f"{fact_schedule_performance['stop_id'].nunique():,}"
)

print(
    f"\nOutput: {output_file}"
)

print(
    "\nFact schedule performance created successfully."
)