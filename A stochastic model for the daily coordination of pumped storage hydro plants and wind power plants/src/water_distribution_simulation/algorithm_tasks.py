"""Simulation Module for Water Distribution Simulation.

WNTR-based hydraulic simulation execution.
"""

import logging
from typing import Optional

import wntr

# Module logger
logger = logging.getLogger("wds.simulation")


def run_simulation(wn: wntr.network.WaterNetworkModel,
                   simulator_type: str = 'wntr') -> wntr.sim.results.SimulationResults:
    """Execute the hydraulic simulation.

    Args:
        wn: The configured water network model.
        simulator_type: Simulator to use: 'wntr' (pure Python) or 'epanet' (EPANET toolkit).

    Returns:
        Simulation results containing node and link data.
    """
    logger.info(f"Running simulation with {simulator_type.upper()} simulator")
    logger.debug(f"Network: {wn.num_nodes} nodes, {wn.num_links} links")
    logger.debug(f"Duration: {wn.options.time.duration / 3600:.1f} hours")

    if simulator_type.lower() == 'epanet':
        sim = wntr.sim.EpanetSimulator(wn)
    else:
        sim = wntr.sim.WNTRSimulator(wn)

    try:
        results = sim.run_sim()
        logger.info("Simulation completed successfully")
        
        # Log summary statistics
        _log_simulation_summary(results, wn)
        
        return results

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise


def _log_simulation_summary(results: wntr.sim.results.SimulationResults,
                            wn: wntr.network.WaterNetworkModel) -> None:
    """Log summary statistics from simulation results.

    Args:
        results: The simulation results.
        wn: The water network model.
    """
    # Node results summary
    pressure = results.node['pressure']
    demand = results.node['demand']

    # Get junction pressures only
    junction_names = wn.junction_name_list
    if junction_names:
        junction_pressure = pressure[junction_names]
        min_pressure = junction_pressure.min().min()
        max_pressure = junction_pressure.max().max()
        mean_pressure = junction_pressure.mean().mean()
        
        logger.info(f"Junction pressures: min={min_pressure:.2f}m, "
                    f"max={max_pressure:.2f}m, mean={mean_pressure:.2f}m")

    # Link results summary
    flowrate = results.link['flowrate']
    velocity = results.link['velocity']

    pipe_names = wn.pipe_name_list
    if pipe_names:
        pipe_flow = flowrate[pipe_names]
        max_flow = pipe_flow.abs().max().max()
        logger.info(f"Max pipe flow: {max_flow:.4f} m³/s ({max_flow * 1000:.2f} L/s)")

    # Tank levels if present
    tank_names = wn.tank_name_list
    if tank_names:
        tank_pressure = pressure[tank_names]
        logger.debug(f"Tank level range: {tank_pressure.min().min():.2f}m - "
                     f"{tank_pressure.max().max():.2f}m")


def run_scenario_simulation(wn: wntr.network.WaterNetworkModel,
                            scenario: dict,
                            simulator_type: str = 'wntr') -> wntr.sim.results.SimulationResults:
    """Run simulation with a specific scenario modification.

    Args:
        wn: The water network model.
        scenario: Scenario specification (e.g., pipe break, increased demand).
        simulator_type: Simulator type to use.

    Returns:
        Simulation results for the scenario.
    """
    scenario_type = scenario.get('type', 'none')
    logger.info(f"Running scenario simulation: {scenario_type}")

    if scenario_type == 'pipe_break':
        # Simulate pipe closure
        pipe_name = scenario.get('pipe_name')
        start_time = scenario.get('start_time', 0)
        end_time = scenario.get('end_time', wn.options.time.duration)

        if pipe_name and pipe_name in wn.pipe_name_list:
            pipe = wn.get_link(pipe_name)
            
            # Add control to close pipe
            action_close = wntr.network.controls.ControlAction(pipe, 'status', 0)
            condition_close = wntr.network.controls.SimTimeCondition(wn, 'above', start_time)
            control_close = wntr.network.controls.Control(condition_close, action_close)
            wn.add_control('pipe_break_close', control_close)

            if end_time < wn.options.time.duration:
                action_open = wntr.network.controls.ControlAction(pipe, 'status', 1)
                condition_open = wntr.network.controls.SimTimeCondition(wn, 'above', end_time)
                control_open = wntr.network.controls.Control(condition_open, action_open)
                wn.add_control('pipe_break_open', control_open)

            logger.debug(f"Pipe {pipe_name} break: {start_time/3600:.1f}h - {end_time/3600:.1f}h")

    elif scenario_type == 'demand_surge':
        # Increase demand at specific node
        node_name = scenario.get('node_name')
        multiplier = scenario.get('multiplier', 2.0)

        if node_name and node_name in wn.junction_name_list:
            junction = wn.get_node(node_name)
            for demand in junction.demand_timeseries_list:
                demand.base_value *= multiplier
            logger.debug(f"Demand at {node_name} multiplied by {multiplier}")

    elif scenario_type == 'pump_failure':
        # Simulate pump outage
        pump_name = scenario.get('pump_name')
        if pump_name is None and wn.pump_name_list:
            pump_name = wn.pump_name_list[0]

        if pump_name and pump_name in wn.pump_name_list:
            pump = wn.get_link(pump_name)
            pump.initial_status = 0
            logger.debug(f"Pump {pump_name} set to failed state")

    return run_simulation(wn, simulator_type)


def run_multiple_simulations(wn: wntr.network.WaterNetworkModel,
                              scenarios: list,
                              simulator_type: str = 'wntr') -> dict:
    """Run multiple scenario simulations.

    Args:
        wn: The base water network model.
        scenarios: List of scenario dictionaries.
        simulator_type: Simulator type to use.

    Returns:
        Dictionary mapping scenario names to results.
    """
    logger.info(f"Running {len(scenarios)} scenario simulations")
    results_dict = {}

    # Run baseline first
    baseline_wn = wn.copy()
    results_dict['baseline'] = run_simulation(baseline_wn, simulator_type)

    # Run each scenario
    for i, scenario in enumerate(scenarios):
        scenario_name = scenario.get('name', f'scenario_{i+1}')
        logger.info(f"Running scenario: {scenario_name}")

        scenario_wn = wn.copy()
        try:
            results_dict[scenario_name] = run_scenario_simulation(
                scenario_wn, scenario, simulator_type
            )
        except Exception as e:
            logger.error(f"Scenario {scenario_name} failed: {e}")
            results_dict[scenario_name] = None

    return results_dict
