import os
import tempfile
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient


RAW_CONTAINER = "raw"
SILVER_CONTAINER = "silver"

GTFS_FILES = [
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
    "shapes.txt",
    "calendar.txt",
    "calendar_dates.txt",
]


def add_exception(
    exceptions,
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


def download_blob(container_client, blob_name, local_path):
    print(f"Downloading: {blob_name}")

    blob_client = container_client.get_blob_client(blob_name)

    with open(local_path, "wb") as file:
        blob_client.download_blob().readinto(file)


def upload_dataframe(
    container_client,
    dataframe,
    blob_name,
    local_path
):
    dataframe.to_csv(
        local_path,
        index=False
    )

    print(f"Uploading: {blob_name}")

    blob_client = container_client.get_blob_client(
        blob_name
    )

    with open(local_path, "rb") as file:
        blob_client.upload_blob(
            file,
            overwrite=True
        )


def main():

    # ---------------------------------------------------------
    # 1. Azure connection
    # ---------------------------------------------------------

    connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING"
    )

    if not connection_string:
        raise ValueError(
            "AZURE_STORAGE_CONNECTION_STRING "
            "environment variable is not set."
        )

    blob_service_client = (
        BlobServiceClient.from_connection_string(
            connection_string
        )
    )

    raw_container = (
        blob_service_client.get_container_client(
            RAW_CONTAINER
        )
    )

    silver_container = (
        blob_service_client.get_container_client(
            SILVER_CONTAINER
        )
    )

    # ---------------------------------------------------------
    # 2. Temporary working directory
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        # -----------------------------------------------------
        # 3. Download Raw GTFS files
        # -----------------------------------------------------

        print("\nDownloading GTFS datasets from Azure...\n")

        for file_name in GTFS_FILES:

            blob_name = f"gtfs/{file_name}"
            local_file = temp_path / file_name

            download_blob(
                raw_container,
                blob_name,
                local_file
            )

        # -----------------------------------------------------
        # 4. Load datasets
        # -----------------------------------------------------

        print("\nLoading GTFS datasets...\n")

        routes = pd.read_csv(
            temp_path / "routes.txt",
            low_memory=False
        )

        stops = pd.read_csv(
            temp_path / "stops.txt",
            low_memory=False
        )

        trips = pd.read_csv(
            temp_path / "trips.txt",
            low_memory=False
        )

        stop_times = pd.read_csv(
            temp_path / "stop_times.txt",
            low_memory=False
        )

        shapes = pd.read_csv(
            temp_path / "shapes.txt",
            low_memory=False
        )

        calendar = pd.read_csv(
            temp_path / "calendar.txt",
            low_memory=False
        )

        calendar_dates = pd.read_csv(
            temp_path / "calendar_dates.txt",
            low_memory=False
        )

        # -----------------------------------------------------
        # 5. Exception list
        # -----------------------------------------------------

        exceptions = []

        # -----------------------------------------------------
        # 6. Clean routes
        # -----------------------------------------------------

        routes["route_id"] = (
            routes["route_id"].astype("string")
        )

        routes["agency_id"] = (
            routes["agency_id"].astype("string")
        )

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

        # -----------------------------------------------------
        # 7. Clean stops
        # -----------------------------------------------------

        stops["stop_id"] = (
            stops["stop_id"].astype("string")
        )

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

        missing_stop_coordinates = (
            stops["stop_lat"].isna()
            | stops["stop_lon"].isna()
        )

        for index in stops[
            missing_stop_coordinates
        ].index:

            add_exception(
                exceptions,
                "stops",
                stops.loc[index, "stop_id"],
                "GTFS001",
                "Missing Stop Coordinates",
                "Medium"
            )

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

        for index in stops[
            invalid_stop_coordinates
        ].index:

            add_exception(
                exceptions,
                "stops",
                stops.loc[index, "stop_id"],
                "GTFS002",
                "Invalid Stop Coordinates",
                "High"
            )

        # -----------------------------------------------------
        # 8. Clean trips
        # -----------------------------------------------------

        trips["route_id"] = (
            trips["route_id"].astype("string")
        )

        trips["trip_id"] = (
            trips["trip_id"].astype("string")
        )

        trips["service_id"] = (
            trips["service_id"].astype("string")
        )

        trips["shape_id"] = (
            trips["shape_id"].astype("string")
        )

        # -----------------------------------------------------
        # 9. Clean stop times
        # -----------------------------------------------------

        stop_times["trip_id"] = (
            stop_times["trip_id"].astype("string")
        )

        stop_times["stop_id"] = (
            stop_times["stop_id"].astype("string")
        )

        stop_times["stop_sequence"] = pd.to_numeric(
            stop_times["stop_sequence"],
            errors="coerce"
        )

        stop_times["arrival_time"] = (
            stop_times["arrival_time"].astype("string")
        )

        stop_times["departure_time"] = (
            stop_times["departure_time"]
            .astype("string")
        )

        # -----------------------------------------------------
        # 10. Clean shapes
        # -----------------------------------------------------

        shapes["shape_id"] = (
            shapes["shape_id"].astype("string")
        )

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

        invalid_shape_coordinates = (
            shapes["shape_pt_lat"].isna()
            | shapes["shape_pt_lon"].isna()
            | (shapes["shape_pt_lat"] < -90)
            | (shapes["shape_pt_lat"] > 90)
            | (shapes["shape_pt_lon"] < -180)
            | (shapes["shape_pt_lon"] > 180)
        )

        for index in shapes[
            invalid_shape_coordinates
        ].index:

            add_exception(
                exceptions,
                "shapes",
                shapes.loc[index, "shape_id"],
                "GTFS003",
                "Invalid Shape Coordinates",
                "High"
            )

        # -----------------------------------------------------
        # 11. Clean calendar
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 12. Clean calendar dates
        # -----------------------------------------------------

        calendar_dates["service_id"] = (
            calendar_dates["service_id"]
            .astype("string")
        )

        calendar_dates["date"] = pd.to_datetime(
            calendar_dates["date"].astype("string"),
            format="%Y%m%d",
            errors="coerce"
        )

        calendar_dates["exception_type"] = (
            pd.to_numeric(
                calendar_dates["exception_type"],
                errors="coerce"
            )
        )

        # -----------------------------------------------------
        # 13. Relationship validation
        # -----------------------------------------------------

        print("\nRunning GTFS relationship checks...")

        route_ids = set(
            routes["route_id"].dropna()
        )

        trip_ids = set(
            trips["trip_id"].dropna()
        )

        stop_ids = set(
            stops["stop_id"].dropna()
        )

        shape_ids = set(
            shapes["shape_id"].dropna()
        )

        # Trips → Routes
        invalid_trip_routes = trips[
            ~trips["route_id"].isin(route_ids)
        ]

        for index in invalid_trip_routes.index:

            add_exception(
                exceptions,
                "trips",
                trips.loc[index, "trip_id"],
                "GTFS004",
                "Invalid Route Reference",
                "High"
            )

        # Stop Times → Trips
        invalid_stop_time_trips = stop_times[
            ~stop_times["trip_id"].isin(trip_ids)
        ]

        for index in invalid_stop_time_trips.index:

            add_exception(
                exceptions,
                "stop_times",
                stop_times.loc[index, "trip_id"],
                "GTFS005",
                "Invalid Trip Reference",
                "High"
            )

        # Stop Times → Stops
        invalid_stop_time_stops = stop_times[
            ~stop_times["stop_id"].isin(stop_ids)
        ]

        for index in invalid_stop_time_stops.index:

            add_exception(
                exceptions,
                "stop_times",
                stop_times.loc[index, "stop_id"],
                "GTFS006",
                "Invalid Stop Reference",
                "High"
            )

        # Trips → Shapes
        invalid_trip_shapes = trips[
            trips["shape_id"].notna()
            & ~trips["shape_id"].isin(shape_ids)
        ]

        for index in invalid_trip_shapes.index:

            add_exception(
                exceptions,
                "trips",
                trips.loc[index, "trip_id"],
                "GTFS007",
                "Invalid Shape Reference",
                "High"
            )

        # -----------------------------------------------------
        # 14. Create exception DataFrame
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 15. Upload Silver datasets
        # -----------------------------------------------------

        print("\nUploading GTFS Silver datasets...\n")

        outputs = [
            (
                routes,
                "routes_clean.csv"
            ),
            (
                stops,
                "stops_clean.csv"
            ),
            (
                trips,
                "trips_clean.csv"
            ),
            (
                stop_times,
                "stop_times_clean.csv"
            ),
            (
                shapes,
                "shapes_clean.csv"
            ),
            (
                calendar,
                "calendar_clean.csv"
            ),
            (
                calendar_dates,
                "calendar_dates_clean.csv"
            ),
            (
                exceptions_df,
                "gtfs_exceptions.csv"
            ),
        ]

        for dataframe, file_name in outputs:

            local_output = (
                temp_path / file_name
            )

            blob_name = (
                f"gtfs/{file_name}"
            )

            upload_dataframe(
                silver_container,
                dataframe,
                blob_name,
                local_output
            )

        # -----------------------------------------------------
        # 16. Summary
        # -----------------------------------------------------

        print("\n========================================")
        print("AZURE GTFS SILVER PROCESSING SUMMARY")
        print("========================================")

        print(f"Routes:         {len(routes):,}")
        print(f"Stops:          {len(stops):,}")
        print(f"Trips:          {len(trips):,}")
        print(f"Stop Times:     {len(stop_times):,}")
        print(f"Shapes:         {len(shapes):,}")
        print(f"Calendar:       {len(calendar):,}")
        print(
            f"Calendar Dates: {len(calendar_dates):,}"
        )

        print(
            f"\nGTFS exceptions: "
            f"{len(exceptions_df):,}"
        )

        if not exceptions_df.empty:

            print("\nExceptions by rule:")

            print(
                exceptions_df["rule_name"]
                .value_counts()
            )

        else:
            print(
                "\nNo GTFS exceptions found."
            )

        print(
            "\nAzure Silver location: silver/gtfs/"
        )

        print(
            "\nGTFS Silver processing "
            "completed successfully."
        )


if __name__ == "__main__":
    main()