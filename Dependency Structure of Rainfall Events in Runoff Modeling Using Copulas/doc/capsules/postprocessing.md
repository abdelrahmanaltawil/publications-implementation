# Postprocessing Module

> **Source**: [`src/postprocessing.py`](../../../src/postprocessing.py)  
> **Last Updated**: 2024-12-24

## Overview

The postprocessing module handles all output operations: saving experiment results, logging metadata, and ensuring reproducibility through comprehensive run documentation.

---

## Functions

### `get_git_revision_hash()`

Retrieves the current Git commit hash for version tracking.

**Returns**: `str` - Git commit SHA or `"unknown"` if not in a git repo.

**Usage**: Automatically called by `save_run_metadata` to record code version.

---

### `save_run_metadata(save_path, metadata, experiment_parameters, logger)`

Saves comprehensive run metadata and experiment configuration.

| Parameter | Type | Description |
|-----------|------|-------------|
| `save_path` | `pathlib.Path` | Results directory |
| `metadata` | `dict` | Runtime metadata (from `collect_run_metadata`) |
| `experiment_parameters` | `dict` | Full config dictionary |
| `logger` | `logging.Logger` | Logger instance |

**Creates**:
| File | Content |
|------|---------|
| `00_run_metadata.yaml` | Execution environment details |
| `00_experiment_parameters.yaml` | Complete config snapshot |
| `00_run_logs.log` | Execution logs (if exists) |

**Metadata Fields Saved**:
```yaml
experiment_id: "ce61"
execution_start_time: "2024-12-24T15:30:00"
execution_end_time: "2024-12-24T15:35:00"
execution_duration_min: 5.0
git_commit: "abc123..."
python_version: "3.12.0"
platform: "macOS-14.0-arm64"
user: "username"
hostname: "machine-name"
working_directory: "/path/to/project"
command: "python workflow.py"
```

**Returns**: Tuple of (metadata, experiment_parameters, log_path)

---

### `save_data(datasets, save_path)`

Saves multiple DataFrames to CSV files in a structured directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `datasets` | `dict` | Mapping of relative paths to DataFrames |
| `save_path` | `pathlib.Path` | Base directory for saving |

**Example Input**:
```python
datasets = {
    "01_input_data/01_hourly_rainfall_data.csv": hourly_df,
    "01_input_data/02_cleaned_hourly_rainfall_data.csv": cleaned_df,
    "02_copula_fitting/01_copula_fit_metrics.csv": metrics_df,
}
```

**Behavior**:
- Creates subdirectories automatically
- Skips `None` values gracefully
- Logs warnings for empty DataFrames
- Saves without index by default

---

## Output Directory Structure

```
results/
└── HAMILTON RBG CS - 6153301 -- 20241224_153000 -- ce61/
    ├── 00_run_metadata.yaml         # Execution metadata
    ├── 00_experiment_parameters.yaml # Config snapshot
    ├── 00_run_logs.log              # Execution logs
    ├── 01_input_data/
    │   ├── 01_hourly_rainfall_data.csv
    │   ├── 02_cleaned_hourly_rainfall_data.csv
    │   └── 03_rainfall_events_data.csv
    ├── 02_copula_fitting/
    │   ├── 01_input_ranks.csv
    │   ├── 02_copula_fit_metrics.csv
    │   ├── 03_cdf_results.csv
    │   └── 04_return_periods.csv
    └── 03_sensitivity__uncertainty_analysis/
        ├── 01_bootstrap_uncertainty.csv
        └── 02_sensitivity_analysis.csv
```

---

## Usage Example

```python
from postprocessing import save_run_metadata, save_data

# Save all result datasets
save_data(
    datasets={
        "01_input_data/01_hourly_rainfall_data.csv": rainfall_data,
        "02_copula_fitting/01_copula_fit_metrics.csv": copula_metrics,
    },
    save_path=results_dir
)

# Save metadata at end of run
save_run_metadata(
    save_path=results_dir,
    metadata={"execution_start_time": start_time},
    experiment_parameters=config,
    logger=logging.getLogger()
)
```

---

## Configuration Reference

```yaml
postprocessing:
  save_path: "./data/results"
  save_metadata: true
```

---

## Reproducibility Features

The module ensures reproducibility through:

1. **Git Hash Tracking**: Links results to exact code version
2. **Full Config Snapshot**: Complete parameter record
3. **Environment Capture**: Python version, platform, user
4. **Execution Timing**: Duration tracking for performance analysis
5. **Log Preservation**: Complete execution trace
