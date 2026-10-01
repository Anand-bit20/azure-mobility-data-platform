import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. Paths
# ---------------------------------------------------------

gold_folder = Path("data/processed/gold")


# ---------------------------------------------------------
# 2. Expected Gold tables
# ---------------------------------------------------------

expected_files = [
    "dim_route.csv",
    "dim_stop.csv",
    "dim_trip.csv",
    "dim_date.csv",
    "fact_vehicle_observation.csv",
    "fact_vehicle_movement.csv",
    "fact_schedule_performance.csv"
]


print("========================================")
print("GOLD LAYER VALIDATION")
print("========================================")


# ---------------------------------------------------------
# 3. Check files
# ---------------------------------------------------------

print("\n1. File existence")

all_files_exist = True

for filename in expected_files:

    file_path = gold_folder / filename

    exists = file_path.exists()

    print(
        f"{filename}:",
        "FOUND" if exists else "MISSING"
    )

    if not exists:
        all_files_exist = False


if not all_files_exist:
    raise FileNotFoundError(
        "One or more Gold tables are missing."
    )


# ---------------------------------------------------------
# 4. Load dimensions
# ---------------------------------------------------------

print("\n2. Loading dimensions")

dim_route = pd.read_csv(
    gold_folder / "dim_route.csv",
    dtype={"route_key": "string"},
    low_memory=False
)

dim_stop = pd.read_csv(
    gold_folder / "dim_stop.csv",
    dtype={"stop_key": "string"},
    low_memory=False
)

dim_trip = pd.read_csv(
    gold_folder / "dim_trip.csv",
    dtype={"trip_key": "string"},
    low_memory=False
)

dim_date = pd.read_csv(
    gold_folder / "dim_date.csv",
    low_memory=False
)


# ---------------------------------------------------------
# 5. Load facts
# ---------------------------------------------------------

print("Loading fact tables")

fact_observation = pd.read_csv(
    gold_folder / "fact_vehicle_observation.csv",
    dtype={
        "vehicle_id": "string",
        "route_id": "string",
        "stop_id": "string",
        "trip_id": "string"
    },
    low_memory=False
)

fact_movement = pd.read_csv(
    gold_folder / "fact_vehicle_movement.csv",
    dtype={
        "vehicle_id": "string",
        "route_id": "string"
    },
    low_memory=False
)

fact_schedule = pd.read_csv(
    gold_folder / "fact_schedule_performance.csv",
    dtype={
        "vehicle_id": "string",
        "route_id": "string",
        "trip_id": "string",
        "stop_id": "string",
        "schedule_status": "string"
    },
    low_memory=False
)


# ---------------------------------------------------------
# 6. Row counts
# ---------------------------------------------------------

print("\n3. Row counts")

print(
    f"dim_route:                 {len(dim_route):,}"
)

print(
    f"dim_stop:                  {len(dim_stop):,}"
)

print(
    f"dim_trip:                  {len(dim_trip):,}"
)

print(
    f"dim_date:                  {len(dim_date):,}"
)

print(
    f"fact_vehicle_observation:  {len(fact_observation):,}"
)

print(
    f"fact_vehicle_movement:     {len(fact_movement):,}"
)

print(
    f"fact_schedule_performance: {len(fact_schedule):,}"
)


# ---------------------------------------------------------
# 7. Dimension key validation
# ---------------------------------------------------------

print("\n4. Dimension key validation")

route_duplicates = (
    dim_route["route_key"].duplicated().sum()
)

stop_duplicates = (
    dim_stop["stop_key"].duplicated().sum()
)

trip_duplicates = (
    dim_trip["trip_key"].duplicated().sum()
)

date_duplicates = (
    dim_date["date_key"].duplicated().sum()
)


print(
    "Duplicate route keys:",
    route_duplicates
)

print(
    "Duplicate stop keys:",
    stop_duplicates
)

print(
    "Duplicate trip keys:",
    trip_duplicates
)

print(
    "Duplicate date keys:",
    date_duplicates
)


# ---------------------------------------------------------
# 8. Referential integrity
# ---------------------------------------------------------

print("\n5. Referential integrity")

route_keys = set(
    dim_route["route_key"].dropna()
)

stop_keys = set(
    dim_stop["stop_key"].dropna()
)

