# Azure Mobility Data Platform — Azure Architecture

## 1. Project Objective

Build an end-to-end mobility data engineering and analytics platform using publicly available MBTA transportation data.

The project demonstrates:

- API-based data ingestion
- GTFS data processing
- Data quality validation
- Raw → Silver → Gold data architecture
- Azure cloud storage
- SQL and Python analytics
- Power BI reporting
- Cloud-ready data engineering practices

---

## 2. Current Architecture

```text
                    MBTA Public Data
                           |
             +-------------+-------------+
             |                           |
       Vehicle API                    GTFS Data
             |                           |
             +-------------+-------------+
                           |
                    Python Ingestion
                           |
                           v
                    Local Raw Layer
                           |
                           v
                  Local Silver Layer
                           |
                           v
                    Local Gold Layer
                           |
                           v
                  Azure Blob Storage
                           |
          +----------------+----------------+
          |                |                |
        raw/            silver/           gold/
          |                |                |
    Raw snapshots     Clean dataset    Analytics datasets