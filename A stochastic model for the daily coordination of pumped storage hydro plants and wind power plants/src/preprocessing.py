"""
Preprocessing Module for EcoNex Optimization.

Data loading, synthetic profile generation, and network topology construction.
"""

import logging
import yaml
import numpy as np
from pathlib import Path

# Module logger
logger = logging.getLogger("econex.preprocessing")


def load_config(config_path: str) -> dict:
    """
    Load YAML configuration file containing all model parameters.
    
    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    
    Returns
    -------
    dict
        Configuration dictionary with sets, parameters, and solver settings.
    """
    logger.info(f"Loading configuration from: {config_path}")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    logger.debug(f"Configuration loaded with {len(config)} top-level keys")
    return config


def generate_solar_profile(T: int, peak_hour: int = 12, max_generation: float = 5.0) -> dict:
    """
    Generate synthetic solar generation profile (bell curve centered at noon).
    
    Parameters
    ----------
    T : int
        Number of time steps (hours).
    peak_hour : int
        Hour of maximum solar generation.
    max_generation : float
        Maximum generation in kW.
    
    Returns
    -------
    dict
        Dictionary {t: generation_kW} for each hour (1-indexed).
    """
    logger.debug(f"Generating solar profile: T={T}, peak_hour={peak_hour}, max={max_generation}kW")
    profile = {}
    for t in range(1, T + 1):
        hour = t - 1
        if 6 <= hour <= 18:
            generation = max_generation * np.exp(-0.5 * ((hour - peak_hour) / 3) ** 2)
        else:
            generation = 0.0
        profile[t] = round(generation, 3)
    
    total_gen = sum(profile.values())
    logger.debug(f"Solar profile generated: total daily generation = {total_gen:.2f} kWh")
    return profile


def generate_demand_profiles(T: int, nodes: list) -> dict:
    """
    Generate water and energy demand profiles with morning/evening peaks.
    
    Parameters
    ----------
    T : int
        Number of time steps.
    nodes : list
        List of node identifiers.
    
    Returns
    -------
    dict
        Nested dictionary {node: {layer: {t: demand}}}.
        Negative values indicate consumption (demand).
    """
    logger.debug(f"Generating demand profiles for {len(nodes)} nodes over {T} hours")
    demands = {}
    
    for node in nodes:
        demands[node] = {'E': {}, 'P': {}, 'W': {}}
        
        for t in range(1, T + 1):
            hour = t - 1
            
            base_energy = 1.0
            if 7 <= hour <= 9 or 18 <= hour <= 22:
                energy_demand = base_energy * 2.0
            else:
                energy_demand = base_energy
            
            base_water = 0.5
            if 6 <= hour <= 8 or 18 <= hour <= 21:
                potable_demand = base_water * 3.0
            else:
                potable_demand = base_water * 0.5
            
            if node == 1:
                energy_demand *= 0.8
            elif node == 2:
                potable_demand *= 2.0
            elif node == 3:
                energy_demand *= 0.3
                potable_demand *= 0.2
            
            demands[node]['E'][t] = -round(energy_demand, 3)
            demands[node]['P'][t] = -round(potable_demand, 3)
            demands[node]['W'][t] = 0.0
    
    # Log summary
    for node in nodes:
        total_e = sum(demands[node]['E'].values())
        total_p = sum(demands[node]['P'].values())
        logger.debug(f"Node {node} demand: Energy={total_e:.2f}kWh, Potable={total_p:.2f}m³")
    
    return demands


def generate_supply_profiles(T: int) -> dict:
    """
    Generate external supply profiles (solar, rainwater).
    
    Returns
    -------
    dict
        Nested dictionary {node: {layer: {t: supply}}}.
        Positive values indicate supply/generation.
    """
    logger.debug(f"Generating supply profiles for {T} hours")
    supplies = {1: {'E': {}, 'P': {}, 'W': {}},
                2: {'E': {}, 'P': {}, 'W': {}},
                3: {'E': {}, 'P': {}, 'W': {}}}
    
    solar_profile = generate_solar_profile(T)
    for t in range(1, T + 1):
        supplies[1]['E'][t] = solar_profile[t]
        supplies[1]['P'][t] = 0.0
        supplies[1]['W'][t] = 0.0
    
    for t in range(1, T + 1):
        supplies[2]['E'][t] = 0.0
        supplies[2]['P'][t] = 0.0
        if 3 <= (t - 1) <= 6:
            supplies[2]['W'][t] = 2.0
        else:
            supplies[2]['W'][t] = 0.0
    
    for t in range(1, T + 1):
        supplies[3]['E'][t] = 0.0
        supplies[3]['P'][t] = 0.0
        supplies[3]['W'][t] = 0.0
    
    total_rain = sum(supplies[2]['W'].values())
    logger.debug(f"Supply profiles generated: rainwater capture = {total_rain:.2f} m³")
    return supplies


