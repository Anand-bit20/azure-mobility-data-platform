import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_folder = Path("data/raw/gtfs/processed")
output_folder = Path("data/processed/gtfs")

output_folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 2. Load GTFS datasets
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

calendar = pd.read_csv(
    input_folder / "calendar.csv",
    low_memory=False
)

calendar_dates = pd.read_csv(
    input_folder / "calendar_dates.csv",
    low_memory=False
)


# ---------------------------------------------------------
# 3. Create exception list
# ---------------------------------------------------------

exceptions = []


def add_exception(
    dataset,
    record_id,
    rule_id,
    rule_name,
    severity
):
    exceptions.append({
        "dataset": dataset,
        "record_id": record_id,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "severity": severity
    })


# ---------------------------------------------------------
# 4. Clean routes
# ---------------------------------------------------------

routes["route_id"] = routes["route_id"].astype("string")

routes["agency_id"] = routes["agency_id"].astype("string")

routes["route_short_name"] = (
    routes["route_short_name"]
    .fillna("")
    .astype("string")
)

routes["route_long_name"] = (
    routes["route_long_name"]
    .fillna("")
    .astype("string")
)


# ---------------------------------------------------------
# 5. Clean stops
# ---------------------------------------------------------

stops["stop_id"] = stops["stop_id"].astype("string")

stops["stop_name"] = (
    stops["stop_name"]
    .fillna("")
    .astype("string")
)

stops["stop_lat"] = pd.to_numeric(
    stops["stop_lat"],
    errors="coerce"
)

stops["stop_lon"] = pd.to_numeric(
    stops["stop_lon"],
    errors="coerce"
)


# Identify stops without coordinates
missing_stop_coordinates = (
    stops["stop_lat"].isna()
    | stops["stop_lon"].isna()
)

for index in stops[missing_stop_coordinates].index:

    add_exception(
        dataset="stops",
        record_id=stops.loc[index, "stop_id"],
        rule_id="GTFS001",
        rule_name="Missing Stop Coordinates",
        severity="Medium"
    )


# Identify invalid coordinates
invalid_stop_coordinates = (
    stops["stop_lat"].notna()
    & stops["stop_lon"].notna()
    & (
        (stops["stop_lat"] < -90)
        | (stops["stop_lat"] > 90)
        | (stops["stop_lon"] < -180)
        | (stops["stop_lon"] > 180)
    )
)

for index in stops[invalid_stop_coordinates].index:

    add_exception(
        dataset="stops",
        record_id=stops.loc[index, "stop_id"],
        rule_id="GTFS002",
        rule_name="Invalid Stop Coordinates",
        severity="High"
    )


# ---------------------------------------------------------
# 6. Clean trips
# ---------------------------------------------------------

trips["route_id"] = trips["route_id"].astype("string")
trips["trip_id"] = trips["trip_id"].astype("string")
trips["service_id"] = trips["service_id"].astype("string")
trips["shape_id"] = trips["shape_id"].astype("string")


# ---------------------------------------------------------
# 7. Clean stop times
# ---------------------------------------------------------

stop_times["trip_id"] = stop_times["trip_id"].astype("string")
stop_times["stop_id"] = stop_times["stop_id"].astype("string")

stop_times["stop_sequence"] = pd.to_numeric(
    stop_times["stop_sequence"],
    errors="coerce"
)

stop_times["arrival_time"] = (
    stop_times["arrival_time"].astype("string")
)

stop_times["departure_time"] = (
    stop_times["departure_time"].astype("string")
)


# ---------------------------------------------------------
# 8. Clean shapes
# ---------------------------------------------------------

shapes["shape_id"] = shapes["shape_id"].astype("string")

shapes["shape_pt_lat"] = pd.to_numeric(
    shapes["shape_pt_lat"],
    errors="coerce"
)

shapes["shape_pt_lon"] = pd.to_numeric(
    shapes["shape_pt_lon"],
    errors="coerce"
)

shapes["shape_pt_sequence"] = pd.to_numeric(
    shapes["shape_pt_sequence"],
    errors="coerce"
)


# ---------------------------------------------------------
# 9. Validate shape coordinates
# ---------------------------------------------------------

invalid_shape_coordinates = (
    shapes["shape_pt_lat"].isna()
    | shapes["shape_pt_lon"].isna()
    | (shapes["shape_pt_lat"] < -90)
    | (shapes["shape_pt_lat"] > 90)
    | (shapes["shape_pt_lon"] < -180)
    | (shapes["shape_pt_lon"] > 180)
)

for index in shapes[invalid_shape_coordinates].index:

    add_exception(
        dataset="shapes",
        record_id=shapes.loc[index, "shape_id"],
        rule_id="GTFS003",
        rule_name="Invalid Shape Coordinates",
        severity="High"
    )


