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
# 2. Load movement analytics
# ---------------------------------------------------------

print("Loading vehicle movement data...")

movement = pd.read_csv(
    processed_folder / "vehicle_movement.csv",
    dtype={
        "vehicle_id": "string",
        "route_id": "string",
        "movement_status": "string"
    },
    low_memory=False
)

print(
    f"Movement records loaded: {len(movement):,}"
)


# ---------------------------------------------------------
# 3. Select Gold fact columns
# ---------------------------------------------------------

fact_vehicle_movement = movement[
    [
        "vehicle_id",
        "route_id",
        "snapshot_timestamp",
        "previous_snapshot_timestamp",
        "latitude",
        "longitude",
        "previous_latitude",
        "previous_longitude",
        "distance_km",
        "time_difference_seconds",
        "calculated_speed_kmh",
        "movement_status"
    ]
].copy()


# ---------------------------------------------------------
# 4. Create movement key
# ---------------------------------------------------------

fact_vehicle_movement.insert(
    0,
    "movement_key",
    range(
        1,
        len(fact_vehicle_movement) + 1
    )
)


# ---------------------------------------------------------
# 5. Standardize timestamps
# ---------------------------------------------------------

fact_vehicle_movement["snapshot_timestamp"] = pd.to_datetime(
    fact_vehicle_movement["snapshot_timestamp"],
    errors="coerce",
    utc=True
)

fact_vehicle_movement["previous_snapshot_timestamp"] = pd.to_datetime(
    fact_vehicle_movement["previous_snapshot_timestamp"],
    errors="coerce",
    utc=True
)


# ---------------------------------------------------------
# 6. Data quality checks
# ---------------------------------------------------------

print("\nFact table quality checks:")

print(
    "Duplicate movement keys:",
    fact_vehicle_movement["movement_key"].duplicated().sum()
)

print(
    "Missing vehicle IDs:",
    fact_vehicle_movement["vehicle_id"].isna().sum()
)

print(
    "Missing route IDs:",
    fact_vehicle_movement["route_id"].isna().sum()
)

print(
    "Missing snapshot timestamps:",
    fact_vehicle_movement["snapshot_timestamp"].isna().sum()
)

print(
    "Negative distances:",
    (
        fact_vehicle_movement["distance_km"] < 0
    ).sum()
)

print(
    "Negative time differences:",
    (
        fact_vehicle_movement["time_difference_seconds"] < 0
    ).sum()
)


# ---------------------------------------------------------
# 7. Referential integrity — Route
# ---------------------------------------------------------

dim_route = pd.read_csv(
    gold_folder / "dim_route.csv",
    dtype={"route_key": "string"},
    usecols=["route_key"]
)

route_keys = set(
    dim_route["route_key"].dropna()
)

route_missing = (
    fact_vehicle_movement["route_id"].notna()
    & ~fact_vehicle_movement["route_id"].isin(route_keys)
)

print(
    "Movement records with invalid route:",
    route_missing.sum()
)


# ---------------------------------------------------------
# 8. Movement status summary
# ---------------------------------------------------------

print("\nMovement status:")

print(
    fact_vehicle_movement["movement_status"]
    .value_counts(dropna=False)
)


# ---------------------------------------------------------
# 9. Save Gold fact
# ---------------------------------------------------------

output_file = (
    gold_folder /
    "fact_vehicle_movement.csv"
)

fact_vehicle_movement.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 10. Final summary
# ---------------------------------------------------------

print("\n========================================")
print("FACT VEHICLE MOVEMENT SUMMARY")
print("========================================")

print(
    f"Rows: {len(fact_vehicle_movement):,}"
)

print(
    f"Columns: {len(fact_vehicle_movement.columns)}"
)

print(
    f"Unique vehicles: "
    f"{fact_vehicle_movement['vehicle_id'].nunique():,}"
)

print(
    f"Unique routes: "
    f"{fact_vehicle_movement['route_id'].nunique():,}"
)

print(
    f"Total distance: "
    f"{fact_vehicle_movement['distance_km'].sum():,.2f} km"
)

print(
    f"\nOutput: {output_file}"
)

print(
    "\nFact vehicle movement created successfully."
)