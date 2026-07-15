# AutoLens AU — Data Dictionary

## Source Layer (raw schema)

### raw.raw_listings
Combined vehicle listings from Kaggle datasets.

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| source_record_id | TEXT | Source-provided row identifier when available | Kaggle |
| brand | VARCHAR(100) | Vehicle manufacturer | Kaggle |
| year | INTEGER | Year of manufacture | Kaggle |
| model | VARCHAR(200) | Vehicle model name/code | Kaggle |
| variant | VARCHAR(200) | Badge/variant where supplied | Kaggle |
| vehicle_type | VARCHAR(50) | Car or SUV | Kaggle |
| title | TEXT | Full listing title | Kaggle |
| condition | VARCHAR(50) | New/Used/Demo | Kaggle |
| transmission | VARCHAR(50) | Automatic/Manual | Kaggle |
| engine | VARCHAR(100) | Engine capacity/power | Kaggle |
| drive_type | VARCHAR(50) | FWD/RWD/AWD/4WD | Kaggle |
| fuel_type | VARCHAR(50) | Petrol/Diesel/Hybrid/Electric | Kaggle |
| fuel_consumption | VARCHAR(50) | L/100km | Kaggle |
| kilometres | NUMERIC | Odometer reading | Kaggle |
| colour | VARCHAR(200) | Exterior/Interior colour | Kaggle |
| location | VARCHAR(200) | City, State | Kaggle |
| cylinders | INTEGER | Number of cylinders | Kaggle |
| body_type | VARCHAR(100) | Sedan/SUV/Hatch/Ute/etc. | Kaggle |
| doors | INTEGER | Number of doors | Kaggle |
| seats | INTEGER | Number of seats | Kaggle |
| price | NUMERIC | Listed price in AUD | Kaggle |
| source | VARCHAR(100) | Source dataset identifier | System |
| listing_fingerprint | VARCHAR(64) | Stable natural-listing SHA-256 fingerprint | System |
| snapshot_date | DATE | Date this source snapshot was ingested | System |
| ingested_at | TIMESTAMP | When record was loaded | System |

### raw.raw_fuel_prices
NSW fuel station prices from FuelCheck API.

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| stationcode | VARCHAR(50) | Station identifier | NSW API |
| fueltype | VARCHAR(50) | Fuel type code | NSW API |
| price | NUMERIC | Price in cents per litre | NSW API |
| lastupdated | TIMESTAMP | When price was reported | NSW API |
| name | VARCHAR(200) | Station name | NSW API |
| suburb | VARCHAR(100) | Station suburb | NSW API |
| state | VARCHAR(10) | State code | NSW API |
| latitude | NUMERIC | Station latitude | NSW API |
| longitude | NUMERIC | Station longitude | NSW API |
| fetched_at | TIMESTAMP | When data was fetched | System |

### raw.raw_qld_registration_activity
Monthly QLD new-registration and transfer activity aggregated from the current partitioned CKAN
package. This is not a count of the total active fleet.

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| activity_month | DATE | Month of transaction activity | QLD Gov |
| make | VARCHAR(100) | Vehicle manufacturer | QLD Gov |
| model | VARCHAR(200) | Vehicle model | QLD Gov |
| badge | VARCHAR(200) | Published badge | QLD Gov |
| body_shape | VARCHAR(100) | Published body shape | QLD Gov |
| fuel_type | VARCHAR(50) | Published fuel type | QLD Gov |
| transaction_type | VARCHAR(50) | New registration or transfer | QLD Gov |
| activity_count | BIGINT | Aggregated transaction count | Derived |
| source_resource_id | UUID | CKAN partition identifier | System |

### raw.raw_bitre_vehicle_makes
National registered-vehicle counts by make and reference year from BITRE Road Vehicles Australia.

### raw.raw_cpi / raw.raw_rba_cash_rate
Official CPI (ABS series republished in RBA G1) and cash-rate target (RBA F1) observations.

---

## Core Layer (Kimball Star Schema)

### core.fact_listing
Fact table: one row per vehicle listing.

| Column | Type | Role | Description |
|--------|------|------|-------------|
| listing_id | VARCHAR | PK/SK | Fingerprint + snapshot surrogate key |
| vehicle_key | VARCHAR | FK → dim_vehicle | Vehicle dimension key |
| location_key | VARCHAR | FK → dim_location | Location dimension key |
| manufacture_year | INTEGER | FK → dim_year | Vehicle manufacture year |
| listing_snapshot_date | DATE | Degenerate time | Listing ingestion snapshot |
| price_aud | NUMERIC | Measure | Listed price |
| kilometres | NUMERIC | Measure | Odometer |
| vehicle_age | INTEGER | Measure | Calculated age |
| avg_annual_km | NUMERIC | Measure | km/age |
| age_km_interaction | NUMERIC | Measure | Feature interaction |

### core.dim_vehicle
Vehicle dimension: unique configurations.

| Column | Type | Description |
|--------|------|-------------|
| vehicle_key | VARCHAR | Surrogate key |
| brand | VARCHAR | Manufacturer |
| model | VARCHAR | Model name |
| variant | VARCHAR | Supplied variant/badge; Unknown when absent |
| body_type | VARCHAR | Body style |
| fuel_type | VARCHAR | Fuel type |
| transmission | VARCHAR | Transmission |
| drive_type | VARCHAR | Drivetrain |
| vehicle_segment | VARCHAR | Classified segment |

### core.dim_location
Location dimension: geographic attributes.

| Column | Type | Description |
|--------|------|-------------|
| location_key | VARCHAR | Surrogate key |
| location_raw | VARCHAR | Original location string |
| state | VARCHAR | AU state/territory code |
| city | VARCHAR | City name |
| metro_regional | VARCHAR | Metro or Regional |

### core.dim_year
Manufacture-year dimension. Listing observation time is retained separately on the fact.

| Column | Type | Description |
|--------|------|-------------|
| year_key | INTEGER | Year as key |
| calendar_year | INTEGER | Calendar year |
| era | VARCHAR | Era classification |