trip_keys = set(
    dim_trip["trip_key"].dropna()
)


# Vehicle observation

observation_invalid_routes = (
    fact_observation["route_id"].notna()
    & ~fact_observation["route_id"].isin(route_keys)
).sum()

observation_invalid_stops = (
    fact_observation["stop_id"].notna()
    & ~fact_observation["stop_id"].isin(stop_keys)
).sum()

observation_invalid_trips = (
    fact_observation["trip_id"].notna()
    & ~fact_observation["trip_id"].isin(trip_keys)
).sum()


# Movement

movement_invalid_routes = (
    fact_movement["route_id"].notna()
    & ~fact_movement["route_id"].isin(route_keys)
).sum()


# Schedule performance

schedule_invalid_routes = (
    fact_schedule["route_id"].notna()
    & ~fact_schedule["route_id"].isin(route_keys)
).sum()

schedule_invalid_stops = (
    fact_schedule["stop_id"].notna()
    & ~fact_schedule["stop_id"].isin(stop_keys)
).sum()

schedule_invalid_trips = (
    fact_schedule["trip_id"].notna()
    & ~fact_schedule["trip_id"].isin(trip_keys)
).sum()


print(
    "Observation invalid routes:",
    observation_invalid_routes
)

print(
    "Observation invalid stops:",
    observation_invalid_stops
)

print(
    "Observation invalid trips:",
    observation_invalid_trips
)

print(
    "Movement invalid routes:",
    movement_invalid_routes
)

print(
    "Schedule invalid routes:",
    schedule_invalid_routes
)

print(
    "Schedule invalid stops:",
    schedule_invalid_stops
)

print(
    "Schedule invalid trips:",
    schedule_invalid_trips
)


# ---------------------------------------------------------
# 9. Movement validation
# ---------------------------------------------------------

print("\n6. Movement validation")

movement_status_counts = (
    fact_movement["movement_status"]
    .value_counts()
)

print(
    movement_status_counts
)

negative_distance = (
    fact_movement["distance_km"] < 0
).sum()

negative_time = (
    fact_movement["time_difference_seconds"] < 0
).sum()

print(
    "Negative distances:",
    negative_distance
)

print(
    "Negative time differences:",
    negative_time
)


# ---------------------------------------------------------
# 10. Schedule validation
# ---------------------------------------------------------

print("\n7. Schedule validation")

schedule_status_counts = (
    fact_schedule["schedule_status"]
    .value_counts()
)

print(
    schedule_status_counts
)

print(
    "Missing arrival deviation:",
    fact_schedule[
        "arrival_deviation_minutes"
    ].isna().sum()
)


# ---------------------------------------------------------
# 11. Expected result checks
# ---------------------------------------------------------

print("\n8. Expected result checks")

expected_movement = {
    "VALID": 1040,
    "DATA_GAP": 328,
    "STATIONARY": 98
}

expected_schedule = {
    "ON_TIME": 1153,
    "DELAYED": 557,
    "EARLY": 237
}


movement_check = all(
    movement_status_counts.get(
        status,
        0
    ) == count
    for status, count in expected_movement.items()
)


schedule_check = all(
    schedule_status_counts.get(
        status,
        0
    ) == count
    for status, count in expected_schedule.items()
)


print(
    "Movement status totals:",
    "PASS" if movement_check else "FAIL"
)

print(
    "Schedule status totals:",
    "PASS" if schedule_check else "FAIL"
)


# ---------------------------------------------------------
# 12. Overall validation
# ---------------------------------------------------------

validation_passed = (
    all_files_exist
    and route_duplicates == 0
    and stop_duplicates == 0
    and trip_duplicates == 0
    and date_duplicates == 0
    and observation_invalid_routes == 0
    and observation_invalid_stops == 0
    and movement_invalid_routes == 0
    and schedule_invalid_routes == 0
    and schedule_invalid_stops == 0
    and schedule_invalid_trips == 0
    and negative_distance == 0
    and negative_time == 0
    and movement_check
    and schedule_check
)


print("\n========================================")

if validation_passed:
    print("GOLD LAYER VALIDATION: PASSED")
else:
    print("GOLD LAYER VALIDATION: FAILED")

print("========================================")