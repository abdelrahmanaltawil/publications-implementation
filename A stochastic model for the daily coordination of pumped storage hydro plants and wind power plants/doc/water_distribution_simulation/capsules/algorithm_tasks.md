# Algorithm Tasks Module (algorithm_tasks.py)

## Purpose
WNTR-based hydraulic simulation execution for water distribution networks.

## Core Functions

### `run_simulation(wn, simulator_type='wntr') -> SimulationResults`
Execute the hydraulic simulation.

**Parameters:**
- `wn`: WNTR WaterNetworkModel (configured network)
- `simulator_type`: `'wntr'` (pure Python) or `'epanet'` (EPANET toolkit)

**Returns:** WNTR SimulationResults containing node and link data.

---

### `run_scenario_simulation(wn, scenario, simulator_type='wntr') -> SimulationResults`
Run simulation with scenario modifications.

**Supported Scenarios:**
| Type | Parameters | Description |
|------|------------|-------------|
| `pipe_break` | `pipe_name`, `start_time`, `end_time` | Simulate pipe closure |
| `demand_surge` | `node_name`, `multiplier` | Increase demand at node |
| `pump_failure` | `pump_name` | Simulate pump outage |

---

### `run_multiple_simulations(wn, scenarios, simulator_type='wntr') -> dict`
Run baseline + multiple scenario simulations.

**Returns:** Dictionary mapping scenario names to results.

---

## Physics Equations

### Governing Laws
1. **Continuity (Mass Balance):**
   $$Q = A \cdot V$$

2. **Energy Conservation (Bernoulli):**
   $$z_1 + \frac{P_1}{\gamma} + \frac{V_1^2}{2g} = z_2 + \frac{P_2}{\gamma} + \frac{V_2^2}{2g} + h_f$$

3. **Friction Loss (Darcy-Weisbach):**
   $$h_f = f \cdot \frac{L}{D} \cdot \frac{V^2}{2g}$$

---

## Simulation Results Structure

| Attribute | Type | Description |
|-----------|------|-------------|
| `results.node['pressure']` | DataFrame | Pressure at each node (m) |
| `results.node['head']` | DataFrame | Hydraulic head at nodes (m) |
| `results.node['demand']` | DataFrame | Demand delivered (m³/s) |
| `results.link['flowrate']` | DataFrame | Flow in links (m³/s) |
| `results.link['velocity']` | DataFrame | Velocity in links (m/s) |
| `results.link['headloss']` | DataFrame | Head loss in links (m) |
