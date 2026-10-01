import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

input_folder = Path("data/raw/gtfs/extracted")
output_folder = Path("data/raw/gtfs/processed")

output_folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 2. GTFS files to ingest
# ---------------------------------------------------------

gtfs_files = [
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
    "shapes.txt",
    "calendar.txt",
    "calendar_dates.txt",
]


# ---------------------------------------------------------
# 3. Read and save each GTFS dataset
# ---------------------------------------------------------

print("Starting GTFS ingestion...\n")

for file_name in gtfs_files:

    input_file = input_folder / file_name

    if not input_file.exists():
        raise FileNotFoundError(
            f"GTFS file not found: {input_file}"
        )

    print(f"Reading: {file_name}")

    df = pd.read_csv(
        input_file,
        low_memory=False
    )

    # Remove completely empty rows if present
    df = df.dropna(how="all")

    # Output filename
    output_file = (
        output_folder
        / file_name.replace(".txt", ".csv")
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(f"  Records: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Saved: {output_file}\n")


# ---------------------------------------------------------
# 4. Pipeline summary
# ---------------------------------------------------------

print("GTFS ingestion completed successfully.")

print("\nProcessed files:")

for file_name in gtfs_files:

    output_file = (
        output_folder
        / file_name.replace(".txt", ".csv")
    )

    print(
        f"  {output_file.name}"
    )