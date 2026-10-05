import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

INPUT_FOLDER = Path("data/raw/gtfs/extracted")

CONTAINER_NAME = "raw"

GTFS_FILES = [
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
    "shapes.txt",
    "calendar.txt",
    "calendar_dates.txt",
]


# ---------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------

def main():

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

    container_client = (
        blob_service_client.get_container_client(
            CONTAINER_NAME
        )
    )

    print("Starting Azure GTFS ingestion...\n")

    uploaded_files = 0

    for file_name in GTFS_FILES:

        local_file = INPUT_FOLDER / file_name

        if not local_file.exists():
            raise FileNotFoundError(
                f"GTFS file not found: {local_file}"
            )

        blob_name = f"gtfs/{file_name}"

        print(f"Uploading: {file_name}")

        blob_client = container_client.get_blob_client(
            blob_name
        )

        with open(local_file, "rb") as data:

            blob_client.upload_blob(
                data,
                overwrite=True
            )

        file_size = local_file.stat().st_size

        print(f"  Size: {file_size:,} bytes")
        print(f"  Blob: {blob_name}\n")

        uploaded_files += 1

    print("Azure GTFS ingestion completed successfully.")
    print("Files uploaded:", uploaded_files)
    print("Azure container:", CONTAINER_NAME)
    print("Blob folder: gtfs/")


if __name__ == "__main__":
    main()