import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_file = Path(
    "data/processed/vehicle_gtfs_integrated.csv"
)

output_folder = Path(
    "data/processed"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

output_file = (
    output_folder
    / "data_quality_report.csv"
)


# ---------------------------------------------------------
# 2. Load integrated dataset
# ---------------------------------------------------------

print("Loading integrated vehicle data...")

df = pd.read_csv(
    input_file,
    low_memory=False
)

print(
    f"Records loaded: {len(df):,}"
)


# ---------------------------------------------------------
# 3. Basic data-quality checks
# ---------------------------------------------------------

total_records = len(df)

duplicate_records = df.duplicated().sum()

missing_vehicle_id = df["vehicle_id"].isna().sum()

missing_latitude = df["latitude"].isna().sum()

missing_longitude = df["longitude"].isna().sum()

invalid_latitude = (
    df["latitude"].notna()
    & ~df["latitude"].between(-90, 90)
).sum()

invalid_longitude = (
    df["longitude"].notna()
    & ~df["longitude"].between(-180, 180)
).sum()


# ---------------------------------------------------------
# 4. Matching metrics
# ---------------------------------------------------------

route_matched = (
    df["route_match_status"] == "MATCHED"
).sum()

trip_matched = (
    df["trip_match_status"] == "MATCHED"
).sum()

stop_matched = (
    df["stop_match_status"] == "MATCHED"
).sum()

full_match = (
    df["integration_status"] == "FULL_MATCH"
).sum()

partial_match = (
    df["integration_status"] == "PARTIAL_MATCH"
).sum()


# ---------------------------------------------------------
# 5. Calculate percentages
# ---------------------------------------------------------

def percentage(value, total):
    if total == 0:
        return 0

    return round(
        (value / total) * 100,
        2
    )


route_match_rate = percentage(
    route_matched,
    total_records
)

trip_match_rate = percentage(
    trip_matched,
    total_records
)

stop_match_rate = percentage(
    stop_matched,
    total_records
)

full_match_rate = percentage(
    full_match,
    total_records
)

partial_match_rate = percentage(
    partial_match,
    total_records
)


# ---------------------------------------------------------
# 6. Exception counts
# ---------------------------------------------------------

exception_counts = (
    df["exception_reason"]
    .value_counts()
)


# ---------------------------------------------------------
# 7. Create quality report
# ---------------------------------------------------------

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
        "percentage": route_match_rate
    },
    {
        "metric": "Trip Match",
        "value": trip_matched,
        "percentage": trip_match_rate
    },
    {
        "metric": "Stop Match",
        "value": stop_matched,
        "percentage": stop_match_rate
    },
    {
        "metric": "Full Integration",
        "value": full_match,
        "percentage": full_match_rate
    },
    {
        "metric": "Partial Integration",
        "value": partial_match,
        "percentage": partial_match_rate
    }
]


quality_report = pd.DataFrame(
    quality_metrics
)


# ---------------------------------------------------------
# 8. Save quality report
# ---------------------------------------------------------

quality_report.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 9. Display summary
# ---------------------------------------------------------

print("\n========================================")
print("DATA QUALITY REPORT")
print("========================================")

print(
    quality_report.to_string(
        index=False
    )
)


# ---------------------------------------------------------
# 10. Display exception breakdown
# ---------------------------------------------------------

print("\n========================================")
print("EXCEPTION BREAKDOWN")
print("========================================")

print(
    exception_counts.to_string()
)


print(
    f"\nOutput file: {output_file}"
)

print(
    "\nData quality report completed."
)