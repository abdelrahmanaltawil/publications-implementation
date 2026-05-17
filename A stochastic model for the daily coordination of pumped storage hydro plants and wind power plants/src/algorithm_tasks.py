"""Algorithm tasks — model construction and solving.

build_model() assembles a shared Pyomo ConcreteModel by delegating to
private sub-model builders based on config flags:
  - config['run_water']  → _add_water_submodel()   (W1–W24)
  - config['run_energy'] → _add_energy_submodel()  (E1–E13)
  - config['run_nexus']  → _add_nexus_constraints() (coupling, placeholder)

solve_model() wraps Pyomo's SolverFactory with timeout and logging.
"""

import logging

import numpy as np
import pyomo.environ as pyo
import wntr
from pyomo.opt import SolverFactory

from src.helpers.water.hydraulic_utils import (
    calc_K,
    create_piecewise_pipe_curve,
    create_piecewise_pump_curve,
    add_pwl_constraint,
    get_pump_curve_points,
)
from scipy.optimize import curve_fit
from src.helpers.energy.power_utils import (
    calc_line_admittance,
    linearized_ac_coefficients,
    create_pwl_current_segments,
)

logger = logging.getLogger("econex.algorithm_tasks")

_MAX_FLOW = 5.0    # m³/s — loose upper bound for water big-M and variable bounds
_MAX_HEAD = 500.0  # metres


def _linearize_hw(K: float, Q0: float, range_Q: float = None):
    """First-order Taylor expansion (or secant) of dH = sign(Q)·K·|Q|^1.852 around Q0.

    Returns (a, b) such that dH ≈ a + b·Q.
    If range_Q is provided, uses MILPNet's two_point_linear approach (secant line).
    At Q0=0 returns (0, 0) — a flat constraint is correct for zero-flow pipes.
    """
    if abs(Q0) < 1e-8:
        return 0.0, 0.0
    
    if range_Q is not None and range_Q > 0:
        # MILPNet two-point linear (secant)
        e1 = 1.852
        Q_1 = Q0 * (1 - range_Q)
        Q_2 = Q0 * (1 + range_Q)
        dH_1 = np.sign(Q_1) * K * abs(Q_1) ** e1
        dH_2 = np.sign(Q_2) * K * abs(Q_2) ** e1
        
        if abs(Q_2 - Q_1) < 1e-8:
            b = 1.852 * K * abs(Q0) ** 0.852
        else:
            b = (dH_2 - dH_1) / (Q_2 - Q_1)
        a = dH_2 - Q_2 * b
    else:
        # MILPNet one-point linear (tangent)
        h0 = np.sign(Q0) * K * abs(Q0) ** 1.852
        b = 1.852 * K * abs(Q0) ** 0.852  # Derivative is always positive
        a = h0 - b * Q0
        
    return float(a), float(b)


def _linearize_pump(pump, Q0: float):
    """First-order Taylor expansion of pump curve H=A-B·Q^2 around Q0.

    Returns (c, d) such that H ≈ c + d·Q.
    """
    pts = get_pump_curve_points(pump)
    xdata = [p[0] for p in pts]
    ydata = [p[1] for p in pts]

    def pump_func(x, a, b):
        return a - b * x ** 2

    try:
        popt, _ = curve_fit(pump_func, xdata, ydata)
        A, B = float(popt[0]), float(popt[1])
    except Exception:
        A, B = float(ydata[0]), 0.1

    if abs(Q0) < 1e-8:
        return float(A), 0.0
    # H(Q) = A - B*Q^2  →  d/dQ = -2*B*Q0
    c = A + B * Q0 ** 2  # H(Q0) + 2*B*Q0^2 - B*Q0^2
    d = -2.0 * B * Q0
    return float(c), float(d)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_model(data: dict, config: dict) -> pyo.ConcreteModel:
    """Construct the shared Pyomo ConcreteModel.

    Args:
        data:   From preprocessing.build_network_data() — keys 'water' and/or 'energy'.
        config: Unified configuration dict.

    Returns:
        ConcreteModel ready to pass to solve_model().
    """
    model = pyo.ConcreteModel(name="EcoNex_Optimization")

    T = config.get("T", 24)
    model.T = pyo.RangeSet(0, T - 1, doc="Hourly time steps")
    model.dt = pyo.Param(initialize=3600, doc="Step size [s]")

    run_water = config.get("run_water", True) or config.get("run_nexus", False)
    run_energy = config.get("run_energy", False) or config.get("run_nexus", False)

    if run_water:
        if "water" not in data:
            raise ValueError("run_water=true but no water data was loaded in preprocessing.")
        _add_water_submodel(model, data["water"])

    if run_energy:
        if "energy" not in data:
            raise ValueError("run_energy=true but no energy data was loaded in preprocessing.")
        _add_energy_submodel(model, data["energy"])

    if config.get("run_nexus", False):
        _add_nexus_constraints(model, data)

    _build_objective(model)

    logger.info("Model assembled successfully")
    return model


