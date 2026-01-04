"""
Optimization Module for EcoNex.

Pyomo model construction for Time-Expanded, Multi-Layer Network Flow optimization.
"""

import logging
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

# Module logger
logger = logging.getLogger("econex.optimization")


def build_model(data: dict) -> pyo.ConcreteModel:
    """
    Construct the Pyomo ConcreteModel from preprocessed data.
    
    Parameters
    ----------
    data : dict
        Network data dictionary from build_network_data().
    
    Returns
    -------
    pyo.ConcreteModel
        Pyomo ConcreteModel ready for solving.
    """
    logger.info("Building Pyomo optimization model")
    model = pyo.ConcreteModel(name="EcoNex_Network_Flow")
    
    # ==========================================================================
    # SETS
    # ==========================================================================
    logger.debug("Defining sets")
    model.T = pyo.Set(initialize=data['T'], doc="Time steps")
    model.N = pyo.Set(initialize=data['nodes'], doc="Physical nodes")
    model.L = pyo.Set(initialize=data['layers'], doc="Layers (E, P, W)")
    
    physical_arcs = [(i, j) for i, j in data['arcs'] 
                     if i in data['nodes'] and j in data['nodes']]
    model.A = pyo.Set(initialize=physical_arcs, doc="Physical arcs between nodes")
    
    logger.debug(f"Sets created: |T|={len(data['T'])}, |N|={len(data['nodes'])}, "
                 f"|L|={len(data['layers'])}, |A|={len(physical_arcs)}")
    
    # ==========================================================================
    # PARAMETERS
    # ==========================================================================
    logger.debug("Defining parameters")
    
    def net_demand_init(model, n, l, t):
        return data['net_demand'].get(n, {}).get(l, {}).get(t, 0.0)
    model.D = pyo.Param(model.N, model.L, model.T, initialize=net_demand_init,
                        doc="Net demand (negative) or supply (positive)")
    
    def storage_cap_init(model, n, l):
        return data['storage_capacity'].get(n, {}).get(l, 10.0)
    model.S_cap = pyo.Param(model.N, model.L, initialize=storage_cap_init,
                            doc="Storage capacity at each node")
    
    def arc_cap_init(model, i, j, l):
        return data['arc_capacity'].get((i, j), {}).get(l, 10.0)
    model.U = pyo.Param(model.A, model.L, initialize=arc_cap_init,
                        doc="Arc capacity")
    
    grid_prices = data['costs']['grid_import']
    model.C_grid = pyo.Param(model.T, initialize=lambda m, t: grid_prices.get(t, 0.1),
                             doc="Grid electricity price")
    model.C_municipal = pyo.Param(initialize=2.0, doc="Municipal water price per m³")
    model.C_transfer = pyo.Param(initialize=0.01, doc="P2P transfer cost")
    model.C_treatment = pyo.Param(initialize=0.1, doc="Water treatment cost per m³")
    
    model.eta = pyo.Param(initialize=data['coupling']['eta'],
                          doc="Treatment efficiency (W->P)")
    model.k = pyo.Param(initialize=data['coupling']['k'],
                        doc="Pumping energy intensity (kWh/m³)")
    
    # ==========================================================================
    # DECISION VARIABLES
    # ==========================================================================
    logger.debug("Defining decision variables")
    
    model.x = pyo.Var(model.A, model.L, model.T, within=pyo.NonNegativeReals,
                      doc="Flow on arcs")
    model.h = pyo.Var(model.N, model.L, model.T, within=pyo.NonNegativeReals,
                      doc="Storage holdover")
    model.grid_import = pyo.Var(model.T, within=pyo.NonNegativeReals,
                                doc="Energy imported from grid")
    model.grid_export = pyo.Var(model.T, within=pyo.NonNegativeReals,
                                doc="Energy exported to grid")
    model.municipal_import = pyo.Var(model.T, within=pyo.NonNegativeReals,
                                     doc="Potable water from municipal")
    model.treatment_in = pyo.Var(model.T, within=pyo.NonNegativeReals,
                                 doc="Waste water into treatment")
    model.treatment_out = pyo.Var(model.T, within=pyo.NonNegativeReals,
                                  doc="Potable water out of treatment")
    model.pump_energy = pyo.Var(model.N, model.T, within=pyo.NonNegativeReals,
                                doc="Energy consumed for pumping at each node")
    
    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================
    logger.debug("Defining constraints")
    
    def mass_balance_rule(model, n, l, t):
        inflow = sum(model.x[j, n, l, t] for (j, i) in model.A if i == n)
        outflow = sum(model.x[n, j, l, t] for (i, j) in model.A if i == n)
        
        if t == 1:
            storage_prev = 0
        else:
            storage_prev = model.h[n, l, t-1]
        storage_curr = model.h[n, l, t]
        
        net_d = model.D[n, l, t]
        
        external_in = 0
        external_out = 0
        
        if n == 3:
            if l == 'E':
                external_in = model.grid_import[t]
                external_out = model.grid_export[t]
            elif l == 'P':
                external_in = model.municipal_import[t] + model.treatment_out[t]
            elif l == 'W':
                external_out = model.treatment_in[t]
        
        pump_consumption = 0
        if l == 'E':
            pump_consumption = model.pump_energy[n, t]
        
        return (inflow + storage_prev + external_in + net_d ==
                outflow + storage_curr + external_out + pump_consumption)
    
    model.mass_balance = pyo.Constraint(model.N, model.L, model.T,
                                        rule=mass_balance_rule,
                                        doc="Mass balance at each node")
    
    def storage_capacity_rule(model, n, l, t):
        return model.h[n, l, t] <= model.S_cap[n, l]
    model.storage_limit = pyo.Constraint(model.N, model.L, model.T,
                                         rule=storage_capacity_rule,
                                         doc="Storage capacity limit")
    
    def arc_capacity_rule(model, i, j, l, t):
        return model.x[i, j, l, t] <= model.U[i, j, l]
    model.arc_limit = pyo.Constraint(model.A, model.L, model.T,
                                     rule=arc_capacity_rule,
                                     doc="Arc flow capacity limit")
    
    def treatment_coupling_rule(model, t):
        return model.treatment_out[t] == model.eta * model.treatment_in[t]
    model.treatment_coupling = pyo.Constraint(model.T,
                                              rule=treatment_coupling_rule,
                                              doc="Treatment efficiency coupling")
    
    def pumping_coupling_rule(model, n, t):
        water_outflow = sum(model.x[n, j, 'P', t] + model.x[n, j, 'W', t]
                            for (i, j) in model.A if i == n)
        return model.pump_energy[n, t] >= model.k * water_outflow
    model.pumping_coupling = pyo.Constraint(model.N, model.T,
                                            rule=pumping_coupling_rule,
                                            doc="Pumping energy requirement")
    
    model.treatment_capacity = pyo.Param(initialize=5.0, doc="Max treatment rate m³/h")
    def treatment_limit_rule(model, t):
        return model.treatment_in[t] <= model.treatment_capacity
    model.treatment_limit = pyo.Constraint(model.T, rule=treatment_limit_rule)
    
    # Count constraints
    num_constraints = sum(1 for _ in model.component_data_objects(pyo.Constraint, active=True))
    logger.debug(f"Total constraints created: {num_constraints}")
    
    # ==========================================================================
    # OBJECTIVE FUNCTION
    # ==========================================================================
    logger.debug("Defining objective function")
    
    def objective_rule(model):
        grid_cost = sum(model.C_grid[t] * model.grid_import[t] for t in model.T)
        grid_revenue = sum(0.05 * model.grid_export[t] for t in model.T)
        municipal_cost = sum(model.C_municipal * model.municipal_import[t] for t in model.T)
        treatment_cost = sum(model.C_treatment * model.treatment_in[t] for t in model.T)
        transfer_cost = sum(model.C_transfer * model.x[i, j, l, t]
                            for (i, j) in model.A
                            for l in model.L
                            for t in model.T)
        
        return grid_cost - grid_revenue + municipal_cost + treatment_cost + transfer_cost
    
    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize,
                                    doc="Minimize total operational cost")
    
    # Count variables
    num_vars = sum(1 for _ in model.component_data_objects(pyo.Var, active=True))
    logger.info(f"Model built: {num_vars} variables, {num_constraints} constraints")
    
    return model


