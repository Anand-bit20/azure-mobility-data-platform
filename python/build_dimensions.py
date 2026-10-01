import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

gtfs_folder = Path(
    "data/processed/gtfs"
)

gold_folder = Path(
    "data/processed/gold"
)

gold_folder.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# 2. Load GTFS reference data
# ---------------------------------------------------------

print("Loading GTFS reference data...")

routes = pd.read_csv(
    gtfs_folder / "routes_clean.csv",
    dtype={
        "route_id": "string",
        "route_short_name": "string",
        "route_long_name": "string",
        "route_desc": "string",
        "route_type": "Int64",
        "route_color": "string",
        "route_text_color": "string"
    },
    low_memory=False
)

stops = pd.read_csv(
    gtfs_folder / "stops_clean.csv",
    dtype={
        "stop_id": "string",
        "stop_code": "string",
        "stop_name": "string",
        "stop_desc": "string",
        "platform_code": "string",
        "platform_name": "string",
        "municipality": "string",
        "on_street": "string",
        "at_street": "string",
        "parent_station": "string"
    },
    low_memory=False
)

trips = pd.read_csv(
    gtfs_folder / "trips_clean.csv",
    dtype={
        "route_id": "string",
        "service_id": "string",
        "trip_id": "string",
        "trip_headsign": "string",
        "trip_short_name": "string",
        "shape_id": "string",
        "route_pattern_id": "string"
    },
    low_memory=False
)


print(
    f"Routes loaded: {len(routes):,}"
)

print(
    f"Stops loaded: {len(stops):,}"
)

print(
    f"Trips loaded: {len(trips):,}"
)


# ---------------------------------------------------------
# 3. Build Route Dimension
# ---------------------------------------------------------

print("\nBuilding dim_route...")

dim_route = routes[
    [
        "route_id",
        "route_short_name",
        "route_long_name",
        "route_desc",
        "route_type",
        "route_color",
        "route_text_color",
        "route_sort_order"
    ]
].copy()

dim_route = dim_route.drop_duplicates(
    subset=["route_id"]
)

dim_route["route_key"] = (
    dim_route["route_id"]
)


# ---------------------------------------------------------
# 4. Build Stop Dimension
# ---------------------------------------------------------

print("Building dim_stop...")

dim_stop = stops[
    [
        "stop_id",
        "stop_code",
        "stop_name",
        "stop_lat",
        "stop_lon",
        "zone_id",
        "municipality",
        "on_street",
        "at_street",
        "parent_station",
        "wheelchair_boarding"
    ]
].copy()

dim_stop = dim_stop.drop_duplicates(
    subset=["stop_id"]
)

dim_stop["stop_key"] = (
    dim_stop["stop_id"]
)


# ---------------------------------------------------------
# 5. Build Trip Dimension
# ---------------------------------------------------------

print("Building dim_trip...")

dim_trip = trips[
    [
        "trip_id",
        "route_id",
        "service_id",
        "trip_headsign",
        "trip_short_name",
        "direction_id",
        "block_id",
        "shape_id",
        "wheelchair_accessible",
        "bikes_allowed",
        "route_pattern_id"
    ]
].copy()

dim_trip = dim_trip.drop_duplicates(
    subset=["trip_id"]
)

dim_trip["trip_key"] = (
    dim_trip["trip_id"]
)


# ---------------------------------------------------------
# 6. Validate dimension keys
# ---------------------------------------------------------

print("\nDimension quality checks:")

print(
    "Duplicate route keys:",
    dim_route["route_key"].duplicated().sum()
)

print(
    "Duplicate stop keys:",
    dim_stop["stop_key"].duplicated().sum()
)

print(
    "Duplicate trip keys:",
    dim_trip["trip_key"].duplicated().sum()
)


# ---------------------------------------------------------
# 7. Save dimensions
# ---------------------------------------------------------

route_file = gold_folder / "dim_route.csv"
stop_file = gold_folder / "dim_stop.csv"
trip_file = gold_folder / "dim_trip.csv"

dim_route.to_csv(
    route_file,
    index=False
)

dim_stop.to_csv(
    stop_file,
    index=False
)

dim_trip.to_csv(
    trip_file,
    index=False
)


# ---------------------------------------------------------
# 8. Final summary
# ---------------------------------------------------------

print("\n========================================")
print("GOLD DIMENSION SUMMARY")
print("========================================")

print(
    f"dim_route rows: {len(dim_route):,}"
)

print(
    f"dim_stop rows: {len(dim_stop):,}"
)

print(
    f"dim_trip rows: {len(dim_trip):,}"
)

print(
    f"\nRoute dimension: {route_file}"
)

print(
    f"Stop dimension: {stop_file}"
)

print(
    f"Trip dimension: {trip_file}"
)

print(
    "\nGold dimensions created successfully."
)