def solve_model(
    model: pyo.ConcreteModel,
    solver: str = "glpk",
    tee: bool = True,
    timeout: int = 300,
    logfile: str = None,
) -> tuple:
    """Solve the assembled model.

    Args:
        model:   ConcreteModel from build_model().
        solver:  Solver name ('glpk', 'gurobi', 'cbc', etc.).
        tee:     Stream solver output to stdout.
        timeout: Time limit in seconds.
        logfile: Path to save solver log.

    Returns:
        (model, solver_results) tuple.

    Raises:
        RuntimeError: If the solver is not available.
    """
    logger.info(f"Solving with {solver} (timeout={timeout}s)")
    opt = SolverFactory(solver)
    if not opt.available():
        raise RuntimeError(
            f"Solver '{solver}' not available. "
            "Install GLPK: brew install glpk  |  pip install glpk"
        )

    if solver == "glpk":
        opt.options["tmlim"] = timeout
    elif solver in ("gurobi", "cplex"):
        opt.options["TimeLimit"] = timeout
    elif solver == "cbc":
        opt.options["seconds"] = timeout

    results = opt.solve(model, tee=tee, logfile=logfile)
    logger.info(
        f"Solver finished: {results.solver.status} / "
        f"{results.solver.termination_condition}"
    )
    return model, results


# ---------------------------------------------------------------------------
# Water sub-model  (W1–W24)
# ---------------------------------------------------------------------------

def _epanet_pipe_max_flows(wn: "wntr.network.WaterNetworkModel", T: int) -> dict:
    """Run a quick EPANET simulation and return 2× peak flow per pipe.

    This is the MILPNet approach: set each pipe's PWL domain to twice the
    maximum absolute flow observed in simulation, so all PWL segments cover
    the actual operating range rather than a global worst-case ceiling.

    Returns:
        Dict[pipe_name, float] — per-pipe PWL upper bound in m³/s.
        Falls back to _MAX_FLOW for pipes not found in the simulation output.
    """
    import copy
    wn_sim = copy.deepcopy(wn)
    wn_sim.options.time.duration = T * 3600
    wn_sim.options.time.hydraulic_timestep = 3600
    wn_sim.options.time.report_timestep = 3600
    try:
        sim = wntr.sim.EpanetSimulator(wn_sim)
        res = sim.run_sim()
        flowrate_df = res.link["flowrate"]
        result = {}
        for pipe in wn.pipe_name_list:
            if pipe in flowrate_df.columns:
                peak = float(flowrate_df[pipe].abs().max())
                result[pipe] = max(peak * 2.0, 0.01)
            else:
                result[pipe] = _MAX_FLOW
        logger.info(f"EPANET pre-simulation: per-pipe max flows computed for {len(result)} pipes")
        return result
    except Exception as exc:
        logger.warning(f"EPANET pre-simulation failed ({exc}); using global max_flow fallback")
        return {}


