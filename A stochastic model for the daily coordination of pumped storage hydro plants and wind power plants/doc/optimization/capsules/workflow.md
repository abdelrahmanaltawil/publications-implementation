# Workflow Module (workflow.py)

## Purpose
Main entry point orchestrating the optimization pipeline.

## Pipeline Steps

```
[1/4] Load Configuration
        ↓
[2/4] Build Network Data
        ↓
[3/4] Build & Solve Model
        ↓
[4/4] Save Results
```

---

## Function

### `run(config_path: str = None) -> dict`
Execute the complete optimization workflow.

**Parameters:**
- `config_path`: Path to YAML config (default: `Data/inputs/config/optimization/config.yaml`)

**Returns:** Solution dictionary if successful, `None` otherwise.

---

## Configuration Parameters

The workflow is driven by a YAML configuration file with the following sections:

### `T`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `T` | int | `24` | Number of time steps (hours) |

### `nodes`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `nodes` | list | `[1, 2, 3]` | List of node IDs in the network |

### `layers`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layers` | list | `[E, P, W]` | Resource layers (Energy, Potable, Waste) |

### `coupling`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `treatment_efficiency` | float | `0.95` | η: W→P conversion efficiency |
| `pumping_intensity` | float | `0.5` | k: Energy per water transport (kWh/m³) |

### `storage`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `{node_id}` | dict | - | Per-node storage capacities `{E: float, P: float, W: float}` |

### `solver`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | `glpk` | Solver: `glpk`, `cbc`, `gurobi`, `cplex` |
| `verbose` | bool | `false` | Print solver output |

### `logging`
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | str | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Example Configuration

```yaml
T: 24
nodes: [1, 2, 3]
layers: [E, P, W]

coupling:
  treatment_efficiency: 0.95
  pumping_intensity: 0.5

storage:
  1: {E: 10.0, P: 5.0, W: 10.0}
  2: {E: 10.0, P: 5.0, W: 10.0}
  3: {E: 10.0, P: 5.0, W: 10.0}

solver:
  name: glpk
  verbose: false

logging:
  level: INFO
```

---

## CLI Usage

```bash
python src/optimization/workflow.py
```

---

## Output

Results are saved to `Data/results/run_YYYYMMDD_HHMMSS/`:
- `flows.csv`: All flow variable values
- `storage.csv`: All storage variable values
- `summary.json`: Objective value and run metadata
- `run.log`: Execution log
