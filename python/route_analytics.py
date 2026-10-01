import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

movement_file = Path("data/processed/vehicle_movement.csv")
anomaly_file = Path("data/processed/vehicle_speed_anomalies.csv")

output_folder = Path("data/processed")
output_folder.mkdir(parents=True, exist_ok=True)

output_file = output_folder / "route_analytics.csv"


# ---------------------------------------------------------
# 2. Load movement data
# ---------------------------------------------------------

movement_df = pd.read_csv(movement_file)

print("Movement records:", len(movement_df))


# ---------------------------------------------------------
# 3. Load speed anomaly data
# ---------------------------------------------------------

anomaly_df = pd.read_csv(anomaly_file)

print("Speed anomalies:", len(anomaly_df))


# ---------------------------------------------------------
# 4. Remove records without route information
# ---------------------------------------------------------

movement_df = movement_df[
    movement_df["route_id"].notna()
].copy()


# ---------------------------------------------------------
# 5. Route-level aggregation
# ---------------------------------------------------------

route_summary = (
    movement_df
    .groupby("route_id")
    .agg(
        vehicle_observations=("vehicle_id", "count"),
        unique_vehicles=("vehicle_id", "nunique"),
        total_distance_km=("distance_km", "sum"),
        average_speed_kmh=("calculated_speed_kmh", "mean"),
        maximum_speed_kmh=("calculated_speed_kmh", "max"),
        stationary_observations=(
            "movement_status",
            lambda x: (x == "STATIONARY").sum()
        ),
        data_gap_observations=(
            "movement_status",
            lambda x: (x == "DATA_GAP").sum()
        ),
    )
    .reset_index()
)


# ---------------------------------------------------------
# 6. Count speed anomalies by route
# ---------------------------------------------------------

anomaly_counts = (
    anomaly_df
    .groupby("route_id")
    .size()
    .reset_index(name="speed_anomalies")
)


# ---------------------------------------------------------
# 7. Join anomaly counts
# ---------------------------------------------------------

route_summary = route_summary.merge(
    anomaly_counts,
    on="route_id",
    how="left"
)


# ---------------------------------------------------------
# 8. Replace missing anomaly counts with zero
# ---------------------------------------------------------

route_summary["speed_anomalies"] = (
    route_summary["speed_anomalies"]
    .fillna(0)
    .astype(int)
)


# ---------------------------------------------------------
# 9. Calculate data quality rate
# ---------------------------------------------------------

route_summary["valid_movement_rate_pct"] = (
    (
        route_summary["vehicle_observations"]
        - route_summary["data_gap_observations"]
    )
    / route_summary["vehicle_observations"]
    * 100
)


# ---------------------------------------------------------
# 10. Round metrics
# ---------------------------------------------------------

route_summary["total_distance_km"] = (
    route_summary["total_distance_km"].round(2)
)

route_summary["average_speed_kmh"] = (
    route_summary["average_speed_kmh"].round(2)
)

route_summary["maximum_speed_kmh"] = (
    route_summary["maximum_speed_kmh"].round(2)
)

route_summary["valid_movement_rate_pct"] = (
    route_summary["valid_movement_rate_pct"].round(2)
)


# ---------------------------------------------------------
# 11. Sort routes by total distance
# ---------------------------------------------------------

route_summary = route_summary.sort_values(
    "total_distance_km",
    ascending=False
).reset_index(drop=True)


# ---------------------------------------------------------
# 12. Save route analytics
# ---------------------------------------------------------

route_summary.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 13. Pipeline summary
# ---------------------------------------------------------

print("\nRoute analytics completed.")

print("Routes analysed:", len(route_summary))

print("Output file:", output_file)


print("\nRoute analytics:")

print(
    route_summary.to_string(index=False)
)