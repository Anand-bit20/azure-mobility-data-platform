import requests
import pandas as pd
import urllib3
from datetime import datetime, timezone
from pathlib import Path


# Suppress SSL warning for our local testing environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://api-v3.mbta.com/vehicles"

# Get current vehicle data
response = requests.get(
    URL,
    timeout=30,
    verify=False
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

# Convert to DataFrame
df = pd.DataFrame(records)

# Create UTC timestamp for the snapshot
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
ingestion_timestamp = datetime.now(timezone.utc).isoformat()

# Create output folder
output_folder = Path("data/raw/vehicle_positions")
output_folder.mkdir(parents=True, exist_ok=True)

# Create timestamped filename
output_path = output_folder / f"vehicle_positions_{timestamp}.csv"

# Save snapshot
df.to_csv(output_path, index=False)

# Create ingestion log
log_path = output_folder / "ingestion_log.csv"

log_record = pd.DataFrame([{
    "ingestion_timestamp": ingestion_timestamp,
    "file_name": output_path.name,
    "record_count": len(df),
    "status": "SUCCESS"
}])

if log_path.exists():
    log_record.to_csv(log_path, mode="a", header=False, index=False)
else:
    log_record.to_csv(log_path, index=False)

print("Data successfully retrieved.")
print("Total vehicles:", len(df))
print("Saved to:", output_path)
print("Ingestion log updated:", log_path)

print("\nColumns:")
print(df.columns.tolist())

print("\nSample data:")
print(df.head())