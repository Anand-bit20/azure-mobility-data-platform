import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient


SILVER_CONTAINER = "silver"


def download_blob(
    container_client,
    blob_name,
    local_path
):
    print(f"Downloading: {blob_name}")

    blob_client = container_client.get_blob_client(
        blob_name
    )

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
            SILVER_CONTAINER
        )
    )

    # ---------------------------------------------------------
    # 2. Find latest Silver vehicle snapshot
    # ---------------------------------------------------------

    vehicle_blobs = list(
        silver_container.list_blobs(
            name_starts_with="vehicle_positions_clean_"
        )
    )

    if not vehicle_blobs:
        raise FileNotFoundError(
            "No clean vehicle position files "
            "found in Azure Silver container."
        )

    latest_vehicle_blob = max(
        vehicle_blobs,
        key=lambda blob: blob.name
    )

    print(
        "Latest vehicle Silver snapshot:",
        latest_vehicle_blob.name
    )

    # ---------------------------------------------------------
    # 3. Temporary working directory
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        vehicle_file = (
            temp_path / "vehicle_positions_clean.csv"
        )

        routes_file = (
            temp_path / "routes_clean.csv"
        )

        trips_file = (
            temp_path / "trips_clean.csv"
        )

        stops_file = (
            temp_path / "stops_clean.csv"
        )

        # -----------------------------------------------------
        # 4. Download Silver datasets
        # -----------------------------------------------------

        print("\nDownloading Silver datasets...\n")

        download_blob(
            silver_container,
            latest_vehicle_blob.name,
            vehicle_file
        )

        download_blob(
            silver_container,
            "gtfs/routes_clean.csv",
            routes_file
        )

        download_blob(
            silver_container,
            "gtfs/trips_clean.csv",
            trips_file
        )

        download_blob(
            silver_container,
            "gtfs/stops_clean.csv",
            stops_file
        )

        # -----------------------------------------------------
        # 5. Load vehicle data
        # -----------------------------------------------------

        print("\nLoading vehicle data...")

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
            f"Vehicle records: {len(vehicles):,}"
        )

        # -----------------------------------------------------
        # 6. Load GTFS reference datasets
        # -----------------------------------------------------

        print("\nLoading GTFS reference data...")

        routes = pd.read_csv(
            routes_file,
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
            trips_file,
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
            stops_file,
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

        # -----------------------------------------------------
        # 7. Route reference
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 8. Vehicle -> Route
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 9. Trip reference
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 10. Vehicle -> Trip
        # -----------------------------------------------------

        vehicles = vehicles.merge(
            trip_reference,
            on=[
                "trip_id",
                "route_id"
            ],
            how="left",
            suffixes=(
                "",
                "_gtfs"
            )
        )

        vehicles["trip_match_status"] = (
            vehicles["service_id"]
            .notna()
            .map({
                True: "MATCHED",
                False: "UNMATCHED"
            })
        )

        # -----------------------------------------------------
        # 11. Stop reference
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 12. Vehicle -> Stop
        # -----------------------------------------------------

        vehicles = vehicles.merge(
            stop_reference,
            on="stop_id",
            how="left",
            suffixes=(
                "",
                "_gtfs"
            )
        )

        vehicles["stop_match_status"] = (
            vehicles["stop_name"]
            .notna()
            .map({
                True: "MATCHED",
                False: "UNMATCHED"
            })
        )

        # -----------------------------------------------------
        # 13. Overall integration status
        # -----------------------------------------------------

        vehicles["integration_status"] = (
            "FULL_MATCH"
        )

        vehicles.loc[
            (
                vehicles["route_match_status"]
                == "UNMATCHED"
            ),
            "integration_status"
        ] = "PARTIAL_MATCH"

        vehicles.loc[
            (
                vehicles["trip_match_status"]
                == "UNMATCHED"
            ),
            "integration_status"
        ] = "PARTIAL_MATCH"

        vehicles.loc[
            (
                vehicles["stop_match_status"]
                == "UNMATCHED"
            ),
            "integration_status"
        ] = "PARTIAL_MATCH"

        # -----------------------------------------------------
        # 14. Integration exception classification
        # -----------------------------------------------------

        vehicles["exception_reason"] = "NONE"

        vehicles.loc[
            (
                vehicles["route_id"]
                == "Shuttle-Generic"
            )
            & (
                vehicles["trip_match_status"]
                == "UNMATCHED"
            )
            & (
                vehicles["stop_match_status"]
                == "UNMATCHED"
            ),
            "exception_reason"
        ] = "SHUTTLE_TRIP_AND_STOP_NOT_IN_GTFS"

        vehicles.loc[
            (
                vehicles["trip_match_status"]
                == "UNMATCHED"
            )
            & (
                vehicles["stop_match_status"]
                == "MATCHED"
            ),
            "exception_reason"
        ] = "REALTIME_TRIP_NOT_IN_GTFS"

        vehicles.loc[
            (
                vehicles["trip_match_status"]
                == "UNMATCHED"
            )
            & (
                vehicles["stop_match_status"]
                == "UNMATCHED"
            )
            & (
                vehicles["route_id"]
                != "Shuttle-Generic"
            ),
            "exception_reason"
        ] = "TRIP_AND_STOP_NOT_IN_GTFS"

        vehicles.loc[
            (
                vehicles["trip_match_status"]
                == "MATCHED"
            )
            & (
                vehicles["stop_match_status"]
                == "UNMATCHED"
            ),
            "exception_reason"
        ] = "STOP_NOT_IN_GTFS"

        # -----------------------------------------------------
        # 15. Save locally temporarily
        # -----------------------------------------------------

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

        output_name = (
            f"vehicle_gtfs_integrated_"
            f"{timestamp}.csv"
        )

        local_output = (
            temp_path / output_name
        )

        vehicles.to_csv(
            local_output,
            index=False
        )

        # -----------------------------------------------------
        # 16. Upload integrated dataset
        # -----------------------------------------------------

        blob_name = (
            f"integrated/{output_name}"
        )

        print(
            "\nUploading integrated dataset..."
        )

        blob_client = (
            silver_container.get_blob_client(
                blob_name
            )
        )

        with open(
            local_output,
            "rb"
        ) as file:

            blob_client.upload_blob(
                file,
                overwrite=True
            )

        # -----------------------------------------------------
        # 17. Summary
        # -----------------------------------------------------

        print("\n========================================")
        print("AZURE VEHICLE + GTFS INTEGRATION")
        print("========================================")

        print(
            f"Integrated records: "
            f"{len(vehicles):,}"
        )

        print("\nRoute matching:")

        print(
            vehicles["route_match_status"]
            .value_counts()
        )

        print("\nTrip matching:")

        print(
            vehicles["trip_match_status"]
            .value_counts()
        )

        print("\nStop matching:")

        print(
            vehicles["stop_match_status"]
            .value_counts()
        )

        print("\nOverall integration:")

        print(
            vehicles["integration_status"]
            .value_counts()
        )

        print("\nException reasons:")

        print(
            vehicles["exception_reason"]
            .value_counts()
        )

        print(
            f"\nAzure output: "
            f"silver/{blob_name}"
        )

        print(
            "\nVehicle + GTFS integration "
            "completed successfully."
        )


if __name__ == "__main__":
    main()