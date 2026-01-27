# EcoNex Optimization & Simulation Project

This project contains a stochastic model for the daily coordination of pumped storage hydro plants and wind power plants.

## Project Structure

```
├── src/
│   ├── optimization/             # Pyomo-based optimization
│   │   ├── algorithm_tasks.py    # Model formulation & solving
│   │   ├── preprocessing.py
│   │   ├── postprocessing.py
│   │   └── workflow.py
│   └── water_distribution_simulation/  # WNTR-based simulation
│       ├── algorithm_tasks.py    # Simulation execution
│       ├── preprocessing.py
│       ├── postprocessing.py
│       └── workflow.py
├── config/
│   ├── optimization/
│   └── water_distribution_simulation/
│       └── simulation_config.yaml
├── notebooks/
│   ├── optimization/
│   └── water_distribution_simulation/
│       └── simulation_visualization.ipynb
├── doc/
│   ├── optimization/
│   │   └── theoretical_background.md
│   └── water_distribution_simulation/
│       └── pumping.md
└── Data/
    └── results/
```

## Usage

### Optimization
```bash
python src/optimization/workflow.py
```
> **Note**: This model uses complex hydraulic constraints (Piecewise Linear). While it is configured to run with `glpk` by default, a commercial solver like **Gurobi** or **CPLEX** is strongly recommended for production use to ensure convergence and performance.
> **Note**: This model uses complex hydraulic constraints (Piecewise Linear). While it is configured to run with `glpk` by default, a commercial solver like **Gurobi** or **CPLEX** is strongly recommended for production use to ensure convergence and performance.

### Simulation
```bash
python src/water_distribution_simulation/workflow.py
```

## Installation
```bash
pip install -r requirements.txt
```
