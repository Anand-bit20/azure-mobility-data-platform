import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AZURE_FOLDER = Path(__file__).resolve().parent


# ---------------------------------------------------------
# Pipeline definitions
# ---------------------------------------------------------

LIVE_PIPELINE_STEPS = [
    (
        "1. Ingest MBTA vehicle positions",
        "ingest_vehicle_positions.py"
    ),
    (
        "2. Process vehicle Raw -> Silver",
        "process_raw_to_silver.py"
    ),
    (
        "3. Integrate vehicle + GTFS",
        "integrate_vehicle_gtfs.py"
    ),
    (
        "4. Generate data quality report",
        "data_quality_report.py"
    ),
    (
        "5. Run analytics",
        "run_analytics.py"
    ),
    (
        "6. Build and validate Gold layer",
        "build_gold_layer.py"
    ),
]


GTFS_REFRESH_STEPS = [
    (
        "GTFS 1. Ingest GTFS Raw data",
        "ingest_gtfs.py"
    ),
    (
        "GTFS 2. Process GTFS Raw -> Silver",
        "process_gtfs_to_silver.py"
    ),
    (
        "GTFS 3. Validate GTFS Silver",
        "validate_gtfs_silver.py"
    ),
]


# ---------------------------------------------------------
# Run one pipeline step
# ---------------------------------------------------------

def run_step(step_name, script_name):

    print("\n" + "=" * 65)
    print(step_name)
    print("=" * 65)

    script_path = AZURE_FOLDER / script_name

    if not script_path.exists():
        raise FileNotFoundError(
            f"Pipeline script not found: {script_path}"
        )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path)
        ],
        cwd=PROJECT_ROOT,
        check=False
    )

    if result.returncode != 0:

        print("\n" + "=" * 65)
        print("AZURE PIPELINE FAILED")
        print("=" * 65)

        print(f"Failed step: {step_name}")
        print(f"Script: {script_name}")
        print(
            f"Return code: {result.returncode}"
        )

        sys.exit(
            result.returncode
        )


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

def main():

    print("=" * 65)
    print("AZURE MOBILITY DATA PLATFORM")
    print("AZURE PIPELINE ORCHESTRATOR")
    print("=" * 65)

    # -----------------------------------------------------
    # Validate Azure credentials
    # -----------------------------------------------------

    if not os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING"
    ):
        print(
            "\nERROR: AZURE_STORAGE_CONNECTION_STRING "
            "is not set."
        )

        print(
            "\nSet it in PowerShell before running:"
        )

        print(
            '$env:AZURE_STORAGE_CONNECTION_STRING='
            '"YOUR_CONNECTION_STRING"'
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Determine run mode
    # -----------------------------------------------------

    full_refresh = (
        "--full-refresh" in sys.argv
    )

    if full_refresh:

        print(
            "\nRun mode: FULL REFRESH"
        )

        print(
            "GTFS + vehicle + analytics + Gold"
        )

        for step_name, script_name in GTFS_REFRESH_STEPS:

            run_step(
                step_name,
                script_name
            )

    else:

        print(
            "\nRun mode: LIVE VEHICLE REFRESH"
        )

        print(
            "Existing Azure GTFS Silver data "
            "will be reused."
        )

    # -----------------------------------------------------
    # Live vehicle pipeline
    # -----------------------------------------------------

    for step_name, script_name in LIVE_PIPELINE_STEPS:

        run_step(
            step_name,
            script_name
        )

    # -----------------------------------------------------
    # Completion
    # -----------------------------------------------------

    print("\n" + "=" * 65)
    print("AZURE PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 65)

    print("\nPipeline layers refreshed:")

    print(" - Raw vehicle snapshots")
    print(" - Silver vehicle dataset")

    if full_refresh:
        print(" - Raw GTFS datasets")
        print(" - Silver GTFS datasets")
        print(" - GTFS validation")

    print(" - Vehicle + GTFS integration")
    print(" - Data quality reports")
    print(" - Schedule analytics")
    print(" - Vehicle movement analytics")
    print(" - Gold dimensions")
    print(" - Gold fact tables")
    print(" - Gold validation")

    print(
        "\nAzure Mobility Data Platform "
        "pipeline completed."
    )


if __name__ == "__main__":
    main()