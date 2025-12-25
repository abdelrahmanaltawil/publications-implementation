# Dependency Structure of Rainfall Events in Runoff Modeling Using Copulas

Implementation of the analytical probabilistic model for rainfall-runoff analysis using copulas, based on the methodology from **Hassini and Guo (2022)**.

---

## Overview

This project models the dependency structure between rainfall event characteristics (volume and duration) and their impact on urban runoff volumes using copula-based statistical methods.

### Key Features
- Rainfall event extraction from hourly precipitation data
- Multi-family copula fitting (Gaussian, t, Clayton, Frank, Gumbel)
- CDF computation for runoff volumes using adaptive quadrature integration
- Bootstrap uncertainty analysis
- Sensitivity analysis across copula parameters

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Dependency Structure of Rainfall Events in Runoff Modeling Using Copulas"

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

1. **Configure parameters** in `data/inputs/config.yaml`:
   - Set database path and station IDs
   - Adjust physical model parameters for your catchment
   - Select copula families to fit

2. **Run the analysis**:
   ```bash
   cd src
   python workflow.py
   ```

3. **View results** in `data/results/<station_name>_<timestamp>/`:
   - `01_input_data/` - Raw and processed rainfall data
   - `02_copula_fitting/` - Copula fit metrics and CDF results
   - `03_sensitivity__uncertainty_analysis/` - Bootstrap and sensitivity outputs

---

## Project Structure

```
├── src/
│   ├── preprocessing.py      # Data loading, cleaning, event extraction
│   ├── algorithm_tasks.py    # Copula fitting, CDF computation, analysis
│   ├── postprocessing.py     # Results saving and metadata logging
│   ├── workflow.py           # Main execution script
│   └── helpers/utils.py      # Integration schemes and copula utilities
├── data/
│   ├── inputs/
│   │   ├── config.yaml       # All configurable parameters
│   │   └── phd_research.db   # SQLite database with climate data
│   └── results/              # Output directory for experiment runs
├── doc/
│   ├── capsules/             # Module documentation (see below)
│   └── *.md                  # Additional guides
├── notebooks/                # Visualization and analysis notebooks
├── tests/                    # Unit tests
└── requirements.txt          # Python dependencies
```

---

## 📚 Documentation Capsules

Detailed documentation for each module is available in the capsules directory:

| Module | Capsule | Description |
|--------|---------|-------------|
| Preprocessing | [preprocessing.md](doc/capsules/preprocessing.md) | Data loading, cleaning, event extraction |
| Algorithm | [algorithm.md](doc/capsules/algorithm.md) | Copula fitting, CDF computation, return periods |
| Integration | [integration.md](doc/capsules/integration.md) | Numerical integration schemes and bounds |
| Postprocessing | [postprocessing.md](doc/capsules/postprocessing.md) | Results saving and metadata |
| Workflow | [workflow.md](doc/capsules/workflow.md) | Main pipeline orchestration |

### Additional Documentation
- [Station Selection Framework](doc/stations_selection_framework.md) - Guide for selecting weather stations
- [Station Table Guide](doc/station_table_guide.md) - Parameter collection guide

---

## ⚠️ Documentation Sync Policy

> [!IMPORTANT]
> **Keep documentation in sync with code changes.**

When modifying source files, update the corresponding capsule:

| If you modify... | Update this capsule |
|-----------------|---------------------|
| `src/preprocessing.py` | [doc/capsules/preprocessing.md](doc/capsules/preprocessing.md) |
| `src/algorithm_tasks.py` | [doc/capsules/algorithm.md](doc/capsules/algorithm.md) |
| `src/helpers/utils.py` | [doc/capsules/integration.md](doc/capsules/integration.md) |
| `src/postprocessing.py` | [doc/capsules/postprocessing.md](doc/capsules/postprocessing.md) |
| `src/workflow.py` | [doc/capsules/workflow.md](doc/capsules/workflow.md) |

**Checklist for code changes:**
- [ ] Update function signatures in capsule
- [ ] Update parameter tables if arguments changed
- [ ] Update usage examples if API changed
- [ ] Update "Last Updated" date in capsule header

---

## Configuration

Key parameters in `config.yaml`:

| Section | Parameter | Description |
|---------|-----------|-------------|
| `preprocessing` | `ietd_threshold` | Inter-event time definition (hours) |
| `physics_model` | `h` | Imperviousness fraction |
| `physics_model` | `fc` | Ultimate infiltration rate (mm/hr) |
| `integration` | `method` | `ADAPTIVE_2D_QUADRATURE` or `MONTE_CARLO` |
| `analysis` | `return_periods` | Return periods to compute (years) |

---

## Testing

Run all tests:
```bash
python -m unittest discover tests/ -v
```

Run specific test file:
```bash
python -m unittest tests.test_preprocessing -v
python -m unittest tests.test_algorithm_tasks -v
python -m unittest tests.test_utils -v
```

---

## Citation
> Hassini, S., & Guo, Y. (2022). Analytical Derivation of Urban Runoff-Volume Frequency Models. Journal of Sustainable Water in the Built Environment, 8(1), 04021022. https://doi.org/10.1061/JSWBAY.0000968

---

## License

MIT License