# ---------------------------------------------------------
# 10. Clean calendar
# ---------------------------------------------------------

calendar["service_id"] = (
    calendar["service_id"].astype("string")
)

calendar["start_date"] = pd.to_datetime(
    calendar["start_date"].astype("string"),
    format="%Y%m%d",
    errors="coerce"
)

calendar["end_date"] = pd.to_datetime(
    calendar["end_date"].astype("string"),
    format="%Y%m%d",
    errors="coerce"
)


# ---------------------------------------------------------
# 11. Clean calendar dates
# ---------------------------------------------------------

calendar_dates["service_id"] = (
    calendar_dates["service_id"].astype("string")
)

calendar_dates["date"] = pd.to_datetime(
    calendar_dates["date"].astype("string"),
    format="%Y%m%d",
    errors="coerce"
)

calendar_dates["exception_type"] = pd.to_numeric(
    calendar_dates["exception_type"],
    errors="coerce"
)


# ---------------------------------------------------------
# 12. Validate GTFS relationships
# ---------------------------------------------------------

route_ids = set(routes["route_id"].dropna())

trip_ids = set(trips["trip_id"].dropna())

stop_ids = set(stops["stop_id"].dropna())

shape_ids = set(shapes["shape_id"].dropna())


# Trips → Routes
invalid_trip_routes = trips[
    ~trips["route_id"].isin(route_ids)
]

for index in invalid_trip_routes.index:

    add_exception(
        dataset="trips",
        record_id=trips.loc[index, "trip_id"],
        rule_id="GTFS004",
        rule_name="Invalid Route Reference",
        severity="High"
    )


# Stop Times → Trips
invalid_stop_time_trips = stop_times[
    ~stop_times["trip_id"].isin(trip_ids)
]

for index in invalid_stop_time_trips.index:

    add_exception(
        dataset="stop_times",
        record_id=stop_times.loc[index, "trip_id"],
        rule_id="GTFS005",
        rule_name="Invalid Trip Reference",
        severity="High"
    )


# Stop Times → Stops
invalid_stop_time_stops = stop_times[
    ~stop_times["stop_id"].isin(stop_ids)
]

for index in invalid_stop_time_stops.index:

    add_exception(
        dataset="stop_times",
        record_id=stop_times.loc[index, "stop_id"],
        rule_id="GTFS006",
        rule_name="Invalid Stop Reference",
        severity="High"
    )


# Trips → Shapes
invalid_trip_shapes = trips[
    trips["shape_id"].notna()
    & ~trips["shape_id"].isin(shape_ids)
]

for index in invalid_trip_shapes.index:

    add_exception(
        dataset="trips",
        record_id=trips.loc[index, "trip_id"],
        rule_id="GTFS007",
        rule_name="Invalid Shape Reference",
        severity="High"
    )


# ---------------------------------------------------------
# 13. Create exception DataFrame
# ---------------------------------------------------------

exceptions_df = pd.DataFrame(
    exceptions,
    columns=[
        "dataset",
        "record_id",
        "rule_id",
        "rule_name",
        "severity"
    ]
)


# ---------------------------------------------------------
# 14. Save Silver datasets
# ---------------------------------------------------------

routes.to_csv(
    output_folder / "routes_clean.csv",
    index=False
)

stops.to_csv(
    output_folder / "stops_clean.csv",
    index=False
)

trips.to_csv(
    output_folder / "trips_clean.csv",
    index=False
)

stop_times.to_csv(
    output_folder / "stop_times_clean.csv",
    index=False
)

shapes.to_csv(
    output_folder / "shapes_clean.csv",
    index=False
)

calendar.to_csv(
    output_folder / "calendar_clean.csv",
    index=False
)

calendar_dates.to_csv(
    output_folder / "calendar_dates_clean.csv",
    index=False
)

exceptions_df.to_csv(
    output_folder / "gtfs_exceptions.csv",
    index=False
)


# ---------------------------------------------------------
# 15. Pipeline summary
# ---------------------------------------------------------

print("\n========================================")
print("GTFS SILVER PROCESSING SUMMARY")
print("========================================")

print(f"Routes:       {len(routes):,}")
print(f"Stops:        {len(stops):,}")
print(f"Trips:        {len(trips):,}")
print(f"Stop Times:   {len(stop_times):,}")
print(f"Shapes:       {len(shapes):,}")
print(f"Calendar:     {len(calendar):,}")
print(f"Calendar Dates: {len(calendar_dates):,}")

print(
    f"\nGTFS exceptions: {len(exceptions_df):,}"
)

if not exceptions_df.empty:

    print("\nExceptions by rule:")

    print(
        exceptions_df["rule_name"]
        .value_counts()
    )

else:

    print("\nNo GTFS exceptions found.")


print(
    f"\nSilver output folder: {output_folder}"
)

print("\nGTFS Silver processing completed.")