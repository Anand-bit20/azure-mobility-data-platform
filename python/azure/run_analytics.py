import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from azure.storage.blob import BlobServiceClient


SILVER_CONTAINER = "silver"
MAX_GAP_SECONDS = 15 * 60


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def download_blob(container, blob_name, local_path):
    print(f"Downloading: {blob_name}")

    blob_client = container.get_blob_client(blob_name)

    with open(local_path, "wb") as file:
        blob_client.download_blob().readinto(file)


def upload_file(container, local_path, blob_name):
    print(f"Uploading: {blob_name}")

    with open(local_path, "rb") as file:
        container.get_blob_client(
            blob_name
        ).upload_blob(
            file,
            overwrite=True
        )


def gtfs_time_to_seconds(value):
    if pd.isna(value):
        return pd.NA

    try:
        parts = str(value).split(":")

        if len(parts) != 3:
            return pd.NA

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])

        return (
            hours * 3600
            + minutes * 60
            + seconds
        )

    except (ValueError, TypeError):
        return pd.NA


def haversine_distance(lat1, lon1, lat2, lon2):

    earth_radius_km = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(delta_lon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))

    return earth_radius_km * c


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

    silver = (
        blob_service_client.get_container_client(
            SILVER_CONTAINER
        )
    )

    # ---------------------------------------------------------
    # 2. Find latest datasets
    # ---------------------------------------------------------

    vehicle_blobs = list(
        silver.list_blobs(
            name_starts_with="vehicle_positions_clean_"
        )
    )

    integrated_blobs = list(
        silver.list_blobs(
            name_starts_with=(
                "integrated/"
                "vehicle_gtfs_integrated_"
            )
        )
    )

    if not vehicle_blobs:
        raise FileNotFoundError(
            "No Silver vehicle dataset found."
        )

    if not integrated_blobs:
        raise FileNotFoundError(
            "No integrated Silver dataset found."
        )

    latest_vehicle = max(
        vehicle_blobs,
        key=lambda blob: blob.name
    )

    latest_integrated = max(
        integrated_blobs,
        key=lambda blob: blob.name
    )

    print(
        "Latest vehicle dataset:",
        latest_vehicle.name
    )

    print(
        "Latest integrated dataset:",
        latest_integrated.name
    )

    # ---------------------------------------------------------
    # 3. Temporary workspace
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp = Path(temp_dir)

        vehicle_file = temp / "vehicles.csv"
        integrated_file = temp / "integrated.csv"
        trips_file = temp / "trips.csv"
        stop_times_file = temp / "stop_times.csv"

        # -----------------------------------------------------
        # 4. Download required Silver datasets
        # -----------------------------------------------------

        print("\nDownloading analytics inputs...\n")

        download_blob(
            silver,
            latest_vehicle.name,
            vehicle_file
        )

        download_blob(
            silver,
            latest_integrated.name,
            integrated_file
        )

        download_blob(
            silver,
            "gtfs/trips_clean.csv",
            trips_file
        )

        download_blob(
            silver,
            "gtfs/stop_times_clean.csv",
            stop_times_file
        )

        # =====================================================
        # SCHEDULE ANALYTICS
        # =====================================================

        print("\n========================================")
        print("BUILDING SCHEDULE ANALYTICS")
        print("========================================")

        # -----------------------------------------------------
        # 5. Load GTFS trips
        # -----------------------------------------------------

        trips = pd.read_csv(
            trips_file,
            dtype={
                "trip_id": "string",
                "route_id": "string",
                "service_id": "string",
                "trip_headsign": "string",
                "shape_id": "string",
                "route_pattern_id": "string"
            },
            low_memory=False
        )

        # -----------------------------------------------------
        # 6. Load GTFS stop times
        # -----------------------------------------------------

        stop_times = pd.read_csv(
            stop_times_file,
            dtype={
                "trip_id": "string",
                "stop_id": "string",
                "stop_sequence": "Int64"
            },
            low_memory=False
        )

        print(
            f"Trips loaded: {len(trips):,}"
        )

        print(
            f"Stop times loaded: {len(stop_times):,}"
        )

        # -----------------------------------------------------
        # 7. Build temporary schedule reference
        # -----------------------------------------------------

        schedule = stop_times[
            [
                "trip_id",
                "arrival_time",
                "departure_time",
                "stop_id",
                "stop_sequence"
            ]
        ].copy()

        schedule = schedule.merge(
            trips[
                [
                    "trip_id",
                    "route_id",
                    "service_id",
                    "trip_headsign",
                    "direction_id",
                    "shape_id",
                    "route_pattern_id"
                ]
            ],
            on="trip_id",
            how="left"
        )

        schedule["arrival_seconds"] = (
            schedule["arrival_time"]
            .apply(gtfs_time_to_seconds)
            .astype("Int64")
        )

        schedule["departure_seconds"] = (
            schedule["departure_time"]
            .apply(gtfs_time_to_seconds)
            .astype("Int64")
        )

        print(
            f"Schedule reference records: "
            f"{len(schedule):,}"
        )

        # -----------------------------------------------------
        # 8. Load integrated vehicle data
        # -----------------------------------------------------

        vehicles = pd.read_csv(
            integrated_file,
            dtype={
                "vehicle_id": "string",
                "route_id": "string",
                "trip_id": "string",
                "stop_id": "string"
            },
            low_memory=False
        )

        vehicles = vehicles[
            (
                vehicles["trip_match_status"]
                == "MATCHED"
            )
            & (
                vehicles["stop_match_status"]
                == "MATCHED"
            )
        ].copy()

        print(
            "Matched trip + stop observations:",
            len(vehicles)
        )

        # -----------------------------------------------------
        # 9. Join vehicle observations to schedule
        # -----------------------------------------------------

        performance = vehicles.merge(
            schedule[
                [
                    "trip_id",
                    "route_id",
                    "stop_id",
                    "stop_sequence",
                    "arrival_time",
                    "departure_time",
                    "arrival_seconds",
                    "departure_seconds"
                ]
            ],
            on=[
                "trip_id",
                "route_id",
                "stop_id"
            ],
            how="inner"
        )

        print(
            "Schedule-matched observations:",
            len(performance)
        )

        # -----------------------------------------------------
        # 10. Timestamp conversion
        # -----------------------------------------------------

        performance["updated_at"] = (
            pd.to_datetime(
                performance["updated_at"],
                errors="coerce",
                utc=True
            )
        )

        performance["snapshot_timestamp"] = (
            pd.to_datetime(
                performance["snapshot_timestamp"],
                errors="coerce",
                utc=True
            )
        )

        performance["local_observation_time"] = (
            performance["updated_at"]
            .dt.tz_convert(
                "America/New_York"
            )
        )

        performance["observation_date"] = (
            performance[
                "local_observation_time"
            ]
            .dt.date
        )

        # -----------------------------------------------------
        # 11. Scheduled datetime
        # -----------------------------------------------------

        performance[
            "scheduled_arrival_datetime"
        ] = (
            pd.to_datetime(
                performance[
                    "observation_date"
                ].astype(str)
            )
            + pd.to_timedelta(
                performance["arrival_seconds"],
                unit="s"
            )
        )

        performance[
            "scheduled_departure_datetime"
        ] = (
            pd.to_datetime(
                performance[
                    "observation_date"
                ].astype(str)
            )
            + pd.to_timedelta(
                performance[
                    "departure_seconds"
                ],
                unit="s"
            )
        )

        performance[
            "scheduled_arrival_datetime"
        ] = (
            performance[
                "scheduled_arrival_datetime"
            ]
            .dt.tz_localize(
                "America/New_York",
                ambiguous="NaT",
                nonexistent="shift_forward"
            )
        )

        performance[
            "scheduled_departure_datetime"
        ] = (
            performance[
                "scheduled_departure_datetime"
            ]
            .dt.tz_localize(
                "America/New_York",
                ambiguous="NaT",
                nonexistent="shift_forward"
            )
        )

        # -----------------------------------------------------
        # 12. Schedule deviation
        # -----------------------------------------------------

        performance[
            "arrival_deviation_minutes"
        ] = (
            (
                performance[
                    "local_observation_time"
                ]
                - performance[
                    "scheduled_arrival_datetime"
                ]
            )
            .dt.total_seconds()
            / 60
        )

        performance[
            "departure_deviation_minutes"
        ] = (
            (
                performance[
                    "local_observation_time"
                ]
                - performance[
                    "scheduled_departure_datetime"
                ]
            )
            .dt.total_seconds()
            / 60
        )

        performance["schedule_status"] = (
            "ON_TIME"
        )

        performance.loc[
            performance[
                "arrival_deviation_minutes"
            ] < -5,
            "schedule_status"
        ] = "EARLY"

        performance.loc[
            performance[
                "arrival_deviation_minutes"
            ] > 5,
            "schedule_status"
        ] = "DELAYED"

        # =====================================================
        # VEHICLE MOVEMENT ANALYTICS
        # =====================================================

        print("\n========================================")
        print("BUILDING VEHICLE MOVEMENT ANALYTICS")
        print("========================================")

        movement = pd.read_csv(
            vehicle_file,
            dtype={
                "vehicle_id": "string",
                "route_id": "string"
            },
            low_memory=False
        )

        movement["snapshot_timestamp"] = (
            pd.to_datetime(
                movement[
                    "snapshot_timestamp"
                ],
                errors="coerce",
                utc=True
            )
        )

        movement = movement.sort_values(
            [
                "vehicle_id",
                "snapshot_timestamp"
            ]
        ).reset_index(drop=True)

        movement[
            "previous_snapshot_timestamp"
        ] = (
            movement.groupby(
                "vehicle_id"
            )["snapshot_timestamp"]
            .shift(1)
        )

        movement["previous_latitude"] = (
            movement.groupby(
                "vehicle_id"
            )["latitude"]
            .shift(1)
        )

        movement["previous_longitude"] = (
            movement.groupby(
                "vehicle_id"
            )["longitude"]
            .shift(1)
        )

        movement[
            "time_difference_seconds"
        ] = (
            movement["snapshot_timestamp"]
            - movement[
                "previous_snapshot_timestamp"
            ]
        ).dt.total_seconds()

        movement["distance_km"] = (
            haversine_distance(
                movement[
                    "previous_latitude"
                ],
                movement[
                    "previous_longitude"
                ],
                movement["latitude"],
                movement["longitude"]
            )
        )

        valid_gap = (
            movement[
                "previous_snapshot_timestamp"
            ].notna()
            & (
                movement[
                    "time_difference_seconds"
                ] > 0
            )
            & (
                movement[
                    "time_difference_seconds"
                ] <= MAX_GAP_SECONDS
            )
        )

        movement[
            "calculated_speed_kmh"
        ] = np.nan

        movement.loc[
            valid_gap,
            "calculated_speed_kmh"
        ] = (
            movement.loc[
                valid_gap,
                "distance_km"
            ]
            / (
                movement.loc[
                    valid_gap,
                    "time_difference_seconds"
                ]
                / 3600
            )
        )

        movement[
            "movement_status"
        ] = "DATA_GAP"

        movement.loc[
            valid_gap,
            "movement_status"
        ] = "VALID"

        stationary = (
            valid_gap
            & (
                movement[
                    "distance_km"
                ] == 0
            )
        )

        movement.loc[
            stationary,
            "movement_status"
        ] = "STATIONARY"

        movement_df = movement[
            movement[
                "previous_snapshot_timestamp"
            ].notna()
        ].copy()

        movement_df = movement_df[
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
        ]

        movement_df[
            "distance_km"
        ] = (
            movement_df[
                "distance_km"
            ].round(4)
        )

        movement_df[
            "calculated_speed_kmh"
        ] = (
            movement_df[
                "calculated_speed_kmh"
            ].round(2)
        )

        movement_df[
            "time_difference_seconds"
        ] = (
            movement_df[
                "time_difference_seconds"
            ].round(0)
        )

        # -----------------------------------------------------
        # 13. Save analytics outputs
        # -----------------------------------------------------

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

        performance_file = (
            temp /
            f"schedule_performance_"
            f"{timestamp}.csv"
        )

        movement_file = (
            temp /
            f"vehicle_movement_"
            f"{timestamp}.csv"
        )

        performance.to_csv(
            performance_file,
            index=False
        )

        movement_df.to_csv(
            movement_file,
            index=False
        )

        performance_blob = (
            "analytics/"
            f"schedule_performance_"
            f"{timestamp}.csv"
        )

        movement_blob = (
            "analytics/"
            f"vehicle_movement_"
            f"{timestamp}.csv"
        )

        print("\nUploading analytics outputs...\n")

        upload_file(
            silver,
            performance_file,
            performance_blob
        )

        upload_file(
            silver,
            movement_file,
            movement_blob
        )

        # -----------------------------------------------------
        # 14. Final summary
        # -----------------------------------------------------

        print("\n========================================")
        print("AZURE ANALYTICS SUMMARY")
        print("========================================")

        print(
            f"Schedule performance records: "
            f"{len(performance):,}"
        )

        if not performance.empty:

            print("\nSchedule status:")

            print(
                performance[
                    "schedule_status"
                ].value_counts()
            )

        print(
            f"\nMovement records: "
            f"{len(movement_df):,}"
        )

        if not movement_df.empty:

            print("\nMovement status:")

            print(
                movement_df[
                    "movement_status"
                ].value_counts()
            )

        print(
            f"\nSchedule output: "
            f"silver/{performance_blob}"
        )

        print(
            f"Movement output: "
            f"silver/{movement_blob}"
        )

        print(
            "\nAzure analytics completed successfully."
        )


if __name__ == "__main__":
    main()