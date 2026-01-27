# Preprocessing Module

## Purpose
Data loading, synthetic profile generation, and network topology construction for the EcoNex optimization model.

## Functions

### `load_config(config_path: str) -> dict`
Load YAML configuration file containing all model parameters.

**Parameters:**
- `config_path`: Path to the YAML configuration file.

**Returns:** Dictionary with sets, parameters, and solver settings.

---

### `generate_solar_profile(T: int, peak_hour: int = 12, max_generation: float = 5.0) -> dict`
Generate synthetic solar generation profile (bell curve centered at noon).

**Parameters:**
- `T`: Number of time steps (hours).
- `peak_hour`: Hour of maximum solar generation.
- `max_generation`: Maximum generation in kW.

**Returns:** Dictionary `{t: generation_kW}` for each hour.

---

### `generate_demand_profiles(T: int, nodes: list) -> dict`
Generate water and energy demand profiles with morning/evening peaks.

**Parameters:**
- `T`: Number of time steps.
- `nodes`: List of node identifiers.

**Returns:** Nested dictionary `{node: {layer: {t: demand}}}`.

---

### `generate_price_profile(T: int, peak_start: int = 16, peak_end: int = 21) -> dict`
Generate Time-of-Use electricity pricing with peak/off-peak rates.

**Parameters:**
- `T`: Number of time steps.
- `peak_start`, `peak_end`: Peak pricing window (hours).

**Returns:** Dictionary `{t: price_per_kWh}`.

---

### `build_network_data(config: dict) -> dict`
Construct complete network data structure for Pyomo model.

**Returns:** Dictionary containing:
- `nodes`: Set of node IDs
- `arcs`: List of (i, j) tuples
- `layers`: Set of layer identifiers {E, P, W}
- `capacities`: Arc and storage capacities
- `costs`: Flow costs by arc and time
- `demands`: Net demand/supply by node, layer, time
- `coupling`: Treatment efficiency η and pumping intensity k
