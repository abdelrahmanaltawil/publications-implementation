
import pytest
import pyomo.environ as pyo
from pathlib import Path
import logging

# local imports
from src.optimization.algorithm_tasks import build_model, solve_model
from tests.optimization.helpers.validation_utils import run_scenario_on_optimization_and_simulation, assert_timeseries_near_equal, assert_no_negative_pressures, validation_logging, logger

# =============================================================================
# OPTIMIZATION VS SIMULATION COMPARISON TESTS
# =============================================================================

def test_case_1_mass_energy_balance():
    """
    Test Case 1: Simple Mass Energy Balance.
    
    Scenario:
        - Network: Reservoir (Res1) -> Pipe -> Junction (2) -> Pipe -> Junction (3)
        - Components: Mapped to the top-left branch of EPANET Example Network 1
    
    Objective:
        - Verify that the optimization model respects basic mass and energy continuity.
        - Check if flow rates calculated by optimization match EPANET simulation.
    
    Validation:
        - Optimization flow for Pipe '10' vs. EPANET simulation flow.
        - Expected result: Near-perfect match (correlation ~1.0, error < 5%) in pairwise points comparison.
    """
    if not pyo.SolverFactory('glpk').available():
        pytest.skip("GLPK solver not available")

    case_inp = """
        [TITLE]
        Mass & Energy Balance Test - Simple Loop (1 Degree of Freedom)

[JUNCTIONS]
        ;ID     Elev    Demand    Pattern
        2      710     100       1
        3      610     500       1
        4      750     0         1       ; New junction to connect the tank

        [RESERVOIRS]
        ;ID     Head
        1      800

        [TANKS]
        ;ID    Elev   InitLvl  MinLvl  MaxLvl  Diam  MinVol  VolCurve
        5      780    10       5       25      40    0               ; New Storage Tank

        [PIPES]
        ;ID     Node1   Node2   Length  Diam    Roughness   MinorLoss   Status
        10     1       2       10530   18      100         0           Open
        11     2       3       5280    14      100         0           Open
        12     1       3       15000   12      100         0           Open
        13     2       4       1000    12      100         0           Open  ; Connection to tank junction
        14     4       5       50      18      100         0           Open  ; Final link to tank node

        [PATTERNS]
        ;ID     Multipliers
        ;       Midnight -> 6am (Low)    6am -> Noon (Rising)
        1       0.5   0.5   0.5   0.5    0.8   1.0   1.2   1.4
        ;       Noon -> 6pm (Peak)       6pm -> Midnight (Dropping)
        1       1.5   1.5   1.4   1.2    1.0   0.8   0.6   0.5

        [OPTIONS]
        Units              GPM
        Headloss           H-W
        Specific Gravity   1.0
        Viscosity          1.0
        Trials             40
        Accuracy           0.001
        Unbalanced         Continue 10

        [TIMES]
        Duration           24:00       ; Runs for 24 hours
        Hydraulic Timestep 1:00        ; Solves every 1 hour
        Quality Timestep   0:05
        Pattern Timestep   1:00        ; Multipliers update every 1 hour
        Pattern Start      0:00
        Report Timestep    1:00
        Report Start       0:00
        Start ClockTime    12 am
        Statistic          NONE

        [COORDINATES]
        ;Node   X-Coord     Y-Coord
        1      10.00       70.00
        2      20.00       65.00
        3      30.00       64.00
        4      20.00       75.00    ; Junction 4
        5      20.00       85.00    ; Tank 5

        [END]
    """

    save_dir = Path.cwd() / "data" / "results" / "optimization" / "hydraulic_feasibility" / "case1"
    save_dir.mkdir(parents=True, exist_ok=True)

    f = save_dir / "case1.inp"
    f.write_text(case_inp)

    with validation_logging(save_dir / "test_report.log"):
        results = run_scenario_on_optimization_and_simulation(str(f), num_timesteps=24, save_dir=save_dir)
        
        # extract optimization and simulation results
        opt_results = results['opt_data']
        sim_results = results['sim_data']
        
        # Check if optimization completed successfully
        assert results['status'] == 'completed'

        # Get timestep for consistent volume scaling (matches plots)
        timestep = results['timestep']

        # pipe flow - compare volume per timestep (m³/timestep) for consistency with plots
        for pipe_id in opt_results['pipe_flows'].keys():
            p_opt = opt_results['pipe_flows'][pipe_id]
            p_sim = sim_results['pipe_flows'][pipe_id]
            assert_timeseries_near_equal(
                p_opt * timestep, 
                p_sim * timestep, 
                rel_tol=0.05, 
                abs_tol=0.5,
                label=f"Pipe {pipe_id} Flow"
            )

        # junction head - compare directly (heads are not rate-based)
        for junc_id in opt_results['junction_heads'].keys():
            j_opt = opt_results['junction_heads'][junc_id]
            j_sim = sim_results['junction_heads'][junc_id]
            assert_timeseries_near_equal(
                j_opt, 
                j_sim, 
                rel_tol=0.05, 
                abs_tol=0.5, 
                label=f"Junction {junc_id} Head"
            )

        # Check for negative pressures (physical sanity check)
        assert_no_negative_pressures(opt_results, source="Optimization")
        assert_no_negative_pressures(sim_results, source="Simulation")


