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
    f"Live records: {len(vehicles):,}"
)


# ---------------------------------------------------------
# 3. Keep records with matched trips and stops
# ---------------------------------------------------------

eligible = vehicles[
    (vehicles["trip_match_status"] == "MATCHED")
    & (vehicles["stop_match_status"] == "MATCHED")
].copy()

print(
    f"Records with matched trip + stop: {len(eligible):,}"
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
# 5. Create unique trip + stop combinations
# ---------------------------------------------------------

schedule_keys = schedule[
    [
        "trip_id",
        "stop_id"
    ]
].drop_duplicates()


# ---------------------------------------------------------
# 6. Validate live trip + stop combinations
# ---------------------------------------------------------

matches = eligible[
    [
        "vehicle_id",
        "route_id",
        "trip_id",
        "stop_id"
    ]
].merge(
    schedule_keys,
    on=[
        "trip_id",
        "stop_id"
    ],
    how="left",
    indicator="_schedule_match"
)


# ---------------------------------------------------------
# 7. Determine match status
# ---------------------------------------------------------

matches["schedule_match_status"] = (
    matches["_schedule_match"]
    .map({
        "both": "MATCHED",
        "left_only": "UNMATCHED"
    })
)

matches = matches.drop(
    columns=["_schedule_match"]
)


# ---------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------

print("\n========================================")
print("LIVE + SCHEDULE MATCH VALIDATION")
print("========================================")

print(
    f"Eligible live records: {len(eligible):,}"
)

print(
    "\nSchedule matching:"
)

print(
    matches["schedule_match_status"]
    .value_counts()
)

matched_count = (
    matches["schedule_match_status"]
    == "MATCHED"
).sum()

coverage = (
    matched_count / len(matches) * 100
    if len(matches) > 0
    else 0
)

print(
    f"\nSchedule match coverage: {coverage:.2f}%"
)


# ---------------------------------------------------------
# 9. Show unmatched combinations
# ---------------------------------------------------------

unmatched = matches[
    matches["schedule_match_status"] == "UNMATCHED"
]

print(
    f"\nUnmatched combinations: {len(unmatched):,}"
)

if not unmatched.empty:
    print("\nSample unmatched records:")

    print(
        unmatched[
            [
                "vehicle_id",
                "route_id",
                "trip_id",
                "stop_id"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


print(
    "\nLive + schedule match validation completed."
)