import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_folder = Path("data/raw/gtfs/processed")


# ---------------------------------------------------------
# 2. Load core GTFS datasets
# ---------------------------------------------------------

print("Loading GTFS datasets...\n")

routes = pd.read_csv(
    input_folder / "routes.csv",
    low_memory=False
)

stops = pd.read_csv(
    input_folder / "stops.csv",
    low_memory=False
)

trips = pd.read_csv(
    input_folder / "trips.csv",
    low_memory=False
)

stop_times = pd.read_csv(
    input_folder / "stop_times.csv",
    low_memory=False
)

shapes = pd.read_csv(
    input_folder / "shapes.csv",
    low_memory=False
)


print(f"Routes:      {len(routes):,}")
print(f"Stops:       {len(stops):,}")
print(f"Trips:       {len(trips):,}")
print(f"Stop Times:  {len(stop_times):,}")
print(f"Shapes:      {len(shapes):,}")


# ---------------------------------------------------------
# 3. Check duplicate primary IDs
# ---------------------------------------------------------

print("\nChecking duplicate IDs...\n")


def check_duplicates(df, column, dataset_name):

    duplicates = df[column].duplicated().sum()

    print(
        f"{dataset_name}.{column}: "
        f"{duplicates:,} duplicate records"
    )


check_duplicates(
    routes,
    "route_id",
    "routes"
)

check_duplicates(
    stops,
    "stop_id",
    "stops"
)

check_duplicates(
    trips,
    "trip_id",
    "trips"
)

check_duplicates(
    shapes,
    "shape_id",
    "shapes"
)


# ---------------------------------------------------------
# 4. Validate trip → route relationship
# ---------------------------------------------------------

print("\nValidating trips → routes...\n")

route_ids = set(routes["route_id"].dropna())

invalid_trip_routes = trips[
    ~trips["route_id"].isin(route_ids)
]

print(
    "Trips with invalid route_id:",
    len(invalid_trip_routes)
)


# ---------------------------------------------------------
# 5. Validate stop_times → trips relationship
# ---------------------------------------------------------

print("\nValidating stop_times → trips...\n")

trip_ids = set(trips["trip_id"].dropna())

invalid_stop_time_trips = stop_times[
    ~stop_times["trip_id"].isin(trip_ids)
]

print(
    "Stop times with invalid trip_id:",
    len(invalid_stop_time_trips)
)


# ---------------------------------------------------------
# 6. Validate stop_times → stops relationship
# ---------------------------------------------------------

print("\nValidating stop_times → stops...\n")

stop_ids = set(stops["stop_id"].dropna())

invalid_stop_time_stops = stop_times[
    ~stop_times["stop_id"].isin(stop_ids)
]

print(
    "Stop times with invalid stop_id:",
    len(invalid_stop_time_stops)
)


# ---------------------------------------------------------
# 7. Validate trips → shapes relationship
# ---------------------------------------------------------

print("\nValidating trips → shapes...\n")

shape_ids = set(shapes["shape_id"].dropna())

invalid_trip_shapes = trips[
    trips["shape_id"].notna()
    & ~trips["shape_id"].isin(shape_ids)
]

print(
    "Trips with invalid shape_id:",
    len(invalid_trip_shapes)
)


# ---------------------------------------------------------
# 8. Validate required fields
# ---------------------------------------------------------

print("\nChecking missing required fields...\n")


required_fields = {
    "routes": (
        routes,
        ["route_id"]
    ),
    "stops": (
        stops,
        ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    ),
    "trips": (
        trips,
        ["route_id", "trip_id", "service_id"]
    ),
    "stop_times": (
        stop_times,
        ["trip_id", "stop_id", "stop_sequence"]
    ),
    "shapes": (
        shapes,
        ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"]
    ),
}


for dataset_name, (df, columns) in required_fields.items():

    for column in columns:

        missing = df[column].isna().sum()

        print(
            f"{dataset_name}.{column}: "
            f"{missing:,} missing"
        )


# ---------------------------------------------------------
# 9. Validate geographic coordinates
# ---------------------------------------------------------

print("\nChecking geographic coordinates...\n")


invalid_stop_coordinates = stops[
    stops["stop_lat"].isna()
    | stops["stop_lon"].isna()
    | (stops["stop_lat"] < -90)
    | (stops["stop_lat"] > 90)
    | (stops["stop_lon"] < -180)
    | (stops["stop_lon"] > 180)
]

print(
    "Stops with invalid coordinates:",
    len(invalid_stop_coordinates)
)


invalid_shape_coordinates = shapes[
    shapes["shape_pt_lat"].isna()
    | shapes["shape_pt_lon"].isna()
    | (shapes["shape_pt_lat"] < -90)
    | (shapes["shape_pt_lat"] > 90)
    | (shapes["shape_pt_lon"] < -180)
    | (shapes["shape_pt_lon"] > 180)
]

print(
    "Shape points with invalid coordinates:",
    len(invalid_shape_coordinates)
)


# ---------------------------------------------------------
# 10. Validate stop sequence
# ---------------------------------------------------------

print("\nChecking stop sequence...\n")

invalid_stop_sequence = stop_times[
    stop_times["stop_sequence"].isna()
    | (stop_times["stop_sequence"] < 0)
]

print(
    "Stop times with invalid stop_sequence:",
    len(invalid_stop_sequence)
)


# ---------------------------------------------------------
# 11. Final validation summary
# ---------------------------------------------------------

print("\n========================================")
print("GTFS VALIDATION SUMMARY")
print("========================================")

validation_results = {
    "Duplicate route IDs": routes["route_id"].duplicated().sum(),
    "Duplicate stop IDs": stops["stop_id"].duplicated().sum(),
    "Duplicate trip IDs": trips["trip_id"].duplicated().sum(),
    "Duplicate shape IDs": shapes["shape_id"].duplicated().sum(),
    "Invalid trip → route": len(invalid_trip_routes),
    "Invalid stop_time → trip": len(invalid_stop_time_trips),
    "Invalid stop_time → stop": len(invalid_stop_time_stops),
    "Invalid trip → shape": len(invalid_trip_shapes),
    "Invalid stop coordinates": len(invalid_stop_coordinates),
    "Invalid shape coordinates": len(invalid_shape_coordinates),
    "Invalid stop sequences": len(invalid_stop_sequence),
}


for check, count in validation_results.items():

    status = "PASS" if count == 0 else "CHECK"

    print(
        f"{status:<6} | {check:<35} | {count:,}"
    )


print("\nGTFS validation completed.")