def _add_water_submodel(model: pyo.ConcreteModel, data: dict) -> None:
    """Add hydraulic variables, parameters, and constraints to model.

    Implements W1–W6 from theoretical_background.md.
    Registers model.water_cost (Expression) for the shared objective.

    Args:
        model: Shared ConcreteModel with model.T and model.dt already set.
        data:  {'inp_file': str, 'config': dict}
    """
    inp_file = data["inp_file"]
    logger.info(f"Building water sub-model from {inp_file}")
    wn = wntr.network.WaterNetworkModel(inp_file)

    # Sets
    junctions  = wn.junction_name_list
    tanks      = wn.tank_name_list
    reservoirs = wn.reservoir_name_list
    nodes      = wn.node_name_list
    pipes      = wn.pipe_name_list
    pumps      = wn.pump_name_list
    valves     = wn.valve_name_list
    links      = wn.link_name_list

    model.Junctions  = pyo.Set(initialize=junctions)
    model.Tanks      = pyo.Set(initialize=tanks)
    model.Reservoirs = pyo.Set(initialize=reservoirs)
    model.Nodes      = pyo.Set(initialize=nodes)
    model.Pipes      = pyo.Set(initialize=pipes)
    model.Pumps      = pyo.Set(initialize=pumps)
    model.Valves     = pyo.Set(initialize=valves)
    model.Links      = pyo.Set(initialize=links)

    link_map = {name: (lnk.start_node_name, lnk.end_node_name)
                for name, lnk in wn.links()}

    # Parameters
    tank_areas     = {t: np.pi * (wn.get_node(t).diameter / 2) ** 2 for t in tanks}
    initial_levels = {t: wn.get_node(t).level + wn.get_node(t).elevation for t in tanks}
    min_levels     = {t: wn.get_node(t).min_level + wn.get_node(t).elevation for t in tanks}
    max_levels     = {t: wn.get_node(t).max_level + wn.get_node(t).elevation for t in tanks}

    T_val = len(list(model.T))
    base_demands = {}
    for j in junctions:
        node = wn.get_node(j)
        demands = []
        for t in range(T_val):
            if not node.demand_timeseries_list:
                demands.append(0.0)
                continue
            ts = node.demand_timeseries_list[0]
            try:
                # Timeseries.at() applies the pattern multiplier at t seconds
                demands.append(ts.at(t * 3600))
            except Exception:
                demands.append(ts.base_value)
        base_demands[j] = demands
    pipe_Ks = {
        p: calc_K(wn.get_link(p).length, wn.get_link(p).diameter, wn.get_link(p).roughness)
        for p in pipes
    }

    # MILPNet approach: run EPANET first to get realistic per-pipe flow ceilings.
    # Using a global ceiling wastes all PWL segments on an irrelevant range when
    # actual flows are orders of magnitude smaller (e.g. 0.1 vs 5.0 m³/s).
    # EPANET operating-point data (per pipe/pump, per timestep) for linearization.
    # When present (validation mode), replaces binary SOS2 PWL with fast linear constraints.
    pipe_flows_sim = data.get("pipe_flows_sim")  # dict[pipe, list[float]]
    pump_flows_sim = data.get("pump_flows_sim")  # dict[pump, list[float]]

    # Fallback: per-pipe max flows for binary SOS2 PWL (non-validation mode)
    if pipe_flows_sim is None:
        pipe_max_flows = data.get("pipe_max_flows") or _epanet_pipe_max_flows(wn, T_val)
    else:
        pipe_max_flows = {}  # not needed when using linearization

    model.TankArea = pyo.Param(model.Tanks, initialize=tank_areas)

    # Variables
    if pipe_flows_sim:
        # Bound each pipe's flow to the direction and ~2× magnitude of the EPANET simulation.
        # In looped networks, the linearized H-W alone has multiple feasible LP solutions;
        # direction-fixing eliminates that degeneracy and drives the solver to the EPANET point.
        def q_bounds(m, l, t):
            if l in m.Pipes:
                Q0 = pipe_flows_sim.get(l, [0.0] * T_val)[t]
                margin = max(abs(Q0) * 2.0, 0.005)
                if abs(Q0) < 1e-6:
                    return (-margin, margin)
                return (0.0, margin) if Q0 > 0 else (-margin, 0.0)
            return (0.0, _MAX_FLOW)  # pumps: non-negative
    else:
        def q_bounds(m, l, t):
            return (-_MAX_FLOW, _MAX_FLOW) if l in m.Pipes else (0, _MAX_FLOW)

    model.Q       = pyo.Var(model.Links, model.T, bounds=q_bounds, domain=pyo.Reals)
    model.H       = pyo.Var(model.Nodes, model.T, bounds=(0, _MAX_HEAD), domain=pyo.NonNegativeReals)
    model.Status  = pyo.Var(model.Pumps | model.Valves, model.T, domain=pyo.Binary)
    model.SlackPos = pyo.Var(model.Junctions, model.T, domain=pyo.NonNegativeReals)
    model.SlackNeg = pyo.Var(model.Junctions, model.T, domain=pyo.NonNegativeReals)

    # W1 — Mass balance
    def mass_balance_rule(m, n, t):
        inflow  = sum(m.Q[l, t] for l in m.Links if link_map[l][1] == n)
        outflow = sum(m.Q[l, t] for l in m.Links if link_map[l][0] == n)
        return inflow - outflow + m.SlackPos[n, t] - m.SlackNeg[n, t] == base_demands[n][t]

    model.MassBalance = pyo.Constraint(model.Junctions, model.T, rule=mass_balance_rule)

    # W4 — Tank dynamics
    def tank_dynamics_rule(m, n, t):
        if t == 0:
            return m.H[n, t] == initial_levels[n]
        inflow  = sum(m.Q[l, t - 1] for l in m.Links if link_map[l][1] == n)
        outflow = sum(m.Q[l, t - 1] for l in m.Links if link_map[l][0] == n)
        return m.H[n, t] == m.H[n, t - 1] + (m.dt / m.TankArea[n]) * (inflow - outflow)

    model.TankDynamics = pyo.Constraint(model.Tanks, model.T, rule=tank_dynamics_rule)
    
    # MILPNet Tank Inlet Auto-Shutoff Logic
    # -------------------------------------
    model.TankAtMax = pyo.Var(model.Tanks, model.T, domain=pyo.Binary)
    model.TankAtMin = pyo.Var(model.Tanks, model.T, domain=pyo.Binary)
    model.TankBoundsHit = pyo.Var(model.Tanks, model.T, domain=pyo.Binary)
    model.TankSlack = pyo.Var(model.Pipes, model.T, domain=pyo.Reals)
    
    _M_tank = 1000.0
    _eps_head = 0.001
    
    def tank_max_1(m, n, t):
        if t == 0: return m.TankAtMax[n, t] == 0
        return m.H[n, t-1] >= max_levels[n] - _M_tank * (1 - m.TankAtMax[n, t])
    def tank_max_2(m, n, t):
        if t == 0: return pyo.Constraint.Skip
        return m.H[n, t-1] + _eps_head <= max_levels[n] + _M_tank * m.TankAtMax[n, t]
        
    def tank_min_1(m, n, t):
        if t == 0: return m.TankAtMin[n, t] == 0
        return m.H[n, t-1] >= min_levels[n] - _M_tank * m.TankAtMin[n, t] + _eps_head
    def tank_min_2(m, n, t):
        if t == 0: return pyo.Constraint.Skip
        return m.H[n, t-1] <= min_levels[n] + _M_tank * (1 - m.TankAtMin[n, t])
        
    model.TankMax1 = pyo.Constraint(model.Tanks, model.T, rule=tank_max_1)
    model.TankMax2 = pyo.Constraint(model.Tanks, model.T, rule=tank_max_2)
    model.TankMin1 = pyo.Constraint(model.Tanks, model.T, rule=tank_min_1)
    model.TankMin2 = pyo.Constraint(model.Tanks, model.T, rule=tank_min_2)
    
    def tank_bounds_hit_rule(m, n, t):
        return m.TankBoundsHit[n, t] <= m.TankAtMax[n, t] + m.TankAtMin[n, t]
    def tank_bounds_hit_rule_2(m, n, t):
        return m.TankBoundsHit[n, t] >= m.TankAtMax[n, t]
    def tank_bounds_hit_rule_3(m, n, t):
        return m.TankBoundsHit[n, t] >= m.TankAtMin[n, t]
        
    model.TankBoundsHit1 = pyo.Constraint(model.Tanks, model.T, rule=tank_bounds_hit_rule)
    model.TankBoundsHit2 = pyo.Constraint(model.Tanks, model.T, rule=tank_bounds_hit_rule_2)
    model.TankBoundsHit3 = pyo.Constraint(model.Tanks, model.T, rule=tank_bounds_hit_rule_3)

    model.TankPipeShutoffUpper = pyo.ConstraintList()
    model.TankPipeShutoffLower = pyo.ConstraintList()
    
    for p in pipes:
        n_list = [n for n in tanks if link_map[p][0] == n or link_map[p][1] == n]
        if not n_list:
            for t in model.T:
                model.TankPipeShutoffUpper.add(model.TankSlack[p, t] == 0.0)
            continue
        
        for t in model.T:
            bounds_hit = sum(model.TankBoundsHit[n, t] for n in n_list)
            # Shut off flow
            model.TankPipeShutoffUpper.add(model.Q[p, t] <= _MAX_FLOW * (1 - bounds_hit))
            model.TankPipeShutoffLower.add(model.Q[p, t] >= -_MAX_FLOW * (1 - bounds_hit))
            # Activate slack decoupling
            model.TankPipeShutoffUpper.add(model.TankSlack[p, t] <= _MAX_HEAD * bounds_hit)
            model.TankPipeShutoffLower.add(model.TankSlack[p, t] >= -_MAX_HEAD * bounds_hit)

    # Reservoir heads (fixed)
    model.ResHead = pyo.Constraint(
        model.Reservoirs, model.T,
        rule=lambda m, n, t: m.H[n, t] == wn.get_node(n).base_head
    )

    # W1–W3 — Pipe head loss (Hazen-Williams)
    model.dH = pyo.Var(model.Pipes, model.T, domain=pyo.Reals)
    model.dH_def = pyo.Constraint(
        model.Pipes, model.T,
        rule=lambda m, p, t: m.dH[p, t] == m.H[link_map[p][0], t] - m.H[link_map[p][1], t]
    )
    t_list = list(model.T)
    if pipe_flows_sim:
        # MILPNet approach adapted: linearize H-W around EPANET operating point.
        # Eliminates all pipe-PWL binary variables → pure LP, solves in seconds.
        for p in pipes:
            K_p = pipe_Ks[p]
            flows_p = pipe_flows_sim.get(p, [0.0] * T_val)
            for t_idx, t in enumerate(t_list):
                a, b = _linearize_hw(K_p, flows_p[t_idx])
                model.add_component(
                    f"lin_hw_{p}_{t}",
                    pyo.Constraint(expr=model.dH[p, t] + model.TankSlack[p, t] == a + b * model.Q[p, t])
                )
    else:
        # Binary SOS2 PWL fallback (general optimization, no prior simulation)
        for p in pipes:
            pwl_max_q = pipe_max_flows.get(p, _MAX_FLOW)
            pts = create_piecewise_pipe_curve(pipe_Ks[p], max_flow=pwl_max_q, num_segments=3)
            for t in model.T:
                add_pwl_constraint(model, f"pwl_pipe_{p}_{t}", model.Q[p, t], model.dH[p, t] + model.TankSlack[p, t], pts)

    # W5–W7 — Pump head-flow curve + ON/OFF coupling
    model.PumpHeadGain = pyo.Var(model.Pumps, model.T, domain=pyo.NonNegativeReals)
    if pump_flows_sim:
        # Linearize pump curve around EPANET operating point (no binary variables)
        for p in pumps:
            pump_link = wn.get_link(p)
            flows_p = pump_flows_sim.get(p, [0.0] * T_val)
            for t_idx, t in enumerate(t_list):
                c, d = _linearize_pump(pump_link, flows_p[t_idx])
                model.add_component(
                    f"lin_pump_{p}_{t}",
                    pyo.Constraint(expr=model.PumpHeadGain[p, t] == c + d * model.Q[p, t])
                )
    else:
        # Binary SOS2 PWL fallback
        for p in pumps:
            pts = create_piecewise_pump_curve(wn.get_link(p), num_segments=6)
            for t in model.T:
                add_pwl_constraint(model, f"pwl_pump_{p}_{t}", model.Q[p, t], model.PumpHeadGain[p, t], pts)

    # Note: model.Status is now restricted to Pumps. Valves use V1/V2/V3.
    model.Status  = pyo.Var(model.Pumps, model.T, domain=pyo.Binary)

    model.PumpStatusFlow = pyo.Constraint(
        model.Pumps, model.T,
        rule=lambda m, p, t: m.Q[p, t] <= _MAX_FLOW * m.Status[p, t]
    )

    _M = 200.0
    model.PumpHeadCoup1 = pyo.Constraint(
        model.Pumps, model.T,
        rule=lambda m, p, t: -_M * (1 - m.Status[p, t]) <= m.H[link_map[p][1], t] - m.H[link_map[p][0], t] - m.PumpHeadGain[p, t]
    )
    model.PumpHeadCoup2 = pyo.Constraint(
        model.Pumps, model.T,
        rule=lambda m, p, t: m.H[link_map[p][1], t] - m.H[link_map[p][0], t] - m.PumpHeadGain[p, t] <= _M * (1 - m.Status[p, t])
    )

    # MILPNet Valve Logic (PRV 3-state and generic valves)
    # ----------------------------------------------------
    model.ValveV1 = pyo.Var(model.Valves, model.T, domain=pyo.Binary) # Active (PRV only)
    model.ValveV2 = pyo.Var(model.Valves, model.T, domain=pyo.Binary) # Open
    model.ValveV3 = pyo.Var(model.Valves, model.T, domain=pyo.Binary) # Closed

    model.ValveState = pyo.Constraint(
        model.Valves, model.T,
        rule=lambda m, v, t: m.ValveV1[v, t] + m.ValveV2[v, t] + m.ValveV3[v, t] == 1
    )

    _M_valve = 1000.0
    _eps_flow = 1e-4
    _eps_head = 1e-3

    valve_settings = {}
    is_prv = {}
    for v in valves:
        valve_obj = wn.get_link(v)
        is_prv[v] = valve_obj.valve_type == 'PRV'
        if is_prv[v]:
            end_node = wn.get_node(valve_obj.end_node_name)
            valve_settings[v] = end_node.elevation + valve_obj.setting
        else:
            valve_settings[v] = 0.0

    model.ValveFlowLower = pyo.Constraint(
        model.Valves, model.T,
        rule=lambda m, v, t: m.Q[v, t] >= _eps_flow * (1 - m.ValveV3[v, t])
    )
    model.ValveFlowUpper = pyo.Constraint(
        model.Valves, model.T,
        rule=lambda m, v, t: m.Q[v, t] <= _MAX_FLOW * (1 - m.ValveV3[v, t])
    )

    model.ValveConstraints = pyo.ConstraintList()
    for v in valves:
        for t in model.T:
            start_n = link_map[v][0]
            end_n = link_map[v][1]
            
            if is_prv[v]:
                H_set = valve_settings[v]
                # V1=1 (Active): H_end == H_set, H_start >= H_set
                model.ValveConstraints.add(model.H[end_n, t] - H_set <= _M_valve * (1 - model.ValveV1[v, t]))
                model.ValveConstraints.add(H_set - model.H[end_n, t] <= _M_valve * (1 - model.ValveV1[v, t]))
                model.ValveConstraints.add(model.H[start_n, t] >= H_set - _M_valve * (1 - model.ValveV1[v, t]))
                
                # V2=1 (Open): H_start == H_end, H_start <= H_set
                model.ValveConstraints.add(model.H[start_n, t] - model.H[end_n, t] <= _M_valve * (1 - model.ValveV2[v, t]))
                model.ValveConstraints.add(model.H[end_n, t] - model.H[start_n, t] <= _M_valve * (1 - model.ValveV2[v, t]))
                model.ValveConstraints.add(model.H[start_n, t] <= H_set + _M_valve * (1 - model.ValveV2[v, t]))
                
                # V3=1 (Closed): H_start <= H_end (check valve logic)
                model.ValveConstraints.add(model.H[start_n, t] - model.H[end_n, t] + _eps_head * model.ValveV3[v, t] <= _M_valve * (1 - model.ValveV3[v, t]))
            else:
                # Generic Valve: V1 is not used.
                model.ValveConstraints.add(model.ValveV1[v, t] == 0)
                # V2=1 (Open): H_start == H_end
                model.ValveConstraints.add(model.H[start_n, t] - model.H[end_n, t] <= _M_valve * (1 - model.ValveV2[v, t]))
                model.ValveConstraints.add(model.H[end_n, t] - model.H[start_n, t] <= _M_valve * (1 - model.ValveV2[v, t]))

    # Cost expression
    model.water_cost = pyo.Expression(rule=lambda m: (
        sum(m.Q[p, t] * 10.0 for p in m.Pumps for t in m.T)
        + sum(1e9 * (m.SlackPos[n, t] + m.SlackNeg[n, t]) for n in m.Junctions for t in m.T)
    ))

    logger.info(f"Water sub-model: {len(nodes)} nodes, {len(links)} links, {len(pumps)} pumps")


