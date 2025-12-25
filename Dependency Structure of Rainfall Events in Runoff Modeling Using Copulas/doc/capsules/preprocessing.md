# Preprocessing Module

> **Source**: [`src/preprocessing.py`](../../../src/preprocessing.py)  
> **Last Updated**: 2024-12-24

## Overview

The preprocessing module handles all data ingestion and preparation tasks, transforming raw hourly rainfall data into structured rainfall events suitable for copula analysis.

---

## Functions

### `create_save_dir(base_dir, stations)`

Creates a unique results directory for each experiment run.

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_dir` | `pathlib.Path` | Base directory for results |
| `stations` | `list[dict]` | List of station configurations |

**Returns**: `pathlib.Path` - Created directory path

**Directory Naming Convention**:
- Single station: `{station_name} - {station_id} -- {timestamp} -- {uuid}`
- Multiple stations: `MULTI-STATIONS -- {timestamp} -- {uuid}`

---

### `load_data(db_path, table_name, climate_id)`

Loads climate data from a SQLite database for a specific station.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `str` | Path to SQLite database |
| `table_name` | `str` | Name of the data table |
| `climate_id` | `str` | Climate station identifier |

**Returns**: `pd.DataFrame` with columns:
- `climate_id` (str): Station identifier
- `datetime` (datetime): Timestamp
- `value` (float): Precipitation value (mm)
- `flag` (str): Data quality flag

**SQL Query Structure**:
```sql
SELECT climate_id, datetime, value, flag
FROM {table_name}
WHERE climate_id = "{climate_id}"
```

---

### `clean_data(data, time_col, rain_col, winter_months, remove_outliers)`

Cleans raw rainfall data by filtering and optionally removing outliers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `pd.DataFrame` | - | Input rainfall data |
| `time_col` | `str` | - | Timestamp column name |
| `rain_col` | `str` | - | Rainfall column name |
| `winter_months` | `list` | `[11,12,1,2,3,4]` | Months to exclude |
| `remove_outliers` | `bool` | `False` | Apply IQR outlier removal |

**Cleaning Steps**:
1. Drop rows with NaN rainfall values
2. Filter out zero rainfall (dry hours)
3. Remove outliers if enabled (IQR method with 3×IQR threshold)
4. Exclude winter months
5. Sort by timestamp

---

### `extract_rainfall_events(data, time_col, rain_col, IETD_threshold)`

Extracts individual rainfall events from hourly data using the Inter-Event Time Definition (IETD).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `pd.DataFrame` | - | Cleaned rainfall data |
| `time_col` | `str` | - | Timestamp column name |
| `rain_col` | `str` | - | Rainfall column name |
| `IETD_threshold` | `int` | `6` | Dry gap threshold (hours) |

**Returns**: `pd.DataFrame` with event features:

| Column | Unit | Description |
|--------|------|-------------|
| `Start Time` | datetime | Event start timestamp |
| `End Time` | datetime | Event end timestamp |
| `Duration (hrs)` | hours | Event duration (End - Start + 1) |
| `Volume (mm)` | mm | Total rainfall |
| `Intensity (mm/hr)` | mm/hr | Average intensity |
| `Peak Precipitation (mm)` | mm | Maximum hourly precipitation |
| `Inter-Event Time (hrs)` | hours | Gap from previous event |
| `IETD (hrs)` | hours | Threshold used |

**Event Separation Logic**:
```
New event starts if: time_gap > IETD_threshold hours
```

> [!NOTE]
> Inter-event time is set to `None` when events cross year boundaries to avoid artificial large gaps.

---

## Usage Example

```python
from preprocessing import load_data, clean_data, extract_rainfall_events

# Load data from database
raw_data = load_data(
    db_path="data/inputs/phd_research.db",
    table_name="CANADA_climate_data",
    climate_id="6153301"
)

# Clean data
cleaned = clean_data(
    raw_data,
    time_col="datetime",
    rain_col="value",
    winter_months=[11, 12, 1, 2, 3, 4],
    remove_outliers=False
)

# Extract rainfall events
events = extract_rainfall_events(
    cleaned,
    time_col="datetime",
    rain_col="value",
    IETD_threshold=6
)
```

---

## Configuration Reference

Related parameters in `config.yaml`:

```yaml
database:
  db_path: "./data/inputs/phd_research.db"
  table_name: "CANADA_climate_data"

preprocessing:
  time_col: "datetime"
  rain_col: "value"
  winter_months: [11, 12, 1, 2, 3, 4]
  remove_outliers: false
  ietd_threshold: 6
```

---

## Tests

Test file: [`tests/test_preprocessing.py`](../../../tests/test_preprocessing.py)

| Test | Description |
|------|-------------|
| `test_empty_dataframe` | Handles empty input gracefully |
| `test_single_continuous_event` | Correctly identifies one event |
| `test_two_events_separated_by_gap` | Separates events by IETD |
| `test_event_not_separated_if_gap_small` | Merges events within IETD |
| `test_year_boundary_reset` | Handles year boundaries |

Run tests:
```bash
python -m unittest tests.test_preprocessing -v
```
