import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

processed_folder = Path(
    "data/processed"
)

gold_folder = Path(
    "data/processed/gold"
)

gold_folder.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# 2. Load integrated vehicle data
# ---------------------------------------------------------

print("Loading integrated vehicle data...")

vehicles = pd.read_csv(
    processed_folder / "vehicle_gtfs_integrated.csv",
    dtype={
        "vehicle_id": "string",
        "vehicle_label": "string",
        "route_id": "string",
        "stop_id": "string",
        "trip_id": "string",
        "route_short_name": "string",
        "route_long_name": "string",
        "stop_name": "string",
        "snapshot_file": "string",
        "route_match_status": "string",
        "trip_match_status": "string",
        "stop_match_status": "string",
        "integration_status": "string"
    },
    low_memory=False
)

print(
    f"Integrated records loaded: {len(vehicles):,}"
)


# ---------------------------------------------------------
# 3. Select fact table columns
# ---------------------------------------------------------

fact_vehicle_observation = vehicles[
    [
        "vehicle_id",
        "vehicle_label",
        "route_id",
        "stop_id",
        "trip_id",
        "latitude",
        "longitude",
        "bearing",
        "speed",
        "current_status",
        "current_stop_sequence",
        "direction_id",
        "occupancy_status",
        "revenue_status",
        "updated_at",
        "snapshot_timestamp",
        "route_match_status",
        "trip_match_status",
        "stop_match_status",
        "integration_status"
    ]
].copy()


# ---------------------------------------------------------
# 4. Create observation key
# ---------------------------------------------------------

fact_vehicle_observation.insert(
    0,
    "observation_key",
    range(
        1,
        len(fact_vehicle_observation) + 1
    )
)


# ---------------------------------------------------------
# 5. Standardize timestamps
# ---------------------------------------------------------

fact_vehicle_observation["updated_at"] = pd.to_datetime(
    fact_vehicle_observation["updated_at"],
    errors="coerce",
    utc=True
)

fact_vehicle_observation["snapshot_timestamp"] = pd.to_datetime(
    fact_vehicle_observation["snapshot_timestamp"],
    errors="coerce",
    utc=True
)


# ---------------------------------------------------------
# 6. Data quality checks
# ---------------------------------------------------------

print("\nFact table quality checks:")

print(
    "Duplicate observation keys:",
    fact_vehicle_observation["observation_key"].duplicated().sum()
)

print(
    "Missing vehicle IDs:",
    fact_vehicle_observation["vehicle_id"].isna().sum()
)

print(
    "Missing route IDs:",
    fact_vehicle_observation["route_id"].isna().sum()
)

print(
    "Missing snapshot timestamps:",
    fact_vehicle_observation["snapshot_timestamp"].isna().sum()
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
    fact_vehicle_observation["route_id"].notna()
    & ~fact_vehicle_observation["route_id"].isin(route_keys)
)

stop_missing = (
    fact_vehicle_observation["stop_id"].notna()
    & ~fact_vehicle_observation["stop_id"].isin(stop_keys)
)

trip_missing = (
    fact_vehicle_observation["trip_id"].notna()
    & ~fact_vehicle_observation["trip_id"].isin(trip_keys)
)


print(
    "Vehicle observations with invalid route:",
    route_missing.sum()
)

print(
    "Vehicle observations with invalid stop:",
    stop_missing.sum()
)

print(
    "Vehicle observations with invalid trip:",
    trip_missing.sum()
)


# ---------------------------------------------------------
# 8. Save fact table
# ---------------------------------------------------------

output_file = (
    gold_folder /
    "fact_vehicle_observation.csv"
)

fact_vehicle_observation.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------

print("\n========================================")
print("FACT VEHICLE OBSERVATION SUMMARY")
print("========================================")

print(
    f"Rows: {len(fact_vehicle_observation):,}"
)

print(
    f"Columns: {len(fact_vehicle_observation.columns)}"
)

print(
    f"Unique vehicles: "
    f"{fact_vehicle_observation['vehicle_id'].nunique():,}"
)

print(
    f"Unique routes: "
    f"{fact_vehicle_observation['route_id'].nunique():,}"
)

print(
    f"Unique trips: "
    f"{fact_vehicle_observation['trip_id'].nunique():,}"
)

print(
    f"Unique stops: "
    f"{fact_vehicle_observation['stop_id'].nunique():,}"
)

print(
    f"\nOutput: {output_file}"
)

print(
    "\nFact vehicle observation created successfully."
)