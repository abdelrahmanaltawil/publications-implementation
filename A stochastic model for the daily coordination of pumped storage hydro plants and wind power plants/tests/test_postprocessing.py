import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path

import pyomo.environ as pyo

from src.postprocessing import extract_solution, create_summary, save_results


@pytest.fixture
def mock_water_model():
    m = pyo.ConcreteModel()
    m.T = pyo.Set(initialize=[0, 1])
    m.Links = pyo.Set(initialize=["L1"])
    m.Nodes = pyo.Set(initialize=["N1"])
    m.Pumps = pyo.Set(initialize=["P1"])
    m.Valves = pyo.Set(initialize=[])
    m.Junctions = pyo.Set(initialize=["N1"])
    m.Q = pyo.Var(m.Links, m.T, initialize=10.0)
    m.H = pyo.Var(m.Nodes, m.T, initialize=50.0)
    m.Status = pyo.Var(m.Pumps, m.T, initialize=1.0)
    m.SlackPos = pyo.Var(m.Junctions, m.T, initialize=0.0)
    m.SlackNeg = pyo.Var(m.Junctions, m.T, initialize=0.0)
    m.objective = pyo.Objective(expr=100.0)
    return m


def test_extract_solution_water(mock_water_model):
    results = extract_solution(mock_water_model)

    assert results["objective"] == 100.0
    assert len(results["water"]["flows"]) == 2          # 1 link × 2 time steps
    assert results["water"]["flows"][0]["flow_rate"] == 10.0
    assert len(results["water"]["heads"]) == 2
    assert results["water"]["heads"][0]["head"] == 50.0
    assert len(results["water"]["pump_status"]) == 2
    assert results["water"]["pump_status"][0]["status"] == 1
    assert results["energy"] == {}


def test_create_summary(mock_water_model):
    results = {"objective": 100.0, "water": {}, "energy": {}}
    solver_results = MagicMock()
    solver_results.solver.status = "ok"
    solver_results.solver.termination_condition = "optimal"
    solver_results.solver.time = 1.5

    summary = create_summary("run_test", mock_water_model, results, solver_results)

    assert summary["run_id"] == "run_test"
    assert summary["objective_value"] == 100.0
    assert summary["solver_status"] == "ok"
    assert summary["num_variables"] > 0


def test_save_results_water(tmp_path):
    run_dir = tmp_path / "run_test"
    run_dir.mkdir()

    results = {
        "objective": 100.0,
        "water": {
            "flows":       [{"link": "L1", "time": 0, "flow_rate": 10}],
            "heads":       [{"node": "N1", "time": 0, "head": 50}],
            "pump_status": [{"pump": "P1", "time": 0, "status": 1}],
            "slack":       [],
        },
        "energy": {},
    }
    summary = {"solver_status": "ok"}

    save_results(results, summary, run_dir)

    assert (run_dir / "water" / "flows.csv").exists()
    assert (run_dir / "water" / "heads.csv").exists()
    assert (run_dir / "water" / "pump_status.csv").exists()
    assert (run_dir / "summary.json").exists()

    with open(run_dir / "summary.json") as f:
        saved = json.load(f)
    assert saved["run_id"] == run_dir.name


def test_save_results_energy(tmp_path):
    run_dir = tmp_path / "run_test"
    run_dir.mkdir()

    results = {
        "objective": 50.0,
        "water": {},
        "energy": {
            "dispatch":   [{"bus": "bus1", "time": 0, "P_import": 10, "P_export": 0,
                            "P_pv": 5, "Q_ch": 2, "Q_dis": 0}],
            "soc":        [{"bus": "bus1", "time": 0, "E_soc": 100}],
            "line_flows": [],
            "voltages":   [{"bus": "bus1", "time": 0, "U": 1.0, "theta": 0.0}],
        },
    }
    summary = {"solver_status": "ok"}

    save_results(results, summary, run_dir)

    assert (run_dir / "energy" / "dispatch.csv").exists()
    assert (run_dir / "energy" / "soc.csv").exists()
    assert (run_dir / "energy" / "voltages.csv").exists()
    assert (run_dir / "summary.json").exists()
