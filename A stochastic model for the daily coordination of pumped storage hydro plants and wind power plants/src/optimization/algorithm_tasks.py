"""Optimization Module for EcoNex.

Pyomo model construction for Hydraulic Network Optimization using EPANET inputs.
"""

import logging
import wntr
import networkx as nx
import numpy as np
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

# Module logger
logger = logging.getLogger("econex.optimization")

from src.optimization.helpers.hydraulic_utils import (
    calc_K,
    create_piecewise_pipe_curve,
    create_piecewise_pump_curve
)



# --------------------------------------------------------------------------------
# Main Model Builder
# --------------------------------------------------------------------------------

def build_model(data: dict) -> pyo.ConcreteModel:
    """Construct the Pyomo ConcreteModel from EPANET .inp file.
    
    Args:
        data : Dictionary containing 'inp_file' path and config.
    
    Returns:
        Pyomo ConcreteModel ready for solving.
    """
    inp_file = data['inp_file']
    logger.info(f"Loading network from {inp_file}")
    
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    logger.info("Building Pyomo optimization model")
    model = pyo.ConcreteModel(name="Hydraulic_Optimization")
    
    # Time parameters
    duration = wn.options.time.duration
    timestep = wn.options.time.hydraulic_timestep
    report_timestep = wn.options.time.report_timestep
    
    # Use config T if specified, otherwise derived from duration
    # User's code used T as number of steps
    num_steps_config = data['config'].get('T', 24)
    # Ensure reasonable relationship between steps and duration
    # If duration is 24h, T=24 implies 1h steps.
    
    model.T = pyo.RangeSet(0, num_steps_config - 1, doc="Time steps")
    dt = 3600 # 1 hour in seconds
    model.dt = pyo.Param(initialize=dt)
    
    # Lists of components
    junctions = wn.junction_name_list
    tanks = wn.tank_name_list
    reservoirs = wn.reservoir_name_list
    nodes = wn.node_name_list
    
    pipes = wn.pipe_name_list
    pumps = wn.pump_name_list
    valves = wn.valve_name_list
    links = wn.link_name_list
    
    model.Junctions = pyo.Set(initialize=junctions)
    model.Tanks = pyo.Set(initialize=tanks)
    model.Reservoirs = pyo.Set(initialize=reservoirs)
    model.Nodes = pyo.Set(initialize=nodes)
    
    model.Pipes = pyo.Set(initialize=pipes)
    model.Pumps = pyo.Set(initialize=pumps)
    model.Valves = pyo.Set(initialize=valves)
    model.Links = pyo.Set(initialize=links)
    
    # Mappings
    link_map = {} # link -> (start_node, end_node)
    for link_name, link in wn.links():
        link_map[link_name] = (link.start_node_name, link.end_node_name)
    
    # Parameters
    # Elevations
    node_elevations = {n: wn.get_node(n).elevation for n in nodes if hasattr(wn.get_node(n), 'elevation')}
    # Reservoirs might calculate head differently (elevation + pattern)
    # For now assume constant head for reservoirs unless pattern exists
    
    # Tank Geometry
    tank_areas = {}
    for t in tanks:
        tank = wn.get_node(t)
        # simplistic cylinder area
        tank_areas[t] = (np.pi * (tank.diameter / 2)**2)
        
    model.TankArea = pyo.Param(model.Tanks, initialize=tank_areas)
    
    # Initial Levels
    initial_levels = {}
    min_levels = {}
    max_levels = {}
    for t in tanks:
        tank = wn.get_node(t)
        initial_levels[t] = tank.level + tank.elevation # Head
        min_levels[t] = tank.min_level + tank.elevation
        max_levels[t] = tank.max_level + tank.elevation
        
    # Demands (assuming constant for now, should read patterns)
    # Using a placeholder demand multiplier if patterns exist
    base_demands = {}
    for j in junctions:
        node = wn.get_node(j)
        base_demands[j] = node.demand_timeseries_list[0].base_value if node.demand_timeseries_list else 0.0

    # --------------------------------------------------------------------------
    # VARIABLES
    # --------------------------------------------------------------------------
    
    # Flow (Q) - defined for all links
    # To handle negative flow in pipes, bounds need to be loose
    max_flow_guess = 5.0 # m3/s, huge bound
    
    def q_bounds(m, l, t):
        if l in m.Pipes:
            return (-max_flow_guess, max_flow_guess)
        elif l in m.Pumps:
            return (0, max_flow_guess)
        elif l in m.Valves:
            return (0, max_flow_guess) # usually unidirectional
        return (-max_flow_guess, max_flow_guess)

    model.Q = pyo.Var(model.Links, model.T, bounds=q_bounds, domain=pyo.Reals, doc="Flow rate")

    # Head (H) - defined for all nodes
    max_head_guess = 500.0 # m
    model.H = pyo.Var(model.Nodes, model.T, bounds=(0, max_head_guess), domain=pyo.NonNegativeReals)
    
    # Status (Pumps/Valves) - Binary
    model.Status = pyo.Var(model.Pumps | model.Valves, model.T, domain=pyo.Binary)
    
    # Slack variables for Mass Balance (Infeasibility diagnosis)
    model.SlackPos = pyo.Var(model.Junctions, model.T, domain=pyo.NonNegativeReals)
    model.SlackNeg = pyo.Var(model.Junctions, model.T, domain=pyo.NonNegativeReals)

    # --------------------------------------------------------------------------
    # CONSTRAINTS
    # --------------------------------------------------------------------------
    
    # 1. Mass Balance at Junctions
    # Sum(Q_in) - Sum(Q_out) = Demand
    def mass_balance_rule(m, n, t):
        if n not in m.Junctions:
            return pyo.Constraint.Skip
        
        inflow = sum(m.Q[l, t] for l in m.Links if link_map[l][1] == n) 
        outflow = sum(m.Q[l, t] for l in m.Links if link_map[l][0] == n)
        
        # Apply demand pattern here if needed, defaulting to base for now
        demand = base_demands.get(n, 0.0)
        
        return inflow - outflow + m.SlackPos[n,t] - m.SlackNeg[n,t] == demand

    model.MassBalance = pyo.Constraint(model.Junctions, model.T, rule=mass_balance_rule)

    # 2. Tank Dynamics
    # H_t = H_{t-1} + (dt/Area) * (Sum(Q_in) - Sum(Q_out))
    def tank_dynamics_rule(m, n, t):
        if t == 0:
            return m.H[n, t] == initial_levels[n]
        
        prev_head = m.H[n, t-1]
        
        inflow = sum(m.Q[l, t-1] for l in m.Links if link_map[l][1] == n)
        outflow = sum(m.Q[l, t-1] for l in m.Links if link_map[l][0] == n)
        
        net_flow = inflow - outflow
        
        return m.H[n, t] == prev_head + (m.dt / m.TankArea[n]) * net_flow

    model.TankDynamics = pyo.Constraint(model.Tanks, model.T, rule=tank_dynamics_rule)
    
    # 3. Tank Bounds
    def tank_bounds_rule(m, n, t):
        return (min_levels[n], m.H[n, t], max_levels[n])
    model.TankLimits = pyo.Constraint(model.Tanks, model.T, rule=tank_bounds_rule)

    # 4. Reservoir Heads (Fixed)
    def res_head_rule(m, n, t):
        res = wn.get_node(n)
        return m.H[n, t] == res.base_head # Assuming constant
    model.ResHead = pyo.Constraint(model.Reservoirs, model.T, rule=res_head_rule)

    # 5. Pipe Head Loss (Hazen-Williams) - Piecewise Linearization
    # h_start - h_end = sign(Q)*K*|Q|^1.852
    
    # Pre-calculate K for all pipes
    pipe_Ks = {}
    for p_name in pipes:
        p = wn.get_link(p_name)
        pipe_Ks[p_name] = calc_K(p.length, p.diameter, p.roughness)

        
    # Helper for manual PWL with Explicit Binary SOS2
    def add_pwl_constraint(m, name, x_var, y_var, points):
        indices = range(len(points)) # 0..N
        segments = range(len(points) - 1) # 0..N-1
        
        x_pts = [p[0] for p in points]
        y_pts = [p[1] for p in points]
        
        # Weights variable (Continuous 0-1)
        w = pyo.Var(indices, bounds=(0, 1))
        m.add_component(f"{name}_w", w)
        
        # Binary variables for segments
        z = pyo.Var(segments, domain=pyo.Binary)
        m.add_component(f"{name}_z", z)
        
        # Convexity: sum(w) == 1
        m.add_component(f"{name}_convex", pyo.Constraint(expr=sum(w[k] for k in indices) == 1))
        
        # One segment active: sum(z) == 1
        m.add_component(f"{name}_z_sum", pyo.Constraint(expr=sum(z[k] for k in segments) == 1))
        
        # SOS2 Logic constraints
        # w[0] <= z[0]
        m.add_component(f"{name}_sos_start", pyo.Constraint(expr=w[0] <= z[0]))
        
        # w[k] <= z[k-1] + z[k]
        for k in range(1, len(points) - 1):
            m.add_component(f"{name}_sos_{k}", pyo.Constraint(expr=w[k] <= z[k-1] + z[k]))
            
        # w[N] <= z[N-1]
        m.add_component(f"{name}_sos_end", pyo.Constraint(expr=w[indices[-1]] <= z[segments[-1]]))
        
        # X interpolation
        m.add_component(f"{name}_x_interp", pyo.Constraint(expr=x_var == sum(w[k]*x_pts[k] for k in indices)))
        
        # Y interpolation
        m.add_component(f"{name}_y_interp", pyo.Constraint(expr=y_var == sum(w[k]*y_pts[k] for k in indices)))


    model.dH = pyo.Var(model.Pipes, model.T, domain=pyo.Reals)
    
    def dh_def_rule(m, p, t):
        n1, n2 = link_map[p]
        return m.dH[p, t] == m.H[n1, t] - m.H[n2, t]
    model.dH_def = pyo.Constraint(model.Pipes, model.T, rule=dh_def_rule)
    
    for p in pipes:
        pts = create_piecewise_pipe_curve(pipe_Ks[p], 2.0, num_segments=2) 
        for t in model.T:
            add_pwl_constraint(model, f"pwl_pipe_{p}_{t}", model.Q[p, t], model.dH[p, t], pts)

    # 6. Pump Head Gain
    model.PumpHeadGain = pyo.Var(model.Pumps, model.T, domain=pyo.NonNegativeReals)
    
    for p in pumps:
        pump_obj = wn.get_link(p)
        pts = create_piecewise_pump_curve(pump_obj, num_segments=2)
        for t in model.T:
            add_pwl_constraint(model, f"pwl_pump_{p}_{t}", model.Q[p, t], model.PumpHeadGain[p, t], pts)
        
    # Pump coupling constraints
    def pump_flow_status_rule(m, p, t):
        return m.Q[p, t] <= max_flow_guess * m.Status[p, t]
    model.PumpStatusFlow = pyo.Constraint(model.Pumps, model.T, rule=pump_flow_status_rule)
    
    # Head relation only holds if ON.
    # If OFF, H_end - H_start <= 0 (check valve? or just decoupled?)
    # usually simple decoupling:
    # -M(1-y) <= (H_end - H_start) - Gain <= M(1-y)  <-- Enforces gain match if y=1
    def pump_head_coupling_rule(m, p, t):
        n1, n2 = link_map[p]
        M = 200
        gain = m.PumpHeadGain[p, t] 
        diff = m.H[n2, t] - m.H[n1, t]
        return -M*(1-m.Status[p,t]) <= diff - gain
    model.PumpHeadCoup1 = pyo.Constraint(model.Pumps, model.T, rule=pump_head_coupling_rule)
    
    def pump_head_coupling_rule2(m, p, t):
        n1, n2 = link_map[p]
        M = 200
        gain = m.PumpHeadGain[p, t]
        diff = m.H[n2, t] - m.H[n1, t]
        return diff - gain <= M*(1-m.Status[p,t])
    model.PumpHeadCoup2 = pyo.Constraint(model.Pumps, model.T, rule=pump_head_coupling_rule2)

    # --------------------------------------------------------------------------
    # OBJECTIVE
    # --------------------------------------------------------------------------
    # Minimize energy cost (Pump Energy)
    # Energy (kWh) = (Gamma * Q * H * dt) / (eta * 3600 * 1000) ??
    # Simplified: Power ~ Q * HeadGain
    # We want to minimize Cost * Power * dt
    
    def objective_rule(m):
        # Cost factor
        gamma_rho_g = 9810 # N/m3
        eta = 0.75 # efficiency guess
        
        total_cost = 0
        for t in m.T:
            energy_kwh_t = 0
            for p in m.Pumps:
                # Power P (kW) = (rho * g * Q * h) / (eta * 1000)
                # Q in m3/s, h in m
                # Simple approximation: maximize efficiency or minimize flow*head
                
                # Nonlinear term Q*H in objective! 
                # Pyomo with GLPK cannot handle Q*H directly unless linearized
                # Propose: Minimize Flow (proxy) or use constant head Approx
                
                energy_kwh_t += m.Q[p, t] * 10.0 # Dummy coefficient
                
            total_cost += energy_kwh_t # * Price[t]
            
            # Penalty for slack violation
            for n in m.Junctions:
                total_cost += 1e9 * (m.SlackPos[n, t] + m.SlackNeg[n, t])
            
        return total_cost

    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)
    
    logger.info("Model built successfully")
    return model


def solve_model(model: pyo.ConcreteModel, solver: str = 'glpk', tee: bool = True, logfile: str = None) -> tuple:
    """Solve the optimization model."""
    logger.info(f"Solving with {solver}")
    
    opt = SolverFactory(solver)
    if not opt.available():
        raise RuntimeError(f"Solver {solver} not found.")
    
    # Set time limit (in seconds for GLPK, check specific solver docs)
    if solver == 'glpk':
        opt.options['tmlim'] = 60 # set tmlim in seconds
        model.user_limit = 60
    
    results = opt.solve(model, tee=tee, logfile=logfile)
    return model, results
