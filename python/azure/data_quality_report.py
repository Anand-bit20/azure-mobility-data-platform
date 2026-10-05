import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient


SILVER_CONTAINER = "silver"


def percentage(value, total):
    if total == 0:
        return 0

    return round(
        (value / total) * 100,
        2
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

    silver_container = (
        blob_service_client.get_container_client(
            SILVER_CONTAINER
        )
    )

    # ---------------------------------------------------------
    # 2. Find latest integrated dataset
    # ---------------------------------------------------------

    integrated_blobs = list(
        silver_container.list_blobs(
            name_starts_with=(
                "integrated/"
                "vehicle_gtfs_integrated_"
            )
        )
    )

    if not integrated_blobs:
        raise FileNotFoundError(
            "No integrated vehicle + GTFS dataset "
            "found in Azure Silver container."
        )

    latest_blob = max(
        integrated_blobs,
        key=lambda blob: blob.name
    )

    print(
        "Latest integrated dataset:",
        latest_blob.name
    )

    # ---------------------------------------------------------
    # 3. Temporary working directory
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        input_file = (
            temp_path /
            "vehicle_gtfs_integrated.csv"
        )

        # -----------------------------------------------------
        # 4. Download integrated dataset
        # -----------------------------------------------------

        print("\nDownloading integrated dataset...")

        blob_client = (
            silver_container.get_blob_client(
                latest_blob.name
            )
        )

        with open(input_file, "wb") as file:
            blob_client.download_blob().readinto(file)

        # -----------------------------------------------------
        # 5. Load dataset
        # -----------------------------------------------------

        print("\nLoading integrated vehicle data...")

        df = pd.read_csv(
            input_file,
            low_memory=False
        )

        total_records = len(df)

        print(
            f"Records loaded: {total_records:,}"
        )

        # -----------------------------------------------------
        # 6. Basic data-quality checks
        # -----------------------------------------------------

        duplicate_records = (
            df.duplicated().sum()
        )

        missing_vehicle_id = (
            df["vehicle_id"].isna().sum()
        )

        missing_latitude = (
            df["latitude"].isna().sum()
        )

        missing_longitude = (
            df["longitude"].isna().sum()
        )

        invalid_latitude = (
            df["latitude"].notna()
            & ~df["latitude"].between(
                -90,
                90
            )
        ).sum()

        invalid_longitude = (
            df["longitude"].notna()
            & ~df["longitude"].between(
                -180,
                180
            )
        ).sum()

        # -----------------------------------------------------
        # 7. Integration matching metrics
        # -----------------------------------------------------

        route_matched = (
            df["route_match_status"]
            == "MATCHED"
        ).sum()

        trip_matched = (
            df["trip_match_status"]
            == "MATCHED"
        ).sum()

        stop_matched = (
            df["stop_match_status"]
            == "MATCHED"
        ).sum()

        full_match = (
            df["integration_status"]
            == "FULL_MATCH"
        ).sum()

        partial_match = (
            df["integration_status"]
            == "PARTIAL_MATCH"
        ).sum()

        # -----------------------------------------------------
        # 8. Create quality report
        # -----------------------------------------------------

        quality_metrics = [
            {
                "metric": "Total Records",
                "value": total_records,
                "percentage": 100.00
            },
            {
                "metric": "Duplicate Records",
                "value": duplicate_records,
                "percentage": percentage(
                    duplicate_records,
                    total_records
                )
            },
            {
                "metric": "Missing Vehicle ID",
                "value": missing_vehicle_id,
                "percentage": percentage(
                    missing_vehicle_id,
                    total_records
                )
            },
            {
                "metric": "Missing Latitude",
                "value": missing_latitude,
                "percentage": percentage(
                    missing_latitude,
                    total_records
                )
            },
            {
                "metric": "Missing Longitude",
                "value": missing_longitude,
                "percentage": percentage(
                    missing_longitude,
                    total_records
                )
            },
            {
                "metric": "Invalid Latitude",
                "value": invalid_latitude,
                "percentage": percentage(
                    invalid_latitude,
                    total_records
                )
            },
            {
                "metric": "Invalid Longitude",
                "value": invalid_longitude,
                "percentage": percentage(
                    invalid_longitude,
                    total_records
                )
            },
            {
                "metric": "Route Match",
                "value": route_matched,
                "percentage": percentage(
                    route_matched,
                    total_records
                )
            },
            {
                "metric": "Trip Match",
                "value": trip_matched,
                "percentage": percentage(
                    trip_matched,
                    total_records
                )
            },
            {
                "metric": "Stop Match",
                "value": stop_matched,
                "percentage": percentage(
                    stop_matched,
                    total_records
                )
            },
            {
                "metric": "Full Integration",
                "value": full_match,
                "percentage": percentage(
                    full_match,
                    total_records
                )
            },
            {
                "metric": "Partial Integration",
                "value": partial_match,
                "percentage": percentage(
                    partial_match,
                    total_records
                )
            }
        ]

        quality_report = pd.DataFrame(
            quality_metrics
        )

        # -----------------------------------------------------
        # 9. Exception summary
        # -----------------------------------------------------

        exception_summary = (
            df["exception_reason"]
            .value_counts()
            .rename_axis("exception_reason")
            .reset_index(name="count")
        )

        exception_summary["percentage"] = (
            exception_summary["count"]
            .apply(
                lambda value:
                percentage(
                    value,
                    total_records
                )
            )
        )

        # -----------------------------------------------------
        # 10. Create timestamped outputs
        # -----------------------------------------------------

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

        quality_file = (
            temp_path /
            f"data_quality_report_"
            f"{timestamp}.csv"
        )

        exception_file = (
            temp_path /
            f"integration_exception_summary_"
            f"{timestamp}.csv"
        )

        quality_report.to_csv(
            quality_file,
            index=False
        )

        exception_summary.to_csv(
            exception_file,
            index=False
        )

        # -----------------------------------------------------
        # 11. Upload reports
        # -----------------------------------------------------

        quality_blob_name = (
            "reports/"
            f"data_quality_report_"
            f"{timestamp}.csv"
        )

        exception_blob_name = (
            "reports/"
            f"integration_exception_summary_"
            f"{timestamp}.csv"
        )

        print("\nUploading reports...")

        with open(
            quality_file,
            "rb"
        ) as file:

            silver_container.get_blob_client(
                quality_blob_name
            ).upload_blob(
                file,
                overwrite=True
            )

        with open(
            exception_file,
            "rb"
        ) as file:

            silver_container.get_blob_client(
                exception_blob_name
            ).upload_blob(
                file,
                overwrite=True
            )

        # -----------------------------------------------------
        # 12. Display summary
        # -----------------------------------------------------

        print("\n========================================")
        print("AZURE DATA QUALITY REPORT")
        print("========================================")

        print(
            quality_report.to_string(
                index=False
            )
        )

        print("\n========================================")
        print("EXCEPTION BREAKDOWN")
        print("========================================")

        print(
            exception_summary.to_string(
                index=False
            )
        )

        print(
            f"\nQuality report: "
            f"silver/{quality_blob_name}"
        )

        print(
            f"Exception report: "
            f"silver/{exception_blob_name}"
        )

        print(
            "\nData quality report "
            "completed successfully."
        )


if __name__ == "__main__":
    main()