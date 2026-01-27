# Postprocessing Module

## Purpose
Solution extraction, results formatting, and metadata logging for reproducibility.

## Functions

### `extract_solution(model: pyo.ConcreteModel) -> dict`
Extract optimal variable values from solved model.

**Parameters:**
- `model`: Solved Pyomo ConcreteModel.

**Returns:** Dictionary containing:
- `flows`: DataFrame with columns [i, j, t, layer, value]
- `storage`: DataFrame with columns [i, t, layer, value]
- `objective`: Optimal objective value

---

### `save_results(results: dict, output_dir: str, run_id: str = None) -> str`
Save extracted results to files.

**Parameters:**
- `results`: Dictionary from `extract_solution()`.
- `output_dir`: Path to output directory.
- `run_id`: Optional run identifier (defaults to timestamp).

**Returns:** Path to created run directory.

**Output Files:**
- `flows.csv`: All flow variable values
- `storage.csv`: All storage variable values
- `summary.json`: Objective value and run metadata

---

### `log_metadata(model: pyo.ConcreteModel, solver_results, output_path: str)`
Log solver status, timing, and model statistics.

**Parameters:**
- `model`: The Pyomo model.
- `solver_results`: Results object from solver.
- `output_path`: Path for metadata JSON file.

**Logged Information:**
- Solver status and termination condition
- Solve time
- Number of variables and constraints
- Objective value
- Timestamp
