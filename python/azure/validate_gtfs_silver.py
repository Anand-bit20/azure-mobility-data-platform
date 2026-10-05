import os
import tempfile
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient


CONTAINER_NAME = "silver"

GTFS_FILES = {
    "routes": "gtfs/routes_clean.csv",
    "stops": "gtfs/stops_clean.csv",
    "trips": "gtfs/trips_clean.csv",
    "stop_times": "gtfs/stop_times_clean.csv",
    "shapes": "gtfs/shapes_clean.csv",
}


def download_blob(container_client, blob_name, local_path):
    print(f"Downloading: {blob_name}")

    blob_client = container_client.get_blob_client(blob_name)

    with open(local_path, "wb") as file:
        blob_client.download_blob().readinto(file)


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

    silver_container = (
        blob_service_client.get_container_client(
            CONTAINER_NAME
        )
    )

    # ---------------------------------------------------------
    # 2. Temporary working directory
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        print(
            "\nDownloading GTFS Silver datasets "
            "from Azure...\n"
        )

        local_files = {}

        for dataset_name, blob_name in GTFS_FILES.items():

            local_file = (
                temp_path / f"{dataset_name}.csv"
            )

            download_blob(
                silver_container,
                blob_name,
                local_file
            )

            local_files[dataset_name] = local_file

        # -----------------------------------------------------
        # 3. Load datasets
        # -----------------------------------------------------

        print("\nLoading datasets...\n")

        routes = pd.read_csv(
            local_files["routes"],
            low_memory=False
        )

        stops = pd.read_csv(
            local_files["stops"],
            low_memory=False
        )

        trips = pd.read_csv(
            local_files["trips"],
            low_memory=False
        )

        stop_times = pd.read_csv(
            local_files["stop_times"],
            low_memory=False
        )

        shapes = pd.read_csv(
            local_files["shapes"],
            low_memory=False
        )

        print(f"Routes:      {len(routes):,}")
        print(f"Stops:       {len(stops):,}")
        print(f"Trips:       {len(trips):,}")
        print(f"Stop Times:  {len(stop_times):,}")
        print(f"Shapes:      {len(shapes):,}")

        # -----------------------------------------------------
        # 4. Duplicate checks
        # -----------------------------------------------------

        duplicate_route_ids = (
            routes["route_id"].duplicated().sum()
        )

        duplicate_stop_ids = (
            stops["stop_id"].duplicated().sum()
        )

        duplicate_trip_ids = (
            trips["trip_id"].duplicated().sum()
        )

        # shapes.txt primary key:
        # shape_id + shape_pt_sequence
        duplicate_shape_points = (
            shapes.duplicated(
                subset=[
                    "shape_id",
                    "shape_pt_sequence"
                ]
            ).sum()
        )

        # -----------------------------------------------------
        # 5. Relationship validation
        # -----------------------------------------------------

        route_ids = set(
            routes["route_id"]
            .dropna()
            .astype(str)
        )

        trip_ids = set(
            trips["trip_id"]
            .dropna()
            .astype(str)
        )

        stop_ids = set(
            stops["stop_id"]
            .dropna()
            .astype(str)
        )

        shape_ids = set(
            shapes["shape_id"]
            .dropna()
            .astype(str)
        )

        invalid_trip_routes = trips[
            ~trips["route_id"]
            .astype(str)
            .isin(route_ids)
        ]

        invalid_stop_time_trips = stop_times[
            ~stop_times["trip_id"]
            .astype(str)
            .isin(trip_ids)
        ]

        invalid_stop_time_stops = stop_times[
            ~stop_times["stop_id"]
            .astype(str)
            .isin(stop_ids)
        ]

        invalid_trip_shapes = trips[
            trips["shape_id"].notna()
            & ~trips["shape_id"]
            .astype(str)
            .isin(shape_ids)
        ]

        # -----------------------------------------------------
        # 6. Required field validation
        # -----------------------------------------------------

        missing_route_id = (
            routes["route_id"].isna().sum()
        )

        missing_stop_id = (
            stops["stop_id"].isna().sum()
        )

        missing_stop_name = (
            stops["stop_name"].isna().sum()
        )

        missing_stop_lat = (
            stops["stop_lat"].isna().sum()
        )

        missing_stop_lon = (
            stops["stop_lon"].isna().sum()
        )

        missing_trip_route = (
            trips["route_id"].isna().sum()
        )

        missing_trip_id = (
            trips["trip_id"].isna().sum()
        )

        missing_service_id = (
            trips["service_id"].isna().sum()
        )

        missing_stop_time_trip = (
            stop_times["trip_id"].isna().sum()
        )

        missing_stop_time_stop = (
            stop_times["stop_id"].isna().sum()
        )

        missing_stop_sequence = (
            stop_times["stop_sequence"].isna().sum()
        )

        # -----------------------------------------------------
        # 7. Geographic validation
        # -----------------------------------------------------

        invalid_stop_coordinates = stops[
            stops["stop_lat"].isna()
            | stops["stop_lon"].isna()
            | (stops["stop_lat"] < -90)
            | (stops["stop_lat"] > 90)
            | (stops["stop_lon"] < -180)
            | (stops["stop_lon"] > 180)
        ]

        invalid_shape_coordinates = shapes[
            shapes["shape_pt_lat"].isna()
            | shapes["shape_pt_lon"].isna()
            | (shapes["shape_pt_lat"] < -90)
            | (shapes["shape_pt_lat"] > 90)
            | (shapes["shape_pt_lon"] < -180)
            | (shapes["shape_pt_lon"] > 180)
        ]

        # -----------------------------------------------------
        # 8. Stop sequence validation
        # -----------------------------------------------------

        invalid_stop_sequence = stop_times[
            stop_times["stop_sequence"].isna()
            | (stop_times["stop_sequence"] < 0)
        ]

        # -----------------------------------------------------
        # 9. Build validation report
        # -----------------------------------------------------

        validation_results = [
            (
                "Duplicate route IDs",
                duplicate_route_ids
            ),
            (
                "Duplicate stop IDs",
                duplicate_stop_ids
            ),
            (
                "Duplicate trip IDs",
                duplicate_trip_ids
            ),
            (
                "Duplicate shape point keys",
                duplicate_shape_points
            ),
            (
                "Invalid trip -> route",
                len(invalid_trip_routes)
            ),
            (
                "Invalid stop_time -> trip",
                len(invalid_stop_time_trips)
            ),
            (
                "Invalid stop_time -> stop",
                len(invalid_stop_time_stops)
            ),
            (
                "Invalid trip -> shape",
                len(invalid_trip_shapes)
            ),
            (
                "Missing route.route_id",
                missing_route_id
            ),
            (
                "Missing stop.stop_id",
                missing_stop_id
            ),
            (
                "Missing stop.stop_name",
                missing_stop_name
            ),
            (
                "Missing stop.stop_lat",
                missing_stop_lat
            ),
            (
                "Missing stop.stop_lon",
                missing_stop_lon
            ),
            (
                "Missing trip.route_id",
                missing_trip_route
            ),
            (
                "Missing trip.trip_id",
                missing_trip_id
            ),
            (
                "Missing trip.service_id",
                missing_service_id
            ),
            (
                "Missing stop_time.trip_id",
                missing_stop_time_trip
            ),
            (
                "Missing stop_time.stop_id",
                missing_stop_time_stop
            ),
            (
                "Missing stop_time.stop_sequence",
                missing_stop_sequence
            ),
            (
                "Invalid stop coordinates",
                len(invalid_stop_coordinates)
            ),
            (
                "Invalid shape coordinates",
                len(invalid_shape_coordinates)
            ),
            (
                "Invalid stop sequences",
                len(invalid_stop_sequence)
            ),
        ]

        validation_df = pd.DataFrame(
            validation_results,
            columns=[
                "check",
                "count"
            ]
        )

        validation_df["status"] = (
            validation_df["count"]
            .apply(
                lambda count:
                "PASS" if count == 0 else "CHECK"
            )
        )

        # -----------------------------------------------------
        # 10. Print summary
        # -----------------------------------------------------

        print("\n========================================")
        print("AZURE GTFS VALIDATION SUMMARY")
        print("========================================")

        for _, row in validation_df.iterrows():

            print(
                f"{row['status']:<6} | "
                f"{row['check']:<38} | "
                f"{row['count']:,}"
            )

        # -----------------------------------------------------
        # 11. Save validation report
        # -----------------------------------------------------

        local_report = (
            temp_path /
            "gtfs_validation_summary.csv"
        )

        validation_df.to_csv(
            local_report,
            index=False
        )

        report_blob_name = (
            "gtfs/gtfs_validation_summary.csv"
        )

        print(
            "\nUploading validation report..."
        )

        blob_client = (
            silver_container.get_blob_client(
                report_blob_name
            )
        )

        with open(local_report, "rb") as file:

            blob_client.upload_blob(
                file,
                overwrite=True
            )

        print(
            "Validation report uploaded:"
        )

        print(
            f"silver/{report_blob_name}"
        )

        print(
            "\nGTFS validation completed."
        )


if __name__ == "__main__":
    main()