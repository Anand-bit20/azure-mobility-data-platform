import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_file = Path("data/processed/vehicle_movement.csv")
output_folder = Path("data/processed")

output_folder.mkdir(parents=True, exist_ok=True)

output_file = output_folder / "vehicle_speed_anomalies.csv"


# ---------------------------------------------------------
# 2. Load movement data
# ---------------------------------------------------------

df = pd.read_csv(input_file)

print("Loaded movement records:", len(df))


# ---------------------------------------------------------
# 3. Define speed threshold
# ---------------------------------------------------------

# Speeds above 100 km/h are flagged for investigation.
# This is an analytical threshold, not a claim that every
# vehicle above this speed is incorrect.

SPEED_THRESHOLD_KMH = 100


# ---------------------------------------------------------
# 4. Detect speed anomalies
# ---------------------------------------------------------

df["speed_anomaly"] = "NO"

df["anomaly_reason"] = ""


valid_speed = (
    df["movement_status"].isin(["VALID", "STATIONARY"])
    & df["calculated_speed_kmh"].notna()
)

high_speed = (
    valid_speed
    & (df["calculated_speed_kmh"] > SPEED_THRESHOLD_KMH)
)

df.loc[high_speed, "speed_anomaly"] = "YES"

df.loc[high_speed, "anomaly_reason"] = (
    "Calculated speed exceeds 100 km/h"
)


# ---------------------------------------------------------
# 5. Create anomaly dataset
# ---------------------------------------------------------

anomalies_df = df[
    df["speed_anomaly"] == "YES"
].copy()


# ---------------------------------------------------------
# 6. Add anomaly severity
# ---------------------------------------------------------

anomalies_df["severity"] = "HIGH"


# ---------------------------------------------------------
# 7. Select useful columns
# ---------------------------------------------------------

anomalies_df = anomalies_df[
    [
        "vehicle_id",
        "route_id",
        "snapshot_timestamp",
        "previous_snapshot_timestamp",
        "distance_km",
        "time_difference_seconds",
        "calculated_speed_kmh",
        "movement_status",
        "speed_anomaly",
        "anomaly_reason",
        "severity",
    ]
]


# ---------------------------------------------------------
# 8. Save anomaly dataset
# ---------------------------------------------------------

anomalies_df.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 9. Pipeline summary
# ---------------------------------------------------------

print("\nSpeed anomaly detection completed.")

print("Total movement records:", len(df))

print("Speed anomalies:", len(anomalies_df))

print("Output file:", output_file)


# ---------------------------------------------------------
# 10. Display anomalies
# ---------------------------------------------------------

if not anomalies_df.empty:

    print("\nDetected anomalies:")

    print(
        anomalies_df.to_string(index=False)
    )

else:

    print("\nNo speed anomalies detected.")