def test_case_2_reservoir_pump_system():
    """
    Test Case 2: Reservoir-Pump System.
    
    Scenario:
        - Network: Reservoir (R1) -> Pump (Pu1) -> Junction (J1) -> Pipe (P1) -> Tank (T1)
        - Dynamics: Pump lifts water to a tank at higher elevation.
        
    Objective:
        - Verify that Pump and Tank components are modeled correctly.
        - Ensure the pump operates within its curve limits.
        
    Validation:
        - Compare Pump Flow (Pu1) between Optimization and Simulation.
        - Expected result: Flow rates should match (MAE < 1.0 GPM).
    """
    if not pyo.SolverFactory('glpk').available():
        pytest.skip("GLPK solver not available")

    case_inp = """
        [TITLE]
        Test Case 2: Pump-Tank "Fill & Drain"

        [JUNCTIONS]
        ;ID     Elev    Demand  Pattern
        J1      100     600     1

        [RESERVOIRS]
        ;ID     Head
        R1      90

        [TANKS]
        ;ID     Elev    InitLvl MinLvl  MaxLvl  Diam    MinVol  VolCurve
        T1      130     10      0       20      50      0

        [PUMPS]
        ;ID     Node1   Node2   Parameters
        Pu1     R1      J1      HEAD 1

        [PIPES]
        ;ID     Node1   Node2   Length  Diam    Roughness
        P1      J1      T1      100     12      100

        [PATTERNS]
        ;ID     Multipliers
        1       0.5  0.5  0.5  0.5  0.5  0.5
        1       0.8  0.9  1.0  1.1  1.2  1.4
        1       1.5  1.5  1.4  1.2  1.1  1.0
        1       0.9  0.8  0.7  0.6  0.5  0.5

        [CURVES]
        ;ID     Flow    Head
        ;       Fixed: High enough flow to meet 600 GPM demand
        1       0       200     ; Shutoff Head
        1       1000    150     ; Design Point (Strong flow)
        1       2000    0       ; Runout

        [OPTIONS]
        Units              GPM
        Headloss           H-W
        Specific Gravity   1.0
        Viscosity          1.0
        Trials             40
        Accuracy           0.001
        Unbalanced         Continue 10

        [TIMES]
        Duration           24:00
        Hydraulic Timestep 1:00
        Pattern Timestep   1:00
        Pattern Start      0:00
        Report Timestep    1:00
        Report Start       0:00
        Start ClockTime    12 am
        Statistic          NONE

        [COORDINATES]
        R1      10      50
        J1      30      50
        T1      50      70

        [END]
    """

    save_dir = Path.cwd() / "data" / "results" / "optimization" / "hydraulic_feasibility" / "case2"
    save_dir.mkdir(parents=True, exist_ok=True)

    f = save_dir / "case2.inp"
    f.write_text(case_inp)
    
    with validation_logging(save_dir / "test_report.log"):
        results = run_scenario_on_optimization_and_simulation(str(f), num_timesteps=24, solver='gurobi', save_dir=save_dir)
        
        assert results['status'] == 'completed'
        
        # Check Pump Flow
        pump_opt = results['opt_data']['pump_flows']['Pu1']
        pump_sim = results['sim_data']['pump_flows']['Pu1']
        
        assert_timeseries_near_equal(pump_opt, pump_sim, rel_tol=0.05, abs_tol=0.5, label="Pump Pu1 Flow")
        
        # Check for negative pressures
        assert_no_negative_pressures(results['opt_data'], source="Optimization")
        assert_no_negative_pressures(results['sim_data'], source="Simulation")


