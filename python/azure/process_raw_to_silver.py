import os
import re
from io import StringIO
from datetime import datetime, timezone

import pandas as pd
from azure.storage.blob import BlobServiceClient


CONTAINER_RAW = "raw"
CONTAINER_SILVER = "silver"


def add_exception(exceptions, row, rule_id, rule_name, severity):
    exceptions.append({
        "vehicle_id": row.get("vehicle_id"),
        "snapshot_file": row.get("snapshot_file"),
        "rule_id": rule_id,
        "rule_name": rule_name,
        "severity": severity
    })


def main():

    # ---------------------------------------------------------
    # 1. Get Azure connection string
    # ---------------------------------------------------------

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError(
            "AZURE_STORAGE_CONNECTION_STRING environment variable is not set."
        )

    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string
    )

    raw_container = blob_service_client.get_container_client(
        CONTAINER_RAW
    )

    silver_container = blob_service_client.get_container_client(
        CONTAINER_SILVER
    )

    # ---------------------------------------------------------
    # 2. Find raw vehicle snapshots
    # ---------------------------------------------------------

    blobs = list(
        raw_container.list_blobs(
            name_starts_with="vehicle_positions_"
        )
    )

    if not blobs:
        raise FileNotFoundError(
            "No vehicle position files found in Azure raw container."
        )

    print("Raw files found:", len(blobs))

    # ---------------------------------------------------------
    # 3. Download all raw snapshots
    # ---------------------------------------------------------

    dataframes = []

    for blob in blobs:

        print("Downloading:", blob.name)

        blob_client = raw_container.get_blob_client(blob.name)

        csv_data = blob_client.download_blob().readall().decode("utf-8")

        df = pd.read_csv(StringIO(csv_data))

        # Track source snapshot
        df["snapshot_file"] = blob.name

        dataframes.append(df)

    df = pd.concat(dataframes, ignore_index=True)

    print("Raw records:", len(df))
    print("Raw columns:", len(df.columns))

    # ---------------------------------------------------------
    # 4. Data quality checks
    # ---------------------------------------------------------

    exceptions = []

    # Missing vehicle ID
    mask = df["vehicle_id"].isna()

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ001",
            "Missing Vehicle ID",
            "High"
        )

    # Invalid latitude
    mask = (
        df["latitude"].isna()
        | (df["latitude"] < -90)
        | (df["latitude"] > 90)
    )

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ002",
            "Invalid Latitude",
            "High"
        )

    # Invalid longitude
    mask = (
        df["longitude"].isna()
        | (df["longitude"] < -180)
        | (df["longitude"] > 180)
    )

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ003",
            "Invalid Longitude",
            "High"
        )

    # Invalid bearing
    mask = (
        df["bearing"].notna()
        & (
            (df["bearing"] < 0)
            | (df["bearing"] > 360)
        )
    )

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ004",
            "Invalid Bearing",
            "Medium"
        )

    # Missing route ID
    mask = df["route_id"].isna()

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ005",
            "Missing Route ID",
            "High"
        )

    # Missing trip ID
    mask = df["trip_id"].isna()

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ006",
            "Missing Trip ID",
            "High"
        )

    # Invalid timestamp
    timestamp_check = pd.to_datetime(
        df["updated_at"],
        errors="coerce"
    )

    mask = timestamp_check.isna()

    for index in df[mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ007",
            "Invalid Timestamp",
            "High"
        )

    # ---------------------------------------------------------
    # 5. Remove duplicate vehicle snapshots
    # ---------------------------------------------------------

    duplicate_mask = df.duplicated(
        subset=["vehicle_id", "snapshot_file"],
        keep="first"
    )

    for index in df[duplicate_mask].index:
        add_exception(
            exceptions,
            df.loc[index],
            "DQ008",
            "Duplicate Vehicle Snapshot",
            "Medium"
        )

    df_clean = df[~duplicate_mask].copy()

    # ---------------------------------------------------------
    # 6. Standardize timestamps
    # ---------------------------------------------------------

    df_clean["updated_at"] = pd.to_datetime(
        df_clean["updated_at"],
        errors="coerce",
        utc=True
    )

    # Extract UTC timestamp from Azure blob filename
    snapshot_match = df_clean["snapshot_file"].str.extract(
        r"vehicle_positions_(\d{8}_\d{6})"
    )[0]

    df_clean["snapshot_timestamp"] = pd.to_datetime(
        snapshot_match,
        format="%Y%m%d_%H%M%S",
        errors="coerce",
        utc=True
    )

    # ---------------------------------------------------------
    # 7. Create exception DataFrame
    # ---------------------------------------------------------

    exceptions_df = pd.DataFrame(exceptions)

    # ---------------------------------------------------------
    # 8. Convert outputs to CSV in memory
    # ---------------------------------------------------------

    clean_buffer = StringIO()
    exception_buffer = StringIO()

    df_clean.to_csv(clean_buffer, index=False)
    exceptions_df.to_csv(exception_buffer, index=False)

    # ---------------------------------------------------------
    # 9. Create timestamped Silver output names
    # ---------------------------------------------------------

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    clean_blob_name = (
        f"vehicle_positions_clean_{timestamp}.csv"
    )

    exception_blob_name = (
        f"vehicle_positions_exceptions_{timestamp}.csv"
    )

    # ---------------------------------------------------------
    # 10. Upload Silver outputs
    # ---------------------------------------------------------

    silver_container.get_blob_client(
        clean_blob_name
    ).upload_blob(
        clean_buffer.getvalue(),
        overwrite=True
    )

    silver_container.get_blob_client(
        exception_blob_name
    ).upload_blob(
        exception_buffer.getvalue(),
        overwrite=True
    )

    # ---------------------------------------------------------
    # 11. Pipeline summary
    # ---------------------------------------------------------

    print("\nSilver processing completed successfully.")

    print("Clean records:", len(df_clean))
    print("Exception records:", len(exceptions_df))

    print("\nAzure Silver container:", CONTAINER_SILVER)
    print("Clean blob:", clean_blob_name)
    print("Exception blob:", exception_blob_name)

    if not exceptions_df.empty:
        print("\nExceptions by rule:")
        print(
            exceptions_df["rule_name"].value_counts()
        )
    else:
        print("\nNo data quality exceptions found.")


if __name__ == "__main__":
    main()