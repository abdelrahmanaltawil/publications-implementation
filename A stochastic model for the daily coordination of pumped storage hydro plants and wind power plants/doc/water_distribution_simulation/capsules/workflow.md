# Workflow Module (workflow.py)

## Purpose
Main entry point orchestrating the simulation pipeline.

## Pipeline Steps

```
[1/4] Load Configuration
        ↓
[2/4] Preprocess Network
        ↓
[3/4] Run Simulation
        ↓
[4/4] Save Results
```

---

## Function

### `run(config_path: str = None) -> dict`
Execute the complete simulation workflow.

**Parameters:**
- `config_path`: Path to YAML config (default: `Data/inputs/config/water_distribution_simulation/config.yaml`)

**Returns:**
```python
{
    'results': SimulationResults,
    'extracted': dict,
    'metrics': dict,
    'run_dir': Path
}
```

---

## Configuration Parameters

The workflow is driven by a YAML configuration file with the following sections:

### `network`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `inp_file` | str | `null` | Path to EPANET .inp file (if null, sample network is generated) |
| `include_pump` | bool | `false` | Include pump in sample network |

### `demand`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern_type` | str | `residential` | Demand pattern: `residential`, `industrial`, `flat`, `custom` |
| `global_multiplier` | float | `1.0` | Scale all demands by this factor |
| `multipliers` | list | - | 24 hourly values (required if `pattern_type: custom`) |

### `pumps`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `control_type` | str | `none` | Control strategy: `none`, `tank_level`, `time_based` |
| `tank_name` | str | - | Tank to monitor (for `tank_level` control) |
| `on_hours` | list | - | Hours pump is on (for `time_based` control) |

### `simulation`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `simulator` | str | `wntr` | Simulator: `wntr` (pure Python) or `epanet` |
| `duration_hours` | int | `24` | Simulation duration |
| `timestep_minutes` | int | `60` | Hydraulic timestep |
| `report_timestep_minutes` | int | `60` | Reporting interval |

### `metrics`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_pressure_threshold` | float | `20.0` | Minimum acceptable pressure (m) |

### `logging`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | str | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Example Configuration

```yaml
network:
  inp_file: null
  include_pump: false

demand:
  pattern_type: residential
  global_multiplier: 1.0

pumps:
  control_type: none

simulation:
  simulator: wntr
  duration_hours: 24
  timestep_minutes: 60

metrics:
  min_pressure_threshold: 20.0

logging:
  level: INFO
```

---

## CLI Usage

```bash
python src/water_distribution_simulation/workflow.py
```

---

## Output

Results are saved to `Data/results/simulation/sim_run_YYYYMMDD_HHMMSS/`:
- Node data (pressure, head, demand)
- Link data (flowrate, velocity, headloss)
- Metrics summary (JSON)
- Simulation log
