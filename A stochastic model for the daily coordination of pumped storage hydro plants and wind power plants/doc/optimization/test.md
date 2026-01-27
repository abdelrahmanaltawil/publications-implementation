# Integrated Water-Energy Nexus Operation Model (IWEN-OM)

## 1. Model Overview
**Goal:** Optimize the 24-hour operational schedule of a co-located water and energy facility.
**Core Function:** Co-optimizes the dispatch of energy generation, water treatment, and pumped hydro storage to maximize economic efficiency while respecting hydraulic and electrical physics.
**Time Resolution:** Hourly ($\Delta t = 1$ hour).
**Horizon:** 24 hours ($T = 24$).

## 2. System Topology
The system consists of two distinct but coupled buses (networks):

### A. Energy Bus (Electrical Balance)
* **External Grid:** Bidirectional flow (Import/Export) with dynamic pricing.
* **Renewable Source:** Solar/Wind generation (non-dispatchable input).
* **Load:** Fixed electrical demand + Flexible Nexus loads (Pumps, Treatment).
* **Generation:** Energy Recovery Turbines (from Water side).

### B. Water Bus (Mass Balance & Hydraulics)
* **External Water Utility:** Import (raw water) / Export (treated water).
* **Storage:** Upper Reservoir & Lower Reservoir (Pumped Storage).
* **Treatment Plant:** Converts raw water to potable water (Energy consumer).
* **Nexus Units:**
    * **Pumps:** Move water Low $\to$ High (Consume Energy).
    * **Turbines (PATs):** Move water High $\to$ Low (Generate Energy).

---

## 3. Mathematical Formulation (MILP)

### Decision Variables
The "Knobs" the solver can turn for each time step $t$:

* **Binary Variables (On/Off Status):**
    * $u_{pump, i, t} \in \{0, 1\}$: Is Pump $i$ active?
    * $u_{turb, j, t} \in \{0, 1\}$: Is Turbine $j$ active?
    * $u_{treat, t} \in \{0, 1\}$: Is the Treatment Plant active?
* **Continuous Variables (Quantities):**
    * $P_{grid, t}$: Power imported (+) or exported (-) [kW].
    * $Q_{pump, i, t}$: Flow rate through pump $i$ [$m^3/h$].
    * $Q_{turb, j, t}$: Flow rate through turbine $j$ [$m^3/h$].
    * $V_{res, t}$: Volume of water in reservoir [$m^3$].
    * $Q_{treat, t}$: Water treated [$m^3/h$].

### Objective Function
**Minimize Total Net Cost ($Z$) over 24 hours:**

$$
\text{Min } Z = \sum_{t=1}^{24} \left( \underbrace{P_{grid, t} \times Price_{elec, t}}_{\text{Grid Cost/Rev}} + \underbrace{Q_{import, t} \times Price_{water, t}}_{\text{Water Cost}} + \underbrace{\sum C_{start}}_{\text{Start-up Costs}} + \underbrace{C_{ops} \times Q_{treat, t}}_{\text{O\&M Cost}} \right)
$$

*Note: If $P_{grid}$ is negative (export), it reduces the cost (revenue).*

---

## 4. Constraints & Physics

### A. The Coupling Constraints (The Nexus)
*Derived from Thomas & Sela (2024) - Linearization*
Instead of non-linear curves ($Power = \rho g Q H \eta$), we use piece-wise linear approximation:
1.  **Pump Power:** $P_{pump, i, t} = \alpha_i \times Q_{pump, i, t} + \beta_i \times u_{pump, i, t}$
2.  **Turbine Power:** $P_{turb, j, t} = \gamma_j \times Q_{turb, j, t} - \delta_j \times u_{turb, j, t}$
3.  **Flow Limits:** $Q_{min} \times u_{t} \le Q_{t} \le Q_{max} \times u_{t}$
    *(Ensures flow is zero if the unit is Off, and within hydraulic limits if On).*

### B. Energy Balance Constraints
*Derived from Giglio et al. (PyPSA style)*
At every time step $t$:
$$
P_{grid, t} + P_{renewables, t} + \sum P_{turb, t} = \text{Load}_{fixed, t} + \sum P_{pump, t} + P_{treatment, t}
$$

### C. Water Mass Balance (Storage)
At every time step $t$:
$$
V_{res, t} = V_{res, t-1} + \sum Q_{pump, t} - \sum Q_{turb, t} + Q_{inflow, t} - Q_{outflow, t}
$$
* **Constraint:** $V_{min} \le V_{res, t} \le V_{max}$
* **Cyclic Constraint:** $V_{res, 24} \ge V_{res, 0}$ (The tank must not be empty at the end of the day).

### D. Treatment & Import Constraints
* **Treatment Physics:** $P_{treatment, t} = \text{SpecificEnergy} \times Q_{treat, t}$
* **Demand Satisfaction:** $\sum Q_{treated, t} \ge \text{DailyWaterDemand}$ (Allows shifting treatment to cheap energy hours).