import subprocess
import sys


# ---------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------

PIPELINE_STEPS = [
    ("1. Ingest MBTA vehicle data", "get_vehicle_positions.py"),
    ("2. Clean vehicle data", "clean_vehicle_positions.py"),
    ("3. Ingest GTFS reference data", "ingest_gtfs.py"),
    ("4. Clean and validate GTFS data", "clean_gtfs.py"),
    ("5. Validate GTFS datasets", "validate_gtfs.py"),
    ("6. Integrate vehicle + GTFS data", "integrate_vehicle_gtfs.py"),
    ("7. Generate data quality report", "data_quality_report.py"),

    # Analytics layer
    ("8. Prepare schedule reference", "prepare_schedule_reference.py"),
    ("9. Calculate schedule performance", "calculate_schedule_performance.py"),
    ("10. Calculate vehicle movement", "calculate_vehicle_movement.py"),

    # Gold layer
    ("11. Build Gold dimensions", "build_dimensions.py"),
    ("12. Build Gold date dimension", "build_dim_date.py"),
    ("13. Build Gold schedule performance fact", "build_fact_schedule_performance.py"),
    ("14. Build Gold vehicle movement fact", "build_fact_vehicle_movement.py"),
    ("15. Build Gold vehicle observation fact", "build_fact_vehicle_observation.py"),
    ("16. Validate Gold layer", "validate_gold_layer.py"),
]


# ---------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------

print("=" * 60)
print("AZURE MOBILITY DATA PLATFORM")
print("LOCAL DATA PIPELINE")
print("=" * 60)


for step_name, script_name in PIPELINE_STEPS:

    print("\n" + "=" * 60)
    print(step_name)
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, f"python/{script_name}"],
        check=False
    )

    if result.returncode != 0:

        print("\n" + "=" * 60)
        print("PIPELINE FAILED")
        print("=" * 60)

        print(f"\nFailed step: {step_name}")
        print(f"Script: {script_name}")

        sys.exit(result.returncode)


# ---------------------------------------------------------
# Completion
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nGenerated layers:")
print(" - Raw MBTA vehicle snapshots")
print(" - Silver vehicle data")
print(" - Silver GTFS data")
print(" - Integrated vehicle + GTFS data")
print(" - Data quality report")
print(" - Schedule reference")
print(" - Schedule performance")
print(" - Vehicle movement")
print(" - Gold dimensions")
print(" - Gold fact tables")
print(" - Gold validation")