# ---------------------------------------------------------------------------
# Energy sub-model  (E1–E13)
# ---------------------------------------------------------------------------

def _add_energy_submodel(model: pyo.ConcreteModel, data: dict) -> None:
    """Add energy-hub and grid variables, parameters, and constraints to model.

    Implements E1–E13 from theoretical_background.md.
    Registers model.energy_cost (Expression) for the shared objective.

    Args:
        model: Shared ConcreteModel with model.T already set.
        data:  Dict from preprocessing.build_network_data()['energy'].
    """
    logger.info("Building energy sub-model (E1–E13)")

    buses      = data["buses"]
    lines      = data["lines"]        # list of (n, m, R, X, I_max)
    loads      = data["loads"]
    pv_profile = data.get("pv_profile", {b: [0.0] * len(list(model.T)) for b in buses})
    stor       = data["storage"]
    tariff     = data["tariff"]

    U0    = data["network"].get("nominal_voltage_pu", 1.0)
    n_seg = data["network"].get("n_current_segments", 5)
    v_tol = data["network"].get("voltage_tolerance", 0.10)

    line_names  = [f"{n}_{m}" for n, m, *_ in lines]
    line_params = {f"{n}_{m}": (R, X, I_max) for n, m, R, X, I_max in lines}

    # Sets
    model.Buses  = pyo.Set(initialize=buses)
    model.ELines = pyo.Set(initialize=line_names)
    model.ESegs  = pyo.RangeSet(0, n_seg)

    # Variables
    model.P_pv    = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.P_import = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.P_export = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.y_import = pyo.Var(model.Buses, model.T, domain=pyo.Binary)
    model.y_export = pyo.Var(model.Buses, model.T, domain=pyo.Binary)
    model.Q_ch  = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.Q_dis = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.y_ch  = pyo.Var(model.Buses, model.T, domain=pyo.Binary)
    model.y_dis = pyo.Var(model.Buses, model.T, domain=pyo.Binary)
    model.E_soc = pyo.Var(model.Buses, model.T, domain=pyo.NonNegativeReals)
    model.P_line = pyo.Var(model.ELines, model.T, domain=pyo.Reals)
    model.Q_line = pyo.Var(model.ELines, model.T, domain=pyo.Reals)
    model.U      = pyo.Var(model.Buses, model.T, bounds=(1.0 - v_tol, 1.0 + v_tol))
    model.theta  = pyo.Var(model.Buses, model.T, domain=pyo.Reals)
    model.I_re   = pyo.Var(model.ELines, model.T, domain=pyo.Reals)
    model.I_im   = pyo.Var(model.ELines, model.T, domain=pyo.Reals)
    model.phi    = pyo.Var(model.ELines, model.T, domain=pyo.NonNegativeReals)
    model.chi    = pyo.Var(model.ELines, model.T, domain=pyo.NonNegativeReals)
    model.lam    = pyo.Var(model.ELines, model.ESegs, model.T, bounds=(0, 1))

    # Pre-compute per-line coefficients and PWL breakpoints
    line_coeffs = {}
    line_pwl    = {}
    for lname, (R, X, I_max) in line_params.items():
        G, B = calc_line_admittance(R, X)
        line_coeffs[lname] = linearized_ac_coefficients(G, B, U0)
        line_pwl[lname]    = create_pwl_current_segments(I_max, n_seg)

    eta_dis = stor["discharge_efficiency"]
    eta_ch  = stor["charge_efficiency"]
    T_list  = list(model.T)
    T_last  = max(T_list)

    def load_at(b, t):
        return loads.get(b, [0.0] * len(T_list))[t]

    # E1 — Electricity balance
    model.ElecBalance = pyo.Constraint(
        model.Buses, model.T,
        rule=lambda m, b, t: (
            m.P_import[b, t] + m.P_pv[b, t]
            + eta_dis * m.Q_dis[b, t] - eta_ch * m.Q_ch[b, t]
            - m.P_export[b, t]
            == load_at(b, t)
        )
    )

    # E3 — Storage SoC continuity
    def soc_rule(m, b, t):
        if t == 0:
            return m.E_soc[b, t] == stor["capacity_kwh"] * stor["initial_soc_frac"]
        return (m.E_soc[b, t]
                == m.E_soc[b, t - 1]
                + eta_ch * m.Q_ch[b, t - 1]
                - (1.0 / eta_dis) * m.Q_dis[b, t - 1])

    model.SoCContinuity = pyo.Constraint(model.Buses, model.T, rule=soc_rule)

    # E4 — Capacity bounds + exclusivity
    E_max     = stor["capacity_kwh"]
    P_ch_max  = stor["max_charge_kw"]
    P_dis_max = stor["max_discharge_kw"]
    M_grid    = max((max(v) for v in loads.values()), default=1e4) * 2

    model.SoCBounds      = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: (0, m.E_soc[b, t], E_max))
    model.ChargeBound    = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.Q_ch[b, t]  <= P_ch_max  * m.y_ch[b, t])
    model.DischargeBound = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.Q_dis[b, t] <= P_dis_max * m.y_dis[b, t])
    model.ChargeDischExcl = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.y_ch[b, t] + m.y_dis[b, t] <= 1)
    model.PVCap          = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.P_pv[b, t] <= pv_profile.get(b, [0.0] * len(T_list))[t])
    model.ImportBound    = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.P_import[b, t] <= M_grid * m.y_import[b, t])
    model.ExportBound    = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.P_export[b, t] <= M_grid * m.y_export[b, t])
    model.ImportExportExcl = pyo.Constraint(model.Buses, model.T, rule=lambda m, b, t: m.y_import[b, t] + m.y_export[b, t] <= 1)

    # E5 — End-of-horizon SoC closure
    model.SoCClosure = pyo.Constraint(
        model.Buses,
        rule=lambda m, b: m.E_soc[b, T_last] >= m.E_soc[b, T_list[0]]
    )

    # E6 — Linearized AC line flows
    def _nm(lname):
        n, mk = lname.split("_", 1)
        return n, mk

    model.PLineFlow = pyo.Constraint(
        model.ELines, model.T,
        rule=lambda m, l, t: m.P_line[l, t] == (
            line_coeffs[l]["P_dU"]     * (m.U[_nm(l)[0], t] - m.U[_nm(l)[1], t])
            + line_coeffs[l]["P_dtheta"] * (m.theta[_nm(l)[0], t] - m.theta[_nm(l)[1], t])
        )
    )
    model.QLineFlow = pyo.Constraint(
        model.ELines, model.T,
        rule=lambda m, l, t: m.Q_line[l, t] == (
            line_coeffs[l]["Q_dU"]     * (m.U[_nm(l)[0], t] - m.U[_nm(l)[1], t])
            + line_coeffs[l]["Q_dtheta"] * (m.theta[_nm(l)[0], t] - m.theta[_nm(l)[1], t])
        )
    )

    # E7 — Nodal active power balance
    def nodal_P_rule(m, b, t):
        inflow  = sum(m.P_line[l, t] for l in m.ELines if _nm(l)[1] == b)
        outflow = sum(m.P_line[l, t] for l in m.ELines if _nm(l)[0] == b)
        return inflow - outflow == m.P_import[b, t] - m.P_export[b, t] + m.P_pv[b, t] - load_at(b, t)

    model.NodalPBalance = pyo.Constraint(model.Buses, model.T, rule=nodal_P_rule)

    # E9 — Voltage reference bus
    if buses:
        ref = buses[0]
        model.RefAngle   = pyo.Constraint(model.T, rule=lambda m, t: m.theta[ref, t] == 0.0)
        model.RefVoltage = pyo.Constraint(model.T, rule=lambda m, t: m.U[ref, t] == U0)

    # E10 — Current decomposition
    def _G(l): return line_coeffs[l]["P_dU"] / U0
    def _B(l): return -line_coeffs[l]["Q_dU"] / U0

    model.IReRule = pyo.Constraint(
        model.ELines, model.T,
        rule=lambda m, l, t: m.I_re[l, t] == (
            _G(l) * (m.U[_nm(l)[0], t]     - m.U[_nm(l)[1], t])
            - _B(l) * (m.theta[_nm(l)[0], t] - m.theta[_nm(l)[1], t])
        )
    )
    model.IImRule = pyo.Constraint(
        model.ELines, model.T,
        rule=lambda m, l, t: m.I_im[l, t] == (
            _G(l) * (m.theta[_nm(l)[0], t] - m.theta[_nm(l)[1], t])
            + _B(l) * (m.U[_nm(l)[0], t]     - m.U[_nm(l)[1], t])
        )
    )

    # E11 — |I_re| and |I_im| absolute value linearization
    model.PhiPos = pyo.Constraint(model.ELines, model.T, rule=lambda m, l, t: m.phi[l, t] >= m.I_re[l, t])
    model.PhiNeg = pyo.Constraint(model.ELines, model.T, rule=lambda m, l, t: m.phi[l, t] >= -m.I_re[l, t])
    model.ChiPos = pyo.Constraint(model.ELines, model.T, rule=lambda m, l, t: m.chi[l, t] >= m.I_im[l, t])
    model.ChiNeg = pyo.Constraint(model.ELines, model.T, rule=lambda m, l, t: m.chi[l, t] >= -m.I_im[l, t])

    # E12–E13 — PWL current magnitude + thermal limit
    for lname in line_names:
        _, _, I_max = line_params[lname]
        pts = line_pwl[lname]
        for t in model.T:
            phi_sq_var = pyo.Var(domain=pyo.NonNegativeReals)
            model.add_component(f"phi_sq_{lname}_{t}", phi_sq_var)
            add_pwl_constraint(model, f"pwl_phi_{lname}_{t}", model.phi[lname, t], phi_sq_var, pts)
            model.add_component(
                f"thermal_{lname}_{t}",
                pyo.Constraint(expr=phi_sq_var + model.chi[lname, t] ** 2 <= I_max ** 2)
            )

    # Cost expression
    model.energy_cost = pyo.Expression(
        rule=lambda m: sum(tariff[t] * m.P_import[b, t] for b in m.Buses for t in m.T)
    )

    logger.info(f"Energy sub-model: {len(buses)} buses, {len(lines)} lines")


