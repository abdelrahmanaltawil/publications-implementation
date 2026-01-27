# Postprocessing Module (postprocessing.py)

## Purpose
Result extraction, metrics computation, and data export for simulation results.

## Functions

### `extract_results(results, wn) -> dict`
Extract simulation results into organized DataFrames.

**Returns:**
```python
{
    'node': {
        'pressure': DataFrame,
        'head': DataFrame,
        'demand': DataFrame
    },
    'link': {
        'flowrate': DataFrame,
        'velocity': DataFrame,
        'headloss': DataFrame
    },
    'metadata': {...}
}
```

---

### `compute_metrics(results, wn, min_pressure_threshold=20.0) -> dict`
Compute resilience and performance metrics.

**Returned Metrics:**
| Metric | Description |
|--------|-------------|
| `pressure` | Min/max/mean/std of junction pressures |
| `service_satisfaction` | % of readings above threshold |
| `critical_nodes` | Nodes that drop below threshold |
| `flow` | Max flowrate, max velocity |
| `total_demand_m3` | Total demand delivered |

---

### `create_run_directory(output_dir: str) -> Path`
Create timestamped directory for results.

**Format:** `sim_run_YYYYMMDD_HHMMSS`

---

### `save_results(extracted, metrics, run_dir) -> None`
Save results to files.

**Output Structure:**
```
run_dir/
├── nodes/
│   ├── pressure.csv
│   ├── head.csv
│   └── demand.csv
├── links/
│   ├── flowrate.csv
│   ├── velocity.csv
│   └── headloss.csv
├── metrics.json
└── metadata.json
```

---

### `print_summary(metrics) -> None`
Print human-readable results summary to console.
