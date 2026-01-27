# Preprocessing Module (preprocessing.py)

## Purpose
Network loading, demand pattern configuration, and pump control setup using WNTR.

## Functions

### `load_config(config_path: str) -> dict`
Load YAML configuration file.

**Returns:** Configuration dictionary with network, simulation, and control settings.

---

### `load_network(config: dict) -> WaterNetworkModel`
Load or build the water network model.

**Behavior:**
- If `config['network']['inp_file']` exists → Load EPANET .inp file
- Otherwise → Build sample network programmatically

---

### `apply_demand_patterns(wn, config) -> WaterNetworkModel`
Apply time-varying demand patterns to the network.

**Pattern Types:**
| Type | Description |
|------|-------------|
| `residential` | Morning/evening peaks (7-9 AM, 6-9 PM) |
| `industrial` | Daytime plateau (8 AM - 6 PM) |
| `flat` | Constant multiplier = 1.0 |
| `custom` | User-defined 24-hour multipliers |

---

### `apply_pump_controls(wn, config) -> WaterNetworkModel`
Configure pump controls and schedules.

**Control Types:**
| Type | Description |
|------|-------------|
| `none` | No controls |
| `tank_level` | On/off based on tank level |
| `time_based` | On/off based on time of day |

---

### `configure_simulation_options(wn, config) -> WaterNetworkModel`
Set simulation time options.

**Parameters from config:**
- `duration_hours`: Simulation duration (default: 24)
- `timestep_minutes`: Hydraulic timestep (default: 60)
- `report_timestep_minutes`: Reporting interval

---

### `preprocess(config_path: str) -> tuple`
Run complete preprocessing pipeline.

**Returns:** `(WaterNetworkModel, config_dict)`
