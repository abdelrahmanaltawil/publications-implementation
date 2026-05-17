"""Postprocessing — solution extraction and result saving.

Handles both water and energy results, writing to run_dir/water/ and
run_dir/energy/ subdirectories respectively.
"""

import json
import logging
import shutil
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo




logger = logging.getLogger("econex.postprocessing")


# ---------------------------------------------------------------------------
# Solution extraction
# ---------------------------------------------------------------------------

def extract_solution(model: pyo.ConcreteModel) -> dict:
    """Extract all solved variable values from the model.

    Returns:
        Dict with 'objective' and domain sub-dicts 'water' and/or 'energy'.
    """
    try:
        obj_val = pyo.value(model.objective)
    except (ValueError, TypeError):
        logger.warning("Model objective has no value — returning empty results.")
        return {"objective": None, "water": {}, "energy": {}}

    results = {"objective": obj_val, "water": {}, "energy": {}}

    if hasattr(model, "Q"):
        results["water"] = _extract_water(model)

    if hasattr(model, "P_import"):
        results["energy"] = _extract_energy(model)

    logger.info(f"Solution extracted. Objective: {obj_val:.4f}")
    return results


def _extract_water(model: pyo.ConcreteModel) -> dict:
    flows, heads, pump_status, slack = [], [], [], []

    for l in model.Links:
        for t in model.T:
            flows.append({"link": l, "time": t, "flow_rate": round(pyo.value(model.Q[l, t]), 4)})

    for n in model.Nodes:
        for t in model.T:
            heads.append({"node": n, "time": t, "head": round(pyo.value(model.H[n, t]), 4)})

    for p in model.Pumps:
        for t in model.T:
            try:
                pump_status.append({"pump": p, "time": t,
                                    "status": int(round(pyo.value(model.Status[p, t])))})
            except Exception:
                pass

    for n in model.Junctions:
        for t in model.T:
            vp = pyo.value(model.SlackPos[n, t])
            vn = pyo.value(model.SlackNeg[n, t])
            if vp > 1e-6 or vn > 1e-6:
                slack.append({"node": n, "time": t, "slack_pos": vp, "slack_neg": vn})

    return {"flows": flows, "heads": heads, "pump_status": pump_status, "slack": slack}


def _extract_energy(model: pyo.ConcreteModel) -> dict:
    dispatch, soc, line_flows, voltages = [], [], [], []

    for b in model.Buses:
        for t in model.T:
            dispatch.append({
                "bus": b, "time": t,
                "P_import": round(pyo.value(model.P_import[b, t]), 4),
                "P_export": round(pyo.value(model.P_export[b, t]), 4),
                "P_pv":     round(pyo.value(model.P_pv[b, t]), 4),
                "Q_ch":     round(pyo.value(model.Q_ch[b, t]), 4),
                "Q_dis":    round(pyo.value(model.Q_dis[b, t]), 4),
            })
            soc.append({
                "bus": b, "time": t,
                "E_soc": round(pyo.value(model.E_soc[b, t]), 4),
            })
            voltages.append({
                "bus": b, "time": t,
                "U": round(pyo.value(model.U[b, t]), 6),
                "theta": round(pyo.value(model.theta[b, t]), 6),
            })

    for l in model.ELines:
        for t in model.T:
            line_flows.append({
                "line": l, "time": t,
                "P_line": round(pyo.value(model.P_line[l, t]), 4),
                "Q_line": round(pyo.value(model.Q_line[l, t]), 4),
                "phi":    round(pyo.value(model.phi[l, t]), 6),
                "chi":    round(pyo.value(model.chi[l, t]), 6),
            })

    return {"dispatch": dispatch, "soc": soc,
            "line_flows": line_flows, "voltages": voltages}


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def create_summary(run_id: str, model: pyo.ConcreteModel,
                   results: dict, solver_results) -> dict:
    """Compute summary metrics.

    Args:
        run_id:         Run directory name.
        model:          Solved ConcreteModel.
        results:        From extract_solution().
        solver_results: Pyomo solver result object.

    Returns:
        Summary dict saved to summary.json.
    """
    n_vars = sum(1 for _ in model.component_data_objects(pyo.Var, active=True))
    n_cons = sum(1 for _ in model.component_data_objects(pyo.Constraint, active=True))

    summary = {
        "run_id": run_id,
        "solver_status": str(solver_results.solver.status),
        "termination_condition": str(solver_results.solver.termination_condition),
        "objective_value": results["objective"],
        "solver_time_s": getattr(solver_results.solver, "time", "N/A"),
        "num_variables": n_vars,
        "num_constraints": n_cons,
    }

    water = results.get("water", {})
    if water.get("slack"):
        summary["water_slack_violations"] = len(water["slack"])

    return summary


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save_results(results: dict, summary: dict, run_dir: Path) -> None:
    """Write all results to disk.

    Water results → run_dir/water/
    Energy results → run_dir/energy/
    Summary        → run_dir/summary.json

    Args:
        results:  From extract_solution().
        summary:  From create_summary().
        run_dir:  Top-level run directory.
    """
    logger.info(f"Saving results to {run_dir}")

    water = results.get("water", {})
    if water:
        w_dir = run_dir / "water"
        w_dir.mkdir(exist_ok=True)
        if water.get("flows"):
            pd.DataFrame(water["flows"]).to_csv(w_dir / "flows.csv", index=False)
        if water.get("heads"):
            pd.DataFrame(water["heads"]).to_csv(w_dir / "heads.csv", index=False)
        if water.get("pump_status"):
            pd.DataFrame(water["pump_status"]).to_csv(w_dir / "pump_status.csv", index=False)
        if water.get("slack"):
            pd.DataFrame(water["slack"]).to_csv(w_dir / "slack.csv", index=False)

    energy = results.get("energy", {})
    if energy:
        e_dir = run_dir / "energy"
        e_dir.mkdir(exist_ok=True)
        if energy.get("dispatch"):
            pd.DataFrame(energy["dispatch"]).to_csv(e_dir / "dispatch.csv", index=False)
        if energy.get("soc"):
            pd.DataFrame(energy["soc"]).to_csv(e_dir / "soc.csv", index=False)
        if energy.get("line_flows"):
            pd.DataFrame(energy["line_flows"]).to_csv(e_dir / "line_flows.csv", index=False)
        if energy.get("voltages"):
            pd.DataFrame(energy["voltages"]).to_csv(e_dir / "voltages.csv", index=False)

    summary["run_id"] = run_dir.name
    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("All results saved")


def save_network_files(run_dir: Path, config: dict, project_root: Path) -> None:
    """Copy input network files to run directory for reproducibility."""
    water_cfg = config.get("water", {})
    if water_cfg.get("network"):
        src = project_root / water_cfg["network"]
        if src.exists():
            shutil.copy2(src, run_dir / src.name)

    energy_cfg = config.get("energy", {})
    if energy_cfg.get("network"):
        src = project_root / energy_cfg["network"]
        if src.exists():
            shutil.copy2(src, run_dir / src.name)