def solve_model(model: pyo.ConcreteModel, solver: str = 'glpk',
                tee: bool = False) -> tuple:
    """
    Solve the optimization model.
    
    Parameters
    ----------
    model : pyo.ConcreteModel
        Pyomo ConcreteModel.
    solver : str
        Solver name (glpk, cbc, gurobi, cplex).
    tee : bool
        If True, print solver output.
    
    Returns
    -------
    tuple
        (model, results) where results is Pyomo SolverResults.
    """
    logger.info(f"Solving model with solver: {solver}")
    
    opt = SolverFactory(solver)
    if not opt.available():
        logger.error(f"Solver '{solver}' is not available")
        raise RuntimeError(f"Solver '{solver}' is not available. Please install it.")
    
    logger.debug("Starting optimization...")
    results = opt.solve(model, tee=tee)
    
    status = results.solver.termination_condition
    obj_value = pyo.value(model.objective)
    
    if status == pyo.TerminationCondition.optimal:
        logger.info(f"Optimal solution found: objective = ${obj_value:.2f}")
    elif status == pyo.TerminationCondition.infeasible:
        logger.error("Model is infeasible")
    elif status == pyo.TerminationCondition.unbounded:
        logger.error("Model is unbounded")
    else:
        logger.warning(f"Solver terminated with status: {status}")
    
    return model, results
