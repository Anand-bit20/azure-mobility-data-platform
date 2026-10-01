import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

processed_folder = Path("data/processed")
gold_folder = Path("data/processed/gold")

gold_folder.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# 2. Load snapshot timestamps
# ---------------------------------------------------------

print("Loading snapshot dates...")

vehicle_movement = pd.read_csv(
    processed_folder / "vehicle_movement.csv",
    usecols=["snapshot_timestamp"]
)

vehicle_movement["snapshot_timestamp"] = pd.to_datetime(
    vehicle_movement["snapshot_timestamp"],
    errors="coerce",
    utc=True
)

snapshot_dates = (
    vehicle_movement["snapshot_timestamp"]
    .dropna()
    .dt.date
)


# ---------------------------------------------------------
# 3. Load schedule observation dates
# ---------------------------------------------------------

print("Loading schedule dates...")

schedule_performance = pd.read_csv(
    processed_folder / "schedule_performance.csv",
    usecols=["observation_date"]
)

schedule_dates = pd.to_datetime(
    schedule_performance["observation_date"],
    errors="coerce"
).dropna().dt.date


# ---------------------------------------------------------
# 4. Determine date range
# ---------------------------------------------------------

all_dates = pd.Series(
    list(snapshot_dates) +
    list(schedule_dates)
)

if all_dates.empty:
    raise ValueError(
        "No valid dates found."
    )

start_date = min(all_dates)
end_date = max(all_dates)

print(
    f"Date range: {start_date} to {end_date}"
)


# ---------------------------------------------------------
# 5. Create continuous date range
# ---------------------------------------------------------

dates = pd.date_range(
    start=start_date,
    end=end_date,
    freq="D"
)

dim_date = pd.DataFrame({
    "date": dates
})


# ---------------------------------------------------------
# 6. Create date attributes
# ---------------------------------------------------------

dim_date["date_key"] = (
    dim_date["date"]
    .dt.strftime("%Y%m%d")
    .astype(int)
)

dim_date["year"] = (
    dim_date["date"].dt.year
)

dim_date["quarter"] = (
    dim_date["date"].dt.quarter
)

dim_date["quarter_name"] = (
    "Q" +
    dim_date["quarter"].astype(str)
)

dim_date["month"] = (
    dim_date["date"].dt.month
)

dim_date["month_name"] = (
    dim_date["date"].dt.month_name()
)

dim_date["month_short_name"] = (
    dim_date["date"].dt.strftime("%b")
)

dim_date["week_of_year"] = (
    dim_date["date"].dt.isocalendar().week.astype(int)
)

dim_date["day"] = (
    dim_date["date"].dt.day
)

dim_date["day_of_week"] = (
    dim_date["date"].dt.dayofweek + 1
)

dim_date["day_name"] = (
    dim_date["date"].dt.day_name()
)

dim_date["is_weekend"] = (
    dim_date["date"].dt.dayofweek >= 5
)


# ---------------------------------------------------------
# 7. Validate Date dimension
# ---------------------------------------------------------

print("\nDate dimension quality checks:")

print(
    "Duplicate date keys:",
    dim_date["date_key"].duplicated().sum()
)

print(
    "Missing dates:",
    dim_date["date"].isna().sum()
)

print(
    "Rows:",
    len(dim_date)
)


# ---------------------------------------------------------
# 8. Save Date dimension
# ---------------------------------------------------------

output_file = (
    gold_folder /
    "dim_date.csv"
)

dim_date.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# 9. Final summary
# ---------------------------------------------------------

print("\n========================================")
print("DIM DATE SUMMARY")
print("========================================")

print(
    f"Rows: {len(dim_date):,}"
)

print(
    f"Start date: {dim_date['date'].min().date()}"
)

print(
    f"End date: {dim_date['date'].max().date()}"
)

print(
    f"\nOutput: {output_file}"
)

print(
    "\nDate dimension created successfully."
)