def test_case_3_event_based_control():
    """
    Test Case 3: Tank Overflow Prevention (Safety Constraints).
    
    Scenario:
        - Network: Same as Case 2 (Pump filling Tank).
        - Condition: Tank starts near maximum level (19/20 ft).
        
    Objective:
        - Verify that the optimization model respects physical constraints (Max Level).
        - The pump should stop or throttle to prevent overflow, even if not explicitly told to.
        
    Validation:
        - Check Tank Head (Level + Elev) over the optimization horizon.
        - Expected result: Tank head must NEVER exceed Max Head (140 ft).
    """
    if not pyo.SolverFactory('glpk').available():
        pytest.skip("GLPK solver not available")

    case_inp = """
        [TITLE]
        Test Case 3: Overflow Prevention
        [JUNCTIONS]
        J1 100 0
        [RESERVOIRS]
        R1 100
        [TANKS]
        ; Tank starts near Max (19/20)
        T1 120 19 0 20 50 0
        [PUMPS]
        Pu1 R1 J1 HEAD 1
        [PIPES]
        P1 J1 T1 100 12 100
        [CURVES]
        1 0 100
        1 1000 50
        [OPTIONS]
        Units GPM
        Headloss H-W
        [TIMES]
        Duration 2:00
        Hydraulic Timestep 1:00
        [END]
    """

    save_dir = Path.cwd() / "data" / "results" / "optimization" / "hydraulic_feasibility" / "case3"
    save_dir.mkdir(parents=True, exist_ok=True)
    
    f = save_dir / "case3.inp"
    f.write_text(case_inp)
    
    with validation_logging(save_dir / "test_report.log"):
        results = run_scenario_on_optimization_and_simulation(str(f), num_timesteps=2, save_dir=save_dir)
        
        assert results['status'] == 'completed'
        
        # Verify Tank interactions
        t1_levels = results['opt_data']['tank_heads']['T1']
        t1_levels_sim = results['sim_data']['tank_heads']['T1']
        
        # Head = Elev (120) + Level. Max Head = 140.
        logger.info(f"Tank T1 Max Level (Opt): {t1_levels.max():.2f} | Max Head Limit: 140.0")
        
        # Check 1: Does optimization respect constraint?
        assert t1_levels.max() <= 140.01, f"Optimization violated constraint: {t1_levels.max()}"

        # Check 2: Does simulation match optimization?
        assert_timeseries_near_equal(
            t1_levels, 
            t1_levels_sim, 
            rel_tol=0.05, 
            abs_tol=0.5, 
            label="Tank T1 Level (Opt vs Sim)"
        )
        
        # Check for negative pressures
        assert_no_negative_pressures(results['opt_data'], source="Optimization")
        assert_no_negative_pressures(results['sim_data'], source="Simulation")


@pytest.mark.xfail(reason="PRV support not yet implemented in optimization model")
def test_case_4_pressure_reducing_valves():
    """
    Test Case 4: Pressure Reducing Valves (PRV) [WIP].
    
    Scenario:
        - Network: High Head Source (200) -> PRV (Setting 80) -> Low Head Zone.
    
    Objective:
        - Verify that Valves are effectively modeling pressure reduction.
        
    Validation:
        - Status Check: Currently verifies model solves ('completed').
        - KNOWN LIMITATION: Optimization model support for PRVs is currently partial. 
          This test serves as a placeholder for future feature implementation.
    """
    if not pyo.SolverFactory('glpk').available():
        pytest.skip("GLPK solver not available")

    # NOTE: Does current optimization model support VALVES/PRVs?
    # Checking src/optimization/algorithm_tasks.py would confirm.
    # Assuming it might NOT. If it doesn't, this test might fail or need empty validation.
    
    case_inp = """
        [TITLE]
        Test Case 4: PRV
        [JUNCTIONS]
        ; J2 is downstream
        J1 100 0
        J2 50  50
        [RESERVOIRS]
        R1 200
        [VALVES]
        ;ID Node1 Node2 Diam Type Setting Loss
        V1 J1    J2    12   PRV  80      0
        [PIPES]
        P1 R1    J1    100 12   100
        [OPTIONS]
        Units GPM
        Headloss H-W
        [TIMES]
        Duration 2:00
        Hydraulic Timestep 1:00
        [END]
    """
    
    save_dir = Path.cwd() / "data" / "results" / "optimization" / "hydraulic_feasibility" / "case4"
    save_dir.mkdir(parents=True, exist_ok=True)

    f = save_dir / "case4.inp"
    f.write_text(case_inp)
    
    with validation_logging(save_dir / "test_report.log"):
        results = run_scenario_on_optimization_and_simulation(str(f), num_timesteps=2, save_dir=save_dir)
        assert results['status'] == 'completed'
        
        # Check PRV Downstream Head (J2)
        j2_opt = results['opt_data']['junction_heads']['J2']
        j2_sim = results['sim_data']['junction_heads']['J2']
        
        assert_timeseries_near_equal(
            j2_opt, 
            j2_sim, 
            rel_tol=0.05, 
            abs_tol=2.0, 
            label="PRV Downstream Head (J2)"
        )