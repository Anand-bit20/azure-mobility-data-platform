import os
import tempfile
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient


SILVER_CONTAINER = "silver"
GOLD_CONTAINER = "gold"


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def download_blob(container, blob_name, local_path):
    print(f"Downloading: {blob_name}")

    blob_client = container.get_blob_client(blob_name)

    with open(local_path, "wb") as file:
        blob_client.download_blob().readinto(file)


def upload_dataframe(container, dataframe, blob_name, local_path):
    dataframe.to_csv(
        local_path,
        index=False
    )

    print(f"Uploading: {blob_name}")

    with open(local_path, "rb") as file:
        container.get_blob_client(
            blob_name
        ).upload_blob(
            file,
            overwrite=True
        )


def get_latest_blob(container, prefix):
    blobs = list(
        container.list_blobs(
            name_starts_with=prefix
        )
    )

    if not blobs:
        raise FileNotFoundError(
            f"No Azure blob found with prefix: {prefix}"
        )

    return max(
        blobs,
        key=lambda blob: blob.name
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    # -----------------------------------------------------
    # 1. Azure connection
    # -----------------------------------------------------

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

    gold = (
        blob_service_client.get_container_client(
            GOLD_CONTAINER
        )
    )

    # -----------------------------------------------------
    # 2. Find latest Azure datasets
    # -----------------------------------------------------

    latest_integrated = get_latest_blob(
        silver,
        "integrated/vehicle_gtfs_integrated_"
    )

    latest_schedule = get_latest_blob(
        silver,
        "analytics/schedule_performance_"
    )

    latest_movement = get_latest_blob(
        silver,
        "analytics/vehicle_movement_"
    )

    print("\nUsing datasets:")

    print(
        "Integrated:",
        latest_integrated.name
    )

    print(
        "Schedule:",
        latest_schedule.name
    )

    print(
        "Movement:",
        latest_movement.name
    )

    # -----------------------------------------------------
    # 3. Temporary workspace
    # -----------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp = Path(temp_dir)

        routes_file = temp / "routes.csv"
        stops_file = temp / "stops.csv"
        trips_file = temp / "trips.csv"

        integrated_file = temp / "integrated.csv"
        schedule_file = temp / "schedule.csv"
        movement_file = temp / "movement.csv"

        # -------------------------------------------------
        # 4. Download datasets
        # -------------------------------------------------

        print("\nDownloading Gold inputs...\n")

        download_blob(
            silver,
            "gtfs/routes_clean.csv",
            routes_file
        )

        download_blob(
            silver,
            "gtfs/stops_clean.csv",
            stops_file
        )

        download_blob(
            silver,
            "gtfs/trips_clean.csv",
            trips_file
        )

        download_blob(
            silver,
            latest_integrated.name,
            integrated_file
        )

        download_blob(
            silver,
            latest_schedule.name,
            schedule_file
        )

        download_blob(
            silver,
            latest_movement.name,
            movement_file
        )

        # =================================================
        # LOAD DATA
        # =================================================

        print("\nLoading Gold inputs...")

        routes = pd.read_csv(
            routes_file,
            dtype={
                "route_id": "string"
            },
            low_memory=False
        )

        stops = pd.read_csv(
            stops_file,
            dtype={
                "stop_id": "string"
            },
            low_memory=False
        )

        trips = pd.read_csv(
            trips_file,
            dtype={
                "trip_id": "string",
                "route_id": "string"
            },
            low_memory=False
        )

        vehicles = pd.read_csv(
            integrated_file,
            dtype={
                "vehicle_id": "string",
                "route_id": "string",
                "stop_id": "string",
                "trip_id": "string"
            },
            low_memory=False
        )

        schedule = pd.read_csv(
            schedule_file,
            dtype={
                "vehicle_id": "string",
                "route_id": "string",
                "trip_id": "string",
                "stop_id": "string",
                "schedule_status": "string"
            },
            low_memory=False
        )

        movement = pd.read_csv(
            movement_file,
            dtype={
                "vehicle_id": "string",
                "route_id": "string",
                "movement_status": "string"
            },
            low_memory=False
        )

        print(
            f"Routes: {len(routes):,}"
        )

        print(
            f"Stops: {len(stops):,}"
        )

        print(
            f"Trips: {len(trips):,}"
        )

        print(
            f"Vehicle observations: {len(vehicles):,}"
        )

        print(
            f"Schedule analytics: {len(schedule):,}"
        )

        print(
            f"Movement analytics: {len(movement):,}"
        )

        # =================================================
        # GOLD DIMENSIONS
        # =================================================

        print("\n========================================")
        print("BUILDING GOLD DIMENSIONS")
        print("========================================")

        # -------------------------------------------------
        # DIM ROUTE
        # -------------------------------------------------

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

        dim_route = (
            dim_route
            .drop_duplicates(
                subset=["route_id"]
            )
        )

        dim_route.insert(
            0,
            "route_key",
            dim_route["route_id"]
        )

        # -------------------------------------------------
        # DIM STOP
        # -------------------------------------------------

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

        dim_stop = (
            dim_stop
            .drop_duplicates(
                subset=["stop_id"]
            )
        )

        dim_stop.insert(
            0,
            "stop_key",
            dim_stop["stop_id"]
        )

        # -------------------------------------------------
        # DIM TRIP
        # -------------------------------------------------

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

        dim_trip = (
            dim_trip
            .drop_duplicates(
                subset=["trip_id"]
            )
        )

        dim_trip.insert(
            0,
            "trip_key",
            dim_trip["trip_id"]
        )

        print(
            f"dim_route: {len(dim_route):,}"
        )

        print(
            f"dim_stop: {len(dim_stop):,}"
        )

        print(
            f"dim_trip: {len(dim_trip):,}"
        )

        # =================================================
        # GOLD FACT - VEHICLE OBSERVATION
        # =================================================

        print("\nBuilding fact_vehicle_observation...")

        fact_vehicle_observation = vehicles[
            [
                "vehicle_id",
                "vehicle_label",
                "route_id",
                "stop_id",
                "trip_id",
                "latitude",
                "longitude",
                "bearing",
                "speed",
                "current_status",
                "current_stop_sequence",
                "direction_id",
                "occupancy_status",
                "revenue_status",
                "updated_at",
                "snapshot_timestamp",
                "route_match_status",
                "trip_match_status",
                "stop_match_status",
                "integration_status",
                "exception_reason"
            ]
        ].copy()

        fact_vehicle_observation.insert(
            0,
            "observation_key",
            range(
                1,
                len(fact_vehicle_observation) + 1
            )
        )

        fact_vehicle_observation[
            "updated_at"
        ] = pd.to_datetime(
            fact_vehicle_observation[
                "updated_at"
            ],
            errors="coerce",
            utc=True
        )

        fact_vehicle_observation[
            "snapshot_timestamp"
        ] = pd.to_datetime(
            fact_vehicle_observation[
                "snapshot_timestamp"
            ],
            errors="coerce",
            utc=True
        )

        fact_vehicle_observation[
            "date_key"
        ] = (
            fact_vehicle_observation[
                "snapshot_timestamp"
            ]
            .dt.strftime("%Y%m%d")
            .astype("Int64")
        )

        # =================================================
        # GOLD FACT - VEHICLE MOVEMENT
        # =================================================

        print("Building fact_vehicle_movement...")

        fact_vehicle_movement = movement[
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
        ].copy()

        fact_vehicle_movement.insert(
            0,
            "movement_key",
            range(
                1,
                len(fact_vehicle_movement) + 1
            )
        )

        fact_vehicle_movement[
            "snapshot_timestamp"
        ] = pd.to_datetime(
            fact_vehicle_movement[
                "snapshot_timestamp"
            ],
            errors="coerce",
            utc=True
        )

        fact_vehicle_movement[
            "previous_snapshot_timestamp"
        ] = pd.to_datetime(
            fact_vehicle_movement[
                "previous_snapshot_timestamp"
            ],
            errors="coerce",
            utc=True
        )

        fact_vehicle_movement[
            "date_key"
        ] = (
            fact_vehicle_movement[
                "snapshot_timestamp"
            ]
            .dt.strftime("%Y%m%d")
            .astype("Int64")
        )

        # =================================================
        # GOLD FACT - SCHEDULE PERFORMANCE
        # =================================================

        print("Building fact_schedule_performance...")

        fact_schedule_performance = schedule[
            [
                "vehicle_id",
                "route_id",
                "trip_id",
                "stop_id",
                "snapshot_timestamp",
                "local_observation_time",
                "scheduled_arrival_datetime",
                "scheduled_departure_datetime",
                "arrival_deviation_minutes",
                "departure_deviation_minutes",
                "schedule_status"
            ]
        ].copy()

        fact_schedule_performance.insert(
            0,
            "performance_key",
            range(
                1,
                len(fact_schedule_performance) + 1
            )
        )

        timestamp_columns = [
            "snapshot_timestamp",
            "local_observation_time",
            "scheduled_arrival_datetime",
            "scheduled_departure_datetime"
        ]

        for column in timestamp_columns:

            fact_schedule_performance[
                column
            ] = pd.to_datetime(
                fact_schedule_performance[
                    column
                ],
                errors="coerce",
                utc=True
            )

        fact_schedule_performance[
            "date_key"
        ] = (
            fact_schedule_performance[
                "local_observation_time"
            ]
            .dt.strftime("%Y%m%d")
            .astype("Int64")
        )

        # =================================================
        # DIM DATE
        # =================================================

        print("Building dim_date...")

        movement_dates = (
            fact_vehicle_movement[
                "snapshot_timestamp"
            ]
            .dropna()
            .dt.date
        )

        schedule_dates = (
            fact_schedule_performance[
                "local_observation_time"
            ]
            .dropna()
            .dt.date
        )

        observation_dates = (
            fact_vehicle_observation[
                "snapshot_timestamp"
            ]
            .dropna()
            .dt.date
        )

        all_dates = pd.Series(
            list(movement_dates)
            + list(schedule_dates)
            + list(observation_dates)
        )

        if all_dates.empty:
            raise ValueError(
                "No valid dates found for dim_date."
            )

        start_date = min(all_dates)
        end_date = max(all_dates)

        dates = pd.date_range(
            start=start_date,
            end=end_date,
            freq="D"
        )

        dim_date = pd.DataFrame({
            "date": dates
        })

        dim_date["date_key"] = (
            dim_date["date"]
            .dt.strftime("%Y%m%d")
            .astype(int)
        )

        dim_date["year"] = (
            dim_date["date"].dt.year
        )

        dim_date["quarter"] = (
            dim_date["date"].dt.quarter
        )

        dim_date["quarter_name"] = (
            "Q"
            + dim_date["quarter"].astype(str)
        )

        dim_date["month"] = (
            dim_date["date"].dt.month
        )

        dim_date["month_name"] = (
            dim_date["date"].dt.month_name()
        )

        dim_date["month_short_name"] = (
            dim_date["date"].dt.strftime("%b")
        )

        dim_date["week_of_year"] = (
            dim_date["date"]
            .dt.isocalendar()
            .week
            .astype(int)
        )

        dim_date["day"] = (
            dim_date["date"].dt.day
        )

        dim_date["day_of_week"] = (
            dim_date["date"].dt.dayofweek + 1
        )

        dim_date["day_name"] = (
            dim_date["date"].dt.day_name()
        )

        dim_date["is_weekend"] = (
            dim_date["date"].dt.dayofweek >= 5
        )

        # =================================================
        # GOLD VALIDATION
        # =================================================

        print("\n========================================")
        print("GOLD LAYER VALIDATION")
        print("========================================")

        route_keys = set(
            dim_route[
                "route_key"
            ].dropna()
        )

        stop_keys = set(
            dim_stop[
                "stop_key"
            ].dropna()
        )

        trip_keys = set(
            dim_trip[
                "trip_key"
            ].dropna()
        )

        # Dimension duplicate checks

        route_duplicates = (
            dim_route[
                "route_key"
            ].duplicated().sum()
        )

        stop_duplicates = (
            dim_stop[
                "stop_key"
            ].duplicated().sum()
        )

        trip_duplicates = (
            dim_trip[
                "trip_key"
            ].duplicated().sum()
        )

        date_duplicates = (
            dim_date[
                "date_key"
            ].duplicated().sum()
        )

        # -------------------------------------------------
        # Observation referential integrity
        #
        # Only FULL_MATCH records are expected to have
        # complete GTFS foreign-key relationships.
        # PARTIAL_MATCH rows are deliberately retained.
        # -------------------------------------------------

        full_observations = (
            fact_vehicle_observation[
                fact_vehicle_observation[
                    "integration_status"
                ] == "FULL_MATCH"
            ]
        )

        observation_invalid_routes = (
            full_observations[
                "route_id"
            ].notna()
            & ~full_observations[
                "route_id"
            ].isin(route_keys)
        ).sum()

        observation_invalid_stops = (
            full_observations[
                "stop_id"
            ].notna()
            & ~full_observations[
                "stop_id"
            ].isin(stop_keys)
        ).sum()

        observation_invalid_trips = (
            full_observations[
                "trip_id"
            ].notna()
            & ~full_observations[
                "trip_id"
            ].isin(trip_keys)
        ).sum()

        # Movement validation

        movement_invalid_routes = (
            fact_vehicle_movement[
                "route_id"
            ].notna()
            & ~fact_vehicle_movement[
                "route_id"
            ].isin(route_keys)
        ).sum()

        negative_distance = (
            fact_vehicle_movement[
                "distance_km"
            ] < 0
        ).sum()

        negative_time = (
            fact_vehicle_movement[
                "time_difference_seconds"
            ] < 0
        ).sum()

        # Schedule referential integrity

        schedule_invalid_routes = (
            fact_schedule_performance[
                "route_id"
            ].notna()
            & ~fact_schedule_performance[
                "route_id"
            ].isin(route_keys)
        ).sum()

        schedule_invalid_stops = (
            fact_schedule_performance[
                "stop_id"
            ].notna()
            & ~fact_schedule_performance[
                "stop_id"
            ].isin(stop_keys)
        ).sum()

        schedule_invalid_trips = (
            fact_schedule_performance[
                "trip_id"
            ].notna()
            & ~fact_schedule_performance[
                "trip_id"
            ].isin(trip_keys)
        ).sum()

        missing_arrival_deviation = (
            fact_schedule_performance[
                "arrival_deviation_minutes"
            ].isna().sum()
        )

        # Status validation

        valid_movement_statuses = {
            "VALID",
            "DATA_GAP",
            "STATIONARY"
        }

        valid_schedule_statuses = {
            "ON_TIME",
            "DELAYED",
            "EARLY"
        }

        movement_status_check = (
            set(
                fact_vehicle_movement[
                    "movement_status"
                ]
                .dropna()
                .unique()
            )
            .issubset(
                valid_movement_statuses
            )
        )

        schedule_status_check = (
            set(
                fact_schedule_performance[
                    "schedule_status"
                ]
                .dropna()
                .unique()
            )
            .issubset(
                valid_schedule_statuses
            )
        )

        # -------------------------------------------------
        # Validation report
        # -------------------------------------------------

        validation_results = [
            (
                "Duplicate route keys",
                route_duplicates
            ),
            (
                "Duplicate stop keys",
                stop_duplicates
            ),
            (
                "Duplicate trip keys",
                trip_duplicates
            ),
            (
                "Duplicate date keys",
                date_duplicates
            ),
            (
                "FULL_MATCH observation invalid routes",
                observation_invalid_routes
            ),
            (
                "FULL_MATCH observation invalid stops",
                observation_invalid_stops
            ),
            (
                "FULL_MATCH observation invalid trips",
                observation_invalid_trips
            ),
            (
                "Movement invalid routes",
                movement_invalid_routes
            ),
            (
                "Schedule invalid routes",
                schedule_invalid_routes
            ),
            (
                "Schedule invalid stops",
                schedule_invalid_stops
            ),
            (
                "Schedule invalid trips",
                schedule_invalid_trips
            ),
            (
                "Negative movement distances",
                negative_distance
            ),
            (
                "Negative movement time differences",
                negative_time
            ),
            (
                "Missing arrival deviations",
                missing_arrival_deviation
            )
        ]

        validation_df = pd.DataFrame(
            validation_results,
            columns=[
                "check",
                "count"
            ]
        )

        validation_df["status"] = (
            validation_df[
                "count"
            ].apply(
                lambda count:
                "PASS"
                if count == 0
                else "CHECK"
            )
        )

        # Add boolean status validations

        extra_validation = pd.DataFrame(
            [
                {
                    "check":
                    "Movement statuses valid",
                    "count":
                    0 if movement_status_check else 1,
                    "status":
                    (
                        "PASS"
                        if movement_status_check
                        else "CHECK"
                    )
                },
                {
                    "check":
                    "Schedule statuses valid",
                    "count":
                    0 if schedule_status_check else 1,
                    "status":
                    (
                        "PASS"
                        if schedule_status_check
                        else "CHECK"
                    )
                }
            ]
        )

        validation_df = pd.concat(
            [
                validation_df,
                extra_validation
            ],
            ignore_index=True
        )

        critical_checks_passed = (
            (
                validation_df[
                    "count"
                ] == 0
            ).all()
        )

        # =================================================
        # UPLOAD GOLD TABLES
        # =================================================

        print("\n========================================")
        print("UPLOADING GOLD LAYER")
        print("========================================\n")

        outputs = [
            (
                dim_route,
                "dimensions/dim_route.csv"
            ),
            (
                dim_stop,
                "dimensions/dim_stop.csv"
            ),
            (
                dim_trip,
                "dimensions/dim_trip.csv"
            ),
            (
                dim_date,
                "dimensions/dim_date.csv"
            ),
            (
                fact_vehicle_observation,
                "facts/fact_vehicle_observation.csv"
            ),
            (
                fact_vehicle_movement,
                "facts/fact_vehicle_movement.csv"
            ),
            (
                fact_schedule_performance,
                "facts/fact_schedule_performance.csv"
            ),
            (
                validation_df,
                "reports/gold_validation_summary.csv"
            )
        ]

        for dataframe, blob_name in outputs:

            local_file = (
                temp /
                Path(blob_name).name
            )

            upload_dataframe(
                gold,
                dataframe,
                blob_name,
                local_file
            )

        # =================================================
        # FINAL SUMMARY
        # =================================================

        print("\n========================================")
        print("AZURE GOLD LAYER SUMMARY")
        print("========================================")

        print(
            f"dim_route:                 "
            f"{len(dim_route):,}"
        )

        print(
            f"dim_stop:                  "
            f"{len(dim_stop):,}"
        )

        print(
            f"dim_trip:                  "
            f"{len(dim_trip):,}"
        )

        print(
            f"dim_date:                  "
            f"{len(dim_date):,}"
        )

        print(
            f"fact_vehicle_observation:  "
            f"{len(fact_vehicle_observation):,}"
        )

        print(
            f"fact_vehicle_movement:     "
            f"{len(fact_vehicle_movement):,}"
        )

        print(
            f"fact_schedule_performance: "
            f"{len(fact_schedule_performance):,}"
        )

        print("\nMovement status:")

        print(
            fact_vehicle_movement[
                "movement_status"
            ].value_counts()
        )

        print("\nSchedule status:")

        print(
            fact_schedule_performance[
                "schedule_status"
            ].value_counts()
        )

        print("\nValidation:")

        print(
            validation_df.to_string(
                index=False
            )
        )

        print("\n========================================")

        if critical_checks_passed:
            print(
                "GOLD LAYER VALIDATION: PASSED"
            )
        else:
            print(
                "GOLD LAYER VALIDATION: CHECK REQUIRED"
            )

        print("========================================")

        print(
            "\nGold layer created successfully."
        )


if __name__ == "__main__":
    main()