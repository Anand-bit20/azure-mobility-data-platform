import os
import requests
import pandas as pd
from datetime import datetime, timezone
from io import StringIO
from azure.storage.blob import BlobServiceClient


URL = "https://api-v3.mbta.com/vehicles"
CONTAINER_NAME = "raw"


def main():
    # Get current vehicle data
    response = requests.get(
        URL,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()["data"]

    # Extract useful fields
    records = []

    for vehicle in data:
        attributes = vehicle["attributes"]
        relationships = vehicle["relationships"]

        route = relationships.get("route", {}).get("data")
        stop = relationships.get("stop", {}).get("data")
        trip = relationships.get("trip", {}).get("data")

        records.append({
            "vehicle_id": vehicle["id"],
            "vehicle_label": attributes.get("label"),
            "latitude": attributes.get("latitude"),
            "longitude": attributes.get("longitude"),
            "bearing": attributes.get("bearing"),
            "speed": attributes.get("speed"),
            "current_status": attributes.get("current_status"),
            "current_stop_sequence": attributes.get("current_stop_sequence"),
            "direction_id": attributes.get("direction_id"),
            "occupancy_status": attributes.get("occupancy_status"),
            "revenue_status": attributes.get("revenue"),
            "updated_at": attributes.get("updated_at"),
            "route_id": route.get("id") if route else None,
            "stop_id": stop.get("id") if stop else None,
            "trip_id": trip.get("id") if trip else None
        })

    df = pd.DataFrame(records)

    # Create UTC timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Convert dataframe to CSV in memory
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_data = csv_buffer.getvalue()

    # Get Azure connection string from environment variable
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError(
            "AZURE_STORAGE_CONNECTION_STRING environment variable is not set."
        )

    # Connect to Azure Blob Storage
    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string
    )

    container_client = blob_service_client.get_container_client(
        CONTAINER_NAME
    )

    # Create timestamped blob name
    blob_name = f"vehicle_positions_{timestamp}.csv"

    # Upload CSV to Azure Blob Storage
    blob_client = container_client.get_blob_client(blob_name)

    blob_client.upload_blob(
        csv_data,
        overwrite=True
    )

    print("Azure ingestion completed successfully.")
    print("Total vehicles:", len(df))
    print("Snapshot timestamp:", timestamp)
    print("CSV size:", len(csv_data), "bytes")
    print("Azure container:", CONTAINER_NAME)
    print("Blob name:", blob_name)


if __name__ == "__main__":
    main()