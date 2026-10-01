import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

vehicle_file = Path(
    "data/processed/vehicle_positions_clean.csv"
)

gtfs_folder = Path(
    "data/processed/gtfs"
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
    / "vehicle_gtfs_integrated.csv"
)


# ---------------------------------------------------------
# 2. Load live vehicle data
# ---------------------------------------------------------

print("Loading live vehicle data...")

vehicles = pd.read_csv(
    vehicle_file,
    dtype={
        "vehicle_id": "string",
        "vehicle_label": "string",
        "route_id": "string",
        "stop_id": "string",
        "trip_id": "string"
    },
    low_memory=False
)

print(
    f"Live vehicle records: {len(vehicles):,}"
)


# ---------------------------------------------------------
# 3. Load GTFS reference datasets
# ---------------------------------------------------------

print("\nLoading GTFS reference data...")

routes = pd.read_csv(
    gtfs_folder / "routes_clean.csv",
    dtype={
        "route_id": "string",
        "route_short_name": "string",
        "route_long_name": "string",
        "route_desc": "string",
        "route_type": "Int64"
    },
    low_memory=False
)

trips = pd.read_csv(
    gtfs_folder / "trips_clean.csv",
    dtype={
        "route_id": "string",
        "trip_id": "string",
        "service_id": "string",
        "trip_headsign": "string",
        "shape_id": "string",
        "route_pattern_id": "string"
    },
    low_memory=False
)

stops = pd.read_csv(
    gtfs_folder / "stops_clean.csv",
    dtype={
        "stop_id": "string",
        "stop_code": "string",
        "stop_name": "string",
        "municipality": "string",
        "on_street": "string",
        "at_street": "string"
    },
    low_memory=False
)


print(
    f"Routes: {len(routes):,}"
)

print(
    f"Trips: {len(trips):,}"
)

print(
    f"Stops: {len(stops):,}"
)


# ---------------------------------------------------------
# 4. Create route reference table
# ---------------------------------------------------------

route_reference = routes[
    [
        "route_id",
        "route_short_name",
        "route_long_name",
        "route_desc",
        "route_type",
        "route_color"
    ]
].copy()


# ---------------------------------------------------------
# 5. Join live vehicles → routes
# ---------------------------------------------------------

vehicles = vehicles.merge(
    route_reference,
    on="route_id",
    how="left",
    indicator="_route_merge"
)

vehicles["route_match_status"] = (
    vehicles["_route_merge"]
    .map({
        "both": "MATCHED",
        "left_only": "UNMATCHED"
    })
)

vehicles = vehicles.drop(
    columns=["_route_merge"]
)


# ---------------------------------------------------------
# 6. Create trip reference table
# ---------------------------------------------------------

trip_reference = trips[
    [
        "trip_id",
        "route_id",
        "service_id",
        "trip_headsign",
        "direction_id",
        "shape_id",
        "route_pattern_id"
    ]
].copy()


# ---------------------------------------------------------
# 7. Join live vehicles → trips
# ---------------------------------------------------------

vehicles = vehicles.merge(
    trip_reference,
    on=["trip_id", "route_id"],
    how="left",
    suffixes=("", "_gtfs")
)

vehicles["trip_match_status"] = (
    vehicles["service_id"]
    .notna()
    .map({
        True: "MATCHED",
        False: "UNMATCHED"
    })
)


# ---------------------------------------------------------
# 8. Create stop reference table
# ---------------------------------------------------------

stop_reference = stops[
    [
        "stop_id",
        "stop_code",
        "stop_name",
        "stop_lat",
        "stop_lon",
        "zone_id",
        "municipality",
        "on_street",
        "at_street"
    ]
].copy()


# ---------------------------------------------------------
# 9. Join live vehicles → stops
# ---------------------------------------------------------

vehicles = vehicles.merge(
    stop_reference,
    on="stop_id",
    how="left",
    suffixes=("", "_gtfs")
)

vehicles["stop_match_status"] = (
    vehicles["stop_name"]
    .notna()
    .map({
        True: "MATCHED",
        False: "UNMATCHED"
    })
)


# ---------------------------------------------------------
# 10. Determine overall integration status
# ---------------------------------------------------------

vehicles["integration_status"] = "FULL_MATCH"

vehicles.loc[
    vehicles["route_match_status"] == "UNMATCHED",
    "integration_status"
] = "PARTIAL_MATCH"

vehicles.loc[
    vehicles["trip_match_status"] == "UNMATCHED",
    "integration_status"
] = "PARTIAL_MATCH"

vehicles.loc[
    vehicles["stop_match_status"] == "UNMATCHED",
    "integration_status"
] = "PARTIAL_MATCH"


# ---------------------------------------------------------
# 11. Save integrated dataset
# ---------------------------------------------------------

vehicles.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 12. Pipeline summary
# ---------------------------------------------------------

print("\n========================================")
print("VEHICLE + GTFS INTEGRATION SUMMARY")
print("========================================")

print(
    f"Integrated records: {len(vehicles):,}"
)

print(
    "\nRoute matching:"
)

print(
    vehicles["route_match_status"]
    .value_counts()
)

print(
    "\nTrip matching:"
)

print(
    vehicles["trip_match_status"]
    .value_counts()
)

print(
    "\nStop matching:"
)

print(
    vehicles["stop_match_status"]
    .value_counts()
)

print(
    "\nOverall integration:"
)

print(
    vehicles["integration_status"]
    .value_counts()
)


# ---------------------------------------------------------
# 13. Display sample enriched records
# ---------------------------------------------------------

print(
    "\nSample integrated records:"
)

sample_columns = [
    "vehicle_id",
    "route_id",
    "route_long_name",
    "trip_id",
    "trip_headsign",
    "stop_id",
    "stop_name",
    "latitude",
    "longitude",
    "integration_status"
]

print(
    vehicles[
        sample_columns
    ]
    .head(10)
    .to_string(index=False)
)


print(
    f"\nOutput file: {output_file}"
)

print(
    "\nVehicle + GTFS integration completed."
)