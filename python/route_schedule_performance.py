import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_file = Path(
    "data/processed/schedule_performance.csv"
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
    / "route_schedule_performance.csv"
)


# ---------------------------------------------------------
# 2. Load schedule performance data
# ---------------------------------------------------------

print("Loading schedule performance data...")

df = pd.read_csv(
    input_file,
    dtype={
        "route_id": "string",
        "vehicle_id": "string",
        "trip_id": "string",
        "stop_id": "string",
        "route_long_name": "string"
    },
    low_memory=False
)

print(
    f"Schedule performance records: {len(df):,}"
)


# ---------------------------------------------------------
# 3. Validate required fields
# ---------------------------------------------------------

required_columns = [
    "route_id",
    "route_long_name",
    "vehicle_id",
    "trip_id",
    "stop_id",
    "arrival_deviation_minutes",
    "schedule_status"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ---------------------------------------------------------
# 4. Create route-level aggregation
# ---------------------------------------------------------

route_summary = (
    df
    .groupby(
        [
            "route_id",
            "route_long_name"
        ],
        dropna=False
    )
    .agg(
        schedule_observations=(
            "route_id",
            "size"
        ),
        unique_vehicles=(
            "vehicle_id",
            "nunique"
        ),
        unique_trips=(
            "trip_id",
            "nunique"
        ),
        unique_stops=(
            "stop_id",
            "nunique"
        ),
        average_deviation_minutes=(
            "arrival_deviation_minutes",
            "mean"
        ),
        median_deviation_minutes=(
            "arrival_deviation_minutes",
            "median"
        ),
        maximum_deviation_minutes=(
            "arrival_deviation_minutes",
            "max"
        ),
        minimum_deviation_minutes=(
            "arrival_deviation_minutes",
            "min"
        )
    )
    .reset_index()
)


# ---------------------------------------------------------
# 5. Calculate status counts
# ---------------------------------------------------------

status_counts = (
    df
    .pivot_table(
        index=[
            "route_id",
            "route_long_name"
        ],
        columns="schedule_status",
        values="vehicle_id",
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

status_counts.columns.name = None


# ---------------------------------------------------------
# 6. Make sure all status columns exist
# ---------------------------------------------------------

for column in [
    "ON_TIME",
    "DELAYED",
    "EARLY"
]:
    if column not in status_counts.columns:
        status_counts[column] = 0


# ---------------------------------------------------------
# 7. Rename status count columns
# ---------------------------------------------------------

status_counts = status_counts.rename(
    columns={
        "ON_TIME": "on_time_observations",
        "DELAYED": "delayed_observations",
        "EARLY": "early_observations"
    }
)


# ---------------------------------------------------------
# 8. Merge status counts
# ---------------------------------------------------------

route_summary = route_summary.merge(
    status_counts,
    on=[
        "route_id",
        "route_long_name"
    ],
    how="left"
)


# ---------------------------------------------------------
# 9. Calculate percentages
# ---------------------------------------------------------

route_summary["on_time_pct"] = (
    route_summary["on_time_observations"]
    / route_summary["schedule_observations"]
    * 100
)

route_summary["delayed_pct"] = (
    route_summary["delayed_observations"]
    / route_summary["schedule_observations"]
    * 100
)

route_summary["early_pct"] = (
    route_summary["early_observations"]
    / route_summary["schedule_observations"]
    * 100
)


# ---------------------------------------------------------
# 10. Round numeric metrics
# ---------------------------------------------------------

numeric_columns = [
    "average_deviation_minutes",
    "median_deviation_minutes",
    "maximum_deviation_minutes",
    "minimum_deviation_minutes",
    "on_time_pct",
    "delayed_pct",
    "early_pct"
]

route_summary[numeric_columns] = (
    route_summary[numeric_columns]
    .round(2)
)


# ---------------------------------------------------------
# 11. Sort by observation volume
# ---------------------------------------------------------

route_summary = route_summary.sort_values(
    by="schedule_observations",
    ascending=False
)


# ---------------------------------------------------------
# 12. Save output
# ---------------------------------------------------------

route_summary.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 13. Summary
# ---------------------------------------------------------

print("\n========================================")
print("ROUTE SCHEDULE PERFORMANCE SUMMARY")
print("========================================")

print(
    f"Routes analyzed: {len(route_summary):,}"
)

print(
    f"Total observations: "
    f"{route_summary['schedule_observations'].sum():,}"
)

print(
    "\nOverall status counts:"
)

print(
    "On time:",
    route_summary["on_time_observations"].sum()
)

print(
    "Delayed:",
    route_summary["delayed_observations"].sum()
)

print(
    "Early:",
    route_summary["early_observations"].sum()
)


# ---------------------------------------------------------
# 14. Display top routes by observation volume
# ---------------------------------------------------------

print(
    "\nTop routes by observation volume:"
)

display_columns = [
    "route_id",
    "route_long_name",
    "schedule_observations",
    "unique_vehicles",
    "average_deviation_minutes",
    "on_time_pct",
    "delayed_pct",
    "early_pct"
]

print(
    route_summary[
        display_columns
    ]
    .head(15)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 15. Output
# ---------------------------------------------------------

print(
    f"\nOutput file: {output_file}"
)

print(
    "\nRoute schedule performance analysis completed."
)