import pandas as pd
import numpy as np
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_file = Path("data/processed/vehicle_positions_clean.csv")
output_folder = Path("data/processed")

output_folder.mkdir(parents=True, exist_ok=True)

output_file = output_folder / "vehicle_movement.csv"


# ---------------------------------------------------------
# 2. Load Silver vehicle data
# ---------------------------------------------------------

df = pd.read_csv(input_file)

print("Loaded records:", len(df))


# ---------------------------------------------------------
# 3. Convert timestamps
# ---------------------------------------------------------

df["snapshot_timestamp"] = pd.to_datetime(
    df["snapshot_timestamp"],
    errors="coerce",
    utc=True
)


# ---------------------------------------------------------
# 4. Sort observations
# ---------------------------------------------------------

df = df.sort_values(
    ["vehicle_id", "snapshot_timestamp"]
).reset_index(drop=True)


# ---------------------------------------------------------
# 5. Get previous observation for each vehicle
# ---------------------------------------------------------

df["previous_snapshot_timestamp"] = (
    df.groupby("vehicle_id")["snapshot_timestamp"]
    .shift(1)
)

df["previous_latitude"] = (
    df.groupby("vehicle_id")["latitude"]
    .shift(1)
)

df["previous_longitude"] = (
    df.groupby("vehicle_id")["longitude"]
    .shift(1)
)


# ---------------------------------------------------------
# 6. Calculate time difference
# ---------------------------------------------------------

df["time_difference_seconds"] = (
    df["snapshot_timestamp"]
    - df["previous_snapshot_timestamp"]
).dt.total_seconds()


# ---------------------------------------------------------
# 7. Haversine distance
# ---------------------------------------------------------

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate geographic distance in kilometers."""

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


df["distance_km"] = haversine_distance(
    df["previous_latitude"],
    df["previous_longitude"],
    df["latitude"],
    df["longitude"]
)


# ---------------------------------------------------------
# 8. Define acceptable observation gap
# ---------------------------------------------------------

# Our current snapshots are normally a few minutes apart.
# A gap greater than 15 minutes is treated as a data gap.

MAX_GAP_SECONDS = 15 * 60


# ---------------------------------------------------------
# 9. Calculate speed only for valid observation gaps
# ---------------------------------------------------------

df["calculated_speed_kmh"] = np.nan

valid_gap = (
    df["previous_snapshot_timestamp"].notna()
    & (df["time_difference_seconds"] > 0)
    & (df["time_difference_seconds"] <= MAX_GAP_SECONDS)
)

df.loc[valid_gap, "calculated_speed_kmh"] = (
    df.loc[valid_gap, "distance_km"]
    / (df.loc[valid_gap, "time_difference_seconds"] / 3600)
)


# ---------------------------------------------------------
# 10. Assign movement status
# ---------------------------------------------------------

df["movement_status"] = "DATA_GAP"

# Valid movement observation
df.loc[valid_gap, "movement_status"] = "VALID"

# Vehicle did not move
stationary = (
    valid_gap
    & (df["distance_km"] == 0)
)

df.loc[stationary, "movement_status"] = "STATIONARY"


# ---------------------------------------------------------
# 11. Keep only records with a previous observation
# ---------------------------------------------------------

movement_df = df[
    df["previous_snapshot_timestamp"].notna()
].copy()


# ---------------------------------------------------------
# 12. Select analytics columns
# ---------------------------------------------------------

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
        "movement_status",
    ]
]


# ---------------------------------------------------------
# 13. Round calculated values
# ---------------------------------------------------------

movement_df["distance_km"] = (
    movement_df["distance_km"].round(4)
)

movement_df["calculated_speed_kmh"] = (
    movement_df["calculated_speed_kmh"].round(2)
)

movement_df["time_difference_seconds"] = (
    movement_df["time_difference_seconds"].round(0)
)


# ---------------------------------------------------------
# 14. Save movement dataset
# ---------------------------------------------------------

movement_df.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 15. Pipeline summary
# ---------------------------------------------------------

print("\nVehicle movement analytics completed.")

print("Movement records:", len(movement_df))

print(
    "Vehicles with movement data:",
    movement_df["vehicle_id"].nunique()
)

print("Output file:", output_file)


print("\nMovement status:")

print(
    movement_df["movement_status"]
    .value_counts()
)


print("\nMovement statistics for VALID records:")

valid_movement = movement_df[
    movement_df["movement_status"] == "VALID"
]

if not valid_movement.empty:

    print(
        valid_movement[
            [
                "distance_km",
                "time_difference_seconds",
                "calculated_speed_kmh"
            ]
        ].describe()
    )


print("\nSample movement data:")

print(
    movement_df.head(10).to_string(index=False)
)