def generate_price_profile(T: int, peak_start: int = 16, peak_end: int = 21,
                           off_peak_price: float = 0.08, peak_price: float = 0.25) -> dict:
    """
    Generate Time-of-Use electricity pricing with peak/off-peak rates.
    
    Parameters
    ----------
    T : int
        Number of time steps.
    peak_start, peak_end : int
        Peak pricing window (hours, 0-indexed).
    off_peak_price : float
        Off-peak price per kWh.
    peak_price : float
        Peak price per kWh.
    
    Returns
    -------
    dict
        Dictionary {t: price_per_kWh}.
    """
    logger.debug(f"Generating price profile: peak={peak_start}-{peak_end}h, "
                 f"off-peak=${off_peak_price}, peak=${peak_price}")
    prices = {}
    for t in range(1, T + 1):
        hour = t - 1
        if peak_start <= hour < peak_end:
            prices[t] = peak_price
        else:
            prices[t] = off_peak_price
    return prices


def build_network_data(config: dict) -> dict:
    """
    Construct complete network data structure for Pyomo model.
    
    Parameters
    ----------
    config : dict
        Configuration dictionary from load_config().
    
    Returns
    -------
    dict
        Network data containing nodes, arcs, layers, capacities, costs, demands.
    """
    logger.info("Building network data structure")
    
    T = config.get('T', 24)
    nodes = config.get('nodes', [1, 2, 3])
    layers = config.get('layers', ['E', 'P', 'W'])
    
    logger.debug(f"Network topology: {len(nodes)} nodes, {len(layers)} layers, {T} time steps")
    
    arcs = []
    for i in nodes:
        for j in nodes:
            if i != j:
                arcs.append((i, j))
    
    arcs.append(('grid', 3))
    arcs.append((3, 'grid'))
    arcs.append(('municipal', 3))
    
    logger.debug(f"Created {len(arcs)} arcs (including external connections)")
    
    coupling = config.get('coupling', {})
    eta = coupling.get('treatment_efficiency', 0.95)
    k = coupling.get('pumping_intensity', 0.5)
    logger.debug(f"Coupling parameters: η={eta}, k={k} kWh/m³")
    
    storage_capacities = config.get('storage', {})
    default_storage = {'E': 10.0, 'P': 5.0, 'W': 10.0}
    
    storage = {}
    for node in nodes:
        storage[node] = storage_capacities.get(node, default_storage.copy())
    
    arc_capacity = config.get('arc_capacity', {})
    default_arc_cap = {'E': 10.0, 'P': 2.0, 'W': 2.0}
    
    capacities = {}
    for arc in arcs:
        capacities[arc] = arc_capacity.get(arc, default_arc_cap.copy())
    
    demands = generate_demand_profiles(T, nodes)
    supplies = generate_supply_profiles(T)
    prices = generate_price_profile(T)
    
    net_demand = {}
    for node in nodes:
        net_demand[node] = {}
        for layer in layers:
            net_demand[node][layer] = {}
            for t in range(1, T + 1):
                d = demands[node][layer].get(t, 0.0)
                s = supplies[node][layer].get(t, 0.0)
                net_demand[node][layer][t] = d + s
    
    costs = {
        'grid_import': prices,
        'grid_export': {t: -0.05 for t in range(1, T + 1)},
        'municipal': {t: 2.0 for t in range(1, T + 1)},
        'treatment': {t: 0.1 for t in range(1, T + 1)},
        'transfer': 0.01,
    }
    
    logger.info(f"Network data built: {len(nodes)} nodes, {len(arcs)} arcs, {T} time steps")
    
    return {
        'T': list(range(1, T + 1)),
        'nodes': nodes,
        'layers': layers,
        'arcs': arcs,
        'storage_capacity': storage,
        'arc_capacity': capacities,
        'net_demand': net_demand,
        'costs': costs,
        'coupling': {'eta': eta, 'k': k},
        'config': config
    }
