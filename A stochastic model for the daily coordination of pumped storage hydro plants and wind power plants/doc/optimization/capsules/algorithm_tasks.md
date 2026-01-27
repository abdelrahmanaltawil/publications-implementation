# Algorithm Tasks Module (algorithm_tasks.py)

## Purpose
Pyomo model construction for the Time-Expanded, Multi-Layer Network Flow optimization.

## Mathematical Formulation

### Sets
- $T = \{1, \ldots, 24\}$: Time steps
- $N = \{1, 2, 3\}$: Nodes (Energy Home, Water Home, Community Hub)
- $L = \{E, P, W\}$: Layers (Energy, Potable, Waste)
- $A$: Arcs (directed edges between nodes)

### Variables
- $x_{ij,t}^l \geq 0$: Flow from node $i$ to $j$ at time $t$ for layer $l$
- $h_{i,t}^l \geq 0$: Storage at node $i$ from $t$ to $t+1$ for layer $l$

### Constraints
1. **Mass Balance:** $\sum_j x_{ji,t}^l + h_{i,t-1}^l + D_{i,t}^l = \sum_k x_{ik,t}^l + h_{i,t}^l$
2. **Flow Capacity:** $x_{ij,t}^l \leq U_{ij}^l$
3. **Storage Capacity:** $h_{i,t}^l \leq S_i^l$
4. **Treatment Coupling:** $x_{out,t}^P = \eta \cdot x_{in,t}^W$
5. **Pumping Coupling:** $x_{pump,t}^E \geq k \cdot x_{pipe,t}^{Water}$

### Objective
Minimize total operational cost:
$$\min Z = \sum_{t,i,j} C_{ij,t}^l \cdot x_{ij,t}^l$$

---

## Functions

### `build_model(data: dict) -> pyo.ConcreteModel`
Construct the Pyomo ConcreteModel from preprocessed data.

**Parameters:**
- `data`: Network data dictionary from `build_network_data()`.

**Returns:** Pyomo ConcreteModel ready for solving.

---

### `solve_model(model: pyo.ConcreteModel, solver: str = 'glpk') -> tuple`
Solve the optimization model.

**Parameters:**
- `model`: Pyomo ConcreteModel.
- `solver`: Solver name (glpk, cbc, gurobi, cplex).
- `tee`: Print solver output.

**Returns:** Tuple (model, results).

---

## Model Components

| Component | Type | Description |
|-----------|------|-------------|
| `model.T` | Set | Time steps |
| `model.N` | Set | Nodes |
| `model.L` | Set | Layers |
| `model.A` | Set | Arcs (i,j) tuples |
| `model.x` | Var | Flow variables |
| `model.h` | Var | Storage variables |
| `model.mass_balance` | Constraint | Conservation at each node |
| `model.treatment_coupling` | Constraint | W→P conversion |
| `model.pumping_coupling` | Constraint | Energy for water transport |
| `model.objective` | Objective | Minimize cost |