# ---------------------------------------------------------------------------
# Nexus coupling  (placeholder)
# ---------------------------------------------------------------------------

def _add_nexus_constraints(model: pyo.ConcreteModel, data: dict) -> None:
    """Add water-energy coupling constraints (not yet implemented).

    Coupling replaces the exogenous pump cost c_k^t with the actual pump
    electrical load, which enters the energy electricity balance (E1).
    See doc/capsules/models/nexus_coupling.md.
    """
    logger.warning("Nexus coupling is not yet implemented — placeholder only.")
    raise NotImplementedError(
        "Nexus coupling is planned for a future milestone. "
        "Set run_nexus: false in config.yaml to run water and energy independently."
    )


# ---------------------------------------------------------------------------
# Shared objective
# ---------------------------------------------------------------------------

def _build_objective(model: pyo.ConcreteModel) -> None:
    """Sum all registered sub-model cost expressions into one objective."""
    cost_terms = []
    if hasattr(model, "water_cost"):
        cost_terms.append(model.water_cost)
    if hasattr(model, "energy_cost"):
        cost_terms.append(model.energy_cost)

    if not cost_terms:
        logger.warning("No cost expressions found — using zero objective.")
        model.objective = pyo.Objective(expr=0, sense=pyo.minimize)
        return

    model.objective = pyo.Objective(expr=sum(cost_terms), sense=pyo.minimize)
