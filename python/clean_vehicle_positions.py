import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. Locate raw snapshot files
# ---------------------------------------------------------

raw_folder = Path("data/raw/vehicle_positions")
processed_folder = Path("data/processed")

processed_folder.mkdir(parents=True, exist_ok=True)

files = sorted(raw_folder.glob("*.csv"))

if not files:
    raise FileNotFoundError("No raw vehicle position files found.")


# ---------------------------------------------------------
# 2. Load all raw snapshots
# ---------------------------------------------------------

dataframes = []

for file in files:
    df = pd.read_csv(file)

    # Keep track of which snapshot produced the record
    df["snapshot_file"] = file.name

    dataframes.append(df)


df = pd.concat(dataframes, ignore_index=True)


print("Raw records:", len(df))
print("Raw columns:", len(df.columns))


# ---------------------------------------------------------
# 3. Data quality checks
# ---------------------------------------------------------

exceptions = []


# Missing vehicle ID
mask = df["vehicle_id"].isna()

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ001",
        "rule_name": "Missing Vehicle ID",
        "severity": "High"
    })


# Invalid latitude
mask = (
    df["latitude"].isna()
    | (df["latitude"] < -90)
    | (df["latitude"] > 90)
)

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ002",
        "rule_name": "Invalid Latitude",
        "severity": "High"
    })


# Invalid longitude
mask = (
    df["longitude"].isna()
    | (df["longitude"] < -180)
    | (df["longitude"] > 180)
)

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ003",
        "rule_name": "Invalid Longitude",
        "severity": "High"
    })


# Invalid bearing
mask = (
    df["bearing"].notna()
    & (
        (df["bearing"] < 0)
        | (df["bearing"] > 360)
    )
)

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ004",
        "rule_name": "Invalid Bearing",
        "severity": "Medium"
    })


# Missing route ID
mask = df["route_id"].isna()

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ005",
        "rule_name": "Missing Route ID",
        "severity": "High"
    })


# Missing trip ID
mask = df["trip_id"].isna()

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ006",
        "rule_name": "Missing Trip ID",
        "severity": "High"
    })


# Invalid timestamp
timestamp_check = pd.to_datetime(
    df["updated_at"],
    errors="coerce"
)

mask = timestamp_check.isna()

for index in df[mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ007",
        "rule_name": "Invalid Timestamp",
        "severity": "High"
    })


# ---------------------------------------------------------
# 4. Remove exact duplicate records
# ---------------------------------------------------------

duplicate_mask = df.duplicated(
    subset=["vehicle_id", "snapshot_file"],
    keep="first"
)

for index in df[duplicate_mask].index:
    exceptions.append({
        "vehicle_id": df.loc[index, "vehicle_id"],
        "snapshot_file": df.loc[index, "snapshot_file"],
        "rule_id": "DQ008",
        "rule_name": "Duplicate Vehicle Snapshot",
        "severity": "Medium"
    })


df_clean = df[~duplicate_mask].copy()


# ---------------------------------------------------------
# 5. Standardize timestamps
# ---------------------------------------------------------

df_clean["updated_at"] = pd.to_datetime(
    df_clean["updated_at"],
    errors="coerce",
    utc=True
)

# Extract snapshot timestamp from filename
df_clean["snapshot_timestamp"] = pd.to_datetime(
    df_clean["snapshot_file"].str.extract(
        r"vehicle_positions_(\d{8}_\d{6})"
    )[0],
    format="%Y%m%d_%H%M%S",
    errors="coerce"
)

# Store snapshot timestamp as UTC
df_clean["snapshot_timestamp"] = (
    df_clean["snapshot_timestamp"]
    .dt.tz_localize("America/New_York")
    .dt.tz_convert("UTC")
)


# ---------------------------------------------------------
# 6. Create exception DataFrame
# ---------------------------------------------------------

exceptions_df = pd.DataFrame(exceptions)


# ---------------------------------------------------------
# 7. Save Silver outputs
# ---------------------------------------------------------

clean_output = processed_folder / "vehicle_positions_clean.csv"
exception_output = processed_folder / "vehicle_positions_exceptions.csv"

df_clean.to_csv(clean_output, index=False)
exceptions_df.to_csv(exception_output, index=False)


# ---------------------------------------------------------
# 8. Print pipeline summary
# ---------------------------------------------------------

print("\nSilver processing completed.")

print("Clean records:", len(df_clean))
print("Exception records:", len(exceptions_df))

print("\nClean output:")
print(clean_output)

print("\nException output:")
print(exception_output)

if not exceptions_df.empty:
    print("\nExceptions by rule:")
    print(
        exceptions_df["rule_name"]
        .value_counts()
    )
else:
    print("\nNo data quality exceptions found.")